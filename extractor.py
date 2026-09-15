# extractor.py
"""
Data extraction engine for @FOREXEXPERTTRADERBOT.
Extracts seven key fields from RFP / tender / project documents.
"""

import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class ExtractedData:
    requirements: List[str] = field(default_factory=list)
    submission_deadline: str = "Not Found"
    required_documents: List[str] = field(default_factory=list)
    eligibility_criteria: List[str] = field(default_factory=list)
    evaluation_criteria: List[str] = field(default_factory=list)
    budget_information: str = "Not Found"
    important_clauses: List[str] = field(default_factory=list)


class TenderExtractor:
    """Extracts key RFP/tender fields from raw document text."""

    SECTION_MAP = {
        "requirements": [
            "requirement", "requirements", "scope of work",
            "specifications", "technical specifications",
        ],
        "required_documents": [
            "required document", "required documents",
            "mandatory document", "mandatory documents",
            "submission documents", "documents required",
        ],
        "eligibility_criteria": [
            "eligibility", "eligibility criteria", "qualification",
            "qualifications", "eligible",
        ],
        "evaluation_criteria": [
            "evaluation criteria", "evaluation", "award criteria",
            "scoring", "scoring criteria",
        ],
    }

    DEADLINE_PATTERNS = [
        r"(?:submission\s+)?deadline[:\s]+([^\n\r]+)",
        r"due\s+date[:\s]+([^\n\r]+)",
        r"submission\s+date[:\s]+([^\n\r]+)",
        r"closing\s+date[:\s]+([^\n\r]+)",
    ]

    BUDGET_PATTERNS = [
        r"budget[:\s]+([^\n\r]+)",
        r"total\s+contract\s+value[:\s]+([^\n\r]+)",
        r"estimated\s+value[:\s]+([^\n\r]+)",
        r"(?:USD|EUR|GBP|\$|€|£)\s*([0-9][0-9,.\s]*(?:million|billion|k)?)",
    ]

    def __init__(self, text: str):
        self.text = text or ""
        self.lower_text = self.text.lower()
        self.data = ExtractedData()

    def extract_all(self) -> ExtractedData:
        self._extract_deadline()
        self._extract_budget()
        self._extract_list_sections()
        self._extract_clauses()
        return self.data

    def _extract_deadline(self):
        for pattern in self.DEADLINE_PATTERNS:
            match = re.search(pattern, self.lower_text)
            if match:
                start, end = match.start(1), match.end(1)
                self.data.submission_deadline = self.text[start:end].strip()
                return

    def _extract_budget(self):
        for pattern in self.BUDGET_PATTERNS:
            match = re.search(pattern, self.lower_text)
            if match:
                start, end = match.start(0), match.end(0)
                self.data.budget_information = self.text[start:end].strip()
                return

    def _extract_list_sections(self):
        lines = self.text.split("\n")

        for key, keywords in self.SECTION_MAP.items():
            start_idx = -1
            for i, line in enumerate(lines):
                stripped = line.strip()
                if not stripped or len(stripped) > 100:
                    continue
                if any(kw in stripped.lower() for kw in keywords):
                    start_idx = i
                    break

            if start_idx == -1:
                continue

            items: List[str] = []
            for line in lines[start_idx + 1:]:
                stripped = line.strip()
                if not stripped:
                    if items:
                        break
                    continue

                if (
                    len(stripped) > 5
                    and stripped.isupper()
                    and not stripped.startswith(("-", "*", "•"))
                ):
                    break

                clean = re.sub(
                    r"^[\s\-\*\u2022\u25CF\u25AA\d\.\)]+", "", stripped
                ).strip()
                if clean and len(clean) > 2:
                    items.append(clean)

                if len(items) >= 30:
                    break

            if items:
                setattr(self.data, key, items)

    def _extract_clauses(self):
        clauses: List[str] = []
        for line in self.text.split("\n"):
            if re.search(
                r"(?:clause|article|section)\s+\d+",
                line,
                re.IGNORECASE,
            ):
                stripped = line.strip()
                if stripped:
                    clauses.append(stripped)
            if len(clauses) >= 5:
                break
        self.data.important_clauses = clauses
