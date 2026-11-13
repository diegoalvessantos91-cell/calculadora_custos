from flask import Flask, render_template_string, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static'
DB_NAME = 'historico_sd.db'

# Custos base padrão para 3D e Serviços (SD Tech & Solutions)
CONFIG_PADRAO = {
    "filamento_kg": 90.00,    # Preço médio do kg de PLA/PETG (R$)
    "kwh_preco": 0.85,        # Preço do kWh na região (R$)
    "consumo_impressora": 0.15, # kW médio (ex: 150W)
    "depreciacao_hora": 2.00, # Custo de desgaste/manutenção por hora
    "taxa_plataforma": 14.00  # % média de taxas (Shopee/Mercado Livre)
}

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_peca TEXT,
            horas REAL,
            gramas REAL,
            preco_venda REAL,
            lucro_liquido REAL,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Template HTML com cálculo separado e botão de Salvar no Demonstrativo
TEMPLATE_HTML = """
<!DOCTYPE html>
<html lang="pt-BR" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Calculadora de Custos | SD Tech & Solutions</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        carbon: '#0A0A0A',
                        carbonCard: '#141414',
                        carbonBorder: '#262626',
                        neonGreen: '#00FF66',
                        neonHover: '#00CC52'
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-carbon text-gray-100 min-h-screen font-sans antialiased flex flex-col justify-between">
    
    <!-- Header com Logo no tamanho exato e centralizada -->
    <header class="border-b border-carbonBorder bg-carbonCard/95 backdrop-blur sticky top-0 z-50 shadow-xl py-6">
        <div class="max-w-5xl mx-auto px-4 flex flex-col items-center justify-center text-center">
            {% if logo_exists %}
                <div class="mb-2">
                    <img src="{{ url_for('static', filename='logo.png') }}" alt="SD Tech & Solutions Logo" class="h-20 w-auto sm:h-24 object-contain drop-shadow-lg">
                </div>
            {% else %}
                <div class="h-20 w-20 rounded-xl bg-neonGreen/10 border border-neonGreen flex items-center justify-center text-neonGreen font-black text-2xl shadow-xl mb-2">SD</div>
            {% endif %}
            
            <p class="text-xs sm:text-sm text-neonGreen font-semibold tracking-widest uppercase">Calculadora de Precificação & Custos 3D</p>
        </div>
    </header>

    <!-- Main Container -->
    <main class="max-w-5xl mx-auto px-4 py-8 w-full flex-grow space-y-8">
        <form method="POST">
            <input type="hidden" name="edit_id" value="{{ edit_id if edit_id else '' }}">
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
                
                <!-- Formulário de Entrada / Parâmetros -->
                <div class="lg:col-span-7 bg-carbonCard border border-carbonBorder rounded-2xl p-6 md:p-8 shadow-2xl">
                    <div class="flex justify-between items-center mb-6 border-b border-carbonBorder pb-4">
                        <h2 class="text-lg font-bold flex items-center text-white">
                            <svg class="w-5 h-5 mr-2.5 text-neonGreen flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path></svg>
                            {% if edit_id %}Editando Parâmetros (ID: {{ edit_id }}){% else %}Parâmetros da Impressão{% endif %}
                        </h2>
                        {% if edit_id %}
                            <a href="{{ url_for('index') }}" class="text-xs px-3 py-1 rounded bg-red-500/10 text-red-400 border border-red-500/30 hover:bg-red-500/20 transition">Cancelar</a>
                        {% endif %}
                    </div>

                    <div class="space-y-4">
                        <div>
                            <label class="block text-xs font-bold uppercase text-gray-400 mb-1 tracking-wider">Nome do Projeto / Peça</label>
                            <input type="text" name="nome_peca" value="{{ dados.nome_peca }}" placeholder="Ex: Suporte Headset V2" required class="w-full bg-carbon border border-carbonBorder rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-neonGreen transition shadow-inner">
                        </div>

                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div>
                                <label class="block text-xs font-bold uppercase text-gray-400 mb-1 tracking-wider">Tempo (Horas)</label>
                                <input type="number" step="0.1" name="horas" value="{{ dados.horas }}" placeholder="Ex: 4.5" required class="w-full bg-carbon border border-carbonBorder rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-neonGreen transition shadow-inner">
                            </div>
                            <div>
                                <label class="block text-xs font-bold uppercase text-gray-400 mb-1 tracking-wider">Peso da Peça (g)</label>
                                <input type="number" step="1" name="gramas" value="{{ dados.gramas }}" placeholder="Ex: 75" required class="w-full bg-carbon border border-carbonBorder rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-neonGreen transition shadow-inner">
                            </div>
                        </div>

                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div>
                                <label class="block text-xs font-bold uppercase text-gray-400 mb-1 tracking-wider">Filamento (R$/kg)</label>
                                <input type="number" step="0.01" name="preco_kg" value="{{ dados.preco_kg }}" placeholder="90.00" required class="w-full bg-carbon border border-carbonBorder rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-neonGreen transition shadow-inner">
                            </div>
                            <div>
                                <label class="block text-xs font-bold uppercase text-gray-400 mb-1 tracking-wider">Embalagem / Extras (R$)</label>
                                <input type="number" step="0.01" name="embalagem" value="{{ dados.embalagem }}" placeholder="3.50" required class="w-full bg-carbon border border-carbonBorder rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-neonGreen transition shadow-inner">
                            </div>
                        </div>

                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div>
                                <label class="block text-xs font-bold uppercase text-gray-400 mb-1 tracking-wider">Margem de Lucro (%)</label>
                                <input type="number" step="1" name="lucro_desejado" value="{{ dados.lucro_desejado }}" placeholder="100" required class="w-full bg-carbon border border-carbonBorder rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-neonGreen transition shadow-inner">
                            </div>
                            <div>
                                <label class="block text-xs font-bold uppercase text-gray-400 mb-1 tracking-wider">Taxas Marketplace (%)</label>
                                <input type="number" step="0.1" name="taxas" value="{{ dados.taxas }}" placeholder="14.0" required class="w-full bg-carbon border border-carbonBorder rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-neonGreen transition shadow-inner">
                            </div>
                        </div>

                        <button type="submit" name="acao" value="calcular" class="w-full bg-carbon border border-neonGreen text-neonGreen font-extrabold py-3.5 px-6 rounded-xl hover:bg-neonGreen/10 transition shadow-lg flex items-center justify-center space-x-2 mt-4 cursor-pointer text-sm uppercase tracking-wider">
                            <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path></svg>
                            <span>Calcular Custos</span>
                        </button>
                    </div>
                </div>

                <!-- Painel de Resultados / Demonstrativo -->
                <div class="lg:col-span-5 space-y-6">
                    <div class="bg-carbonCard border border-carbonBorder rounded-2xl p-6 md:p-8 shadow-2xl relative overflow-hidden">
                        <h2 class="text-lg font-bold mb-6 flex items-center text-white border-b border-carbonBorder pb-4">
                            <svg class="w-5 h-5 mr-2.5 text-neonGreen flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path></svg>
                            Demonstrativo de Custos
                        </h2>

                        {% if resultado %}
                        <div class="space-y-4">
                            <input type="hidden" name="res_custo_filamento" value="{{ resultado.custo_filamento }}">
                            <input type="hidden" name="res_custo_energia" value="{{ resultado.custo_energia }}">
                            <input type="hidden" name="res_custo_depreciacao" value="{{ resultado.custo_depreciacao }}">
                            <input type="hidden" name="res_embalagem" value="{{ resultado.embalagem }}">
                            <input type="hidden" name="res_custo_total" value="{{ resultado.custo_total }}">
                            <input type="hidden" name="res_lucro_liquido" value="{{ resultado.lucro_liquido }}">
                            <input type="hidden" name="res_valor_taxas" value="{{ resultado.valor_taxas }}">
                            <input type="hidden" name="res_preco_venda" value="{{ resultado.preco_venda }}">

                            <div class="flex justify-between py-2 border-b border-carbonBorder/60 text-sm">
                                <span class="text-gray-400">Custo do Filamento:</span>
                                <span class="font-mono font-semibold text-white">R$ {{ "%.2f"|format(resultado.custo_filamento) }}</span>
                            </div>
                            <div class="flex justify-between py-2 border-b border-carbonBorder/60 text-sm">
                                <span class="text-gray-400">Energia Elétrica:</span>
                                <span class="font-mono font-semibold text-white">R$ {{ "%.2f"|format(resultado.custo_energia) }}</span>
                            </div>
                            <div class="flex justify-between py-2 border-b border-carbonBorder/60 text-sm">
                                <span class="text-gray-400">Desgaste / Manutenção:</span>
                                <span class="font-mono font-semibold text-white">R$ {{ "%.2f"|format(resultado.custo_depreciacao) }}</span>
                            </div>
                            <div class="flex justify-between py-2 border-b border-carbonBorder/60 text-sm">
                                <span class="text-gray-400">Embalagem & Insumos:</span>
                                <span class="font-mono font-semibold text-white">R$ {{ "%.2f"|format(resultado.embalagem) }}</span>
                            </div>
                            <div class="flex justify-between py-2.5 border-b border-carbonBorder font-bold text-sm">
                                <span class="text-gray-300">Custo Total de Produção:</span>
                                <span class="font-mono text-neonGreen text-base">R$ {{ "%.2f"|format(resultado.custo_total) }}</span>
                            </div>

                            <div class="pt-4 mt-2 border border-neonGreen/30 bg-carbon/80 p-5 rounded-xl shadow-inner">
                                <div class="text-xs text-neonGreen font-bold uppercase tracking-wider mb-1">Preço de Venda Sugerido</div>
                                <div class="text-3xl md:text-4xl font-black font-mono text-white">R$ {{ "%.2f"|format(resultado.preco_venda) }}</div>
                                <div class="text-xs text-gray-400 mt-3 pt-3 border-t border-carbonBorder flex flex-col gap-1.5">
                                    <div class="flex justify-between"><span>Lucro Líquido:</span> <strong class="text-neonGreen font-mono">R$ {{ "%.2f"|format(resultado.lucro_liquido) }}</strong></div>
                                    <div class="flex justify-between"><span>Taxas Marketplace:</span> <strong class="text-gray-300 font-mono">R$ {{ "%.2f"|format(resultado.valor_taxas) }}</strong></div>
                                </div>
                            </div>

                            <!-- Botão de Salvar no Demonstrativo -->
                            <button type="submit" name="acao" value="salvar" class="w-full bg-neonGreen text-carbon font-extrabold py-3.5 px-6 rounded-xl hover:bg-neonHover transition shadow-lg shadow-neonGreen/20 flex items-center justify-center space-x-2 mt-4 cursor-pointer text-sm uppercase tracking-wider">
                                <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                                <span>{% if edit_id %}Atualizar Orçamento{% else %}Salvar Orçamento{% endif %}</span>
                            </button>
                        </div>
                        {% else %}
                        <div class="text-center py-14 text-gray-500">
                            <svg class="w-12 h-12 mx-auto mb-3 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
                            <p class="text-sm">Preencha os parâmetros e clique em "Calcular Custos" para ver o demonstrativo e salvar.</p>
                        </div>
                        {% endif %}
                    </div>
                </div>

            </div>
        </form>

        <!-- Tabela de Histórico com Ações (Lápis e Cestinha) -->
        <div class="bg-carbonCard border border-carbonBorder rounded-2xl p-6 md:p-8 shadow-2xl">
            <h3 class="text-base font-bold mb-4 flex items-center text-white border-b border-carbonBorder pb-3">
                <svg class="w-5 h-5 mr-2 text-neonGreen" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                Histórico de Peças Salvas
            </h3>
            <div class="overflow-x-auto">
                <table class="w-full text-left text-sm text-gray-300">
                    <thead class="bg-carbon text-gray-400 uppercase text-xs border-b border-carbonBorder">
                        <tr>
                            <th class="py-3 px-4">Data / Hora</th>
                            <th class="py-3 px-4">Peça / Projeto</th>
                            <th class="py-3 px-4">Tempo</th>
                            <th class="py-3 px-4">Peso</th>
                            <th class="py-3 px-4">Preço Sugerido</th>
                            <th class="py-3 px-4">Lucro Líquido</th>
                            <th class="py-3 px-4 text-center">Ações</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-carbonBorder">
                        {% if historico %}
                            {% for item in historico %}
                            <tr class="hover:bg-carbon/40 transition">
                                <td class="py-3 px-4 text-xs text-gray-400 font-mono">{{ item[6] }}</td>
                                <td class="py-3 px-4 font-bold text-white">{{ item[1] }}</td>
                                <td class="py-3 px-4 font-mono">{{ item[2] }}h</td>
                                <td class="py-3 px-4 font-mono">{{ item[3] }}g</td>
                                <td class="py-3 px-4 font-mono text-neonGreen font-bold">R$ {{ "%.2f"|format(item[4]) }}</td>
                                <td class="py-3 px-4 font-mono text-gray-200">R$ {{ "%.2f"|format(item[5]) }}</td>
                                <td class="py-3 px-4 text-center space-x-2">
                                    <!-- Botão Editar (Lápis) -->
                                    <a href="{{ url_for('editar', id=item[0]) }}" title="Editar" class="inline-block p-1.5 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/30 hover:bg-blue-500/20 transition">
                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path></svg>
                                    </a>
                                    <!-- Botão Excluir (Cestinha / Lixeira) -->
                                    <a href="{{ url_for('deletar', id=item[0]) }}" onclick="return confirm('Deseja realmente excluir este item do histórico?');" title="Excluir" class="inline-block p-1.5 rounded-lg bg-red-500/10 text-red-400 border border-red-500/30 hover:bg-red-500/20 transition">
                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                                    </a>
                                </td>
                            </tr>
                            {% endfor %}
                        {% else %}
                            <tr>
                                <td colspan="7" class="text-center py-6 text-gray-500">Nenhum cálculo salvo no banco de dados ainda.</td>
                            </tr>
                        {% endif %}
                    </tbody>
                </table>
            </div>
        </div>
    </main>

    <!-- Footer -->
    <footer class="border-t border-carbonBorder bg-carbonCard/50 py-4 text-center text-xs text-gray-500">
        SD Tech & Solutions &copy; 2026 — Todos os direitos reservados
    </footer>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    init_db()
    logo_path = os.path.join(app.root_path, 'static', 'logo.png')
    logo_exists = os.path.exists(logo_path)

    dados_iniciais = {
        "nome_peca": "",
        "horas": "",
        "gramas": "",
        "preco_kg": "",
        "embalagem": "",
        "lucro_desejado": "",
        "taxas": ""
    }

    resultado = None
    edit_id = None

    if request.method == 'POST':
        try:
            acao = request.form.get('acao')
            edit_id = request.form.get('edit_id')
            nome_peca = request.form.get('nome_peca', 'Peça Sem Nome')
            horas = float(request.form.get('horas', 0))
            gramas = float(request.form.get('gramas', 0))
            preco_kg = float(request.form.get('preco_kg', 0))
            embalagem = float(request.form.get('embalagem', 0))
            lucro_desejado = float(request.form.get('lucro_desejado', 0))
            taxas_perc = float(request.form.get('taxas', 0))

            dados_iniciais = {
                "nome_peca": nome_peca,
                "horas": horas,
                "gramas": gramas,
                "preco_kg": preco_kg,
                "embalagem": embalagem,
                "lucro_desejado": lucro_desejado,
                "taxas": taxas_perc
            }

            custo_filamento = (gramas / 1000.0) * preco_kg
            custo_energia = (CONFIG_PADRAO["consumo_impressora"] * horas) * CONFIG_PADRAO["kwh_preco"]
            custo_depreciacao = horas * CONFIG_PADRAO["depreciacao_hora"]
            
            custo_total = custo_filamento + custo_energia + custo_depreciacao + embalagem
            lucro_liquido = custo_total * (lucro_desejado / 100.0)
            subtotal_com_lucro = custo_total + lucro_liquido

            divisor = 1.0 - (taxas_perc / 100.0)
            if divisor <= 0:
                divisor = 0.1
            
            preco_venda = subtotal_com_lucro / divisor
            valor_taxas = preco_venda * (taxas_perc / 100.0)

            resultado = {
                "custo_filamento": custo_filamento,
                "custo_energia": custo_energia,
                "custo_depreciacao": custo_depreciacao,
                "embalagem": embalagem,
                "custo_total": custo_total,
                "lucro_liquido": lucro_liquido,
                "valor_taxas": valor_taxas,
                "preco_venda": preco_venda
            }

            # Se clicou em "Salvar Orçamento" no Demonstrativo
            if acao == 'salvar':
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                
                if edit_id:
                    cursor.execute('''
                        UPDATE historico 
                        SET nome_peca = ?, horas = ?, gramas = ?, preco_venda = ?, lucro_liquido = ?
                        WHERE id = ?
                    ''', (nome_peca, horas, gramas, preco_venda, lucro_liquido, edit_id))
                else:
                    cursor.execute('''
                        INSERT INTO historico (nome_peca, horas, gramas, preco_venda, lucro_liquido)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (nome_peca, horas, gramas, preco_venda, lucro_liquido))
                
                conn.commit()
                conn.close()
                return redirect(url_for('index'))

        except ValueError:
            pass

    # Busca o histórico salvo para exibir na tabela
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id, nome_peca, horas, gramas, preco_venda, lucro_liquido, data FROM historico ORDER BY id DESC LIMIT 10')
    historico = cursor.fetchall()
    conn.close()

    return render_template_string(TEMPLATE_HTML, dados=dados_iniciais, resultado=resultado, historico=historico, logo_exists=logo_exists, edit_id=edit_id)

@app.route('/editar/<int:id>', methods=['GET'])
def editar(id):
    init_db()
    logo_path = os.path.join(app.root_path, 'static', 'logo.png')
    logo_exists = os.path.exists(logo_path)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id, nome_peca, horas, gramas FROM historico WHERE id = ?', (id,))
    item = cursor.fetchone()
    
    cursor.execute('SELECT id, nome_peca, horas, gramas, preco_venda, lucro_liquido, data FROM historico ORDER BY id DESC LIMIT 10')
    historico = cursor.fetchall()
    conn.close()

    if not item:
        return redirect(url_for('index'))

    dados_iniciais = {
        "nome_peca": item[1],
        "horas": item[2],
        "gramas": item[3],
        "preco_kg": CONFIG_PADRAO["filamento_kg"],
        "embalagem": 3.50,
        "lucro_desejado": 100,
        "taxas": CONFIG_PADRAO["taxa_plataforma"]
    }

    return render_template_string(TEMPLATE_HTML, dados=dados_iniciais, resultado=None, historico=historico, logo_exists=logo_exists, edit_id=item[0])

@app.route('/deletar/<int:id>', methods=['GET'])
def deletar(id):
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM historico WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    os.makedirs('static', exist_ok=True)
    init_db()
    app.run(debug=True, port=5000)