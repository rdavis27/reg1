from __future__ import annotations

from functools import lru_cache
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.io as pio
from shiny import App, reactive, render, ui


INPUT_DIR = Path("input") if Path("input").exists() else Path("reg1/input")
MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

REG_FILES = {
    2017: "Party Affilation Reports - 2017.xlsx",
    2018: "Party-Affilation-by-County-2018.xlsx",
    2019: "party-affilation-by-county-2019.xlsx",
    2020: "Party Affilation by County 2020.xlsx",
    2021: "party-affiliation-by-county-2021.xlsx",
    2022: "party-affiliation-by-county-2022.xlsx",
    2023: "party-affiliation-by-county-2023.xlsx",
    2024: "party-affiliation-by-county-2024.xlsx",
    2025: "party-affiliation-by-county-2025.xlsx",
    2026: "party-affiliation-by-county-2026.xlsx",
}

PARTIES = ["REP", "DEM", "Minor", "None"]
PARTY_CHOICES = ["DEM", "REP", "Minor", "None"]
DEFAULT_COLORS = "blue3,green3,gray60,red3"
DEFAULT_SHAPES = "16,17,2,15"

R_TO_PLOTLY_COLORS = {
    "blue3": "#0000CD",
    "green3": "#00CD00",
    "gray60": "#999999",
    "grey60": "#999999",
    "red3": "#CD0000",
}

R_TO_PLOTLY_SYMBOLS = {
    0: "circle-open",
    1: "circle",
    2: "triangle-up-open",
    15: "square",
    16: "circle",
    17: "triangle-up",
}


def reg_file_path(year: int) -> Path:
    return (
        INPUT_DIR
        / "FL"
        / "reg"
        / f"voter-registration-report-archive-{year}"
        / REG_FILES.get(year, f"invalid_year {year}")
    )


@lru_cache(maxsize=None)
def read_month(year: int, month: str) -> pd.DataFrame:
    df = pd.read_excel(reg_file_path(year), sheet_name=month, skiprows=3)
    df = df.iloc[:, :6].copy()
    df.columns = ["COUNTY", "REP", "DEM", "Minor", "None", "Total"]
    df["COUNTY"] = df["COUNTY"].astype(str).str.upper().str.strip()
    df = df[df["Total"].notna()].copy()
    return df


def parse_colors(value: str) -> dict[str, str]:
    colors = [R_TO_PLOTLY_COLORS.get(x.strip(), x.strip()) for x in value.split(",")]
    while len(colors) < len(PARTIES):
        colors.append(None)
    return dict(zip(PARTIES, colors))


def parse_symbols(value: str) -> dict[str, str]:
    try:
        symbols = [R_TO_PLOTLY_SYMBOLS.get(int(x.strip()), "circle") for x in value.split(",")]
    except ValueError:
        symbols = ["circle"] * len(PARTIES)
    while len(symbols) < len(PARTIES):
        symbols.append("circle")
    return dict(zip(PARTIES, symbols))


def selected_filename(input, suffix: str) -> str:
    change = "_change" if input.dochange() else ""
    if input.plotbounties():
        return f"reg_counties_{input.xparty()}{change}.{suffix}"
    return f"reg_{input.xcounty()}{change}.{suffix}"


def make_plot(df: pd.DataFrame, input, *, interactive: bool = True):
    prefix1 = f"Change since {input.minyear()} in " if input.dochange() else ""
    prefix2 = "Change in " if input.dochange() else ""
    lcount = "Thousands of " if input.dothousands() else "Number of "

    if input.plotbounties():
        party = input.xparty()
        plot_df = df[["COUNTY", "Date", party]].rename(columns={party: "Registered"}).copy()
        if input.dothousands():
            plot_df["Registered"] = plot_df["Registered"] / 1000

        county_colors = (
            px.colors.qualitative.Alphabet
            + px.colors.qualitative.Dark24
            + px.colors.qualitative.Light24
            + px.colors.qualitative.Set3
        )
        title = f"Florida Counties - {prefix1}{lcount}{party} Registered Voters"
        fig = px.line(
            plot_df,
            x="Date",
            y="Registered",
            color="COUNTY",
            line_dash="COUNTY",
            color_discrete_sequence=county_colors,
            title=title,
        )
        fig.update_traces(line={"width": 1.7}, opacity=0.85)
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title=f"{prefix2}{lcount}{party} Registered Voters",
            legend_title_text="COUNTY",
            margin={"l": 60, "r": 20, "t": 70, "b": 60},
            template="plotly_white",
        )
        if not interactive:
            fig.update_layout(dragmode=False, showlegend=False)
        return fig

    plot_df = df.melt(
        id_vars=["COUNTY", "Total", "YEAR", "MO", "Date"],
        value_vars=PARTIES,
        var_name="Party",
        value_name="Registered",
    )
    if input.dothousands():
        plot_df["Registered"] = plot_df["Registered"] / 1000

    title = f"{input.xcounty()}, FL - {prefix1}{lcount}Registered Voters by Party"

    fig = px.line(
        plot_df,
        x="Date",
        y="Registered",
        color="Party",
        symbol="Party",
        markers=True,
        color_discrete_map=parse_colors(input.xcolor()),
        symbol_map=parse_symbols(input.xshape()),
        title=title,
    )
    fig.update_traces(marker={"size": input.dotsize(), "opacity": 0.7}, line={"width": 2})
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title=f"{prefix2}{lcount}Registered Voters",
        legend_title_text="Party",
        margin={"l": 60, "r": 20, "t": 70, "b": 60},
        template="plotly_white",
    )
    if not interactive:
        fig.update_layout(dragmode=False)
    return fig


app_ui = ui.page_fluid(
    ui.tags.style(
        """
        .app-shell {
            display: grid;
            grid-template-columns: 250px minmax(0, 1fr);
            gap: 24px;
            align-items: start;
        }

        .side-panel {
            background: #f5f5f5;
            border: 1px solid #e3e3e3;
            border-radius: 4px;
            padding: 15px;
        }

        .side-panel .form-group,
        .side-panel .shiny-input-container {
            width: 100%;
        }

        .side-panel .shiny-download-link {
            display: block;
            margin-bottom: 8px;
            width: 100%;
        }

        .main-panel {
            min-width: 0;
        }

        @media (max-width: 768px) {
            .app-shell {
                grid-template-columns: 1fr;
            }
        }
        """
    ),
    ui.h2("Active Registered Voters in Florida"),
    ui.div(
        ui.div(
            ui.input_numeric("minyear", "Min Year", min=2017, max=2026, value=2017),
            ui.input_numeric("maxyear", "Max Year", min=2017, max=2026, value=2026),
            ui.input_select("xcounty", "COUNTY", choices=["TOTALS"], selected="TOTALS"),
            ui.input_select("xparty", "PARTY", choices=PARTY_CHOICES, selected="DEM"),
            ui.input_text("xcolor", "Color", value=DEFAULT_COLORS),
            ui.input_text("xshape", "Shape", value=DEFAULT_SHAPES),
            ui.input_checkbox("dochange", "Calculate change", value=True),
            ui.input_checkbox("plotbounties", "Plot counties", value=False),
            ui.input_checkbox("dothousands", "Thousands", value=True),
            ui.input_numeric("maxcounties", "Max counties", min=1, value=10),
            ui.input_numeric("dotsize", "Dot Size", value=8),
            ui.download_button("getcsv", "Get CSV"),
            ui.download_button("getexcel", "Get Excel"),
            class_="side-panel",
        ),
        ui.div(
            ui.navset_tab(
                ui.nav_panel("Plotly", ui.output_ui("myPlotly")),
                ui.nav_panel("Plot", ui.output_ui("myPlot")),
                ui.nav_panel("Data", ui.output_text_verbatim("myData")),
                selected="Plotly",
            ),
            class_="main-panel",
        ),
        class_="app-shell",
    ),
)


def server(input, output, session):
    @reactive.effect
    def _populate_counties():
        try:
            counties = read_month(2024, "January")["COUNTY"].tolist()
        except Exception:
            counties = ["TOTALS"]
        ui.update_select("xcounty", choices=counties, selected="TOTALS", session=session)

    @reactive.calc
    def get_data() -> pd.DataFrame:
        minyear = int(input.minyear())
        maxyear = int(input.maxyear())
        if minyear > maxyear:
            minyear, maxyear = maxyear, minyear

        rows = []
        for year in range(minyear, maxyear + 1):
            for month_num, month in enumerate(MONTHS, start=1):
                month_df = read_month(year, month)
                if input.plotbounties():
                    county_df = month_df[month_df["COUNTY"] != "TOTALS"].copy()
                else:
                    county_df = month_df[month_df["COUNTY"] == input.xcounty()].copy()
                if county_df.empty:
                    continue
                county_df["YEAR"] = year
                county_df["MO"] = month_num
                rows.append(county_df)

        if not rows:
            return pd.DataFrame(columns=["COUNTY", *PARTIES, "Total", "YEAR", "MO", "Date"])

        df = pd.concat(rows, ignore_index=True)
        df["Date"] = pd.to_datetime(
            {"year": df["YEAR"].astype(int), "month": df["MO"].astype(int), "day": 1}
        )

        if input.plotbounties() and not df.empty:
            max_counties = max(1, int(input.maxcounties()))
            latest_date = df["Date"].max()
            top_counties = (
                df[df["Date"] == latest_date]
                .sort_values("Total", ascending=False)
                .head(max_counties)["COUNTY"]
            )
            df = df[df["COUNTY"].isin(top_counties)].copy()

        if input.dochange() and not df.empty:
            if input.plotbounties():
                first_values = df.groupby("COUNTY")[PARTIES].transform("first")
                df.loc[:, PARTIES] = df.loc[:, PARTIES] - first_values
            else:
                first_values = df.loc[df.index[0], PARTIES]
                df.loc[:, PARTIES] = df.loc[:, PARTIES].subtract(first_values, axis="columns")

        return df

    @output
    @render.ui
    def myPlotly():
        fig = make_plot(get_data(), input, interactive=True)
        return ui.HTML(
            pio.to_html(fig, full_html=False, include_plotlyjs=True, config={"responsive": True})
        )

    @output
    @render.ui
    def myPlot():
        fig = make_plot(get_data(), input, interactive=False)
        return ui.HTML(
            pio.to_html(
                fig,
                full_html=False,
                include_plotlyjs=True,
                config={"displayModeBar": False, "staticPlot": True, "responsive": True},
            )
        )

    @output
    @render.text
    def myData():
        return get_data().to_string(index=False)

    @output
    @render.download(
        filename=lambda: selected_filename(input, "csv"),
        media_type="text/csv",
    )
    def getcsv():
        yield get_data().to_csv(index=False)

    @output
    @render.download(
        filename=lambda: selected_filename(input, "xlsx"),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    def getexcel():
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            get_data().to_excel(writer, index=False, sheet_name="Registration")
        yield buffer.getvalue()


app = App(app_ui, server)
