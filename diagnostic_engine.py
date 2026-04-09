from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set, Union

try:
    from diagnostic_mapping import DIAGNOSTIC_MAPPING as DEFAULT_MAPPING
except Exception:
    DEFAULT_MAPPING = None


JsonLike = Dict[str, Any]


def load_mapping(source: Union[str, Path, Dict[str, Any], None] = None) -> JsonLike:
    if isinstance(source, dict):
        return source
    if source is None:
        if DEFAULT_MAPPING is not None:
            return DEFAULT_MAPPING
        raise ValueError("No mapping source provided and DEFAULT_MAPPING is unavailable.")

    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Mapping file not found: {path}")

    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if path.suffix.lower() == ".py":
        namespace: Dict[str, Any] = {}
        exec(path.read_text(encoding="utf-8"), namespace)
        if "DIAGNOSTIC_MAPPING" not in namespace:
            raise ValueError("Python mapping file must define DIAGNOSTIC_MAPPING")
        return namespace["DIAGNOSTIC_MAPPING"]

    raise ValueError("Unsupported mapping format. Use .json, .py, or pass a dict.")


def _truthy_flag_expr(flags: Set[str], expr: str, current_level: str | None = None) -> bool:
    """
    Évalue une petite expression booléenne basée sur les flags et current_level,
    sans laisser des noms nus comme platform_missing provoquer un NameError.
    Syntaxe supportée : 'flag == true', 'flag == false', 'and', 'or'.
    """

    expr = expr.strip()

    # Gestion simple de current_level si présent dans l'expression
    if "current_level" in expr:
        # On ne supporte que des tests du type current_level == 'pret'
        if f"current_level == 'pret'" in expr or f'current_level == "pret"' in expr:
            return current_level == "pret"
        if f"current_level == 'en_chemin'" in expr or f'current_level == "en_chemin"' in expr:
            return current_level == "en_chemin"
        if f"current_level == 'en_retard'" in expr or f'current_level == "en_retard"' in expr:
            return current_level == "en_retard"
        # Si autre chose, on n'essaie pas d'interpréter
        return False

    # Gestion des cas simples de type: "flag == true", "flag == false"
    # et combinaisons avec "and"/"or"

    # On découpe d'abord sur ' or '
    or_parts = [p.strip() for p in expr.split(" or ")]

    def eval_and_part(part: str) -> bool:
        # Exemple: "platform_missing == true and tool_manual == true"
        and_parts = [p.strip() for p in part.split(" and ")]
        for cond in and_parts:
            if "==" not in cond:
                return False
            name, value = [x.strip() for x in cond.split("==", 1)]
            # value doit être true/false
            value = value.lower()
            if value == "true":
                expected = True
            elif value == "false":
                expected = False
            else:
                return False
            # Vérifie si le flag est présent dans l'ensemble
            actual = (name in flags)
            if actual != expected:
                return False
        return True

    # L'expression entière est vraie si au moins une partie reliée par 'or' est vraie
    return any(eval_and_part(p) for p in or_parts)


def _compute_base_level(score: int, score_bands: Dict[str, Dict[str, int]]) -> str:
    for level, band in score_bands.items():
        if band["min"] <= score <= band["max"]:
            return level
    raise ValueError(f"No score band matched score={score}")


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def compute_diagnostic(
    answers: Dict[str, Any],
    mapping_source: Union[str, Path, Dict[str, Any], None] = None,
    max_actions: int = 3,
) -> Dict[str, Any]:
    mapping = load_mapping(mapping_source)
    questions = mapping["questions"]
    score_bands = mapping["score_bands"]
    blocking_rules = mapping.get("blocking_rules", [])
    adjustment_rules = mapping.get("adjustment_rules", [])
    actions_catalog = mapping.get("actions_catalog", {})

    score = 0
    flags: Set[str] = set()
    raw_action_ids: List[str] = []
    applied_questions: List[str] = []
    ignored_questions: List[str] = []

    for question_id, question_def in questions.items():
        if question_id not in answers:
            continue

        condition = question_def.get("condition")
        if condition and not _truthy_flag_expr(flags, condition):
            ignored_questions.append(question_id)
            continue

        answer_value = answers[question_id]
        question_type = question_def["type"]
        answer_defs = question_def["answers"]

        if question_type == "multi_choice":
            if not isinstance(answer_value, list):
                raise ValueError(f"{question_id} expects a list of answers")
            for single_value in answer_value:
                if single_value not in answer_defs:
                    raise ValueError(f"Invalid answer '{single_value}' for {question_id}")
                rule = answer_defs[single_value]
                score += int(rule.get("score_delta", 0))
                flags.update(rule.get("flags_add", []))
                for f in rule.get("flags_remove", []):
                    flags.discard(f)
                raw_action_ids.extend(rule.get("actions_add", []))
            applied_questions.append(question_id)
            continue

        key = str(answer_value)
        if key not in answer_defs:
            raise ValueError(f"Invalid answer '{answer_value}' for {question_id}")

        rule = answer_defs[key]
        score += int(rule.get("score_delta", 0))
        flags.update(rule.get("flags_add", []))
        for f in rule.get("flags_remove", []):
            flags.discard(f)
        raw_action_ids.extend(rule.get("actions_add", []))
        applied_questions.append(question_id)

    level = _compute_base_level(score, score_bands)
    triggered_blocking_rules: List[str] = []
    for rule in blocking_rules:
        if _truthy_flag_expr(flags, rule["when"], current_level=level):
            triggered_blocking_rules.append(rule["id"])
            if rule.get("force_level_min") == "en_retard":
                level = "en_retard"

    applied_adjustment_rules: List[str] = []
    for rule in adjustment_rules:
        if _truthy_flag_expr(flags, rule["when"], current_level=level):
            level = rule["set_level"]
            applied_adjustment_rules.append(rule["id"])

    action_ids = _dedupe_keep_order(raw_action_ids)
    top_action_ids = action_ids[:max_actions]
    top_actions = [actions_catalog.get(action_id, action_id) for action_id in top_action_ids]

    return {
        "score": score,
        "level": level,
        "flags": sorted(flags),
        "applied_questions": applied_questions,
        "ignored_questions": ignored_questions,
        "triggered_blocking_rules": triggered_blocking_rules,
        "applied_adjustment_rules": applied_adjustment_rules,
        "action_ids": action_ids,
        "top_action_ids": top_action_ids,
        "top_actions": top_actions,
    }


if __name__ == "__main__":
    example_answers = {
        "Q01": "pme",
        "Q03": "reel_normal",
        "Q05": ["b2b_france", "b2c_france"],
        "Q08": "excel_word",
        "Q09": "pdf_email",
        "Q10": "unknown",
        "Q12": "partial",
        "Q15": "evaluating",
        "Q16B": "unknown",
        "Q16C": "unknown",
        "Q17": "no",
        "Q18": "informed_lightly",
        "Q19A": "in_progress",
        "Q19B": "no",
        "Q20": 2,
    }

    result = compute_diagnostic(example_answers)
    print(json.dumps(result, ensure_ascii=False, indent=2))
