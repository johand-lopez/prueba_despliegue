import dash
from dash import dcc, html, Input, Output, dash_table
import dash_leaflet as dl
import pandas as pd
import geopandas as gpd
import plotly.express as px
import json
import numpy as np
import branca.colormap as cm
import dash_bootstrap_components as dbc  # 👈 nuevo

# =============================
#   Mortalidad en Antioquia – Dash
# =============================

# Usamos un tema de Bootstrap (puedes probar otros: FLATLY, CYBORG, LUX...)
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server

# 1. Lectura de datos
ruta_dataset = "data/Mortalidad_General_en_el_departamento_de_Antioquia_desde_2005_20250915.csv"
ruta_shapefile = "data/MGN_MPIO_POLITICO.shp"

dataset = pd.read_csv(
    ruta_dataset,
    dtype={"CodigoMunicipio": str}
)

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

        # ----- Contexto -----
        dcc.Tab(label="Contexto", children=[
            dbc.Container([
                html.H2("Contexto del proyecto", className="mt-4"),
                html.P("Este proyecto realiza un análisis georreferenciado de la mortalidad en el departamento de Antioquia, "
                       "a partir de registros municipales de defunciones ocurridas entre 2005 y 2021. El trabajo combina datos "
                       "estadísticos (número de casos de defunción y tasa de mortalidad por mil habitantes) con herramientas de "
                       "análisis espacial, permitiendo visualizar patrones y diferencias entre municipios y subregiones.",
                       className="fs-5"),

                html.H3("Objetivo del análisis", className="mt-3"),
                html.P("El objetivo de este trabajo es integrar y analizar la información de mortalidad en el departamento de Antioquia "
                       "de manera espacial, utilizando herramientas de georreferenciación. A partir de los datos de defunciones y de la "
                       "tasa de mortalidad por cada mil habitantes en cada municipio, junto con las geometrías oficiales de los límites "
                       "municipales, se busca:", className="fs-5"),

                html.Ul([
                    html.Li("Visualizar la distribución espacial de la mortalidad en los municipios de Antioquia."),
                    html.Li("Identificar patrones territoriales que puedan reflejar diferencias en las condiciones de salud, acceso a servicios médicos o características demográficas."),
                    html.Li("Generar mapas coropléticos y otras representaciones gráficas que faciliten la comprensión de las áreas con mayor o menor riesgo de mortalidad.")
                ], className="fs-5"),

                html.H3("Fuente del dataset", className="mt-3"),
                html.P("Los datos utilizados en este proyecto provienen del portal oficial de "
                       "Datos Abiertos de Colombia.", className="fs-5"),

                html.A("https://www.datos.gov.co/Salud-y-Protecci-n-Social/Mortalidad-General-en-el-departamento-de-Antioquia/fuc4-tvui/about_data",
                       href="https://www.datos.gov.co/Salud-y-Protecci-n-Social/Mortalidad-General-en-el-departamento-de-Antioquia/fuc4-tvui/about_data",
                       target="_blank", className="fs-5 text-primary"),

                html.Br(),
                html.Br(),
                html.P("Autor: Johan David Diaz Lopez", className="fw-bold fs-5")
            ], fluid=True)
        ]),

        # ----- Tabla de Datos -----
        dcc.Tab(label="Tabla de Datos", children=[
            dash_table.DataTable(
                id="tabla_merge",
                data=df_merge.drop(columns="geometry").to_dict("records"),
                columns=[{"name": i, "id": i} for i in df_merge.drop(columns="geometry").columns],
                page_size=15,
                style_table={"overflowX": "auto"},
            )
        ]),

        # ----- Estadísticas -----
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

        # ----- Tasa -----
        dcc.Tab(label="Tasa de mortalidad", children=[
            dcc.Tabs([
                dcc.Tab(label="Mapa interactivo", children=[
                    html.Label("Seleccione un año:"),
                    dcc.Dropdown(id="anio_tasa", options=[{"label": i, "value": i} for i in lista_anios],
                                 value="Todos los años"),
                    html.Div(id="mapa_tasa")
                ]),
                dcc.Tab(label="Top 10 más altos", children=[
                    html.Label("Seleccione un año:"),
                    dcc.Dropdown(id="anio_top_tasa_alta", options=[{"label": i, "value": i} for i in lista_anios],
                                 value="Todos los años"),
                    dcc.Graph(id="plot_top10_tasa_alta")
                ]),
                dcc.Tab(label="Top 10 más bajos", children=[
                    html.Label("Seleccione un año:"),
                    dcc.Dropdown(id="anio_top_tasa_baja", options=[{"label": i, "value": i} for i in lista_anios],
                                 value="Todos los años"),
                    dcc.Graph(id="plot_top10_tasa_baja")
                ])
            ])
        ]),

        # ----- Defunciones -----
        dcc.Tab(label="Número de defunciones", children=[
            dcc.Tabs([
                dcc.Tab(label="Mapa interactivo", children=[
                    html.Label("Seleccione un año:"),
                    dcc.Dropdown(id="anio_casos", options=[{"label": i, "value": i} for i in lista_anios],
                                 value="Todos los años"),
                    html.Div(id="mapa_casos")
                ]),
                dcc.Tab(label="Top 10 más altos", children=[
                    html.Label("Seleccione un año:"),
                    dcc.Dropdown(id="anio_top_casos_alto", options=[{"label": i, "value": i} for i in lista_anios],
                                 value="Todos los años"),
                    dcc.Graph(id="plot_top10_casos_alto")
                ]),
                dcc.Tab(label="Top 10 más bajos", children=[
                    html.Label("Seleccione un año:"),
                    dcc.Dropdown(id="anio_top_casos_bajo", options=[{"label": i, "value": i} for i in lista_anios],
                                 value="Todos los años"),
                    dcc.Graph(id="plot_top10_casos_bajo")
                ])
            ])
        ])
    ])
], fluid=True)

# =============================
#   Callbacks
# =============================

@app.callback(
    Output("tabla_summary", "data"),
    Input("tabla_summary", "id")
)
def update_summary(_):
    def resumen(x):
        return {
            "Mínimo": x.min(),
            "1er Cuartil": x.quantile(0.25),
            "Mediana": x.median(),
            "Media": x.mean(),
            "3er Cuartil": x.quantile(0.75),
            "Máximo": x.max()
        }

    df = []
    for col in ["NumeroCasos", "TasaXMilHabitantes"]:
        stats = resumen(df_merge[col])
        for k, v in stats.items():
            df.append({"Variable": col, "Estadistico": k, "Valor": round(v, 2)})
    return df

# ---- Mapas ----
@app.callback(
    Output("mapa_tasa", "children"),
    Input("anio_tasa", "value")
)
def update_mapa_tasa(anio):
    if anio == "Todos los años":
        df = df_merge.groupby(
            ["NombreMunicipio", "CodigoMunicipio", "NombreRegion", "geometry"]
        ).agg({"TasaXMilHabitantes": "mean"}).reset_index()
    else:
        df = df_merge[df_merge["Año"] == anio]

    values = df["TasaXMilHabitantes"]
    min_val, max_val = values.min(), values.max()
    cmap = cm.linear.YlOrRd_09.scale(min_val, max_val)

    geojson = json.loads(df.to_json())

    for feature in geojson["features"]:
        municipio = feature["properties"]["NombreMunicipio"]
        valor = feature["properties"]["TasaXMilHabitantes"]
        feature["properties"]["tooltip"] = f"{municipio}: {round(valor, 2)}"

    choropleth = dl.GeoJSON(
        data=geojson,
        id="geojson_tasa",
        zoomToBounds=True,
        options=dict(style=dict(weight=1, opacity=1, color="black", fillOpacity=0.7)),
    )

    return dl.Map(
        children=[
            dl.TileLayer(),
            choropleth,
            dl.Colorbar(colorscale=cmap.colors, width=20, height=150,
                        min=min_val, max=max_val, unit="Tasa por mil")
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
        df = df_merge.groupby(
            ["NombreMunicipio", "CodigoMunicipio", "NombreRegion", "geometry"]
        ).agg({"NumeroCasos": "sum"}).reset_index()
    else:
        df = df_merge[df_merge["Año"] == anio]

    values = df["NumeroCasos"]
    min_val, max_val = values.min(), values.max()
    cmap = cm.linear.Blues_09.scale(min_val, max_val)

    geojson = json.loads(df.to_json())

    for feature in geojson["features"]:
        municipio = feature["properties"]["NombreMunicipio"]
        valor = feature["properties"]["NumeroCasos"]
        feature["properties"]["tooltip"] = f"{municipio}: {int(valor)}"

    choropleth = dl.GeoJSON(
        data=geojson,
        id="geojson_casos",
        zoomToBounds=True,
        options=dict(style=dict(weight=1, opacity=1, color="black", fillOpacity=0.7)),
    )

    return dl.Map(
        children=[
            dl.TileLayer(),
            choropleth,
            dl.Colorbar(colorscale=cmap.colors, width=20, height=150,
                        min=min_val, max=max_val, unit="Número de casos")
        ],
        style={"width": "100%", "height": "600px"},
        center=[6.5, -75.5], zoom=7
    )


# ---- Gráficos ----
@app.callback(
    Output("plot_top10_tasa_alta", "figure"),
    Input("anio_top_tasa_alta", "value")
)
def plot_top10_tasa_alta(anio):
    df = df_merge if anio == "Todos los años" else df_merge[df_merge["Año"] == anio]
    df = df.groupby("NombreMunicipio")["TasaXMilHabitantes"].mean().nlargest(10).reset_index()
    return px.bar(df, x="TasaXMilHabitantes", y="NombreMunicipio", orientation="h",
                  title="Top 10 municipios con mayor tasa de mortalidad", color="TasaXMilHabitantes")

@app.callback(
    Output("plot_top10_tasa_baja", "figure"),
    Input("anio_top_tasa_baja", "value")
)
def plot_top10_tasa_baja(anio):
    df = df_merge if anio == "Todos los años" else df_merge[df_merge["Año"] == anio]
    df = df.groupby("NombreMunicipio")["TasaXMilHabitantes"].mean().nsmallest(10).reset_index()
    return px.bar(df, x="TasaXMilHabitantes", y="NombreMunicipio", orientation="h",
                  title="Top 10 municipios con menor tasa de mortalidad", color="TasaXMilHabitantes")

@app.callback(
    Output("plot_top10_casos_alto", "figure"),
    Input("anio_top_casos_alto", "value")
)
def plot_top10_casos_alto(anio):
    df = df_merge if anio == "Todos los años" else df_merge[df_merge["Año"] == anio]
    df = df.groupby("NombreMunicipio")["NumeroCasos"].sum().nlargest(10).reset_index()
    return px.bar(df, x="NumeroCasos", y="NombreMunicipio", orientation="h",
                  title="Top 10 municipios con mayor número de defunciones", color="NumeroCasos")

@app.callback(
    Output("plot_top10_casos_bajo", "figure"),
    Input("anio_top_casos_bajo", "value")
)
def plot_top10_casos_bajo(anio):
    df = df_merge if anio == "Todos los años" else df_merge[df_merge["Año"] == anio]
    df = df.groupby("NombreMunicipio")["NumeroCasos"].sum().nsmallest(10).reset_index()
    return px.bar(df, x="NumeroCasos", y="NombreMunicipio", orientation="h",
                  title="Top 10 municipios con menor número de defunciones", color="NumeroCasos")

# =============================
#   Lanzar app
# =============================
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8050)

