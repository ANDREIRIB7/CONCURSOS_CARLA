"""
╔══════════════════════════════════════════════════════════════╗
║  ConcursoFocus — Sistema de Estudos para Concursos Públicos  ║
╠══════════════════════════════════════════════════════════════╣
║  PERSISTÊNCIA (escolha UMA opção no Streamlit Secrets):      ║
║                                                              ║
║  ── OPÇÃO A: Supabase (recomendado, 100% grátis) ──────────  ║
║  1. Crie conta em https://supabase.com (grátis)              ║
║  2. New Project → SQL Editor → execute o SQL abaixo:         ║
║                                                              ║
║    CREATE TABLE IF NOT EXISTS materias (                     ║
║      id SERIAL PRIMARY KEY,                                  ║
║      dados JSONB NOT NULL DEFAULT '[]'::jsonb,               ║
║      updated_at TIMESTAMPTZ DEFAULT NOW()                    ║
║    );                                                        ║
║    INSERT INTO materias (dados) VALUES ('[]'::jsonb);        ║
║                                                              ║
║    CREATE TABLE IF NOT EXISTS sessoes (                      ║
║      id SERIAL PRIMARY KEY,                                  ║
║      dados JSONB NOT NULL,                                   ║
║      created_at TIMESTAMPTZ DEFAULT NOW()                    ║
║    );                                                        ║
║                                                              ║
║  3. Settings → API → copie URL e anon key                    ║
║  4. Streamlit Cloud → App Settings → Secrets:                ║
║    [supabase]                                                ║
║    url = "https://xxxx.supabase.co"                          ║
║    key = "eyJhbGci..."                                       ║
║                                                              ║
║  ── OPÇÃO B: GitHub Gist (alternativo) ────────────────────  ║
║    [gist]                                                    ║
║    token   = "ghp_xxxx"                                      ║
║    gist_id = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"              ║
║    (crie o Gist com materias.json e sessoes.json = [])       ║
╚══════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import json, os, csv, io
from datetime import datetime, date, timedelta

# ─────────────────────────────────────────────────────────────
#  CONFIGURAÇÃO DA PÁGINA  (deve ser a 1ª chamada Streamlit)
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Concursos",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
#  CAMADA DE PERSISTÊNCIA
# ─────────────────────────────────────────────────────────────

# ── Supabase ──────────────────────────────────────────────────
def _supa_cfg():
    try:
        s = st.secrets.get("supabase", {})
        u, k = s.get("url"), s.get("key")
        return (u.rstrip("/"), k) if u and k else None
    except Exception:
        return None

def _supa_get_materias() -> list:
    cfg = _supa_cfg()
    if not cfg: return None
    try:
        import urllib.request
        url, key = cfg
        req = urllib.request.Request(
            f"{url}/rest/v1/materias?select=dados&order=id.desc&limit=1",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            rows = json.loads(r.read())
        return rows[0]["dados"] if rows else []
    except Exception:
        return None

def _supa_set_materias(data: list):
    cfg = _supa_cfg()
    if not cfg: return
    try:
        import urllib.request
        url, key = cfg
        # upsert row id=1
        body = json.dumps({"id": 1, "dados": data}).encode()
        req = urllib.request.Request(
            f"{url}/rest/v1/materias",
            data=body,
            headers={
                "apikey": key, "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates",
            },
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass

def _supa_get_sessoes() -> list:
    cfg = _supa_cfg()
    if not cfg: return None
    try:
        import urllib.request
        url, key = cfg
        req = urllib.request.Request(
            f"{url}/rest/v1/sessoes?select=dados&order=id.asc",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            rows = json.loads(r.read())
        return [row["dados"] for row in rows]
    except Exception:
        return None

def _supa_add_sessao(sessao: dict):
    cfg = _supa_cfg()
    if not cfg: return False
    try:
        import urllib.request
        url, key = cfg
        body = json.dumps({"dados": sessao}).encode()
        req = urllib.request.Request(
            f"{url}/rest/v1/sessoes",
            data=body,
            headers={
                "apikey": key, "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception:
        return False

# ── GitHub Gist ───────────────────────────────────────────────
def _gist_cfg():
    try:
        g = st.secrets.get("gist", {})
        t, gid = g.get("token"), g.get("gist_id")
        return (t, gid) if t and gid else None
    except Exception:
        return None

def _gist_load(filename: str) -> list:
    cfg = _gist_cfg()
    if not cfg: return None
    try:
        import urllib.request
        t, gid = cfg
        req = urllib.request.Request(
            f"https://api.github.com/gists/{gid}",
            headers={"Authorization": f"token {t}", "User-Agent": "ConcursoFocus"},
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        return json.loads(data["files"][filename]["content"])
    except Exception:
        return None

def _gist_save(filename: str, data: list):
    cfg = _gist_cfg()
    if not cfg: return
    try:
        import urllib.request
        t, gid = cfg
        body = json.dumps({"files": {filename: {"content": json.dumps(data, ensure_ascii=False, indent=2, default=str)}}}).encode()
        req = urllib.request.Request(
            f"https://api.github.com/gists/{gid}",
            data=body,
            headers={"Authorization": f"token {t}", "User-Agent": "ConcursoFocus", "Content-Type": "application/json"},
            method="PATCH",
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass

# ── Local (desenvolvimento) ───────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
MAT_FILE = os.path.join(DATA_DIR, "materias.json")
SES_FILE = os.path.join(DATA_DIR, "sessoes.json")

def _local_load(path):
    try:
        with open(path, encoding="utf-8") as f: return json.load(f)
    except Exception: return []

def _local_save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

# ── API pública ───────────────────────────────────────────────
if "db_mat" not in st.session_state: st.session_state.db_mat = None
if "db_ses" not in st.session_state: st.session_state.db_ses = None

def get_materias(force=False) -> list:
    if st.session_state.db_mat is None or force:
        v = _supa_get_materias()
        if v is None: v = _gist_load("materias.json")
        if v is None: v = _local_load(MAT_FILE)
        st.session_state.db_mat = v
    return st.session_state.db_mat

def get_sessoes(force=False) -> list:
    if st.session_state.db_ses is None or force:
        v = _supa_get_sessoes()
        if v is None: v = _gist_load("sessoes.json")
        if v is None: v = _local_load(SES_FILE)
        st.session_state.db_ses = v
    return st.session_state.db_ses

def save_materias(data: list):
    st.session_state.db_mat = data
    if _supa_cfg():
        _supa_set_materias(data)
    elif _gist_cfg():
        _gist_save("materias.json", data)
    else:
        _local_save(MAT_FILE, data)

def add_sessao(s: dict):
    ses = get_sessoes()
    ses.append(s)
    st.session_state.db_ses = ses
    if _supa_cfg():
        _supa_add_sessao(s)
    elif _gist_cfg():
        _gist_save("sessoes.json", ses)
    else:
        _local_save(SES_FILE, ses)

# ─────────────────────────────────────────────────────────────
#  CSS — NUCLEAR FIX para inputs brancos + tema navy blue
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

/* ══ RESET BASE ══════════════════════════════════════════════ */
html, body, [class*="css"], .stApp * {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  box-sizing: border-box;
}
.stApp                         { background: #1a1f3a !important; }
.block-container               { padding-top: 1.2rem !important; max-width: 1200px !important; }
header[data-testid="stHeader"] { display: none !important; }
footer                         { display: none !important; }
#MainMenu                      { display: none !important; }

/* ══ SIDEBAR ═════════════════════════════════════════════════ */
section[data-testid="stSidebar"]          { background: #1e2447 !important; border-right: 1px solid rgba(255,255,255,.07) !important; }
section[data-testid="stSidebar"] *        { color: #a0aac8 !important; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3       { color: #e8ecff !important; }

/* ══ MÉTRICAS ════════════════════════════════════════════════ */
[data-testid="stMetric"]                  { background: #232b50 !important; border: 1px solid rgba(255,255,255,.07) !important; border-radius: 12px !important; padding: 14px 16px !important; }
[data-testid="stMetricLabel"] p           { color: #6b7a9e !important; font-size: 11px !important; text-transform: uppercase !important; letter-spacing: .5px !important; margin: 0 !important; }
[data-testid="stMetricValue"]             { color: #e8ecff !important; font-size: 24px !important; font-weight: 700 !important; }
[data-testid="stMetricDelta"] *           { font-size: 11px !important; }

/* ══ FORCE-DARK em TODOS os inputs nativos ═══════════════════
   Streamlit injeta fundo branco via inline style em alguns
   componentes. Usamos !important em todos os seletores.       */
input,
input[type="text"],
input[type="number"],
input[type="date"],
input[type="time"],
input[type="datetime-local"],
input[type="email"],
input[type="password"],
input[type="search"],
textarea {
  background-color: #1c2340 !important;
  background:       #1c2340 !important;
  color:            #e8ecff !important;
  border:           1px solid rgba(91,124,253,.28) !important;
  border-radius:    9px !important;
  caret-color:      #7b96ff !important;
  -webkit-text-fill-color: #e8ecff !important;
}
input::placeholder, textarea::placeholder {
  color: #3e4870 !important;
  -webkit-text-fill-color: #3e4870 !important;
  opacity: 1 !important;
}
input:focus, textarea:focus {
  border-color: #5b7cfd !important;
  box-shadow: 0 0 0 3px rgba(91,124,253,.15) !important;
  outline: none !important;
}

/* Wrappers do Streamlit que ganham fundo branco */
div[data-testid="stTextInput"]    > div > div,
div[data-testid="stNumberInput"]  > div > div,
div[data-testid="stTextArea"]     > div > div,
div[data-testid="stDateInput"]    > div > div,
div[data-testid="stTimeInput"]    > div > div {
  background-color: #1c2340 !important;
  background:       #1c2340 !important;
  border:           1px solid rgba(91,124,253,.28) !important;
  border-radius:    9px !important;
}
/* remove borda dupla */
div[data-testid="stTextInput"]    > div > div > input,
div[data-testid="stNumberInput"]  > div > div > input,
div[data-testid="stTextArea"]     > div > div > textarea {
  border: none !important;
  box-shadow: none !important;
}

/* ══ SELECTBOX ════════════════════════════════════════════════ */
div[data-baseweb="select"] > div {
  background-color: #1c2340 !important;
  background:       #1c2340 !important;
  border:           1px solid rgba(91,124,253,.28) !important;
  border-radius:    9px !important;
  color:            #e8ecff !important;
}
div[data-baseweb="select"] div[class*="singleValue"],
div[data-baseweb="select"] div[class*="placeholder"],
div[data-baseweb="select"] input {
  color:            #e8ecff !important;
  -webkit-text-fill-color: #e8ecff !important;
  background:       transparent !important;
}
div[data-baseweb="select"] div[class*="placeholder"] {
  color:            #3e4870 !important;
  -webkit-text-fill-color: #3e4870 !important;
}
/* dropdown aberto */
div[data-baseweb="popover"],
div[data-baseweb="menu"],
div[data-baseweb="popover"] ul {
  background-color: #1e2447 !important;
  border:           1px solid rgba(91,124,253,.2) !important;
  border-radius:    10px !important;
}
div[data-baseweb="option"] {
  background-color: #1e2447 !important;
  color:            #a0aac8 !important;
}
div[data-baseweb="option"]:hover,
div[data-baseweb="option"][aria-selected="true"] {
  background-color: #2d3561 !important;
  color:            #e8ecff !important;
}
div[data-baseweb="select"] svg { fill: #6b7a9e !important; }

/* ══ LABELS ══════════════════════════════════════════════════ */
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label,
label {
  color:           #6b7a9e !important;
  font-size:       11px !important;
  font-weight:     600 !important;
  text-transform:  uppercase !important;
  letter-spacing:  .5px !important;
}

/* ══ BOTÕES ══════════════════════════════════════════════════ */
.stButton > button,
[data-testid="stFormSubmitButton"] > button {
  background:   linear-gradient(135deg,#5b7cfd,#6c63ff) !important;
  color:        #ffffff !important;
  border:       none !important;
  border-radius:9px !important;
  font-weight:  700 !important;
  font-size:    13px !important;
  box-shadow:   0 4px 14px rgba(91,124,253,.3) !important;
  padding:      10px 20px !important;
  transition:   filter .18s, transform .18s !important;
}
.stButton > button:hover,
[data-testid="stFormSubmitButton"] > button:hover {
  filter: brightness(1.12) !important;
  transform: translateY(-1px) !important;
}
[data-testid="stDownloadButton"] > button {
  background:   rgba(255,255,255,.06) !important;
  color:        #a0aac8 !important;
  border:       1px solid rgba(255,255,255,.12) !important;
  box-shadow:   none !important;
}
[data-testid="stFormSubmitButton"] > button { width: 100% !important; padding: 12px !important; }

/* ══ CHECKBOX & RADIO ════════════════════════════════════════ */
.stCheckbox span, .stRadio span   { color: #a0aac8 !important; -webkit-text-fill-color: #a0aac8 !important; }
.stCheckbox input[type="checkbox"] { accent-color: #5b7cfd !important; }
.stRadio [data-testid="stMarkdownContainer"] p { color: #a0aac8 !important; font-size: 13px !important; font-weight: 500 !important; text-transform: none !important; letter-spacing: 0 !important; }
.stRadio > div { gap: 6px !important; }

/* ══ NUMBER INPUT buttons ════════════════════════════════════ */
div[data-testid="stNumberInput"] button {
  background: #2d3561 !important;
  color:      #e8ecff !important;
  border:     none !important;
  border-radius: 6px !important;
}

/* ══ DATE / TIME ─ ícones e picker ═══════════════════════════ */
div[data-testid="stDateInput"] button,
div[data-testid="stTimeInput"] button {
  color:      #6b7a9e !important;
  background: transparent !important;
  border:     none !important;
}

/* ══ DATAFRAME ════════════════════════════════════════════════ */
[data-testid="stDataFrame"]           { background: #1e2447 !important; border-radius: 12px !important; overflow: hidden; }
[data-testid="stDataFrame"] *         { background: #1e2447 !important; color: #a0aac8 !important; }
[data-testid="stDataFrame"] th        { color: #6b7a9e !important; font-size: 11px !important; text-transform: uppercase !important; background: #1a1f3a !important; }
[data-testid="stDataFrame"] tr:hover td { background: rgba(91,124,253,.05) !important; }

/* ══ FORM container ══════════════════════════════════════════ */
[data-testid="stForm"] {
  background:   #232b50 !important;
  border:       1px solid rgba(255,255,255,.07) !important;
  border-radius:14px !important;
  padding:      20px !important;
}

/* ══ ALERTS ══════════════════════════════════════════════════ */
[data-testid="stAlert"]  { border-radius: 10px !important; }
.stSuccess               { background: rgba(74,201,138,.1) !important; border-color: rgba(74,201,138,.3) !important; }
.stSuccess *             { color: #4ac98a !important; }
.stWarning               { background: rgba(245,166,35,.1) !important; }
.stWarning *             { color: #f5a623 !important; }
.stInfo                  { background: rgba(91,124,253,.1) !important; }
.stInfo *                { color: #7b96ff !important; }

/* ══ DIVIDER & TEXTOS ════════════════════════════════════════ */
hr                       { border-color: rgba(255,255,255,.07) !important; }
p, li                    { color: #a0aac8 !important; -webkit-text-fill-color: #a0aac8; }
h1, h2, h3               { color: #e8ecff !important; -webkit-text-fill-color: #e8ecff !important; }

/* ══ EXPANDER ════════════════════════════════════════════════ */
[data-testid="stExpander"] {
  background:   #232b50 !important;
  border:       1px solid rgba(255,255,255,.07) !important;
  border-radius:12px !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary * { color: #e8ecff !important; }

/* ══ TABS ════════════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"]           { background: #1e2447 !important; border-radius: 10px !important; gap: 4px !important; padding: 4px !important; }
.stTabs [data-baseweb="tab"]                { background: transparent !important; border-radius: 7px !important; color: #6b7a9e !important; font-weight: 600 !important; font-size: 13px !important; }
.stTabs [aria-selected="true"]              { background: #232b50 !important; color: #7b96ff !important; }
.stTabs [data-baseweb="tab-panel"]          { background: transparent !important; padding-top: .8rem !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
#  ALGORITMO DE SUGESTÃO
# ─────────────────────────────────────────────────────────────
def calcular_score(materia, sessoes, modo):
    nome     = materia["nome"]
    prio     = materia.get("prioridade", 2)
    q_edital = materia.get("questoes_edital", 10)
    sm       = [s for s in sessoes if s.get("materia") == nome]
    dias     = (datetime.now() - max([datetime.fromisoformat(s["data_inicio"]) for s in sm])).days if sm else 30
    fator    = 1.0
    if modo == "questoes":
        ac  = sum(s.get("acertos", 0) for s in sm)
        tot = ac + sum(s.get("erros", 0) for s in sm)
        if tot > 0: fator = 2.0 - (ac / tot)
    return {1: 3.0, 2: 2.0, 3: 1.0}.get(prio, 2.0) * (q_edital / 10) * (1 + dias / 7) * fator

def sugerir(modo, turbo):
    mat = get_materias()
    ses = get_sessoes()
    if not mat: return None
    cands  = mat if turbo else ([m for m in mat if m.get("prioridade", 2) <= 2] or mat)
    scores = sorted([(m, calcular_score(m, ses, modo)) for m in cands], key=lambda x: x[1], reverse=True)
    best   = scores[0][0]
    sm     = [s for s in ses if s.get("materia") == best["nome"]]
    cc     = {}
    for s in sm: cc[s.get("conteudo", "")] = cc.get(s.get("conteudo", ""), 0) + 1
    conts  = sorted(best.get("conteudos", []), key=lambda c: c.get("prioridade", 2) * 10 - cc.get(c["nome"], 0), reverse=True)
    return {
        "materia": best["nome"],
        "conteudo": conts[0]["nome"] if conts else "Geral",
        "prioridade": best.get("prioridade", 2),
        "questoes_edital": best.get("questoes_edital", 0),
        "top5": [{"nome": m["nome"], "score": round(s, 1)} for m, s in scores[:5]],
    }

# ─────────────────────────────────────────────────────────────
#  DADOS DO DASHBOARD
# ─────────────────────────────────────────────────────────────
def calc_dash():
    ses   = get_sessoes()
    hoje  = date.today().isoformat()
    s_ini = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    th    = sum(s.get("duracao_min", 0) for s in ses) / 60
    ac    = sum(s.get("acertos", 0) for s in ses)
    er    = sum(s.get("erros", 0) for s in ses)
    tq    = ac + er
    taxa  = round(ac / tq * 100, 1) if tq else 0
    hj    = sum(s.get("duracao_min", 0) for s in ses if s.get("data_inicio", "").startswith(hoje)) / 60
    sem   = sum(s.get("duracao_min", 0) for s in ses if s.get("data_inicio", "") >= s_ini) / 60
    streak = 0
    for i in range(30):
        d = (date.today() - timedelta(days=i)).isoformat()
        if any(s.get("data_inicio", "").startswith(d) for s in ses):
            streak += 1
        else:
            break
    pm = {}
    for s in ses:
        m = s.get("materia", "?")
        pm.setdefault(m, {"horas": 0, "acertos": 0, "erros": 0})
        pm[m]["horas"]   += s.get("duracao_min", 0) / 60
        pm[m]["acertos"] += s.get("acertos", 0)
        pm[m]["erros"]   += s.get("erros", 0)
    for m in pm:
        t = pm[m]["acertos"] + pm[m]["erros"]
        pm[m]["taxa"]  = round(pm[m]["acertos"] / t * 100, 1) if t else 0
        pm[m]["horas"] = round(pm[m]["horas"], 1)
    evo = {}
    for i in range(13, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        evo[d] = 0.0
    for s in ses:
        d = s.get("data_inicio", "")[:10]
        if d in evo: evo[d] = round(evo[d] + s.get("duracao_min", 0) / 60, 2)
    return {
        "th": round(th, 1), "taxa": taxa, "tq": tq,
        "streak": streak, "hj": round(hj, 1), "sem": round(sem, 1),
        "pm": pm, "evo": evo,
        "recentes": sorted(ses, key=lambda x: x.get("data_inicio", ""), reverse=True)[:5],
    }

# ─────────────────────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────────────────────
def _card(txt): return f"<div style='background:#232b50;border-radius:9px;padding:9px 12px;display:flex;justify-content:space-between;margin-bottom:5px'>{txt}</div>"

with st.sidebar:
    st.markdown("""
    <div style='padding:4px 0 16px'>
      <div style='display:flex;align-items:center;gap:10px'>
        <div style='width:36px;height:36px;background:linear-gradient(135deg,#5b7cfd,#9b72f7);border-radius:10px;
                    display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0'>⚡</div>
        <div>
          <div style='font-size:15px;font-weight:700;color:#e8ecff !important'>ConcursoFocus</div>
          <div style='font-size:10px;color:#6b7a9e'>Sistema de Aprovação</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)
    st.divider()

    pagina = st.radio(
        "nav", label_visibility="collapsed",
        options=["📊 Dashboard", "🎯 Estudar", "✏️ Registrar", "📚 Matérias", "🗂️ Histórico"],
    )

    st.divider()
    d = calc_dash()
    st.markdown("<div style='font-size:10px;color:#6b7a9e;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px'>Resumo Rápido</div>", unsafe_allow_html=True)
    st.markdown(
        _card(f"<span style='font-size:12px;color:#6b7a9e'>Horas totais</span><span style='font-size:12px;font-weight:700;color:#7b96ff'>{d['th']}h</span>") +
        _card(f"<span style='font-size:12px;color:#6b7a9e'>Taxa de acerto</span><span style='font-size:12px;font-weight:700;color:#4ac98a'>{d['taxa']}%</span>") +
        _card(f"<span style='font-size:12px;color:#6b7a9e'>Sequência</span><span style='font-size:12px;font-weight:700;color:#f5a623'>{d['streak']} 🔥</span>"),
        unsafe_allow_html=True,
    )

    # indicador de backend
    st.markdown("<br>", unsafe_allow_html=True)
    if _supa_cfg():
        st.markdown("<div style='font-size:10px;color:#4ac98a;text-align:center'>🟢 Supabase conectado</div>", unsafe_allow_html=True)
    elif _gist_cfg():
        st.markdown("<div style='font-size:10px;color:#f5a623;text-align:center'>🟡 GitHub Gist</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='font-size:10px;color:#f56565;text-align:center'>🔴 Somente local</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
#  HELPERS DE UI
# ─────────────────────────────────────────────────────────────
def banner_card(titulo, subtitulo, emoji="🎯"):
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#2a3578,#3040a0,#4050c0);border-radius:14px;
                padding:20px 24px;margin-bottom:20px;border:1px solid rgba(91,124,253,.3);
                position:relative;overflow:hidden'>
      <div style='font-size:18px;font-weight:700;color:#fff;margin-bottom:3px'>{titulo}</div>
      <div style='font-size:12.5px;color:rgba(255,255,255,.65)'>{subtitulo}</div>
      <div style='position:absolute;right:20px;bottom:-5px;font-size:56px;opacity:.18'>{emoji}</div>
    </div>""", unsafe_allow_html=True)

def section_card(conteudo_html, titulo=None, cor_dot="#5b7cfd"):
    header = f"<div style='font-size:13px;font-weight:700;color:#e8ecff;margin-bottom:14px;display:flex;align-items:center;gap:7px'><span style='width:7px;height:7px;border-radius:50%;background:{cor_dot};display:inline-block'></span>{titulo}</div>" if titulo else ""
    st.markdown(f"<div style='background:#232b50;border:1px solid rgba(255,255,255,.07);border-radius:12px;padding:18px'>{header}{conteudo_html}</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
#  PÁGINA: DASHBOARD
# ─────────────────────────────────────────────────────────────
if pagina == "📊 Dashboard":
    hoje_br = date.today().strftime("%A, %d de %B de %Y").capitalize()
    st.markdown(f"<h2 style='margin-bottom:2px'>Painel de Desempenho</h2><p style='color:#6b7a9e;margin-bottom:18px'>{hoje_br}</p>", unsafe_allow_html=True)

    d = calc_dash()
    msg = (f"🔥 {d['streak']} dias seguidos! Modo aprovação ativado!"
           if d["streak"] >= 7 else
           f"{d['th']}h estudadas · {d['taxa']}% de acerto geral"
           if d["th"] > 0 else
           "Nenhuma sessão ainda — comece hoje! 🚀")
    banner_card("Bom estudo, Carla! 👋", msg)

    # Métricas
    cols = st.columns(6)
    metrics = [
        ("⏱️ Horas Totais",  f"{d['th']}h"),
        ("✅ Taxa Acerto",   f"{d['taxa']}%"),
        ("📝 Questões",      d["tq"]),
        ("🔥 Dias Seguidos", d["streak"]),
        ("📅 Hoje",          f"{d['hj']}h"),
        ("📆 Semana",        f"{d['sem']}h"),
    ]
    for col, (lbl, val) in zip(cols, metrics):
        col.metric(lbl, val)

    st.markdown("<br>", unsafe_allow_html=True)

    # Gráfico + Streak
    col1, col2 = st.columns([3, 1])
    with col1:
        evo   = d["evo"]
        dts   = list(evo.keys())
        vals  = [evo[k] for k in dts]
        maxv  = max(vals) if any(v > 0 for v in vals) else 1
        lbls  = [k[5:].replace("-", "/") for k in dts]
        bars  = "<div style='display:flex;align-items:flex-end;gap:4px;height:90px;margin-top:8px'>"
        for lbl, v in zip(lbls, vals):
            pct = max(v / maxv * 100, v > 0 and 5 or 0)
            bg  = "linear-gradient(180deg,#7b96ff,#5b7cfd)" if v > 0 else "#2d3561"
            bars += f"<div style='flex:1;display:flex;flex-direction:column;align-items:center;gap:3px'><div style='width:100%;height:{pct}%;background:{bg};border-radius:3px 3px 0 0;min-height:3px' title='{lbl}: {v}h'></div><div style='font-size:8px;color:#6b7a9e'>{lbl}</div></div>"
        bars += "</div>"
        section_card(bars, "📈 Horas de Estudo — 14 dias")

    with col2:
        sk_msg = ("Comece hoje!" if d["streak"] == 0
                  else "Ótimo começo!" if d["streak"] < 3
                  else "Pegando ritmo! 🔥" if d["streak"] < 7
                  else "Campeão! 💪" if d["streak"] < 14
                  else "Imparável! 🏆")
        section_card(f"""
          <div style='text-align:center;padding:8px 0'>
            <div style='font-size:28px;margin-bottom:4px'>🔥</div>
            <div style='font-size:46px;font-weight:800;background:linear-gradient(135deg,#f5a623,#f56565);
                        -webkit-background-clip:text;-webkit-text-fill-color:transparent;line-height:1'>{d['streak']}</div>
            <div style='font-size:11px;color:#6b7a9e;margin-top:3px'>dias consecutivos</div>
            <div style='font-size:12px;color:#a0aac8;margin-top:9px'>{sk_msg}</div>
          </div>""", "🔥 Sequência", "#f5a623")

    st.markdown("<br>", unsafe_allow_html=True)

    # Tabela por matéria
    if d["pm"]:
        import pandas as pd
        rows = []
        for m, r in sorted(d["pm"].items(), key=lambda x: x[1]["horas"], reverse=True):
            tot = r["acertos"] + r["erros"]
            rows.append({
                "Matéria": m,
                "Horas": f"{r['horas']}h",
                "Questões": tot,
                "Taxa de Acerto": f"{r['taxa']}%" if tot > 0 else "—",
                "Status": "🟢 Bom" if r["taxa"] >= 70 else "🟡 Médio" if r["taxa"] >= 50 and tot > 0 else "🔴 Atenção" if tot > 0 else "⚪ Sem dados",
            })
        section_card(
            "<div id='df-mat'></div>",
            "📚 Desempenho por Matéria", "#9b72f7"
        )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Sessões recentes
    if d["recentes"]:
        st.markdown("<br>", unsafe_allow_html=True)
        rows_html = ""
        for s in d["recentes"]:
            dt  = datetime.fromisoformat(s["data_inicio"]).strftime("%d/%m %H:%M")
            dur = f"{s.get('duracao_min',0)}min" if s.get("duracao_min", 0) < 60 else f"{s.get('duracao_min',0)/60:.1f}h"
            q   = s.get("acertos", 0) + s.get("erros", 0)
            q_s = f" · {s['acertos']}/{q} acertos" if q > 0 else ""
            enc = " · <span style='color:#4ac98a'>✓ Concluído</span>" if s.get("encerrou_assunto") else ""
            ico = "🧩" if s.get("tipo") == "questoes" else "📖"
            rows_html += f"""
            <div style='display:flex;align-items:center;gap:11px;padding:9px 0;border-bottom:1px solid rgba(255,255,255,.05)'>
              <div style='width:34px;height:34px;border-radius:9px;background:rgba(91,124,253,.14);
                          display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0'>{ico}</div>
              <div style='flex:1'>
                <div style='font-size:12.5px;font-weight:600;color:#e8ecff'>{s['materia']} · <span style='font-weight:400'>{s['conteudo']}</span></div>
                <div style='font-size:11px;color:#6b7a9e'>{dt} · {dur}{q_s}{enc}</div>
              </div>
            </div>"""
        section_card(rows_html, "🕒 Últimas Sessões", "#47c8f5")

# ─────────────────────────────────────────────────────────────
#  PÁGINA: ESTUDAR
# ─────────────────────────────────────────────────────────────
elif pagina == "🎯 Estudar":
    st.markdown("<h2 style='margin-bottom:2px'>Iniciar Estudo</h2><p style='color:#6b7a9e;margin-bottom:18px'>Algoritmo de revisão espaçada + peso edital</p>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1: modo  = st.radio("Modo", ["📖 Estudar Matéria", "🧩 Resolver Questões"], horizontal=True, key="rm")
    with c2: plano = st.radio("Plano", ["📋 Pré-Edital", "⚡ Pós-Edital Turbo"],       horizontal=True, key="rp")
    modo_k  = "questoes" if "Questões" in modo  else "materia"
    turbo_k = "Turbo" in plano

    sug = sugerir(modo_k, turbo_k)
    if not sug:
        st.warning("⚠️ Nenhuma matéria cadastrada. Vá até **📚 Matérias** e importe uma planilha CSV.")
    else:
        prio_lbl = {1: "🔴 Alta", 2: "🟡 Média", 3: "⚪ Baixa"}
        st.markdown(f"""
        <div style='background:linear-gradient(135deg,#2a3578,#1e2a60 60%,#232b52);
                    border:1px solid rgba(91,124,253,.35);border-radius:14px;padding:24px;margin:14px 0;
                    position:relative;overflow:hidden'>
          <div style='position:absolute;top:-50px;right:-40px;width:160px;height:160px;
                      background:radial-gradient(circle,rgba(91,124,253,.18) 0%,transparent 70%)'></div>
          <div style='font-size:9.5px;font-weight:700;text-transform:uppercase;letter-spacing:2px;color:#7b96ff;margin-bottom:7px'>📌 Sugestão do Sistema</div>
          <div style='font-size:22px;font-weight:700;color:#fff;margin-bottom:5px'>{sug['materia']}</div>
          <div style='font-size:13px;color:#a0aac8;margin-bottom:14px'>{sug['conteudo']}</div>
          <div style='display:flex;gap:8px;flex-wrap:wrap;margin-bottom:18px'>
            <span style='background:rgba(255,255,255,.08);border-radius:20px;padding:3px 11px;font-size:11px;color:#a0aac8'>📋 {sug['questoes_edital']} questões no edital</span>
            <span style='background:rgba(255,255,255,.08);border-radius:20px;padding:3px 11px;font-size:11px;color:#a0aac8'>{prio_lbl.get(sug['prioridade'], '')}</span>
            <span style='background:rgba(255,255,255,.08);border-radius:20px;padding:3px 11px;font-size:11px;color:#a0aac8'>{'🧩 Questões' if modo_k=='questoes' else '📖 Teoria'}</span>
            <span style='background:rgba(255,255,255,.08);border-radius:20px;padding:3px 11px;font-size:11px;color:#a0aac8'>{'⚡ Turbo' if turbo_k else '📋 Pré-Edital'}</span>
          </div>
        </div>""", unsafe_allow_html=True)

        bc1, bc2, _ = st.columns([1.2, 1, 3])
        with bc1:
            if st.button("▶ Usar esta sugestão", key="btn_usar"):
                st.session_state["sug_mat"]  = sug["materia"]
                st.session_state["sug_cont"] = sug["conteudo"]
                st.session_state["sug_tipo"] = modo_k
                st.success("✅ Sugestão selecionada! Vá para **✏️ Registrar** para lançar os dados.")
        with bc2:
            if st.button("↻ Nova sugestão", key="btn_nova"):
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        rows_t5 = "".join([f"""
          <div style='display:flex;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.05)'>
            <div style='width:20px;font-size:11px;color:#6b7a9e;font-weight:600'>{i+1}</div>
            <div style='flex:1;font-size:12.5px;color:#a0aac8'>{x['nome']}</div>
            <span style='padding:2px 9px;border-radius:20px;font-size:11px;font-weight:600;background:rgba(91,124,253,.14);color:#7b96ff'>{x['score']} pts</span>
          </div>""" for i, x in enumerate(sug["top5"])])
        section_card(rows_t5, "🏆 Ranking de Prioridade", "#f5a623")

# ─────────────────────────────────────────────────────────────
#  PÁGINA: REGISTRAR
# ─────────────────────────────────────────────────────────────
elif pagina == "✏️ Registrar":
    st.markdown("<h2 style='margin-bottom:2px'>Registrar Sessão</h2><p style='color:#6b7a9e;margin-bottom:18px'>Lançar resultado da bateria de estudos</p>", unsafe_allow_html=True)

    materias = get_materias()
    if not materias:
        st.warning("⚠️ Nenhuma matéria cadastrada. Vá até **📚 Matérias** primeiro.")
        st.stop()

    with st.form("form_sessao", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            tipo = st.selectbox("Tipo de Sessão", ["📖 Estudo de Matéria", "🧩 Resolução de Questões"])
        with c2:
            nomes   = [m["nome"] for m in materias]
            def_mat = st.session_state.get("sug_mat", nomes[0])
            def_idx = nomes.index(def_mat) if def_mat in nomes else 0
            mat_sel = st.selectbox("Matéria", nomes, index=def_idx)

        mat_obj  = next((m for m in materias if m["nome"] == mat_sel), None)
        cont_lst = [c["nome"] for c in mat_obj.get("conteudos", [])] if mat_obj else ["Geral"]
        def_c    = st.session_state.get("sug_cont", "")
        def_ci   = cont_lst.index(def_c) if def_c in cont_lst else 0
        cont_sel = st.selectbox("Conteúdo", cont_lst, index=def_ci)

        c1, c2 = st.columns(2)
        with c1:
            d_ini = st.date_input("Data Início", value=date.today())
            h_ini = st.time_input("Hora Início", value=datetime.now().replace(hour=max(datetime.now().hour - 1, 0), minute=0, second=0, microsecond=0))
        with c2:
            d_fim = st.date_input("Data Fim", value=date.today())
            h_fim = st.time_input("Hora Fim",   value=datetime.now().replace(second=0, microsecond=0))

        acertos = erros = 0
        if "Questões" in tipo:
            qc1, qc2 = st.columns(2)
            with qc1: acertos = st.number_input("✅ Acertos", min_value=0, value=0, step=1)
            with qc2: erros   = st.number_input("❌ Erros",   min_value=0, value=0, step=1)

        encerrou = st.checkbox("Encerrei esse assunto ✓")
        obs      = st.text_area("Observações", placeholder="Anotações, dificuldades, dúvidas...")

        if st.form_submit_button("💾  Salvar Sessão"):
            dt_ini = datetime.combine(d_ini, h_ini)
            dt_fim = datetime.combine(d_fim, h_fim)
            dur    = max(int((dt_fim - dt_ini).total_seconds() / 60), 0)
            add_sessao({
                "id":               datetime.now().isoformat(),
                "materia":          mat_sel,
                "conteudo":         cont_sel,
                "tipo":             "questoes" if "Questões" in tipo else "materia",
                "data_inicio":      dt_ini.isoformat(),
                "data_fim":         dt_fim.isoformat(),
                "duracao_min":      dur,
                "encerrou_assunto": encerrou,
                "acertos":          int(acertos),
                "erros":            int(erros),
                "observacoes":      obs,
            })
            for k in ("sug_mat", "sug_cont", "sug_tipo"):
                st.session_state.pop(k, None)
            st.success(f"✅ Sessão de {dur} min salva com sucesso!")

# ─────────────────────────────────────────────────────────────
#  PÁGINA: MATÉRIAS
# ─────────────────────────────────────────────────────────────
elif pagina == "📚 Matérias":
    st.markdown("<h2 style='margin-bottom:2px'>Gestão de Matérias</h2><p style='color:#6b7a9e;margin-bottom:18px'>Edital, conteúdos e prioridades</p>", unsafe_allow_html=True)

    # modelo CSV
    modelo_rows = [
        ["materia", "conteudo", "prioridade"],
        ["Direito Constitucional", "Princípios Fundamentais", 1],
        ["Direito Constitucional", "Direitos e Garantias", 1],
        ["Direito Constitucional", "Organização do Estado", 2],
        ["Direito Administrativo", "Atos Administrativos", 1],
        ["Direito Administrativo", "Licitações e Contratos", 1],
        ["Língua Portuguesa", "Interpretação de Texto", 1],
        ["Língua Portuguesa", "Gramática", 2],
        ["Raciocínio Lógico", "Proposições Lógicas", 1],
        ["Informática", "Segurança da Informação", 1],
    ]
    buf_m = io.StringIO()
    csv.writer(buf_m).writerows(modelo_rows)

    c1, c2 = st.columns([2, 1])
    with c1:
        arquivo = st.file_uploader("📤 Importar Planilha CSV", type=["csv"])
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button("⬇ Baixar Modelo CSV", buf_m.getvalue().encode("utf-8-sig"), "modelo_materias.csv", "text/csv")

    if arquivo:
        content = arquivo.read().decode("utf-8-sig")
        reader  = csv.DictReader(io.StringIO(content))
        md = {}
        for row in reader:
            nome = row.get("materia", "").strip()
            cont = row.get("conteudo", "").strip()
            prio = int(row.get("prioridade", 2) or 2)
            if not nome: continue
            if nome not in md:
                md[nome] = {"nome": nome, "prioridade": prio, "questoes_edital": 10, "conteudos": []}
            if cont:
                md[nome]["conteudos"].append({"nome": cont, "prioridade": prio})
            if prio < md[nome]["prioridade"]:
                md[nome]["prioridade"] = prio

        mat_novas = list(md.values())
        st.markdown("<br><div style='font-size:13px;font-weight:700;color:#e8ecff;margin-bottom:10px'>⚙️ Configure questões do edital e prioridade</div>", unsafe_allow_html=True)

        with st.form("form_import"):
            st.markdown("<div style='display:grid;grid-template-columns:1fr 140px 110px;gap:8px;font-size:10px;color:#6b7a9e;text-transform:uppercase;letter-spacing:.5px;padding:4px 0 10px;border-bottom:1px solid rgba(255,255,255,.07)'><div>Matéria</div><div>Prioridade</div><div>Questões</div></div>", unsafe_allow_html=True)
            for i, m in enumerate(mat_novas):
                cc1, cc2, cc3 = st.columns([3, 1.2, 1])
                with cc1:
                    st.markdown(f"<div style='padding:10px 0;font-size:13px;color:#a0aac8'>{m['nome']}</div>", unsafe_allow_html=True)
                with cc2:
                    ops  = ["🔴 Alta (1)", "🟡 Média (2)", "⚪ Baixa (3)"]
                    pidx = m["prioridade"] - 1
                    psel = st.selectbox("p", ops, index=pidx, key=f"pi_{i}", label_visibility="collapsed")
                    mat_novas[i]["prioridade"] = ops.index(psel) + 1
                with cc3:
                    q = st.number_input("q", min_value=0, value=m["questoes_edital"], key=f"qi_{i}", label_visibility="collapsed")
                    mat_novas[i]["questoes_edital"] = int(q)

            if st.form_submit_button("✅  Salvar Matérias"):
                save_materias(mat_novas)
                st.session_state.db_mat = None  # força reload
                st.success(f"✅ {len(mat_novas)} matérias salvas!")
                st.rerun()

    # tabela de matérias cadastradas
    mats = get_materias()
    if mats:
        import pandas as pd
        st.markdown("<br>", unsafe_allow_html=True)
        rows = [{"Matéria": m["nome"],
                 "Prioridade": {1:"🔴 Alta",2:"🟡 Média",3:"⚪ Baixa"}.get(m.get("prioridade",2),"—"),
                 "Questões Edital": m.get("questoes_edital", 0),
                 "Nº Conteúdos": len(m.get("conteudos", []))} for m in mats]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    elif not arquivo:
        st.info("Nenhuma matéria cadastrada ainda. Importe um CSV acima.")

# ─────────────────────────────────────────────────────────────
#  PÁGINA: HISTÓRICO
# ─────────────────────────────────────────────────────────────
elif pagina == "🗂️ Histórico":
    st.markdown("<h2 style='margin-bottom:2px'>Histórico de Sessões</h2><p style='color:#6b7a9e;margin-bottom:18px'>Todos os seus registros de estudo</p>", unsafe_allow_html=True)

    ses = get_sessoes()
    if not ses:
        st.info("Nenhuma sessão registrada ainda.")
    else:
        import pandas as pd
        rows = []
        for s in reversed(ses):
            dt  = datetime.fromisoformat(s["data_inicio"]).strftime("%d/%m/%Y %H:%M")
            dur = f"{s.get('duracao_min',0)}min" if s.get("duracao_min", 0) < 60 else f"{s.get('duracao_min',0)/60:.1f}h"
            q   = s.get("acertos", 0) + s.get("erros", 0)
            pct = round(s.get("acertos", 0) / q * 100) if q > 0 else None
            rows.append({
                "Data":       dt,
                "Matéria":    s.get("materia", ""),
                "Conteúdo":   s.get("conteudo", ""),
                "Tipo":       "🧩 Questões" if s.get("tipo") == "questoes" else "📖 Estudo",
                "Duração":    dur,
                "Resultado":  f"{s.get('acertos',0)}/{q} ({pct}%)" if q > 0 else "—",
                "Encerrou":   "✓" if s.get("encerrou_assunto") else "—",
            })

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        buf_e = io.StringIO()
        pd.DataFrame(rows).to_csv(buf_e, index=False)
        st.download_button("⬇ Exportar histórico CSV", buf_e.getvalue().encode("utf-8-sig"), "historico_sessoes.csv", "text/csv")
