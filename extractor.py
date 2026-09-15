# extractor.py
import re
from dataclasses import dataclass, field

@dataclass
class ExtractedData:
    requirements: list = field(default_factory=list)
    submission_deadline: str = "Not Found"
    required_documents: list = field(default_factory=list)
    eligibility_criteria: list = field(default_factory=list)
    evaluation_criteria: list = field(default_factory=list)
    budget_information: str = "Not Found"
    important_clauses: list = field(default_factory=list)

class TenderExtractor:
    def __init__(self, text: str):
        self.text = text
        self.lower_text = text.lower()
        self.data = ExtractedData()

    def extract_all(self):
        self._extract_deadline()
        self._extract_budget()
        self._extract_list_sections()
        self._extract_clauses()
        return self.data

    def _extract_deadline(self):
        # Looks for patterns like "Deadline: 15 Jan 2025" or "Submission Due Date: ..."
        patterns = [
            r"(?:submission\s+)?deadline[:\s]+([^\n\r]+)",
            r"due\s+date[:\s]+([^\n\r]+)",
            r"submission\s+date[:\s]+([^\n\r]+)"
        ]
        for pattern in patterns:
            match = re.search(pattern, self.lower_text)
            if match:
                # Get the actual string from the original text to preserve casing
                start = match.start(1)
                end = match.end(1)
                self.data.submission_deadline = self.text[start:end].strip()
                break

    def _extract_budget(self):
        # Looks for currency or "budget" keyword
        patterns = [
            r"budget[:\s]+([^\n\r]+)",
            r"total\s+contract\s+value[:\s]+([^\n\r]+)",
            r"(?:USD|EUR|GBP|\$|€|£)\s*([0-9,.]+(?:\s*(?:million|billion|k))?)"
        ]
        for pattern in patterns:
            match = re.search(pattern, self.lower_text)
            if match:
                start = match.start(1)
                end = match.end(1)
                # If regex matched currency symbol, include it
                if pattern.startswith("(?:"):
                    start = match.start(0)
                    end = match.end(0)
                self.data.budget_information = self.text[start:end].strip()
                break

    def _extract_list_sections(self):
        # Map keywords to the data fields
        section_map = {
            "requirements": ["requirement", "scope of work", "specifications"],
            "required_documents": ["required document", "mandatory document", "submission documents"],
            "eligibility_criteria": ["eligibility", "qualification", "eligible"],
            "evaluation_criteria": ["evaluation criteria", "award criteria", "scoring"]
        }

        # Split text into lines for easier processing
        lines = self.text.split('\n')
        
        for key, keywords in section_map.items():
            # Find the line index where the section starts
            start_idx = -1
            for i, line in enumerate(lines):
                if any(kw in line.lower() for kw in keywords):
                    # Ensure it's a heading and not just a mention
                    if len(line.strip()) < 100:
                        start_idx = i
                        break
            
            if start_idx != -1:
                # Collect items until we hit a blank line or another major heading
                items = []
                for line in lines[start_idx+1:]:
                    stripped = line.strip()
                    if not stripped:
                        break
                    # Stop if we hit what looks like another section header (all caps or short)
                    if len(stripped) > 5 and stripped.isupper():
                        break
                    # Clean up bullet points
                    clean_line = re.sub(r'^[\s\-\*\u2022\d\.]+', '', stripped).strip()
                    if clean_line:
                        items.append(clean_line)
                
                if items:
                    setattr(self.data, key, items)

    def _extract_clauses(self):
        # Finds lines with "Clause X" or "Article Y"
        clauses = []
        for line in self.text.split('\n'):
            if re.search(r'(?:clause|article|section)\s+\d+', line, re.IGNORECASE):
                clauses.append(line.strip())
        if clauses:
            self.data.important_clauses = clauses[:5] # Limit to top 5 for brevity
