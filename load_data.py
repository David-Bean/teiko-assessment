import sqlite3
import pandas as pd

DB_PATH = "teiko.db"
CSV_PATH = "cell-count.csv"

CELL_POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]


def init_db(conn):
    conn.executescript("""
        CREATE TABLE projects (
            project_id  TEXT PRIMARY KEY
        );

        CREATE TABLE subjects (
            subject_id  TEXT PRIMARY KEY,
            project_id  TEXT NOT NULL,
            condition   TEXT,
            age         INTEGER,
            sex         TEXT,
            treatment   TEXT,
            response    TEXT,
            FOREIGN KEY (project_id) REFERENCES projects (project_id)
        );

        CREATE TABLE samples (
            sample_id            TEXT PRIMARY KEY,
            subject_id           TEXT NOT NULL,
            sample_type          TEXT,
            time_from_treatment  INTEGER,
            FOREIGN KEY (subject_id) REFERENCES subjects (subject_id)
        );

        CREATE TABLE cell_counts (
            sample_id  TEXT NOT NULL,
            cell_type  TEXT NOT NULL,
            count      INTEGER NOT NULL,
            PRIMARY KEY (sample_id, cell_type),
            FOREIGN KEY (sample_id) REFERENCES samples (sample_id)
        );
    """)


def load_data(conn):
    df = pd.read_csv(CSV_PATH)

    projects_df = df[["project"]].drop_duplicates().rename(columns={"project": "project_id"})
    projects_df.to_sql("projects", conn, if_exists="append", index=False)

    subjects_df = df[["subject", "project", "condition", "age", "sex", "treatment", "response"]].drop_duplicates(subset=["subject"])
    subjects_df = subjects_df.rename(columns={"subject": "subject_id", "project": "project_id"})
    subjects_df.to_sql("subjects", conn, if_exists="append", index=False)

    samples_df = df[["sample", "subject", "sample_type", "time_from_treatment_start"]].drop_duplicates(subset=["sample"])
    samples_df = samples_df.rename(columns={"sample": "sample_id", "subject": "subject_id", "time_from_treatment_start": "time_from_treatment"})
    samples_df.to_sql("samples", conn, if_exists="append", index=False)

    long_df = (
        df[["sample"] + CELL_POPULATIONS]
        .melt(id_vars="sample", var_name="cell_type", value_name="count")
        .rename(columns={"sample": "sample_id"})
    )
    long_df.to_sql("cell_counts", conn, if_exists="append", index=False)

    print(f"Loaded {len(projects_df)} projects, {len(subjects_df)} subjects, {len(samples_df)} samples, {len(long_df)} cell count records.")


if __name__ == "__main__":
    with sqlite3.connect(DB_PATH) as conn:
        init_db(conn)
        load_data(conn)
    print(f"Database ready: {DB_PATH}")
