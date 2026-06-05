import os
import sqlite3

import pandas as pd
from scipy import stats

DB_PATH = "teiko.db"
OUTPUT_DIR = "outputs"

os.makedirs(OUTPUT_DIR, exist_ok=True)

with sqlite3.connect(DB_PATH) as conn:
    df = pd.read_sql_query(
        """
        SELECT
            sample_id                                                  AS sample,
            cell_type                                                  AS population,
            count,
            SUM(count) OVER (PARTITION BY sample_id)                  AS total_count,
            count * 100.0 / SUM(count) OVER (PARTITION BY sample_id)  AS percentage
        FROM cell_counts
        ORDER BY sample_id, cell_type
        """,
        conn,
    )

df.to_csv(f"{OUTPUT_DIR}/summary_table.csv", index=False)
print(f"Wrote {len(df)} rows to {OUTPUT_DIR}/summary_table.csv")

# Part 3: Responder vs non-responder comparison
# Melanoma patients on miraclib, PBMC samples only
with sqlite3.connect(DB_PATH) as conn:
    responder_df = pd.read_sql_query(
        """
        SELECT
            cc.sample_id                                                          AS sample,
            cc.cell_type                                                          AS population,
            cc.count,
            SUM(cc.count) OVER (PARTITION BY cc.sample_id)                       AS total_count,
            cc.count * 100.0 / SUM(cc.count) OVER (PARTITION BY cc.sample_id)   AS percentage,
            s.sample_type,
            sub.condition,
            sub.response
        FROM cell_counts cc
        JOIN samples s   ON cc.sample_id = s.sample_id
        JOIN subjects sub ON s.subject_id = sub.subject_id
        WHERE sub.condition  = 'melanoma'
          AND sub.treatment  = 'miraclib'
          AND s.sample_type  = 'PBMC'
        ORDER BY cc.sample_id, cc.cell_type
        """,
        conn,
    )

responder_df.to_csv(f"{OUTPUT_DIR}/responder_comparison.csv", index=False)
print(f"Wrote {len(responder_df)} rows to {OUTPUT_DIR}/responder_comparison.csv")

# Part 3: Significance testing (Mann-Whitney U) per cell population
significance_rows = []
for pop in responder_df["population"].unique():
    pop_data = responder_df[responder_df["population"] == pop]
    responders = pop_data[pop_data["response"] == "yes"]["percentage"]
    non_responders = pop_data[pop_data["response"] == "no"]["percentage"]
    u_stat, p_value = stats.mannwhitneyu(responders, non_responders, alternative="two-sided")
    median_r = responders.median()
    median_nr = non_responders.median()
    n1, n2 = len(responders), len(non_responders)
    effect_size = round(1 - (2 * u_stat) / (n1 * n2), 3)
    if p_value < 0.05:
        direction = "Higher in responders" if median_r > median_nr else "Lower in responders"
    else:
        direction = ""
    significance_rows.append({
        "population": pop,
        "p_value": round(p_value, 4),
        "significant": "Yes" if p_value < 0.05 else "No",
        "effect_size_r": effect_size,
        "median_responders": round(median_r, 2),
        "median_non_responders": round(median_nr, 2),
        "direction": direction,
    })

significance_df = pd.DataFrame(significance_rows).sort_values("p_value")
significance_df.to_csv(f"{OUTPUT_DIR}/significance_results.csv", index=False)
print(f"Wrote {len(significance_df)} rows to {OUTPUT_DIR}/significance_results.csv")
