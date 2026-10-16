from __future__ import annotations

from datetime import date
from enum import StrEnum

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .infrai_ocr import InfraiError, InfraiOcrClient


class FollowUpState(StrEnum):
    COMPLETE = "complete"
    MONITOR = "monitor"
    FOLLOW_UP = "follow_up"


class MatterIntake(BaseModel):
    matter_id: str = Field(min_length=1)
    scanned_pdf: str = Field(min_length=1)
    response_deadline: date
    signed_document_delivered: bool = False
    ocr_language: str = "eng"


class IntakeResult(BaseModel):
    matter_id: str
    ocr_job_id: str
    follow_up: FollowUpState
    days_until_deadline: int


def decide_follow_up(deadline: date, delivered: bool, today: date) -> FollowUpState:
    if delivered:
        return FollowUpState.COMPLETE
    if (deadline - today).days <= 3:
        return FollowUpState.FOLLOW_UP
    return FollowUpState.MONITOR


def process_intake(request: MatterIntake, ocr: InfraiOcrClient, today: date) -> IntakeResult:
    job_id = ocr.start_ocr(
        pdf=request.scanned_pdf,
        request_id=f"matter-{request.matter_id}-ocr",
        lang=request.ocr_language,
    )
    days = (request.response_deadline - today).days
    return IntakeResult(
        matter_id=request.matter_id,
        ocr_job_id=job_id,
        follow_up=decide_follow_up(request.response_deadline, request.signed_document_delivered, today),
        days_until_deadline=days,
    )


app = FastAPI(title="Legal scan intake")


@app.post("/matters/intake", response_model=IntakeResult)
def intake(request: MatterIntake) -> IntakeResult:
    try:
        return process_intake(request, InfraiOcrClient(), date.today())
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=client_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
