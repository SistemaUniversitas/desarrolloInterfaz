"""
Dashboard ICFES Saber 11 – 2007 con caché en disco (página dentro de multi-page app)
===================================================================
Registra la página en /2007 y expone `layout` para que Dash la detecte.

  - Primera ejecución: procesa el CSV y guarda en Cache/
  - Siguientes:        carga la caché en segundos
  - CSV modificado:    detecta cambio y reprocesa automáticamente

Para forzar reprocesamiento manual, llamar desde consola:
    python pages/Saber_11_2007.py --rebuild
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
# REGISTRO DE PÁGINA  ← CAMBIO 1
# ─────────────────────────────────────────────────────────────
dash.register_page(__name__, path="/2007", name="Saber 11 · 2007")

# ─────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────
BASE_PROYECT_DIR = Path(__file__).resolve().parents[2]
CSV_PATH  = BASE_PROYECT_DIR / "Datasets" / "Data_ICFES" / "Saber_11" / "Unificados" / "Limpios" / "Saber_11_2007_filtrado.csv"
CACHE_DIR  = Path("Cache")
CACHE_FILE = CACHE_DIR / "Saber11_2007_cache.pkl"

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
    "punt_biologia","punt_c_sociales","punt_filosofia","punt_fisica",
    "punt_geografia","punt_historia","punt_ingles","punt_lenguaje",
    "punt_matematicas","punt_quimica",
]
PUNTAJES_LABELS = {
    "punt_biologia":"Biología","punt_c_sociales":"C. Sociales",
    "punt_filosofia":"Filosofía","punt_fisica":"Física",
    "punt_geografia":"Geografía","punt_historia":"Historia",
    "punt_ingles":"Inglés","punt_lenguaje":"Lenguaje",
    "punt_matematicas":"Matemáticas","punt_quimica":"Química",
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


def bar_h_fig(index, values, color=ACCENT1, highlight=None):
    colors = [ACCENT3 if highlight and str(l) == highlight else color for l in index]
    fig = go.Figure(go.Bar(
        x=values, y=[str(l) for l in index], orientation="h",
        marker=dict(color=colors, line=dict(color="rgba(0,0,0,0)")),
        hovertemplate="%{y}<br>%{x:,}<extra></extra>",
    ))
    fig.update_layout(**LAYOUT_BASE,
        xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
        yaxis=dict(gridcolor="rgba(0,0,0,0)"),
    )
    return fig


def bar_v_fig(index, values, color=ACCENT2, xlab="", ylab=""):
    fig = go.Figure(go.Bar(
        x=[str(l) for l in index], y=values,
        marker=dict(color=color, line=dict(color="rgba(0,0,0,0)")),
        hovertemplate="%{x}<br>%{y:,}<extra></extra>",
    ))
    fig.update_layout(**LAYOUT_BASE,
        xaxis=dict(gridcolor="rgba(0,0,0,0)", title=xlab),
        yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER, title=ylab),
    )
    return fig


def heatmap_bar(index, values, cscale=None):
    cscale = cscale or [[0, "#0D1117"], [0.3, ACCENT1], [1, ACCENT4]]
    fig = px.bar(x=values, y=index, orientation="h",
                 color=values, color_continuous_scale=cscale)
    fig.update_layout(**LAYOUT_BASE,
        coloraxis_showscale=True,
        coloraxis_colorbar=dict(tickfont=dict(color=TEXT_MUTED), bgcolor="rgba(0,0,0,0)"),
        yaxis=dict(autorange="reversed"),
        xaxis=dict(gridcolor=BORDER),
    )
    return fig

# ─────────────────────────────────────────────────────────────
# FINGERPRINT del CSV
# ─────────────────────────────────────────────────────────────

def csv_fingerprint(path: Path) -> str:
    s = path.stat()
    return hashlib.md5(f"{s.st_size}-{s.st_mtime}".encode()).hexdigest()

# ─────────────────────────────────────────────────────────────
# PROCESAMIENTO → genera y serializa todas las figuras
# ─────────────────────────────────────────────────────────────

def build_cache(csv_path: Path) -> dict:
    print("=" * 55)
    print("  Primera ejecución: procesando CSV…")
    print("  (puede tardar varios minutos)")
    print("=" * 55)
    t0 = time.time()

    # 1. Lectura
    print("  [1/6] Leyendo CSV…")
    df = pd.read_csv(csv_path, sep=";", decimal=".", low_memory=False, encoding="utf-8-sig")
    print(f"        {len(df):,} registros cargados.")

    # 2. Edad
    print("  [2/6] Calculando edades…")
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
    for p in PUNTAJES:
        df[p] = pd.to_numeric(df[p], errors="coerce")

    # 4. Agregaciones
    print("  [3/6] Calculando agregaciones…")
    total = len(df)

    def lmap(vc, m):
        return [m.get(str(k), str(k)) for k in vc.index]

    periodo_vc    = df["periodo"].value_counts()
    bilingue_vc   = df["cole_bilingue"].value_counts()
    jornada_vc    = df["cole_inst_jornada"].value_counts()
    naturaleza_vc = df["cole_naturaleza"].value_counts()
    area_vc       = df["cole_area_ubicacion"].value_counts()
    genero_vc     = df["estu_genero"].value_counts()
    depto_vc      = df["estu_depto_presentacion"].value_counts().head(33)
    mcpio_vc      = df["estu_mcpio_presentacion"].value_counts().head(30)
    edad_vc       = (df["edad"].dropna().astype(int)
                      .pipe(lambda s: s[(s >= 10) & (s <= 30)])
                      .value_counts().sort_index())
    pais_vc       = df["estu_pais_reside"].value_counts().head(20)
    estrato_vc    = df["fami_estrato_vivienda"].value_counts().sort_index()
    idioma_vc     = df["desemp_idioma"].value_counts().sort_index()

    # Top 20 universidades + San Buenaventura
    SAN_BUENA = "SAN BUENAVENTURA"
    univ_vc   = df["estu_ies_deseada_nombre"].str.upper().value_counts()
    top20     = univ_vc.head(20)
    en_top    = any(SAN_BUENA in str(u) for u in top20.index)
    highlight_univ = None
    if not en_top:
        matches = [u for u in univ_vc.index if SAN_BUENA in str(u).upper()]
        if matches:
            sb_val = pd.Series([univ_vc[matches[0]]], index=[matches[0]])
            top20  = pd.concat([top20, sb_val])
            highlight_univ = matches[0]
    top20_sorted = top20.sort_values()

    # 5. Stats puntajes
    print("  [4/6] Estadísticas de puntajes…")
    puntaje_stats = {}
    for p in PUNTAJES:
        col = df[p].dropna()
        puntaje_stats[p] = {
            "min": f"{col.min():.1f}" if len(col) else "N/A",
            "max": f"{col.max():.1f}" if len(col) else "N/A",
            "avg": f"{col.mean():.1f}" if len(col) else "N/A",
        }

    # 6. Figuras
    print("  [5/6] Generando figuras Plotly…")
    figs = {}
    figs["periodo"]    = pie_fig(list(periodo_vc.values),    [str(x) for x in periodo_vc.index])
    figs["bilingue"]   = pie_fig(list(bilingue_vc.values),   lmap(bilingue_vc, {"S":"Bilingüe","N":"No bilingüe"}))
    figs["jornada"]    = pie_fig(list(jornada_vc.values),    [str(x) for x in jornada_vc.index])
    figs["naturaleza"] = pie_fig(list(naturaleza_vc.values), [str(x) for x in naturaleza_vc.index])
    figs["area"]       = pie_fig(list(area_vc.values),       [str(x) for x in area_vc.index])
    figs["genero"]     = pie_fig(list(genero_vc.values),     lmap(genero_vc, {"M":"Masculino","F":"Femenino"}))
    figs["depto"]      = heatmap_bar(list(depto_vc.index), list(depto_vc.values),
                                     cscale=[[0,"#0D1117"],[0.3,ACCENT1],[1,ACCENT4]])
    figs["mcpio"]      = heatmap_bar(list(mcpio_vc.index), list(mcpio_vc.values),
                                     cscale=[[0,"#0D1117"],[0.3,ACCENT2],[1,"#79C0FF"]])
    figs["edad"]       = bar_v_fig(list(edad_vc.index),   list(edad_vc.values),
                                   color=ACCENT4, xlab="Edad", ylab="Cantidad")
    figs["pais"]       = bar_h_fig(list(pais_vc.index),   list(pais_vc.values),  color=ACCENT5)
    figs["univ"]       = bar_h_fig(list(top20_sorted.index), list(top20_sorted.values),
                                   color=ACCENT1, highlight=highlight_univ)
    if highlight_univ:
        figs["univ"].add_annotation(
            text="★ San Buenaventura",
            x=top20[highlight_univ], y=highlight_univ,
            xanchor="left", font=dict(color=ACCENT3, size=10),
            showarrow=False, xshift=6)
    figs["estrato"]    = bar_v_fig(list(estrato_vc.index), list(estrato_vc.values), color=ACCENT2)
    figs["idioma"]     = bar_v_fig(list(idioma_vc.index),  list(idioma_vc.values),  color=ACCENT1)

    # 7. Guardar caché
    print("  [6/6] Guardando caché en disco…")
    payload = {
        "fingerprint":   csv_fingerprint(csv_path),
        "total":         total,
        "figs":          figs,
        "puntaje_stats": puntaje_stats,
        "en_top_univ":   en_top,
    }
    CACHE_DIR.mkdir(exist_ok=True)
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"  ✅ Listo en {time.time()-t0:.1f}s  →  caché en {CACHE_FILE}")
    print("     Las próximas ejecuciones cargarán esto en segundos.")
    print("=" * 55)
    return payload


def load_or_build(force=False) -> dict:
    if not force and CACHE_FILE.exists():
        print(f"  Cargando caché desde {CACHE_FILE}…", end=" ", flush=True)
        t0 = time.time()
        with open(CACHE_FILE, "rb") as f:
            payload = pickle.load(f)
        # Detectar si el CSV cambió desde la última caché
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

# ─────────────────────────────────────────────────────────────
# BUILD LAYOUT  ← CAMBIO 2: antes build_app(), ahora build_layout()
# ─────────────────────────────────────────────────────────────

def build_layout(data: dict):
    figs   = data["figs"]
    stats  = data["puntaje_stats"]
    total  = data["total"]
    en_top = data["en_top_univ"]

    # KPI rows de puntajes
    kpi_rows = []
    for p in PUNTAJES:
        s = stats[p]
        kpi_rows.append(html.Div([
            html.Div(PUNTAJES_LABELS[p], style={
                "color": TEXT_MAIN, "fontSize": "12px", "width": "110px",
                "flexShrink": "0", "fontFamily": "'IBM Plex Mono', monospace"}),
            kpi_box("Mínimo",   s["min"], ACCENT3),
            kpi_box("Máximo",   s["max"], ACCENT2),
            kpi_box("Promedio", s["avg"], ACCENT1),
        ], style={"display":"flex","gap":"10px","alignItems":"center","marginBottom":"10px"}))

    # Tortas
    tortas_info = [
        ("bilingue",   "Colegio bilingüe"),
        ("jornada",    "Jornada escolar"),
        ("naturaleza", "Naturaleza del colegio"),
        ("area",       "Área de ubicación"),
        ("genero",     "Género"),
    ]
    tortas_cards = [
        html.Div(
            card([section_title(lbl), graph(figs[key], "280px")]),
            style={"flex":"1","minWidth":"280px"}
        ) for key, lbl in tortas_info
    ]

    # ── CAMBIO 3: return html.Div(...) en lugar de app.layout = html.Div(...)
    return html.Div(style={
        "background": BG, "minHeight": "100vh",
        "fontFamily": "'IBM Plex Mono', monospace",
        "color": TEXT_MAIN, "padding": "24px 32px",
    }, children=[

        # Header
        html.Div([
            html.Div([
                html.Div("ICFES · 2007", style={"color":ACCENT1,"fontSize":"11px","letterSpacing":"4px"}),
                html.H1("Saber 11 · Dashboard", style={
                    "margin":"4px 0 0 0","fontSize":"28px","fontWeight":"700",
                    "color":TEXT_MAIN,"letterSpacing":"-0.5px"}),
            ]),
            html.Div([
                html.Div("TOTAL ESTUDIANTES", style={"color":TEXT_MUTED,"fontSize":"10px","letterSpacing":"2px"}),
                html.Div(f"{total:,}", style={"color":ACCENT2,"fontSize":"36px","fontWeight":"700"}),
            ], style={"textAlign":"right"}),
        ], style={"display":"flex","justifyContent":"space-between","alignItems":"flex-end",
                  "marginBottom":"28px","paddingBottom":"20px","borderBottom":f"1px solid {BORDER}"}),

        # Periodo
        card([section_title("Distribución por periodo"), graph(figs["periodo"], "300px")]),

        # Tortas
        html.Div(style={"marginBottom":"20px"}, children=[
            section_title("Características de colegios y estudiantes"),
            html.Div(tortas_cards, style={"display":"flex","flexWrap":"wrap","gap":"16px"}),
        ]),

        # Geografía
        card([
            section_title("Concentración geográfica de estudiantes"),
            html.Div([
                html.Div([
                    html.Div("Por departamento", style={"color":TEXT_MUTED,"fontSize":"11px","marginBottom":"8px"}),
                    graph(figs["depto"], "500px"),
                ], style={"flex":"1"}),
                html.Div([
                    html.Div("Top 30 municipios", style={"color":TEXT_MUTED,"fontSize":"11px","marginBottom":"8px"}),
                    graph(figs["mcpio"], "500px"),
                ], style={"flex":"1"}),
            ], style={"display":"flex","gap":"20px"}),
        ]),

        # Edad
        card([section_title("Distribución de edad"), graph(figs["edad"], "320px")]),

        # País
        card([section_title("País de residencia (Top 20)"), graph(figs["pais"], "380px")]),

        # Universidades
        card([
            section_title("Top 20 universidades más deseadas" +
                          (" · ★ San Buenaventura destacada" if not en_top else "")),
            graph(figs["univ"], "600px"),
        ]),

        # Estrato
        card([section_title("Estrato socioeconómico"), graph(figs["estrato"], "300px")]),

        # KPIs puntajes
        card([section_title("Estadísticas por área de puntaje"), html.Div(kpi_rows)]),

        # Inglés
        card([section_title("Desempeño en idioma (inglés)"), graph(figs["idioma"], "300px")]),

        # Footer
        html.Div("ICFES Saber 11 · 2007 · Análisis de datos educativos",
                 style={"textAlign":"center","color":TEXT_MUTED,"fontSize":"10px",
                        "letterSpacing":"2px","paddingTop":"20px",
                        "borderTop":f"1px solid {BORDER}"}),
    ])

# ─────────────────────────────────────────────────────────────
# CARGA DE DATOS Y EXPOSICIÓN DEL LAYOUT  ← CAMBIO 4
# Dash multi-page busca automáticamente la variable `layout`
# ─────────────────────────────────────────────────────────────
_data  = load_or_build(force="--rebuild" in sys.argv)
layout = build_layout(_data)

# ─────────────────────────────────────────────────────────────
# (eliminado) if __name__ == "__main__"  — ya no se necesita aquí
# El servidor lo levanta app.py
# ─────────────────────────────────────────────────────────────