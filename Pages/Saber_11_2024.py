"""
Dashboard ICFES Saber 11 – 2024 con caché en disco (página dentro de multi-page app)
===================================================================
Registra la página en /2024 y expone `layout` para que Dash la detecte.

  - Primera ejecución: procesa el CSV y guarda en Cache/
  - Siguientes:        carga la caché en segundos
  - CSV modificado:    detecta cambio y reprocesa automáticamente

Para forzar reprocesamiento manual:
    python pages/Saber_11_2024.py --rebuild
"""

import sys
import pickle
import hashlib
import time
from pathlib import Path
from datetime import date
import warnings

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dash import html, dcc
import dash

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────
# REGISTRO DE PÁGINA
# ─────────────────────────────────────────────────────────────
dash.register_page(__name__, path="/2024", name="Saber 11 · 2024")

# ─────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────
BASE_PROYECT_DIR = Path(__file__).resolve().parents[2]
CSV_PATH   = BASE_PROYECT_DIR / "Datasets" / "Data_ICFES" / "Saber_11" / "Unificados" / "Limpios" / "Saber_11_2024_filtrado.csv"
CACHE_DIR  = Path("Cache")
CACHE_FILE = CACHE_DIR / "Saber11_2024_cache.pkl"

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

PUNTAJES = [
    "punt_c_naturales",
    "punt_lectura_critica",
    "punt_ingles",
    "punt_matematicas",
    "punt_sociales_ciudadanas",
    "punt_global",
]
PUNTAJES_LABELS = {
    "punt_c_naturales":        "C. Naturales",
    "punt_lectura_critica":    "Lectura Crítica",
    "punt_ingles":             "Inglés",
    "punt_matematicas":        "Matemáticas",
    "punt_sociales_ciudadanas":"Sociales Ciudadanas",
    "punt_global":             "Puntaje Global",
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
        df_map["geo_key"]   = df_map["departamento"].apply(norm)
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
        # Fallback barras si no hay red
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
        "BOGOTÁ": (4.711, -74.0721), "MEDELLÍN": (6.2442, -75.5812),
        "CALI": (3.4516, -76.5319), "BARRANQUILLA": (10.9685, -74.7813),
        "CARTAGENA": (10.3910, -75.4794), "BUCARAMANGA": (7.1193, -73.1227),
        "PEREIRA": (4.8133, -75.6961), "MANIZALES": (5.0703, -75.5138),
        "IBAGUÉ": (4.4389, -75.2322), "CÚCUTA": (7.8939, -72.5078),
        "VILLAVICENCIO": (4.1420, -73.6266), "PASTO": (1.2136, -77.2811),
        "ARMENIA": (4.5339, -75.6811), "NEIVA": (2.9273, -75.2820),
        "MONTERÍA": (8.7575, -75.8851), "SANTA MARTA": (11.2408, -74.1990),
        "POPAYÁN": (2.4448, -76.6147), "VALLEDUPAR": (10.4631, -73.2532),
        "SINCELEJO": (9.3047, -75.3978), "FLORENCIA": (1.6144, -75.6062),
        "TUNJA": (5.5353, -73.3678), "QUIBDÓ": (5.6919, -76.6583),
        "RIOHACHA": (11.5444, -72.9072), "YOPAL": (5.3378, -72.3956),
        "MOCOA": (1.1521, -76.6494), "LETICIA": (-4.2153, -69.9406),
        "SAN ANDRÉS": (12.5847, -81.7006), "BELLO": (6.3367, -75.5570),
        "SOACHA": (4.5793, -74.2179), "ITAGÜÍ": (6.1845, -75.5990),
        "ENVIGADO": (6.1752, -75.5838), "SOLEDAD": (10.9162, -74.7671),
        "BUENAVENTURA": (3.8801, -77.0311), "PALMIRA": (3.5394, -76.3035),
        "FLORIDABLANCA": (7.0649, -73.0893), "GIRARDOT": (4.3033, -74.8027),
        "SOGAMOSO": (5.7193, -72.9267), "DUITAMA": (5.8279, -73.0267),
        "CHÍA": (4.8629, -74.0592), "ZIPAQUIRÁ": (5.0231, -74.0059),
        "FUSAGASUGÁ": (4.3433, -74.3648), "BUGA": (3.9008, -76.2986),
        "TULÚA": (4.0847, -76.2005), "SAHAGÚN": (8.9516, -75.4440),
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
    print("  Primera ejecución: procesando CSV 2024…")
    print("=" * 55)
    t0 = time.time()

    # 1. Lectura
    print("  [1/7] Leyendo CSV…")
    df = pd.read_csv(csv_path, sep=";", decimal=".", low_memory=False, encoding="utf-8-sig")
    print(f"        {len(df):,} registros cargados.")

    # 2. Edad
    print("  [2/7] Calculando edades…")
    def calc_edad(s):
        try:
            n = pd.to_datetime(s, dayfirst=True, errors="coerce")
            if pd.isna(n): return None
            h = date.today()
            return h.year - n.year - ((h.month, h.day) < (n.month, n.day))
        except Exception:
            return None
    df["edad"] = df["estu_fechanacimiento"].apply(calc_edad)

    # 3. Puntajes numéricos
    print("  [3/7] Procesando puntajes…")
    for p in PUNTAJES:
        df[p] = pd.to_numeric(df[p], errors="coerce")

    # 4. Agregaciones
    print("  [4/7] Calculando agregaciones…")
    total = len(df)

    def lmap(vc, m):
        return [m.get(str(k), str(k)) for k in vc.index]

    # Periodo
    periodo_vc = df["periodo"].value_counts().sort_index()

    # Características del colegio
    bilingue_vc   = df["cole_bilingue"].value_counts()
    jornada_vc    = df["cole_jornada"].value_counts()
    naturaleza_vc = df["cole_naturaleza"].value_counts()
    area_vc       = df["cole_area_ubicacion"].value_counts()

    # Género
    genero_vc = df["estu_genero"].value_counts()

    # Geografía
    depto_vc = df["estu_depto_presentacion"].value_counts()
    mcpio_vc = df["estu_mcpio_presentacion"].value_counts().head(60)

    # Edad
    edad_vc = (df["edad"].dropna().astype(int)
                .pipe(lambda s: s[(s >= 10) & (s <= 30)])
                .value_counts().sort_index())

    # Nacionalidad: Colombia vs extranjeros
    nac_raw     = df["estu_nacionalidad"].fillna("COLOMBIA").str.upper().str.strip()
    colombia    = int((nac_raw == "COLOMBIA").sum())
    extranjeros = nac_raw[nac_raw != "COLOMBIA"].value_counts().head(20)
    nac_index   = ["COLOMBIA"] + list(extranjeros.index)
    nac_values  = [colombia]   + list(extranjeros.values)

    # Estrato
    estrato_vc = df["fami_estratovivienda"].value_counts().sort_index()

    # Desempeño inglés
    idioma_vc = df["desemp_ingles"].value_counts().sort_index()

    # Educación padres
    edu_padre_vc = df["fami_educacionpadre"].value_counts()
    edu_madre_vc = df["fami_educacionmadre"].value_counts()

    # 5. Stats puntajes
    print("  [5/7] Estadísticas de puntajes…")
    puntaje_stats = {}
    for p in PUNTAJES:
        col = df[p].dropna()
        puntaje_stats[p] = {
            "min": f"{col.min():.1f}" if len(col) else "N/A",
            "max": f"{col.max():.1f}" if len(col) else "N/A",
            "avg": f"{col.mean():.1f}" if len(col) else "N/A",
        }

    # 6. Figuras estáticas
    print("  [6/7] Generando figuras Plotly…")
    figs = {}

    figs["periodo"] = pie_fig(
        list(periodo_vc.values),
        [f"Periodo {x}" for x in periodo_vc.index]
    )
    figs["bilingue"] = pie_fig(
        list(bilingue_vc.values),
        lmap(bilingue_vc, {"S": "Bilingüe", "N": "No bilingüe"})
    )
    figs["jornada"]    = pie_fig(list(jornada_vc.values),    [str(x) for x in jornada_vc.index])
    figs["naturaleza"] = pie_fig(list(naturaleza_vc.values), [str(x) for x in naturaleza_vc.index])
    figs["area"]       = pie_fig(list(area_vc.values),       lmap(area_vc, {"U": "Urbano", "R": "Rural"}))
    figs["genero"]     = pie_fig(list(genero_vc.values),     lmap(genero_vc, {"M": "Masculino", "F": "Femenino"}))

    figs["edad"] = bar_v_fig(
        list(edad_vc.index), list(edad_vc.values),
        color=ACCENT4, xlab="Edad", ylab="Cantidad"
    )
    figs["nacionalidad"] = bar_h_fig(nac_index, nac_values, color=ACCENT5)
    figs["estrato"]      = bar_v_fig(list(estrato_vc.index), list(estrato_vc.values), color=ACCENT2)
    figs["idioma"]       = bar_v_fig(list(idioma_vc.index),  list(idioma_vc.values),  color=ACCENT1)
    edu_padre_s = edu_padre_vc.sort_values()
    edu_madre_s = edu_madre_vc.sort_values()
    figs["edu_padre"] = bar_h_fig(list(edu_padre_s.index), list(edu_padre_s.values), color=ACCENT3)
    figs["edu_madre"] = bar_h_fig(list(edu_madre_s.index), list(edu_madre_s.values), color=ACCENT4)

    # 7. Mapas
    print("  [7/7] Generando mapas de Colombia…")
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
        "fingerprint":   csv_fingerprint(csv_path),
        "total":         total,
        "figs":          figs,
        "puntaje_stats": puntaje_stats,
    }
    CACHE_DIR.mkdir(exist_ok=True)
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"  ✅ Listo en {time.time()-t0:.1f}s  →  caché en {CACHE_FILE}")
    print("=" * 55)
    return payload


def load_or_build(force=False) -> dict:
    if not force and CACHE_FILE.exists():
        print(f"  Cargando caché 2024 desde {CACHE_FILE}…", end=" ", flush=True)
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

# ─────────────────────────────────────────────────────────────
# BUILD LAYOUT
# ─────────────────────────────────────────────────────────────

def build_layout(data: dict):
    figs  = data["figs"]
    stats = data["puntaje_stats"]
    total = data["total"]

    # KPI rows puntajes
    kpi_rows = []
    for p in PUNTAJES:
        s = stats[p]
        kpi_rows.append(html.Div([
            html.Div(PUNTAJES_LABELS[p], style={
                "color": TEXT_MAIN, "fontSize": "12px", "width": "170px",
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
                html.Div("ICFES · 2024", style={"color": ACCENT1, "fontSize": "11px", "letterSpacing": "4px"}),
                html.H1("Saber 11 · Dashboard", style={
                    "margin": "4px 0 0 0", "fontSize": "28px", "fontWeight": "700",
                    "color": TEXT_MAIN, "letterSpacing": "-0.5px"}),
            ]),
            html.Div([
                html.Div("TOTAL ESTUDIANTES", style={"color": TEXT_MUTED, "fontSize": "10px", "letterSpacing": "2px"}),
                html.Div(f"{total:,}", style={"color": ACCENT2, "fontSize": "36px", "fontWeight": "700"}),
            ], style={"textAlign": "right"}),
        ], style={
            "display": "flex", "justifyContent": "space-between", "alignItems": "flex-end",
            "marginBottom": "28px", "paddingBottom": "20px", "borderBottom": f"1px solid {BORDER}"
        }),

        # ── 1. Periodo ──
        card([
            section_title("Distribución por periodo"),
            graph(figs["periodo"], "300px"),
        ]),

        # ── 2. Características del colegio + género ──
        card([
            section_title("Características del colegio y género"),
            row(
                col(card([sublabel("Bilingüe"),   graph(figs["bilingue"],   "240px")])),
                col(card([sublabel("Jornada"),     graph(figs["jornada"],    "240px")])),
                col(card([sublabel("Naturaleza"),  graph(figs["naturaleza"], "240px")])),
                col(card([sublabel("Área"),        graph(figs["area"],       "240px")])),
                col(card([sublabel("Género"),      graph(figs["genero"],     "240px")])),
            ),
        ]),

        # ── 3. Mapas Colombia ──
        card([
            section_title("Concentración geográfica de estudiantes"),
            row(
                col([sublabel("Por departamento"),              graph(figs["mapa_depto"], "520px")]),
                col([sublabel("Por municipio (top ciudades)"),  graph(figs["mapa_mcpio"], "520px")]),
            ),
        ]),

        # ── 4. Edad ──
        card([
            section_title("Distribución de edad"),
            graph(figs["edad"], "320px"),
        ]),

        # ── 5. Nacionalidad ──
        card([
            section_title("Nacionalidad (Colombia + extranjeros)"),
            graph(figs["nacionalidad"], "420px"),
        ]),

        # ── 6. Estrato ──
        card([
            section_title("Estrato socioeconómico"),
            graph(figs["estrato"], "300px"),
        ]),

        # ── 7. KPIs puntajes ──
        card([
            section_title("Estadísticas por área de puntaje"),
            html.Div(kpi_rows),
        ]),

        # ── 8. Niveles de inglés ──
        card([
            section_title("Niveles de desempeño en inglés"),
            graph(figs["idioma"], "300px"),
        ]),

        # ── 9. Educación padres ──
        card([
            section_title("Nivel educativo de los padres"),
            row(
                col([sublabel("Padre"), graph(figs["edu_padre"], "400px")]),
                col([sublabel("Madre"), graph(figs["edu_madre"], "400px")]),
            ),
        ]),

        # ── Footer ──
        html.Div("ICFES Saber 11 · 2024 · Análisis de datos educativos",
                 style={"textAlign": "center", "color": TEXT_MUTED, "fontSize": "10px",
                        "letterSpacing": "2px", "paddingTop": "20px",
                        "borderTop": f"1px solid {BORDER}"}),
    ])

# ─────────────────────────────────────────────────────────────
# CARGA Y EXPOSICIÓN DEL LAYOUT
# ─────────────────────────────────────────────────────────────
_data  = load_or_build(force="--rebuild" in sys.argv)
layout = build_layout(_data)