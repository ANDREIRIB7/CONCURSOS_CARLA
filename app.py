from flask import Flask, render_template, request, jsonify, send_file
import json
import os
import csv
import io
from datetime import datetime, date, timedelta
import math

app = Flask(__name__)
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

MATERIAS_FILE = os.path.join(DATA_DIR, 'materias.json')
SESSOES_FILE = os.path.join(DATA_DIR, 'sessoes.json')

# ─── helpers ────────────────────────────────────────────────────────────────

def load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

def get_materias():
    return load_json(MATERIAS_FILE, [])

def get_sessoes():
    return load_json(SESSOES_FILE, [])

# ─── algoritmo de prioridade (revisão espaçada + peso edital) ────────────────

def calcular_prioridade(materia, sessoes, modo):
    """
    Score de prioridade combinando:
    - Peso edital (questões cobradas)
    - Prioridade manual (1=alta, 3=baixa)
    - Última vez estudada (revisão espaçada)
    - Taxa de acerto (reforça o que erra)
    """
    nome = materia['nome']
    prio = materia.get('prioridade', 2)
    questoes_edital = materia.get('questoes_edital', 10)

    sessoes_mat = [s for s in sessoes if s.get('materia') == nome]

    # Dias desde último estudo
    if sessoes_mat:
        datas = [datetime.fromisoformat(s['data_inicio']) for s in sessoes_mat]
        ultima = max(datas)
        dias_sem_estudar = (datetime.now() - ultima).days
    else:
        dias_sem_estudar = 30  # nunca estudou → alta prioridade

    # Taxa de acerto (só para modo questões)
    taxa_acerto = 1.0
    if modo == 'questoes':
        acertos_total = sum(s.get('acertos', 0) for s in sessoes_mat)
        erros_total = sum(s.get('erros', 0) for s in sessoes_mat)
        total_q = acertos_total + erros_total
        if total_q > 0:
            taxa_acerto = acertos_total / total_q
        # Quem erra mais precisa mais atenção
        fator_erro = 2.0 - taxa_acerto  # entre 1.0 e 2.0
    else:
        fator_erro = 1.0

    # Score: maior = mais prioritário
    peso_prio = {1: 3.0, 2: 2.0, 3: 1.0}.get(prio, 2.0)
    score = (
        peso_prio
        * (questoes_edital / 10)
        * (1 + dias_sem_estudar / 7)
        * fator_erro
    )
    return score

def sugerir_estudo(modo, turbo=False):
    materias = get_materias()
    sessoes = get_sessoes()
    if not materias:
        return None

    # Filtra por modo (pré-edital: só prioridade 1 e 2 ; turbo: tudo)
    if not turbo:
        candidatas = [m for m in materias if m.get('prioridade', 2) <= 2]
        if not candidatas:
            candidatas = materias
    else:
        candidatas = materias

    scores = [(m, calcular_prioridade(m, sessoes, modo)) for m in candidatas]
    scores.sort(key=lambda x: x[1], reverse=True)

    melhor_materia = scores[0][0]

    # Conteúdos da matéria ordenados por prioridade e menos estudados
    conteudos = melhor_materia.get('conteudos', [])
    sessoes_mat = [s for s in sessoes if s.get('materia') == melhor_materia['nome']]
    conteudos_estudados = {}
    for s in sessoes_mat:
        c = s.get('conteudo', '')
        conteudos_estudados[c] = conteudos_estudados.get(c, 0) + 1

    def score_conteudo(c):
        vezes = conteudos_estudados.get(c['nome'], 0)
        p = c.get('prioridade', 2)
        return p * 10 - vezes  # menos estudado e mais prioritário = maior score

    conteudos_ordenados = sorted(conteudos, key=score_conteudo, reverse=True)
    conteudo_sugerido = conteudos_ordenados[0] if conteudos_ordenados else None

    return {
        'materia': melhor_materia['nome'],
        'conteudo': conteudo_sugerido['nome'] if conteudo_sugerido else 'Geral',
        'prioridade': melhor_materia.get('prioridade', 2),
        'questoes_edital': melhor_materia.get('questoes_edital', 0),
        'top5': [{'nome': m['nome'], 'score': round(s, 1)} for m, s in scores[:5]],
    }

# ─── rotas ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/dashboard')
def api_dashboard():
    sessoes = get_sessoes()
    materias = get_materias()

    hoje = date.today().isoformat()
    semana_inicio = (date.today() - timedelta(days=date.today().weekday())).isoformat()

    # Totais gerais
    total_sessoes = len(sessoes)
    total_horas = sum(s.get('duracao_min', 0) for s in sessoes) / 60
    total_acertos = sum(s.get('acertos', 0) for s in sessoes)
    total_erros = sum(s.get('erros', 0) for s in sessoes)
    total_questoes = total_acertos + total_erros
    taxa_geral = round(total_acertos / total_questoes * 100, 1) if total_questoes else 0

    # Esta semana
    sessoes_semana = [s for s in sessoes if s.get('data_inicio', '') >= semana_inicio]
    horas_semana = sum(s.get('duracao_min', 0) for s in sessoes_semana) / 60
    acertos_sem = sum(s.get('acertos', 0) for s in sessoes_semana)
    erros_sem = sum(s.get('erros', 0) for s in sessoes_semana)
    questoes_sem = acertos_sem + erros_sem
    taxa_sem = round(acertos_sem / questoes_sem * 100, 1) if questoes_sem else 0

    # Hoje
    sessoes_hoje = [s for s in sessoes if s.get('data_inicio', '').startswith(hoje)]
    horas_hoje = sum(s.get('duracao_min', 0) for s in sessoes_hoje) / 60

    # Por matéria
    por_materia = {}
    for s in sessoes:
        m = s.get('materia', 'Desconhecida')
        if m not in por_materia:
            por_materia[m] = {'horas': 0, 'acertos': 0, 'erros': 0, 'sessoes': 0}
        por_materia[m]['horas'] += s.get('duracao_min', 0) / 60
        por_materia[m]['acertos'] += s.get('acertos', 0)
        por_materia[m]['erros'] += s.get('erros', 0)
        por_materia[m]['sessoes'] += 1

    for m in por_materia:
        t = por_materia[m]['acertos'] + por_materia[m]['erros']
        por_materia[m]['taxa'] = round(por_materia[m]['acertos'] / t * 100, 1) if t else 0
        por_materia[m]['horas'] = round(por_materia[m]['horas'], 1)

    # Evolução diária (últimos 14 dias)
    evolucao = {}
    for i in range(13, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        evolucao[d] = {'horas': 0, 'taxa': 0, 'questoes': 0}
    for s in sessoes:
        d = s.get('data_inicio', '')[:10]
        if d in evolucao:
            evolucao[d]['horas'] += s.get('duracao_min', 0) / 60
            evolucao[d]['questoes'] += s.get('acertos', 0) + s.get('erros', 0)
    for d in evolucao:
        evolucao[d]['horas'] = round(evolucao[d]['horas'], 1)

    # Sequência de dias
    streak = 0
    for i in range(0, 30):
        d = (date.today() - timedelta(days=i)).isoformat()
        if any(s.get('data_inicio', '').startswith(d) for s in sessoes):
            streak += 1
        else:
            break

    return jsonify({
        'total_sessoes': total_sessoes,
        'total_horas': round(total_horas, 1),
        'total_questoes': total_questoes,
        'taxa_geral': taxa_geral,
        'horas_semana': round(horas_semana, 1),
        'taxa_semana': taxa_sem,
        'questoes_semana': questoes_sem,
        'horas_hoje': round(horas_hoje, 1),
        'streak': streak,
        'por_materia': por_materia,
        'evolucao': evolucao,
        'total_materias': len(materias),
        'sessoes_recentes': sorted(sessoes, key=lambda x: x.get('data_inicio',''), reverse=True)[:5],
    })

@app.route('/api/sugerir')
def api_sugerir():
    modo = request.args.get('modo', 'materia')
    turbo = request.args.get('turbo', 'false') == 'true'
    sugestao = sugerir_estudo(modo, turbo)
    if not sugestao:
        return jsonify({'erro': 'Nenhuma matéria cadastrada'}), 404
    return jsonify(sugestao)

@app.route('/api/sessoes', methods=['GET'])
def api_get_sessoes():
    return jsonify(get_sessoes())

@app.route('/api/sessoes', methods=['POST'])
def api_post_sessao():
    data = request.json
    sessoes = get_sessoes()
    sessao = {
        'id': datetime.now().isoformat(),
        'materia': data.get('materia', ''),
        'conteudo': data.get('conteudo', ''),
        'tipo': data.get('tipo', 'materia'),  # 'materia' ou 'questoes'
        'data_inicio': data.get('data_inicio', datetime.now().isoformat()),
        'data_fim': data.get('data_fim', datetime.now().isoformat()),
        'duracao_min': data.get('duracao_min', 0),
        'encerrou_assunto': data.get('encerrou_assunto', False),
        'acertos': data.get('acertos', 0),
        'erros': data.get('erros', 0),
        'observacoes': data.get('observacoes', ''),
    }
    sessoes.append(sessao)
    save_json(SESSOES_FILE, sessoes)
    return jsonify({'ok': True, 'id': sessao['id']})

@app.route('/api/materias', methods=['GET'])
def api_get_materias():
    return jsonify(get_materias())

@app.route('/api/materias', methods=['POST'])
def api_post_materias():
    data = request.json
    save_json(MATERIAS_FILE, data)
    return jsonify({'ok': True})

@app.route('/api/upload_planilha', methods=['POST'])
def api_upload_planilha():
    """Recebe JSON com matérias vindas do front após o usuário preencher questões_edital"""
    data = request.json
    save_json(MATERIAS_FILE, data)
    return jsonify({'ok': True, 'total': len(data)})

@app.route('/api/modelo_csv')
def api_modelo_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['materia', 'conteudo', 'prioridade'])
    exemplos = [
        ['Direito Constitucional', 'Princípios Fundamentais', 1],
        ['Direito Constitucional', 'Direitos e Garantias', 1],
        ['Direito Constitucional', 'Organização do Estado', 2],
        ['Direito Administrativo', 'Atos Administrativos', 1],
        ['Direito Administrativo', 'Licitações', 1],
        ['Direito Administrativo', 'Contratos Administrativos', 2],
        ['Língua Portuguesa', 'Interpretação de Texto', 1],
        ['Língua Portuguesa', 'Gramática', 2],
        ['Raciocínio Lógico', 'Proposições Lógicas', 1],
        ['Raciocínio Lógico', 'Sequências', 2],
        ['Informática', 'Word/Excel', 2],
        ['Informática', 'Segurança da Informação', 1],
    ]
    writer.writerows(exemplos)
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='modelo_materias.csv'
    )

@app.route('/api/parse_csv', methods=['POST'])
def api_parse_csv():
    """Lê CSV e retorna estrutura agrupada por matéria, sem salvar ainda"""
    file = request.files.get('file')
    if not file:
        return jsonify({'erro': 'Nenhum arquivo'}), 400
    
    content = file.read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(content))
    
    materias_dict = {}
    for row in reader:
        nome = row.get('materia', '').strip()
        conteudo = row.get('conteudo', '').strip()
        try:
            prio = int(row.get('prioridade', 2))
        except:
            prio = 2
        
        if not nome:
            continue
        
        if nome not in materias_dict:
            materias_dict[nome] = {
                'nome': nome,
                'prioridade': prio,
                'questoes_edital': 10,
                'conteudos': []
            }
        
        if conteudo:
            materias_dict[nome]['conteudos'].append({
                'nome': conteudo,
                'prioridade': prio
            })
        
        # usa a menor prioridade (mais alta) encontrada para a matéria
        if prio < materias_dict[nome]['prioridade']:
            materias_dict[nome]['prioridade'] = prio
    
    return jsonify(list(materias_dict.values()))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
