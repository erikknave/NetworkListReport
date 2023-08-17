import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# pip install openpyxl

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
    df = pd.read_excel("Network_List.xlsx", sheet_name="Lista")

    # Convert the date columns to week numbers
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


report_data = generate_report()


# Plotting the grap

col1, col2 = st.columns([1, 1])
with col1:
    "Weekly report - Values"
    report_data

with col2:
    "Weekly report - Chart"
    altair_data = pd.melt(
        report_data,
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
