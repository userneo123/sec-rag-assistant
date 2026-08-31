"""Synthetic 10-K excerpts for 3 companies, used until real EDGAR ingestion is added."""

SEC_FILINGS = [
    {
        "company": "Aster Robotics Inc.",
        "ticker": "ASTR",
        "filing_type": "10-K",
        "fiscal_year": 2025,
        "text": """
        Item 7. Management's Discussion and Analysis of Financial Condition and Results of Operations.

        Total revenue for fiscal year 2025 was $412.6 million, an increase of 18% compared to
        $349.7 million in fiscal year 2024. This growth was primarily driven by increased demand
        for our warehouse automation robotics platform and a 24% increase in recurring software
        subscription revenue.

        Net income for fiscal year 2025 was $38.2 million, compared to net income of $21.4 million
        in fiscal year 2024. Diluted earnings per share was $0.94, compared to $0.53 in the prior year.

        Research and development expenses increased to $86.1 million in fiscal 2025 from
        $71.3 million in fiscal 2024, reflecting continued investment in next-generation
        perception and navigation systems.

        As of the end of fiscal year 2025, the Company held $210.4 million in cash and cash
        equivalents, with total liabilities of $180.9 million.

        Item 1A. Risk Factors.

        Our business is subject to risks related to supply chain disruptions, particularly for
        semiconductor components used in our robotics hardware. A sustained shortage of these
        components could materially delay product shipments and adversely affect revenue.
        We also face risks related to increasing competition in the warehouse automation market
        from both established industrial automation companies and new entrants.
        """,
    },
    {
        "company": "Bluepeak Analytics Corp.",
        "ticker": "BPKA",
        "filing_type": "10-K",
        "fiscal_year": 2025,
        "text": """
        Item 7. Management's Discussion and Analysis of Financial Condition and Results of Operations.

        Total revenue was $1.28 billion for fiscal year 2025, up 9% year-over-year from
        $1.17 billion in fiscal year 2024. Subscription revenue represented 82% of total revenue.

        Net income declined to $94.3 million in fiscal year 2025, down from $118.6 million in
        fiscal year 2024, primarily due to a one-time restructuring charge of $46.2 million
        related to the consolidation of our data center footprint.

        Diluted earnings per share was $1.12 for fiscal 2025, compared to $1.41 for fiscal 2024.

        Gross margin was 74.2%, compared to 75.8% in the prior fiscal year, reflecting higher
        cloud infrastructure costs.

        Item 1A. Risk Factors.

        We rely on a small number of third-party cloud infrastructure providers to deliver our
        services. Any significant interruption in these services could harm our reputation and
        operating results. Additionally, our international operations expose us to foreign
        currency exchange rate fluctuations that could adversely affect reported revenue.
        """,
    },
    {
        "company": "Coral Harbor Foods Inc.",
        "ticker": "CHFI",
        "filing_type": "10-K",
        "fiscal_year": 2025,
        "text": """
        Item 7. Management's Discussion and Analysis of Financial Condition and Results of Operations.

        Net sales for fiscal year 2025 were $2.94 billion, a decrease of 3% compared to
        $3.03 billion in fiscal year 2024, primarily due to divestiture of our frozen foods
        segment in the second quarter.

        Net income for fiscal year 2025 was $187.5 million, compared to $203.1 million in the
        prior fiscal year. Diluted earnings per share was $2.31, compared to $2.44 in fiscal 2024.

        The Company returned $150.0 million to shareholders through dividends and repurchased
        $75.0 million of common stock during fiscal year 2025.

        Item 1A. Risk Factors.

        Our results are sensitive to fluctuations in commodity input costs, including wheat,
        dairy, and packaging materials. Prolonged inflation in these input costs without
        corresponding pricing actions could compress margins. We are also subject to evolving
        food safety regulations across the jurisdictions in which we operate.
        """,
    },
]
