"""Regex-based structured financial metric extraction.

Carried over unchanged from the original notebook (sec_rag_assistant.ipynb, Section 6).
"""
import re

# NOTE: filing text wraps across multiple lines (indented triple-quoted strings),
# so every gap between tokens uses \s+ rather than a literal space -- a literal
# " " would only match text that happens to sit on one physical line.
METRIC_PATTERNS = {
    "revenue": r"(?:[Tt]otal revenue|[Nn]et sales)(?:\s+for fiscal year \d{4})?\s+(?:was|were)\s+\$([\d,.]+)\s+(million|billion)",
    "prior_revenue": r"(?:compared to|from)\s+\$([\d,.]+)\s+(million|billion)\s+in fiscal year \d{4}",
    "net_income": r"[Nn]et income(?:\s+for fiscal year \d{4})?(?:\s+was|\s+declined to)\s+\$([\d,.]+)\s+million",
    "eps": r"[Dd]iluted earnings per share was \$([\d.]+)",
}


def _to_number(value, unit=None):
    num = float(value.replace(",", ""))
    if unit == "billion":
        num *= 1000  # normalize to millions
    return num


def extract_financial_metrics(filing):
    text = filing["text"]
    metrics = {"company": filing["company"], "ticker": filing["ticker"], "fiscal_year": filing["fiscal_year"]}

    rev_matches = re.findall(METRIC_PATTERNS["revenue"], text)
    if rev_matches:
        value, unit = rev_matches[0]
        metrics["revenue_musd"] = _to_number(value, unit)

    prior_rev_matches = re.findall(METRIC_PATTERNS["prior_revenue"], text)
    if prior_rev_matches and "revenue_musd" in metrics:
        prev_value, prev_unit = prior_rev_matches[0]
        metrics["prior_revenue_musd"] = _to_number(prev_value, prev_unit)
        metrics["revenue_growth_pct"] = round(
            (metrics["revenue_musd"] - metrics["prior_revenue_musd"]) / metrics["prior_revenue_musd"] * 100, 1
        )

    ni_matches = re.findall(METRIC_PATTERNS["net_income"], text)
    if ni_matches:
        metrics["net_income_musd"] = _to_number(ni_matches[0])

    eps_matches = re.findall(METRIC_PATTERNS["eps"], text)
    if eps_matches:
        metrics["diluted_eps"] = float(eps_matches[0])

    return metrics
