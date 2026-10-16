import base64
from datetime import date, timedelta

from legal_intake_service.infrai_ocr import InfraiOcrClient
from legal_intake_service.intake_service import MatterIntake, process_intake


def sample_pdf() -> str:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length 62 >>\nstream\nBT /F1 18 Tf 72 700 Td (Signed filing received for Rivera) Tj ET\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return base64.b64encode(pdf).decode("ascii")


def main() -> None:
    request = MatterIntake(
        matter_id="rivera-2026-014",
        scanned_pdf=sample_pdf(),
        response_deadline=date.today() + timedelta(days=2),
        signed_document_delivered=False,
    )
    result = process_intake(request, InfraiOcrClient(), date.today())
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
