import pandas as pd
import plotly.graph_objects as go
import streamlit as st


@st.cache_data
def load_data() -> pd.DataFrame:
    return pd.read_csv("outputs/summary_table.csv")


@st.cache_data
def compute_averages(df: pd.DataFrame) -> pd.Series:
    return df.groupby("population")["percentage"].mean()


@st.cache_data
def load_responder_data() -> pd.DataFrame:
    return pd.read_csv("outputs/responder_comparison.csv")


@st.cache_data
def load_significance_data() -> pd.DataFrame:
    return pd.read_csv("outputs/significance_results.csv")


st.title("Initial Analysis")

st.write("**Question:** *What is the frequency of each cell type in each sample?*")

st.write(
    "This table shows the **immune cell composition** for each sample. "
    "For each sample, the count and relative frequency (as a *percentage of total cells*) "
    "are shown for five cell populations: B cells, CD8 T cells, CD4 T cells, NK cells, and monocytes."
)

df = load_data()
avg_pct = compute_averages(df)

search_col, _ = st.columns(2)
with search_col:
    search = st.text_input("", placeholder="Search by sample")
filtered_df = df[df["sample"].str.contains(search, case=False)] if search else df

event = st.dataframe(filtered_df, width="stretch", on_select="rerun", selection_mode="single-row")

selected_rows = event.selection.rows
if selected_rows:
    selected_sample = filtered_df.iloc[selected_rows[0]]["sample"]
    selected_population = filtered_df.iloc[selected_rows[0]]["population"]
else:
    selected_sample = "sample00000"
    selected_population = None

avg_label = "Average<br>(all samples)"
sample_label = f"{selected_sample}<br>{selected_population}" if selected_population else selected_sample

sample_pct = df[df["sample"] == selected_sample].set_index("population")["percentage"]

populations = sorted(df["population"].unique())

st.write(
    "To visualize the proportion of a given cell population within a sample, and its comparison to the average "
    "proportion of that cell type among all samples, select a row in the table."
)

fig = go.Figure()
for pop in populations:
    is_selected = pop == selected_population
    if is_selected:
        avg_text = f"{pop}<br><b>{avg_pct[pop]:.1f}%</b>"
        sample_text = f"{pop}<br><b>{sample_pct[pop]:.1f}%</b>"
    else:
        avg_text = f"{avg_pct[pop]:.1f}%"
        sample_text = f"{sample_pct[pop]:.1f}%"
    fig.add_trace(go.Bar(
        name=pop,
        y=[avg_label, sample_label],
        x=[avg_pct[pop], sample_pct[pop]],
        orientation="h",
        text=[avg_text, sample_text],
        textposition="inside",
    ))

fig.update_layout(
    barmode="stack",
    xaxis_title="Percentage (%)",
    xaxis=dict(range=[0, 100]),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0,
        title="Population",
        traceorder="normal",
    ),
)

st.plotly_chart(fig, width="stretch")

st.title("Statistical Analysis")

st.write("**Question:** *Which cell populations differ in relative frequency between melanoma patients on miraclib who respond versus those who do not?*")

responder_df = load_responder_data()

st.write(
    "The boxplot below compares the relative frequency of each immune cell population between "
    "responders and non-responders. Each box shows the median, interquartile range, and spread "
    "of frequencies across samples, allowing visual identification of populations that may differ "
    "between the two groups."
)

with st.expander("Click here to view table"):
    st.dataframe(responder_df, width="stretch")

box_fig = go.Figure()
for response_val, label in [("yes", "Responders"), ("no", "Non-responders")]:
    subset = responder_df[responder_df["response"] == response_val]
    box_fig.add_trace(go.Box(
        y=subset["population"],
        x=subset["percentage"],
        name=label,
        orientation="h",
        hoverinfo="none",
    ))

box_fig.update_layout(
    boxmode="group",
    xaxis_title="Relative Frequency (%)",
    yaxis_title="Cell Population",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0,
        title="Response",
    ),
)

st.plotly_chart(box_fig, width="stretch")

significance_df = load_significance_data()
st.write(
    "**Significance Results** — Mann-Whitney U test (two-sided), α = 0.05"
)
st.dataframe(significance_df.drop(columns=["effect_size_r"]), height=220)

significant = significance_df[significance_df["significant"] == "Yes"]
if not significant.empty:
    for _, row in significant.iterrows():
        st.write(
            f"**{row['population']}** is significantly {row['direction'].lower()} "
            f"(median {row['median_responders']:.1f}% in responders vs "
            f"{row['median_non_responders']:.1f}% in non-responders, p = {row['p_value']})."
        )

st.write("**Effect Size — Statistically Significant Populations (Rank-Biserial Correlation)**")
effect_rows = []
for _, row in significant.iterrows():
    r = abs(row["effect_size_r"])
    if r < 0.1:
        interpretation = "negligible"
    elif r < 0.3:
        interpretation = "small"
    elif r < 0.5:
        interpretation = "medium"
    else:
        interpretation = "large"
    effect_rows.append({
        "cell_type": row["population"],
        "r value": row["effect_size_r"],
        "interpretation": interpretation,
    })
effect_size_df = pd.DataFrame(effect_rows)
st.dataframe(effect_size_df, hide_index=True, height=35 * len(effect_size_df) + 38)

st.write(
    "**Interpretation:** Among the melanoma patients who received miraclib and whose sampling "
    "method was PBMC, cell populations were mostly consistent between responders and non-responders. "
    "The only significant difference in cell populations was CD4 T cells, but the effect size was "
    "small and therefore the difference may not be biologically significant."
)
