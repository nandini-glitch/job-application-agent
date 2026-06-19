from pypdf import PdfReader


def extract_resume_text(pdf_path: str) -> str:
    """
    Extracts all text content from a resume PDF.

    Args:
        pdf_path: Path to the resume PDF file.

    Returns:
        Full extracted text as a single string.
    """
    reader = PdfReader(pdf_path)
    text = ""

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

    return text.strip()


# Quick test
if __name__ == "__main__":
    path = input("Enter path to your resume PDF: ")
    resume_text = extract_resume_text(path)
    print("\n--- Extracted Resume Text ---\n")
    print(resume_text)
    print(f"\n\nTotal characters extracted: {len(resume_text)}")