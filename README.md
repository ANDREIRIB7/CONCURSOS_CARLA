# ⚡ ConcursoFocus — Sistema de Estudos para Concursos

Sistema completo de gerenciamento de estudos para concursos públicos com:
- Painel de desempenho com métricas
- Algoritmo inteligente de sugestão de estudos (revisão espaçada + peso edital)
- Modos: Pré-Edital e Pós-Edital (Turbo)
- Registro de sessões com timer
- Controle de questões (acertos/erros)
- Importação via CSV

---

## 🚀 Deploy Gratuito — Railway (Recomendado)

1. Crie conta em https://railway.app
2. Clique em **New Project → Deploy from GitHub Repo**
3. Faça upload desta pasta ou conecte ao GitHub
4. Variável de ambiente: `PORT=8080` (Railway define automaticamente)
5. Pronto! URL gerada automaticamente.

## 🚀 Deploy Alternativo — Render.com

1. Crie conta em https://render.com
2. New Web Service → conecte repositório GitHub
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT`
5. Deploy!

## 🚀 Rodar Local

```bash
pip install -r requirements.txt
python app.py
# Acesse: http://localhost:5000
```

---

## 📋 Como Usar

### 1. Importar Matérias
- Vá em **Matérias** → Baixar Modelo CSV
- Preencha com suas matérias, conteúdos e prioridades (1=alta, 2=média, 3=baixa)
- Faça o upload do CSV
- Configure quantidade de questões do edital por matéria

### 2. Estudar
- Clique em **Estudar** → o sistema sugere matéria/conteúdo automaticamente
- Escolha entre **Pré-Edital** (foco nas mais importantes) ou **Pós-Edital Turbo** (tudo)
- Inicie o timer, estude, encerre e registre os resultados

### 3. Acompanhar Evolução
- Acesse o **Dashboard** para ver horas, taxa de acerto, sequência de dias e evolução por matéria

---

## 🧠 Algoritmo de Sugestão

O sistema combina:
- **Peso do edital** (quantas questões a matéria tem)
- **Prioridade manual** (1, 2, 3)
- **Revisão espaçada** (prioriza o que faz mais dias sem estudar)
- **Taxa de acerto** (reforça o que você erra mais em questões)

---

## 📊 Modelo CSV

| materia | conteudo | prioridade |
|---------|----------|------------|
| Direito Constitucional | Princípios Fundamentais | 1 |
| Direito Administrativo | Atos Administrativos | 1 |
| Língua Portuguesa | Interpretação de Texto | 1 |
