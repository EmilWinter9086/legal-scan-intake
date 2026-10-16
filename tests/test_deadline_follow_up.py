from datetime import date

from legal_intake_service.intake_service import (
    FollowUpState,
    MatterIntake,
    process_intake,
)


class RecordingOcr:
    def __init__(self) -> None:
        self.request_id = ""

    def start_ocr(self, pdf: str, request_id: str, lang: str = "eng") -> str:
        self.request_id = request_id
        return "job-legal-42"


def test_unsigned_matter_near_deadline_is_flagged_for_follow_up() -> None:
    ocr = RecordingOcr()
    request = MatterIntake(
        matter_id="rivera-2026-014",
        scanned_pdf="https://documents.example.com/rivera-scan.pdf",
        response_deadline=date(2026, 9, 8),
        signed_document_delivered=False,
    )

    result = process_intake(request, ocr, today=date(2026, 9, 5))  # type: ignore[arg-type]

    assert result.follow_up is FollowUpState.FOLLOW_UP
    assert result.days_until_deadline == 3
    assert result.ocr_job_id == "job-legal-42"
    assert ocr.request_id == "matter-rivera-2026-014-ocr"


def test_delivered_document_closes_follow_up_even_when_overdue() -> None:
    ocr = RecordingOcr()
    request = MatterIntake(
        matter_id="chen-2026-009",
        scanned_pdf="https://documents.example.com/chen-scan.pdf",
        response_deadline=date(2026, 9, 1),
        signed_document_delivered=True,
    )

    result = process_intake(request, ocr, today=date(2026, 9, 5))  # type: ignore[arg-type]

    assert result.follow_up is FollowUpState.COMPLETE
