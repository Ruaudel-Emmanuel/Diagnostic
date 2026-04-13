from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI
from pydantic import BaseModel, Field

from diagnostic_engine import compute_diagnostic

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="fiscal-reform-readiness-api",
    version="1.0.0"
)

origins = [
    "https://rennesdev.fr",
    "https://www.rennesdev.fr",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AnswerValue = Union[str, int, List[str]]


class DiagnosticRequest(BaseModel):
    answers: Dict[str, AnswerValue] = Field(
        ...,
        description="Dictionary of questionnaire answers keyed by question id, e.g. Q01, Q05, Q15.",
        examples=[
            {
                "Q01": "pme",
                "Q03": "reel_normal",
                "Q05": ["b2b_france", "b2c_france"],
                "Q08": "logiciel_facturation",
                "Q09": "pdf_email",
                "Q10": "update_announced",
                "Q12": "partial",
                "Q15": "evaluating",
                "Q16B": "unknown",
                "Q16C": "unknown",
                "Q17": "planned",
                "Q18": "informed_lightly",
                "Q19A": "in_progress",
                "Q19B": "in_progress",
                "Q20": 3
            }
        ],
    )
    max_actions: int = Field(3, ge=1, le=10, description="Maximum number of recommended actions returned.")


class DiagnosticResponse(BaseModel):
    score: int
    level: str
    flags: List[str]
    applied_questions: List[str]
    ignored_questions: List[str]
    triggered_blocking_rules: List[str]
    applied_adjustment_rules: List[str]
    action_ids: List[str]
    top_action_ids: List[str]
    top_actions: List[str]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="fiscal-reform-readiness-api",
        version="1.0.0",
    )


@app.post("/diagnostic", response_model=DiagnosticResponse, tags=["diagnostic"])
def create_diagnostic(payload: DiagnosticRequest) -> DiagnosticResponse:
    result = compute_diagnostic(payload.answers, max_actions=payload.max_actions)
    return DiagnosticResponse(**result)


@app.get("/", tags=["system"])
def root() -> Dict[str, Any]:
    return {
        "message": "Fiscal Reform Readiness API is running.",
        "docs": "/docs",
        "health": "/health",
        "diagnostic": "/diagnostic",
    }


# Run locally with:
# uvicorn fastapi_diagnostic_app:app --host 0.0.0.0 --port 8000 --reload
