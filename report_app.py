import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import requests
import io
import os  # <-- Imported the os module

# Title for the app
st.set_page_config(layout="wide")
with st.container():
    cols = st.columns([1, 1, 1])
    with cols[1]:
        st.title("Eriks Networking Sheet Reporting")


def iso_to_gregorian(iso_year, iso_week, iso_day):
    """
    Convert ISO year/week/day format to Gregorian date.
    """
    fourth_jan = pd.Timestamp(f"{iso_year}-01-04")
    _, year_start_week, year_start_day = fourth_jan.isocalendar()

    return fourth_jan + pd.Timedelta(
        days=-year_start_day + iso_day, weeks=-year_start_week + iso_week
    )


def generate_report():
    # df = pd.read_excel("Network_List.xlsx", sheet_name="Leads")
    # df = pd.read_csv(st.secrets["public_gsheets_url"])
    response = requests.get(
        st.secrets["public_gsheets_url"],
        verify=False,
    )
    df = pd.read_csv(io.StringIO(response.content.decode("utf-8")))

    #  Convert the date columns to week numbers
    df["Week of Senaste kontakt"] = (
        pd.to_datetime(df["Senaste kontakt"]).dt.isocalendar().week
    )
    df["Week of Senaste inbokade möte"] = (
        pd.to_datetime(df["Senaste inbokade möte"]).dt.isocalendar().week
    )
    df["Week of Senaste möte"] = (
        pd.to_datetime(df["Senaste möte"]).dt.isocalendar().week
    )

    # Group by each week and count non-null entries for each type of interaction
    contact_counts = df.groupby("Week of Senaste kontakt").size()
    meeting_planned_counts = df.groupby("Week of Senaste inbokade möte").size()
    meeting_performed_counts = df.groupby("Week of Senaste möte").size()

    # Construct the report dataframe
    report_df = pd.DataFrame(
        {
            "Week": list(range(1, 53)),
            "Contacts made": contact_counts.reindex(
                list(range(1, 53)), fill_value=0
            ).values,
            "Meetings planned": meeting_planned_counts.reindex(
                list(range(1, 53)), fill_value=0
            ).values,
            "Meetings performed": meeting_performed_counts.reindex(
                list(range(1, 53)), fill_value=0
            ).values,
        }
    )

    # Add start and end date columns for each week
    current_year = pd.Timestamp.now().year
    report_df["Start"] = report_df["Week"].apply(
        lambda x: iso_to_gregorian(current_year, x, 1).strftime("%b-%d")
    )
    report_df["End"] = report_df["Week"].apply(
        lambda x: (
            iso_to_gregorian(current_year, x, 1) + pd.Timedelta(days=6)
        ).strftime("%b-%d")
    )

    # Filter rows where at least one of the columns has a value other than 0
    report_df = report_df[
        report_df[
            [
                "Contacts made",
                "Meetings planned",
                "Meetings performed",
            ]
        ].sum(axis=1)
        != 0
    ]

    # Reorder columns
    report_df = report_df[
        [
            "Week",
            "Start",
            "End",
            "Contacts made",
            "Meetings planned",
            "Meetings performed",
        ]
    ]

    return report_df


# 1. Check if 'statistics_data.csv' exists, if not, create it
csv_file_path = "statistics_data.csv"  # <-- Path to the CSV file
if not os.path.exists(csv_file_path):
    pd.DataFrame(
        columns=["Week", "Contacts made", "Meetings planned", "Meetings performed"]
    ).to_csv(csv_file_path, index=False)

# Load previous data from the CSV
previous_data = pd.read_csv(csv_file_path)

# Generate the new report data
report_data = generate_report()

# Create a dataframe with all weeks
all_weeks = pd.DataFrame({"Week": list(range(1, 54))})

# Ensure that all weeks are present in both dataframes
report_data = all_weeks.merge(report_data, on="Week", how="left")
previous_data = all_weeks.merge(previous_data, on="Week", how="left")

# Merge data to get the maximum values for each week and interaction type
merged_data = report_data.merge(
    previous_data, on="Week", how="outer", suffixes=("_report", "_csv")
)
for column in ["Contacts made", "Meetings planned", "Meetings performed"]:
    merged_data[column] = merged_data[[f"{column}_report", f"{column}_csv"]].max(axis=1)
    merged_data.drop(columns=[f"{column}_report", f"{column}_csv"], inplace=True)

# Handle the Start and End date columns
if "Start_report" in merged_data.columns and "Start_csv" in merged_data.columns:
    merged_data["Start"] = merged_data["Start_report"].combine_first(
        merged_data["Start_csv"]
    )
    merged_data["End"] = merged_data["End_report"].combine_first(merged_data["End_csv"])
    merged_data.drop(
        columns=["Start_report", "End_report", "Start_csv", "End_csv"], inplace=True
    )
elif "Start_report" in merged_data.columns:
    merged_data["Start"] = merged_data["Start_report"]
    merged_data["End"] = merged_data["End_report"]
    merged_data.drop(columns=["Start_report", "End_report"], inplace=True)
elif "Start_csv" in merged_data.columns:
    merged_data["Start"] = merged_data["Start_csv"]
    merged_data["End"] = merged_data["End_csv"]
    merged_data.drop(columns=["Start_csv", "End_csv"], inplace=True)

# Drop rows where all columns (except 'Week') are NaN
merged_data = merged_data.dropna(
    subset=["Start", "End", "Contacts made", "Meetings planned", "Meetings performed"],
    how="all",
)

# Reorder columns
merged_data = merged_data[
    ["Week", "Start", "End", "Contacts made", "Meetings planned", "Meetings performed"]
]


# Plotting the graph
col1, col2 = st.columns([1, 1])
with col1:
    "Weekly report - Values"
    edited_merged_data = st.data_editor(
        merged_data, disabled=("Week", "Start", "End"), hide_index=True
    )

with col2:
    "Weekly report - Chart"
    altair_data = pd.melt(
        edited_merged_data,
        id_vars=["Week"],
        value_vars=["Contacts made", "Meetings planned", "Meetings performed"],
    )

    chart = (
        alt.Chart(altair_data)
        .mark_bar(
            opacity=1,
        )
        .encode(
            column=alt.Column(
                "Week:O", spacing=10, header=alt.Header(labelOrient="bottom")
            ),
            x=alt.X(
                "variable",
                sort=["Contacts made", "Meetings planned", "Meetings performed"],
                axis=None,
            ),
            y=alt.Y("value:Q"),
            color=alt.Color("variable"),
        )
        .configure_view(stroke="transparent")
    )

    cols = st.columns([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])

    with cols[0]:
        st.altair_chart(chart, theme=None, use_container_width=True)

# Save merged data to the CSV
edited_merged_data.to_csv(csv_file_path, index=False)
