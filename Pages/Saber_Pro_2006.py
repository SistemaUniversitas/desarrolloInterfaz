"""
Dashboard ICFES Saber Pro – Genéricas 2006  (página dentro de multi-page app)
==============================================================================
Registra la página en /saberpro2006 y expone `layout` para que Dash la detecte.

Cache en disco:
  - Primera ejecución: procesa el CSV y guarda en Cache/
  - Siguientes:        carga la caché en segundos
  - CSV modificado:    detecta cambio y reprocesa automáticamente

Para forzar reprocesamiento:
    python pages/Saber_Pro_2006.py --rebuild
"""

import sys
import pickle
import hashlib
import time
from pathlib import Path
import warnings

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dash import html, dcc, dash_table
import dash

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────
# REGISTRO DE PÁGINA
# ─────────────────────────────────────────────────────────────
dash.register_page(__name__, path="/saberpro2006", name="Saber Pro · 2006")

# ─────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────
BASE_PROYECT_DIR = Path(__file__).resolve().parents[2]
CSV_PATH   = BASE_PROYECT_DIR / "Datasets" / "Data_ICFES" / "Saber_Pro" / "Unificados" / "Limpios" / "SaberPro_Genéricas_2006_filtrado.csv"
CACHE_DIR  = Path("Cache")
CACHE_FILE = CACHE_DIR / "SaberPro_2006_cache.pkl"

# ─────────────────────────────────────────────────────────────
# PALETA Y ESTILO
# ─────────────────────────────────────────────────────────────
BG         = "#0D1117"
CARD_BG    = "#161B22"
ACCENT1    = "#58A6FF"
ACCENT2    = "#3FB950"
ACCENT3    = "#F78166"
ACCENT4    = "#D2A8FF"
ACCENT5    = "#FFA657"
TEXT_MAIN  = "#E6EDF3"
TEXT_MUTED = "#8B949E"
BORDER     = "#30363D"

PALETTE = [ACCENT1, ACCENT2, ACCENT3, ACCENT4, ACCENT5,
           "#79C0FF", "#56D364", "#FF7B72", "#BC8CFF", "#FFA657"]

LAYOUT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor ="rgba(0,0,0,0)",
    font=dict(family="'IBM Plex Mono', monospace", color=TEXT_MAIN, size=12),
    margin=dict(t=40, b=40, l=40, r=40),
)
PIE_LAYOUT = dict(
    **LAYOUT_BASE,
    showlegend=True,
    legend=dict(font=dict(size=10, color=TEXT_MUTED),
                bgcolor="rgba(0,0,0,0)", bordercolor=BORDER, borderwidth=1),
)

PUNTAJES = ["MOD_INGLES_PUNT", "MOD_COMP_LECT_PUNT"]
PUNTAJES_LABELS = {
    "MOD_INGLES_PUNT":    "Inglés",
    "MOD_COMP_LECT_PUNT": "Comprensión Lectora",
}

# ─────────────────────────────────────────────────────────────
# FUNCIONES DE FIGURA
# ─────────────────────────────────────────────────────────────

def pie_fig(counts, labels):
    fig = go.Figure(go.Pie(
        labels=labels, values=counts, hole=0.45,
        marker=dict(colors=PALETTE, line=dict(color=BG, width=2)),
        textfont=dict(size=11),
        hovertemplate="%{label}<br>%{value:,} estudiantes<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(**PIE_LAYOUT)
    return fig


def bar_h_fig(index, values, color=ACCENT1):
    fig = go.Figure(go.Bar(
        x=values, y=[str(l) for l in index], orientation="h",
        marker=dict(color=color, line=dict(color="rgba(0,0,0,0)")),
        hovertemplate="%{y}<br>%{x:,}<extra></extra>",
    ))
    fig.update_layout(**LAYOUT_BASE,
        xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
        yaxis=dict(gridcolor="rgba(0,0,0,0)"),
    )
    return fig


def bar_v_fig(index, values, color=ACCENT2, xlab="", ylab="", tickangle=0):
    fig = go.Figure(go.Bar(
        x=[str(l) for l in index], y=values,
        marker=dict(color=color, line=dict(color="rgba(0,0,0,0)")),
        hovertemplate="%{x}<br>%{y:,}<extra></extra>",
    ))
    fig.update_layout(**LAYOUT_BASE,
        xaxis=dict(gridcolor="rgba(0,0,0,0)", title=xlab, tickangle=tickangle),
        yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER, title=ylab),
    )
    return fig


def choropleth_colombia(dept_counts: dict):
    """Mapa coroplético de Colombia por departamento."""
    import urllib.request, json, unicodedata

    GEOJSON_URL = (
        "https://raw.githubusercontent.com/angelnmara/geojson/master/"
        "colombiaDepartamentos.json"
    )
    try:
        with urllib.request.urlopen(GEOJSON_URL, timeout=15) as r:
            geojson = json.loads(r.read().decode())
    except Exception:
        geojson = None

    df_map = pd.DataFrame(list(dept_counts.items()), columns=["departamento", "conteo"])

    if geojson:
        def norm(s):
            s = s.upper()
            return ''.join(c for c in unicodedata.normalize('NFD', s)
                           if unicodedata.category(c) != 'Mn')
        geo_names = [f["properties"].get("NOMBRE_DPT", "") for f in geojson["features"]]
        geo_norm  = {norm(n): n for n in geo_names}
        df_map["geo_key"]    = df_map["departamento"].apply(norm)
        df_map["nombre_geo"] = df_map["geo_key"].map(geo_norm)
        df_map = df_map.dropna(subset=["nombre_geo"])

        fig = px.choropleth(
            df_map,
            geojson=geojson,
            locations="nombre_geo",
            featureidkey="properties.NOMBRE_DPT",
            color="conteo",
            color_continuous_scale=[[0, "#0D1117"], [0.2, ACCENT1], [1, ACCENT4]],
            hover_name="departamento",
            hover_data={"conteo": True, "nombre_geo": False},
        )
        fig.update_geos(fitbounds="locations", visible=False)
    else:
        df_s = df_map.sort_values("conteo").tail(33)
        fig = go.Figure(go.Bar(
            x=df_s["conteo"].tolist(), y=df_s["departamento"].tolist(),
            orientation="h", marker=dict(color=ACCENT1),
            hovertemplate="%{y}<br>%{x:,}<extra></extra>",
        ))

    fig.update_layout(
        **LAYOUT_BASE,
        coloraxis_colorbar=dict(
            tickfont=dict(color=TEXT_MUTED), bgcolor="rgba(0,0,0,0)",
            title=dict(text="Estudiantes", font=dict(color=TEXT_MUTED, size=10)),
        ),
        geo=dict(bgcolor="rgba(0,0,0,0)"),
    )
    return fig


def scatter_mcpio(mcpio_counts: dict):
    """Mapa de burbujas por municipio sobre Colombia."""
    MCPIO_COORDS = {
        "BOGOTÁ": (4.711, -74.0721), "BOGOTA": (4.711, -74.0721),
        "MEDELLÍN": (6.2442, -75.5812), "MEDELLIN": (6.2442, -75.5812),
        "CALI": (3.4516, -76.5319), "BARRANQUILLA": (10.9685, -74.7813),
        "CARTAGENA": (10.3910, -75.4794), "BUCARAMANGA": (7.1193, -73.1227),
        "PEREIRA": (4.8133, -75.6961), "MANIZALES": (5.0703, -75.5138),
        "IBAGUÉ": (4.4389, -75.2322), "IBAGUE": (4.4389, -75.2322),
        "CÚCUTA": (7.8939, -72.5078), "CUCUTA": (7.8939, -72.5078),
        "VILLAVICENCIO": (4.1420, -73.6266), "PASTO": (1.2136, -77.2811),
        "ARMENIA": (4.5339, -75.6811), "NEIVA": (2.9273, -75.2820),
        "MONTERÍA": (8.7575, -75.8851), "MONTERIA": (8.7575, -75.8851),
        "SANTA MARTA": (11.2408, -74.1990), "POPAYÁN": (2.4448, -76.6147),
        "POPAYAN": (2.4448, -76.6147), "VALLEDUPAR": (10.4631, -73.2532),
        "SINCELEJO": (9.3047, -75.3978), "FLORENCIA": (1.6144, -75.6062),
        "TUNJA": (5.5353, -73.3678), "QUIBDÓ": (5.6919, -76.6583),
        "QUIBDO": (5.6919, -76.6583), "RIOHACHA": (11.5444, -72.9072),
        "YOPAL": (5.3378, -72.3956), "LETICIA": (-4.2153, -69.9406),
        "SAN ANDRÉS": (12.5847, -81.7006), "SAN ANDRES": (12.5847, -81.7006),
        "BELLO": (6.3367, -75.5570), "SOACHA": (4.5793, -74.2179),
        "ITAGÜÍ": (6.1845, -75.5990), "ITAGUI": (6.1845, -75.5990),
        "ENVIGADO": (6.1752, -75.5838), "SOLEDAD": (10.9162, -74.7671),
        "BUENAVENTURA": (3.8801, -77.0311), "PALMIRA": (3.5394, -76.3035),
        "FLORIDABLANCA": (7.0649, -73.0893), "GIRARDOT": (4.3033, -74.8027),
        "SOGAMOSO": (5.7193, -72.9267), "DUITAMA": (5.8279, -73.0267),
        "CHÍA": (4.8629, -74.0592), "CHIA": (4.8629, -74.0592),
        "ZIPAQUIRÁ": (5.0231, -74.0059), "ZIPAQUIRA": (5.0231, -74.0059),
        "FUSAGASUGÁ": (4.3433, -74.3648), "FUSAGASUGA": (4.3433, -74.3648),
        "BUGA": (3.9008, -76.2986), "TULÚA": (4.0847, -76.2005),
        "TULUA": (4.0847, -76.2005), "SAHAGÚN": (8.9516, -75.4440),
        "SAHAGÚN": (8.9516, -75.4440),
    }
    df_m = pd.DataFrame(list(mcpio_counts.items()), columns=["municipio", "conteo"])
    df_m["municipio_norm"] = df_m["municipio"].str.upper().str.strip()
    df_m["lat"] = df_m["municipio_norm"].map(lambda x: MCPIO_COORDS.get(x, (None, None))[0])
    df_m["lon"] = df_m["municipio_norm"].map(lambda x: MCPIO_COORDS.get(x, (None, None))[1])
    df_m = df_m.dropna(subset=["lat", "lon"])

    fig = px.scatter_geo(
        df_m, lat="lat", lon="lon",
        size="conteo", color="conteo",
        hover_name="municipio",
        color_continuous_scale=[[0, ACCENT2], [1, ACCENT1]],
        size_max=50,
    )
    fig.update_geos(
        scope="south america",
        center=dict(lat=4.5, lon=-74.0),
        projection_scale=3.5,
        bgcolor="rgba(0,0,0,0)",
        showland=True,  landcolor="#1C2128",
        showocean=True, oceancolor="#0D1117",
        showlakes=True, lakecolor="#0D1117",
        showcountries=True, countrycolor=BORDER,
        showcoastlines=True, coastlinecolor=BORDER,
    )
    fig.update_layout(
        **LAYOUT_BASE,
        coloraxis_colorbar=dict(
            tickfont=dict(color=TEXT_MUTED), bgcolor="rgba(0,0,0,0)",
            title=dict(text="Estudiantes", font=dict(color=TEXT_MUTED, size=10)),
        ),
    )
    return fig

# ─────────────────────────────────────────────────────────────
# FINGERPRINT del CSV
# ─────────────────────────────────────────────────────────────

def csv_fingerprint(path: Path) -> str:
    s = path.stat()
    return hashlib.md5(f"{s.st_size}-{s.st_mtime}".encode()).hexdigest()

# ─────────────────────────────────────────────────────────────
# PROCESAMIENTO
# ─────────────────────────────────────────────────────────────

def build_cache(csv_path: Path) -> dict:
    print("=" * 55)
    print("  Primera ejecución: procesando CSV Saber Pro 2006…")
    print("=" * 55)
    t0 = time.time()

    # 1. Lectura
    print("  [1/6] Leyendo CSV…")
    df = pd.read_csv(csv_path, sep=";", decimal=".", low_memory=False, encoding="utf-8-sig")
    print(f"        {len(df):,} registros cargados.")
    print(f"        Columnas: {list(df.columns)}")

    total = len(df)

    # 2. Puntajes numéricos
    print("  [2/6] Procesando puntajes…")
    for p in PUNTAJES:
        df[p] = pd.to_numeric(df[p], errors="coerce")

    # 3. Agregaciones
    print("  [3/6] Calculando agregaciones…")

    def lmap(vc, m):
        return [m.get(str(k), str(k)) for k in vc.index]

    prueba_vc       = df["PRUEBA"].value_counts().sort_index()
    pais_vc         = df["ESTU_PAIS_RESIDE"].value_counts().head(30)

    # Calcular edad a partir del año de nacimiento
    from datetime import date as _date
    anno_actual = 2006
    df["edad"] = pd.to_numeric(df["ESTU_NACIMIENTO_ANNO"], errors="coerce")
    df["edad"] = anno_actual - df["edad"]
    edad_vc = (df["edad"].dropna().astype(int)
               .pipe(lambda s: s[(s >= 15) & (s <= 60)])
               .value_counts().sort_index())
    depto_vc        = df["ESTU_EXAM_DEPT_PRESENTACION"].value_counts()
    mcpio_vc        = df["ESTU_EXAM_MPIO_PRESENTACION"].value_counts().head(60)
    genero_vc       = df["ESTU_GENERO"].value_counts()
    estrato_vc      = df["ESTU_ESTRATO"].value_counts().sort_index()
    semestre_pres_vc = df["ESTU_EXAM_SEMESTRE_PRESTACION"].value_counts().sort_index()
    anno_pres_vc    = df["ESTU_EXAM_ANNO_PRESENTACION"].value_counts().sort_index()
    semestre_cur_vc = df["ESTU_SEMESTRE_CURSANDO"].value_counts().sort_index()
    area_vc         = df["ESTU_AREA_CONOC"].value_counts().sort_values(ascending=True)

    # Nacionalidad: separar Colombia de extranjeros (incluye variantes de escritura)
    import unicodedata as _ud

    def _norm_country(value):
        s = str(value).upper().strip()
        return "".join(c for c in _ud.normalize("NFD", s) if _ud.category(c) != "Mn")

    nac_raw = df["ESTU_PAIS_RESIDE"].fillna("COLOMBIA").astype(str).str.upper().str.strip()
    nac_norm = nac_raw.map(_norm_country)
    is_colombia = nac_norm.str.startswith("COLOMBIA")
    colombia_count = int(is_colombia.sum())
    extranjeros_vc = nac_raw[~is_colombia].value_counts().head(25).sort_values()

    # Tablas: top 50 instituciones y programas
    inst_table = (df["INST_NOMBRE_INSTITUCION"]
                  .value_counts()
                  .reset_index()
                  .rename(columns={"index": "Institución", "INST_NOMBRE_INSTITUCION": "Conteo"})
                  .head(50))
    # Compatibilidad pandas >= 1.x y >= 2.x
    if "INST_NOMBRE_INSTITUCION" in inst_table.columns and "count" in inst_table.columns:
        inst_table.columns = ["Institución", "Conteo"]
    else:
        inst_table.columns = ["Institución", "Conteo"]

    prgm_table = (df["ESTU_PRGM_ACADEMICO"]
                  .value_counts()
                  .reset_index()
                  .rename(columns={"index": "Programa", "ESTU_PRGM_ACADEMICO": "Conteo"})
                  .head(50))
    prgm_table.columns = ["Programa", "Conteo"]

    # 4. Stats puntajes
    print("  [4/6] Estadísticas de puntajes…")
    puntaje_stats = {}
    for p in PUNTAJES:
        col = df[p].dropna()
        puntaje_stats[p] = {
            "min": f"{col.min():.1f}" if len(col) else "N/A",
            "max": f"{col.max():.1f}" if len(col) else "N/A",
            "avg": f"{col.mean():.1f}" if len(col) else "N/A",
        }

    # 5. Figuras
    print("  [5/6] Generando figuras Plotly…")
    figs = {}

    figs["prueba"] = pie_fig(
        list(prueba_vc.values),
        [str(x) for x in prueba_vc.index]
    )
    figs["edad"] = bar_v_fig(
        list(edad_vc.index),
        list(edad_vc.values),
        color=ACCENT4, xlab="Edad", ylab="Cantidad"
    )
    figs["extranjeros"] = bar_h_fig(
        list(extranjeros_vc.index),
        list(extranjeros_vc.values),
        color=ACCENT5
    )
    figs["genero"] = pie_fig(
        list(genero_vc.values),
        lmap(genero_vc, {"M": "Masculino", "F": "Femenino"})
    )
    figs["estrato"] = bar_v_fig(
        list(estrato_vc.index),
        list(estrato_vc.values),
        color=ACCENT2, xlab="Estrato", ylab="Cantidad"
    )
    figs["semestre_pres"] = pie_fig(
        list(semestre_pres_vc.values),
        [f"Semestre {x}" for x in semestre_pres_vc.index]
    )
    figs["anno_pres"] = bar_v_fig(
        list(anno_pres_vc.index),
        list(anno_pres_vc.values),
        color=ACCENT1, xlab="Año", ylab="Cantidad"
    )
    figs["semestre_cur"] = pie_fig(
        list(semestre_cur_vc.values),
        [f"Semestre {x}" for x in semestre_cur_vc.index]
    )
    figs["area"] = bar_h_fig(
        list(area_vc.index),
        list(area_vc.values),
        color=ACCENT3
    )

    # 6. Mapas
    print("  [6/6] Generando mapas de Colombia…")
    try:
        figs["mapa_depto"] = choropleth_colombia(
            {str(k): int(v) for k, v in depto_vc.items()}
        )
        figs["mapa_mcpio"] = scatter_mcpio(
            {str(k): int(v) for k, v in mcpio_vc.items()}
        )
        print("        ✅ Mapas generados.")
    except Exception as e:
        print(f"        ⚠️  Error en mapas: {e}. Usando barras como fallback.")
        depto_s = depto_vc.sort_values().tail(33)
        mcpio_s = mcpio_vc.sort_values().tail(30)
        figs["mapa_depto"] = bar_h_fig(list(depto_s.index), list(depto_s.values), color=ACCENT1)
        figs["mapa_mcpio"] = bar_h_fig(list(mcpio_s.index), list(mcpio_s.values), color=ACCENT2)

    # Guardar caché
    payload = {
        "fingerprint":    csv_fingerprint(csv_path),
        "total":          total,
        "figs":           figs,
        "puntaje_stats":  puntaje_stats,
        "inst_table":     inst_table.to_dict("records"),
        "prgm_table":     prgm_table.to_dict("records"),
        "colombia_count": colombia_count,
    }
    CACHE_DIR.mkdir(exist_ok=True)
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"  ✅ Listo en {time.time()-t0:.1f}s  →  caché en {CACHE_FILE}")
    print("=" * 55)
    return payload


def load_or_build(force=False) -> dict:
    if not force and CACHE_FILE.exists():
        print(f"  Cargando caché Saber Pro 2006 desde {CACHE_FILE}…", end=" ", flush=True)
        t0 = time.time()
        with open(CACHE_FILE, "rb") as f:
            payload = pickle.load(f)
        """
        if CSV_PATH.exists() and payload.get("fingerprint") != csv_fingerprint(CSV_PATH):
            print("\n  ⚠️  El CSV cambió. Reprocesando caché…")
            return build_cache(CSV_PATH)
        """
        print(f"OK ({time.time()-t0:.1f}s)  →  {payload['total']:,} registros listos.")
        return payload
    return build_cache(CSV_PATH)

# ─────────────────────────────────────────────────────────────
# COMPONENTES DE UI
# ─────────────────────────────────────────────────────────────

TABLE_STYLE = {
    "style_table": {
        "overflowX": "auto",
        "overflowY": "auto",
        "maxHeight": "420px",
        "border": f"1px solid {BORDER}",
        "borderRadius": "8px",
    },
    "style_header": {
        "backgroundColor": "#0D1117",
        "color": ACCENT1,
        "fontFamily": "'IBM Plex Mono', monospace",
        "fontSize": "11px",
        "letterSpacing": "1.5px",
        "textTransform": "uppercase",
        "border": f"1px solid {BORDER}",
        "padding": "10px 14px",
    },
    "style_cell": {
        "backgroundColor": CARD_BG,
        "color": TEXT_MAIN,
        "fontFamily": "'IBM Plex Mono', monospace",
        "fontSize": "12px",
        "border": f"1px solid {BORDER}",
        "padding": "8px 14px",
        "textAlign": "left",
        "whiteSpace": "normal",
        "height": "auto",
    },
    "style_data_conditional": [
        {
            "if": {"row_index": "odd"},
            "backgroundColor": "#0D1117",
        },
        {
            "if": {"column_id": "Conteo"},
            "color": ACCENT2,
            "fontWeight": "700",
            "textAlign": "right",
        },
    ],
}


def card(children, extra_style=None):
    style = {"background": CARD_BG, "border": f"1px solid {BORDER}",
             "borderRadius": "12px", "padding": "20px", "marginBottom": "20px"}
    if extra_style: style.update(extra_style)
    return html.Div(children, style=style)

def section_title(text):
    return html.H3(text, style={
        "color": ACCENT1, "fontFamily": "'IBM Plex Mono', monospace",
        "fontSize": "13px", "letterSpacing": "2px", "textTransform": "uppercase",
        "marginBottom": "16px", "marginTop": "0",
        "borderLeft": f"3px solid {ACCENT1}", "paddingLeft": "10px",
    })

def kpi_box(label, value, color=ACCENT1):
    return html.Div([
        html.Div(label, style={"color": TEXT_MUTED, "fontSize": "10px",
                               "letterSpacing": "1.5px", "textTransform": "uppercase"}),
        html.Div(value, style={"color": color, "fontSize": "22px",
                               "fontWeight": "700", "marginTop": "4px"}),
    ], style={"background": BG, "border": f"1px solid {BORDER}", "borderRadius": "8px",
              "padding": "14px 18px", "textAlign": "center", "flex": "1",
              "minWidth": "100px", "fontFamily": "'IBM Plex Mono', monospace"})

def graph(fig, height="300px"):
    return dcc.Graph(figure=fig, config={"displayModeBar": False},
                     style={"height": height})

def row(*children, gap="16px"):
    return html.Div(list(children),
                    style={"display": "flex", "flexWrap": "wrap", "gap": gap})

def col(children, flex="1", min_width="280px"):
    return html.Div(children, style={"flex": flex, "minWidth": min_width})

def sublabel(text):
    return html.Div(text, style={"color": TEXT_MUTED, "fontSize": "11px", "marginBottom": "8px"})

def data_table(table_id, data, columns):
    return dash_table.DataTable(
        id=table_id,
        data=data,
        columns=[{"name": c, "id": c} for c in columns],
        page_size=15,
        sort_action="native",
        filter_action="native",
        **TABLE_STYLE,
    )

# ─────────────────────────────────────────────────────────────
# BUILD LAYOUT
# ─────────────────────────────────────────────────────────────

def build_layout(data: dict):
    figs           = data["figs"]
    stats          = data["puntaje_stats"]
    total          = data["total"]
    inst_data      = data["inst_table"]
    prgm_data      = data["prgm_table"]
    colombia_count = data["colombia_count"]

    # KPI rows puntajes
    kpi_rows = []
    for p in PUNTAJES:
        s = stats[p]
        kpi_rows.append(html.Div([
            html.Div(PUNTAJES_LABELS[p], style={
                "color": TEXT_MAIN, "fontSize": "12px", "width": "180px",
                "flexShrink": "0", "fontFamily": "'IBM Plex Mono', monospace"}),
            kpi_box("Mínimo",   s["min"], ACCENT3),
            kpi_box("Máximo",   s["max"], ACCENT2),
            kpi_box("Promedio", s["avg"], ACCENT1),
        ], style={"display": "flex", "gap": "10px", "alignItems": "center", "marginBottom": "10px"}))

    return html.Div(style={
        "background": BG, "minHeight": "100vh",
        "fontFamily": "'IBM Plex Mono', monospace",
        "color": TEXT_MAIN, "padding": "24px 32px",
    }, children=[

        # ── Header ──
        html.Div([
            html.Div([
                html.Div("ICFES · SABER PRO · 2006", style={"color": ACCENT1, "fontSize": "11px", "letterSpacing": "4px"}),
                html.H1("Genéricas · Dashboard", style={
                    "margin": "4px 0 0 0", "fontSize": "28px", "fontWeight": "700",
                    "color": TEXT_MAIN, "letterSpacing": "-0.5px"}),
            ]),
            html.Div([
                html.Div("TOTAL REGISTROS", style={"color": TEXT_MUTED, "fontSize": "10px", "letterSpacing": "2px"}),
                html.Div(f"{total:,}", style={"color": ACCENT2, "fontSize": "36px", "fontWeight": "700"}),
            ], style={"textAlign": "right"}),
        ], style={
            "display": "flex", "justifyContent": "space-between", "alignItems": "flex-end",
            "marginBottom": "28px", "paddingBottom": "20px", "borderBottom": f"1px solid {BORDER}"
        }),

        # ── 1. Prueba + Género + Semestre presentación + Semestre cursando ──
        card([
            section_title("Distribuciones generales"),
            row(
                col(card([sublabel("Prueba"),                graph(figs["prueba"],        "260px")])),
                col(card([sublabel("Género"),                graph(figs["genero"],        "260px")])),
                col(card([sublabel("Semestre presentación"), graph(figs["semestre_pres"], "260px")])),
                col(card([sublabel("Semestre cursando"),     graph(figs["semestre_cur"],  "260px")])),
            ),
        ]),

        # ── 2. Distribución de edad ──
        card([
            section_title("Distribución de edad"),
            graph(figs["edad"], "320px"),
        ]),

        # ── 3. Mapas ──
        card([
            section_title("Concentración geográfica de presentación"),
            row(
                col([sublabel("Por departamento"),             graph(figs["mapa_depto"], "520px")]),
                col([sublabel("Por municipio (top ciudades)"), graph(figs["mapa_mcpio"], "520px")]),
            ),
        ]),

        # ── 4. Extranjeros + KPI Colombia ──
        card([
            section_title("Nacionalidad de los estudiantes"),
            html.Div([
                kpi_box("Estudiantes colombianos", f"{colombia_count:,}", ACCENT2),
            ], style={"display": "flex", "marginBottom": "20px"}),
            sublabel("Estudiantes extranjeros por país de residencia (Top 25)"),
            graph(figs["extranjeros"], "420px"),
        ]),

        # ── 5. Estrato ──
        card([
            section_title("Estrato socioeconómico"),
            graph(figs["estrato"], "300px"),
        ]),

        # ── 6. Área de conocimiento ──
        card([
            section_title("Área de conocimiento del programa"),
            graph(figs["area"], "460px"),
        ]),

        # ── 7. KPIs puntajes ──
        card([
            section_title("Estadísticas de puntajes"),
            html.Div(kpi_rows),
        ]),

        # ── 8. Tablas ──
        card([
            section_title("Instituciones educativas"),
            html.Div("Top 50 · ordenable y filtrable", style={"color": TEXT_MUTED, "fontSize": "10px", "marginBottom": "12px"}),
            data_table("tabla_inst", inst_data, ["Institución", "Conteo"]),
        ]),

        card([
            section_title("Programas académicos"),
            html.Div("Top 50 · ordenable y filtrable", style={"color": TEXT_MUTED, "fontSize": "10px", "marginBottom": "12px"}),
            data_table("tabla_prgm", prgm_data, ["Programa", "Conteo"]),
        ]),

        # ── Footer ──
        html.Div("ICFES Saber Pro · Genéricas 2006 · Análisis de datos educativos",
                 style={"textAlign": "center", "color": TEXT_MUTED, "fontSize": "10px",
                        "letterSpacing": "2px", "paddingTop": "20px",
                        "borderTop": f"1px solid {BORDER}"}),
    ])

# ─────────────────────────────────────────────────────────────
# CARGA Y EXPOSICIÓN DEL LAYOUT
# ─────────────────────────────────────────────────────────────
_data  = load_or_build(force="--rebuild" in sys.argv)
layout = build_layout(_data)