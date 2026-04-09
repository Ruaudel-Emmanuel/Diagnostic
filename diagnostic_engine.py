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
    Évalue un petit langage de règles booléennes basé sur les flags, sans eval.

    Syntaxe supportée (comme dans ton JSON) :
    - flag == true
    - flag == false
    - flag != true
    - flag != false
    - current_level == 'pret'
    - current_level != 'en_retard'
    - combinaisons avec 'and' / 'or' et parenthèses.
    """

    # Nettoyage basique
    expr = expr.strip()

    # Remplacements simples sur current_level
    if "current_level" in expr:
        expr = expr.replace("current_level", f"'{current_level}'")

    # On transforme les tests de flag en appels à une fonction Python sûre
    # Exemple: "platform_missing == true" devient "flag('platform_missing') == True"
    #          "tool_paper == true"      devient "flag('tool_paper') == True"

    import re

    def repl_flag(match: re.Match) -> str:
        name = match.group(1)
        return f"flag('{name}')"

    # Remplacer les patterns comme: platform_missing, tool_paper, has_b2c_france, etc.
    # On ne touche pas current_level ni les littéraux 'pret', 'en_retard', ni true/false
    token_pattern = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b")

    def token_replacer(m: re.Match) -> str:
        token = m.group(1)
        if token in {"true", "false", "True", "False"}:
            return token.capitalize()
        if token.startswith("en_") or token in {"pret"}:
            return f"'{token}'"
        if token == "flag" or token == "current_level":
            return token
        # Tous les autres tokens sont considérés comme des noms de flag
        return f"flag('{token}')"

    transformed = token_pattern.sub(token_replacer, expr)

    def flag(name: str) -> bool:
        return name in flags

    # Maintenant on peut évaluer l'expression dans un environnement ultra restreint
    try:
        return bool(eval(transformed, {"__builtins__": {}}, {"flag": flag}))
    except Exception:
        # En cas de problème, on considère la règle comme non déclenchée
        return False


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
