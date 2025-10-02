import dash
from dash import dcc, html, Input, Output, dash_table
import dash_leaflet as dl
import pandas as pd
import geopandas as gpd
import plotly.express as px
import json
import numpy as np
import branca.colormap as cm
import dash_bootstrap_components as dbc

# =============================
#   Mortalidad en Antioquia – Dash
# =============================

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server

# 1. Lectura de datos
ruta_dataset = "data/Mortalidad_General_en_el_departamento_de_Antioquia_desde_2005_20250915.csv"
ruta_shapefile = "data/MGN_MPIO_POLITICO.shp"

dataset = pd.read_csv(ruta_dataset, dtype={"CodigoMunicipio": str})

dataset_shapefile = gpd.read_file(ruta_shapefile)
dataset_shapefile = dataset_shapefile[dataset_shapefile["DPTO_CCDGO"] == "05"]
dataset_shapefile = dataset_shapefile[["MPIO_CDPMP", "MPIO_CNMBR", "geometry"]].to_crs(epsg=4326)

dataset_final = dataset[["NombreMunicipio", "CodigoMunicipio", "NombreRegion", "Año", "NumeroCasos", "TasaXMilHabitantes"]]
dataset_final["CodigoMunicipio"] = dataset_final["CodigoMunicipio"].astype(str)
dataset_shapefile["MPIO_CDPMP"] = dataset_shapefile["MPIO_CDPMP"].astype(str)

df_merge = dataset_shapefile.merge(dataset_final, left_on="MPIO_CDPMP", right_on="CodigoMunicipio")
lista_anios = ["Todos los años"] + sorted(df_merge["Año"].unique().tolist())

# =============================
#   Layout con Bootstrap
# =============================
app.layout = dbc.Container([
    dcc.Tabs([
        dcc.Tab(label="Contexto", children=[
            dbc.Container([
                html.H2("Contexto del proyecto", className="mt-4"),
                html.P("Este proyecto realiza un análisis georreferenciado de la mortalidad en el departamento de Antioquia...",
                       className="fs-6"),
                html.H3("Objetivo del análisis", className="mt-3"),
                html.P("El objetivo de este trabajo es integrar y analizar...", className="fs-6"),
                html.Ul([
                    html.Li("Visualizar la distribución espacial de la mortalidad."),
                    html.Li("Identificar patrones territoriales."),
                    html.Li("Generar mapas coropléticos y gráficas.")
                ], className="fs-6"),
                html.H3("Fuente del dataset", className="mt-3"),
                html.A("Datos Abiertos de Colombia",
                       href="https://www.datos.gov.co/Salud-y-Protecci-n-Social/Mortalidad-General-en-el-departamento-de-Antioquia/fuc4-tvui/about_data",
                       target="_blank", className="fs-6 text-primary"),
                html.Br(),
                html.P("Autor: Johan David Diaz Lopez", className="fw-bold fs-6")
            ], fluid=True)
        ]),

        dcc.Tab(label="Tabla de Datos", children=[
            dash_table.DataTable(
                id="tabla_merge",
                data=df_merge.drop(columns="geometry").to_dict("records"),
                columns=[{"name": i, "id": i} for i in df_merge.drop(columns="geometry").columns],
                page_size=15,
                style_table={"overflowX": "auto"},
            )
        ]),

        dcc.Tab(label="Estadísticas descriptivas", children=[
            dash_table.DataTable(
                id="tabla_summary",
                columns=[{"name": "Variable", "id": "Variable"},
                         {"name": "Estadístico", "id": "Estadistico"},
                         {"name": "Valor", "id": "Valor"}],
                style_table={"overflowX": "auto"},
                style_cell={"fontSize": 12}
            )
        ]),

        dcc.Tab(label="Tasa de mortalidad", children=[
            dcc.Tabs([
                dcc.Tab(label="Mapa interactivo", children=[
                    html.Label("Seleccione un año:"),
                    dcc.Dropdown(id="anio_tasa", options=[{"label": i, "value": i} for i in lista_anios],
                                 value="Todos los años"),
                    html.Div(id="mapa_tasa")
                ])
            ])
        ]),

        dcc.Tab(label="Número de defunciones", children=[
            dcc.Tabs([
                dcc.Tab(label="Mapa interactivo", children=[
                    html.Label("Seleccione un año:"),
                    dcc.Dropdown(id="anio_casos", options=[{"label": i, "value": i} for i in lista_anios],
                                 value="Todos los años"),
                    html.Div(id="mapa_casos")
                ])
            ])
        ])
    ])
], fluid=True)

# =============================
#   Callbacks
# =============================

@app.callback(
    Output("mapa_tasa", "children"),
    Input("anio_tasa", "value")
)
def update_mapa_tasa(anio):
    if anio == "Todos los años":
        df = df_merge.groupby(["NombreMunicipio", "CodigoMunicipio", "NombreRegion", "geometry"]).agg({
            "TasaXMilHabitantes": "mean"
        }).reset_index()
    else:
        df = df_merge[df_merge["Año"] == anio]

    # aseguramos GeoDataFrame
    df = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")

    values = df["TasaXMilHabitantes"].fillna(0)
    min_val, max_val = values.min(), values.max()
    if min_val == max_val:
        max_val = min_val + 1
    cmap = cm.linear.Reds_09.scale(min_val, max_val)

    geojson = json.loads(df.to_json())
    for f in geojson["features"]:
        muni = f["properties"]["NombreMunicipio"]
        val = f["properties"]["TasaXMilHabitantes"]
        f["properties"]["tooltip"] = f"{muni}: {round(val or 0, 2)}"

    return dl.Map(
        children=[
            dl.TileLayer(),
            dl.GeoJSON(data=geojson, id="geojson_tasa", zoomToBounds=True,
                       options=dict(style=dict(weight=1, opacity=1, color="black", fillOpacity=0.7))),
            dl.Colorbar(colorscale=cmap, width=20, height=150,
                        min=min_val, max=max_val, unit="Tasa por mil hab.")
        ],
        style={"width": "100%", "height": "600px"},
        center=[6.5, -75.5], zoom=7
    )


@app.callback(
    Output("mapa_casos", "children"),
    Input("anio_casos", "value")
)
def update_mapa_casos(anio):
    if anio == "Todos los años":
        df = df_merge.groupby(["NombreMunicipio", "CodigoMunicipio", "NombreRegion", "geometry"]).agg({
            "NumeroCasos": "sum"
        }).reset_index()
    else:
        df = df_merge[df_merge["Año"] == anio]

    df = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")

    values = df["NumeroCasos"].fillna(0)
    min_val, max_val = values.min(), values.max()
    if min_val == max_val:
        max_val = min_val + 1
    cmap = cm.linear.Blues_09.scale(min_val, max_val)

    geojson = json.loads(df.to_json())
    for f in geojson["features"]:
        muni = f["properties"]["NombreMunicipio"]
        val = f["properties"]["NumeroCasos"]
        f["properties"]["tooltip"] = f"{muni}: {int(val or 0)}"

    return dl.Map(
        children=[
            dl.TileLayer(),
            dl.GeoJSON(data=geojson, id="geojson_casos", zoomToBounds=True,
                       options=dict(style=dict(weight=1, opacity=1, color="black", fillOpacity=0.7))),
            dl.Colorbar(colorscale=cmap, width=20, height=150,
                        min=min_val, max=max_val, unit="Número de casos")
        ],
        style={"width": "100%", "height": "600px"},
        center=[6.5, -75.5], zoom=7
    )

# =============================
#   Lanzar app
# =============================
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8050)
