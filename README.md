<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Fiscal Reform Readiness Diagnostic – README

This project is a **questionnaire‑based diagnostic tool** that helps French businesses and accountants assess their readiness for the 2026–2027 electronic invoicing (e‑invoicing) and e‑reporting reform.[^1][^2]

The logic of the diagnostic is described in a machine‑readable JSON file (`diagnostic_mapping.json`), designed to be consumed by a Python/FastAPI backend or any other web service.[^3][^4]

***

## What the tool does

- Asks a short series of structured questions about:
    - company profile (size, sector, VAT status, invoice volumes)[^2][^5]
    - invoicing flows (B2B/B2C, domestic vs. cross‑border)[^6][^3]
    - current invoicing tools and formats (paper, PDF, structured e‑invoice)[^4][^7]
    - data quality (customer SIREN, delivery address, nature of operation, VAT breakdown)[^8][^9]
    - platform and e‑reporting setup (PDP/public portal, reception, issuance, e‑reporting)[^10][^1][^3]
    - internal organisation (processes, team awareness, tests, procedures).[^11][^6]
- Computes a **readiness score** and maps it to one of three levels:
    - `en_retard` – behind schedule on key mandatory foundations.
    - `en_chemin` – on the way, but with several open points.
    - `pret` – main requirements covered, only fine‑tuning and tests left.[^5][^7]
- Highlights **blocking issues** (e.g. no platform chosen, no reception capability, incompatible tool, missing customer SIREN, purely paper/manual process, missing e‑reporting for relevant flows).[^3][^4][^8]
- Returns a small set of **prioritised actions** (max 3), phrased as practical next steps (choose a platform, complete SIREN collection, configure reception, schedule pilot tests, etc.).[^12][^6]

***

## Core concepts encoded in the JSON

### Questions

The `questions` section describes each question with:

- `field`: technical name used in code (e.g. `company_size`, `platform_choice`).
- `type`: `single_choice`, `multi_choice`, or `scale`.
- `answers`: each possible answer has:
    - `score_delta`: contribution to the global maturity score.
    - `flags_add` / `flags_remove`: internal tags used by rules (e.g. `tool_compatible`, `siren_missing`).
    - `actions_add`: IDs of suggested actions to add to the final recommendations.
    - `notes`: optional comment for maintainers.[^4][^3]

Some questions also have a `condition` field (simple boolean expression on flags) so they are only evaluated when relevant (for example, e‑reporting questions only when B2C or cross‑border flows exist).[^6][^3]

### Blocking rules

The `blocking_rules` section defines conditions that **force at least** the `en_retard` level, regardless of the numeric score, for example:

- no platform selected,
- no reception capability configured,
- incompatible/unknown tool,
- missing customer SIREN,
- only paper/manual invoicing,
- missing e‑reporting while B2C or foreign flows exist.[^8][^3][^6]

These rules implement the idea that some prerequisites are non‑negotiable before September 2026.[^1][^2]

### Score bands and adjustments

- `score_bands` defines how the aggregated score maps to the three readiness levels:
    - `en_retard`: score ≤ 4
    - `en_chemin`: 5–11
    - `pret`: ≥ 12
- `adjustment_rules` apply final tweaks, for example:
    - downgrade from `pret` to `en_chemin` if no pilot tests were done,
    - downgrade if no platform has actually been chosen yet,
    - downgrade if reception is not confirmed as ready.[^7][^5]

This ensures the final level reflects both the numeric score and a few critical qualitative checks.[^3][^4]

### Actions catalog

The `actions_catalog` maps action IDs (e.g. `select_platform`, `configure_ereporting`) to short human‑readable sentences. These sentences are meant to be displayed to the end user as next steps.[^12][^6]

***

## Typical backend usage (high‑level)

1. **Load the JSON mapping** at startup.
2. **Collect answers** from the user (web form / API payload) using the `field` names.
3. For each question:
    - look up the question in `questions`,
    - get the associated answer object,
    - accumulate `score_delta`,
    - maintain a set of flags,
    - accumulate `actions_add` (deduplicated, truncated to 3–5 items).[^4][^3]
4. **Compute provisional level** from `score_bands`.
5. Apply `blocking_rules` and `adjustment_rules` to derive the **final level**.
6. Build a response containing:
    - `score`,
    - `level` (`en_retard` / `en_chemin` / `pret`),
    - `flags` (debug/analytics),
    - `top_actions` (short actionable recommendations).[^5][^6]

***

## What this project does *not* do

- It does **not generate invoices** or connect directly to PDP/PPF platforms.
- It does not replace legal or tax advice; it provides a structured, high‑level readiness assessment that should be reviewed with a qualified accountant or tax expert.[^7][^6]

***

If you’d like, I can now draft a **Python example** (pure function or FastAPI endpoint) showing exactly how to load `diagnostic_mapping.json`, process user answers, and return the computed diagnostic.

<div align="center">⁂</div>

[^1]: https://entreprendre.service-public.gouv.fr/actualites/A15683

[^2]: https://www.pennylane.com/fr/fiches-pratiques/facture-electronique/facturation-electronique-dates-cles-et-calendrier

[^3]: https://www.francenum.gouv.fr/guides-et-conseils/pilotage-de-lentreprise/dematerialisation-des-documents/facturation-1

[^4]: https://www.pennylane.com/fr/fiches-pratiques/facture-electronique/reforme-facturation-electronique

[^5]: https://www.kanta.fr/articles/calendrier-de-facture-electronique-2026-2027-les-dates-cles-a-retenir

[^6]: https://bpifrance-creation.fr/encyclopedie/gerer-lentreprise/gestion-financiere-comptable/facturation-electronique-obligation-e

[^7]: https://www.qweeby.fr/les-obligations/il-faut-viser-sept-26-et-pas-27

[^8]: https://www.fiducial.fr/facturation-electronique/faq/mentions-obligatoires-facture-electronique

[^9]: https://www.cerfrance.fr/actualites/les-nouvelles-mentions-obligatoires-sur-vos-factures

[^10]: https://www.portail-autoentrepreneur.fr/academie/gestion-auto-entreprise/facturation/facturation-electronique-2026

[^11]: https://formalites.lesechos.fr/actualites/comment-preparer-son-entreprise-a-l-e-invoicing-obligatoire-d-ici-2026/

[^12]: https://www.cegid.com/fr/blog/facturation-electronique-2024-zoom-sur-le-e-reporting/

