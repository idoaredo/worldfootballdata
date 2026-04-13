#!/usr/bin/env python3
# coding: utf-8
"""
generate_map.py
Gera mapa interativo HTML de torcidas do Brasil.
Dados: Facebook curtidas 2015/2017 | Pop: Censo IBGE 2022
"""

import base64
import gzip
import json
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

# ── Configuração ──────────────────────────────────────────────────────────────

BASE_DIR  = Path(__file__).parent
OUTPUT    = BASE_DIR / 'mapa_torcidas_brasil.html'
DRB_FILE  = BASE_DIR / 'divisoes_regionais_brasileiras.xlsx'
CURTIDAS  = BASE_DIR / 'mapa_de_curtidas_final.xlsm'
CACHE_DIR = BASE_DIR / '_cache'
CACHE_DIR.mkdir(exist_ok=True)

# Censo IBGE 2022
POP_2022 = {
    'RO': 1815278, 'AC': 906876,  'AM': 4269995, 'RR': 652713,
    'PA': 8777124, 'AP': 877613,  'TO': 1607363, 'MA': 7153262,
    'PI': 3289290, 'CE': 9240580, 'RN': 3560903, 'PB': 4059905,
    'PE': 9674793, 'AL': 3351543, 'SE': 2338474, 'BA': 14930634,
    'MG': 21411923,'ES': 4108508, 'RJ': 17463349,'SP': 44420459,
    'PR': 11516840,'SC': 7762557, 'RS': 11466630,'MS': 2833742,
    'MT': 3658813, 'GO': 7206589, 'DF': 2923369,
}

UF_CODE = {
    11:'RO', 12:'AC', 13:'AM', 14:'RR', 15:'PA', 16:'AP', 17:'TO',
    21:'MA', 22:'PI', 23:'CE', 24:'RN', 25:'PB', 26:'PE', 27:'AL',
    28:'SE', 29:'BA', 31:'MG', 32:'ES', 33:'RJ', 35:'SP',
    41:'PR', 42:'SC', 43:'RS', 50:'MS', 51:'MT', 52:'GO', 53:'DF',
}

REGIOES = {
    'Norte':       ['RO','AC','AM','RR','PA','AP','TO'],
    'Nordeste':    ['MA','PI','CE','RN','PB','PE','AL','SE','BA'],
    'Centro-Oeste':['MS','MT','GO','DF'],
    'Sudeste':     ['MG','ES','RJ','SP'],
    'Sul':         ['PR','SC','RS'],
}
UF_TO_REGIAO = {uf: r for r, ufs in REGIOES.items() for uf in ufs}

CLUB_COLORS = {
    # ── Grandes nacionais ────────────────────────────────────────────────────
    'FLAMENGO':        '#CC0000',   # vermelho Flamengo
    'CORINTHIANS':     '#000000',   # preto Corinthians
    'SÃO PAULO':       '#6B6B6B',   # cinza São Paulo FC
    'PALMEIRAS':       '#00693E',   # verde palestra
    'SANTOS':          '#1A1A1A',   # preto-acinzentado Santos
    'VASCO':           '#000000',   # preto Vasco
    'FLUMINENSE':      '#9B1B33',   # grená Fluminense
    'BOTAFOGO':        '#191919',   # preto Botafogo
    'GRÊMIO':          '#3B71C8',   # azul Grêmio
    'INTERNACIONAL':   '#DD0000',   # vermelho colorado
    'CRUZEIRO':        '#003087',   # azul cruzeiro (marinho)
    'ATLÉTICO-MG':     '#222222',   # preto Galo
    # ── Nordeste ────────────────────────────────────────────────────────────
    'BAHIA':           '#0099DD',   # azul celeste Bahia (distinto do navy Cruzeiro)
    'VITÓRIA':         '#CC0000',   # vermelho-preto Vitória
    'SPORT':           '#CC0000',   # vermelho-preto Sport
    'SANTA CRUZ':      '#CC0000',   # vermelho Santa Cruz
    'NÁUTICO':         '#CC0000',   # vermelho Náutico
    'NAUTICO':         '#CC0000',
    'FORTALEZA':       '#0D2D6B',   # azul Fortaleza
    'CEARÁ':           '#000000',   # preto-branco Ceará
    'ABC':             '#CC0000',   # vermelho ABC
    'AMÉRICA-RN':      '#009933',   # verde América-RN
    'AMERICA-RN':      '#009933',
    'CAMPINENSE':      '#CC0000',   # vermelho Campinense
    'TREZE':           '#CC0000',   # vermelho Treze
    'BOTAFOGO-PB':     '#000080',   # azul Botafogo-PB
    'CRB':             '#CC0000',   # vermelho CRB
    'CSA':             '#0055A4',   # azul CSA
    'ASA':             '#CC0000',   # vermelho ASA
    'CONFIANÇA':       '#006400',   # verde Confiança
    'MOTO CLUB':       '#CC0000',   # vermelho Moto Club
    'SAMPAIO CORRÊA':  '#CC0000',   # vermelho Sampaio Corrêa
    'SAMPAIO CORREA':  '#CC0000',
    'SALGUEIRO':       '#CC0000',
    'SERGIPE':         '#CC0000',
    # ── Sul ──────────────────────────────────────────────────────────────────
    'ATLÉTICO-PR':     '#CC0000',   # vermelho-preto CAP (Furacão)
    'ATHLETICO-PR':    '#CC0000',
    'CORITIBA':        '#006437',   # verde Coritiba
    'LONDRINA':        '#CC0000',   # vermelho Londrina
    'PONTE PRETA':     '#000000',   # preto Ponte Preta
    'GUARANI':         '#009B3A',   # verde Guarani
    'CHAPECOENSE':     '#007A33',   # verde Chapecoense
    'AVAÍ':            '#003087',   # azul Avaí
    'AVAI':            '#003087',
    'FIGUEIRENSE':     '#000000',   # preto-branco Figueirense
    'JOINVILLE':       '#CC0000',   # vermelho Joinville
    'CRICIÚMA':        '#F5A800',   # amarelo Criciúma
    'CRICIUMA':        '#F5A800',
    'JUVENTUDE':       '#006437',   # verde Juventude
    'BRASIL DE PELOTAS':'#CC0000',
    'YPIRANGA-RS':     '#F5A800',   # amarelo Ypiranga
    # ── São Paulo ────────────────────────────────────────────────────────────
    'PORTUGUESA':      '#CC0000',   # vermelho Portuguesa
    'BRAGANTINO':      '#CC0000',   # vermelho Bragantino / Red Bull
    'GUARANI':         '#009B3A',
    'OESTE':           '#CC0000',
    'SÃO BENTO':       '#0055A4',
    'SAO BENTO':       '#0055A4',
    'MOGI MIRIM':      '#CC0000',
    'BOTAFOGO-SP':     '#CC0000',
    # ── Minas Gerais ────────────────────────────────────────────────────────
    'ATLÉTICO-GO':     '#CC0000',
    'TOMBENSE':        '#CC0000',
    'TUPI-MG':         '#009B3A',
    'AMERICA-MG':      '#009B3A',   # verde América-MG
    'AMÉRICA-MG':      '#009B3A',
    'BOA ESPORTE':     '#009B3A',
    # ── Centro-Oeste ─────────────────────────────────────────────────────────
    'GOIÁS':           '#009B3A',   # verde Goiás
    'GOIAS':           '#009B3A',
    'ATLÉTICO-GO':     '#CC0000',   # vermelho-preto Atlético-GO
    'VILA NOVA':       '#CC0000',   # vermelho-preto Vila Nova
    'CUIABÁ':          '#F5A800',   # dourado Cuiabá
    'CUIABA':          '#F5A800',
    'LUVERDENSE':      '#009B3A',
    # ── Norte ─────────────────────────────────────────────────────────────────
    'REMO':            '#003087',   # azul Remo
    'PAYSANDU':        '#0055A4',   # azul Paysandu
    # ── Outros ────────────────────────────────────────────────────────────────
    'VOLTA REDONDA':   '#000080',
    'PARANA':          '#009B3A',
    'PARANÁ':          '#009B3A',
}
DEFAULT_COLOR = '#888888'

CLUB_ALIASES = {
    'ATLETICO-MG':    'ATLÉTICO-MG',
    'ATLETICO MG':    'ATLÉTICO-MG',
    'ATLÉTICO MG':    'ATLÉTICO-MG',
    'GREMIO':         'GRÊMIO',
    'CEARA':          'CEARÁ',
    'VITORIA':        'VITÓRIA',
    'SAO PAULO':      'SÃO PAULO',
    'ATLETICO-PR':    'ATLÉTICO-PR',
    'ATHLETICO-PR':   'ATLÉTICO-PR',
    'AMERICA-RN':     'AMÉRICA-RN',
    'AMERICA-MG':     'AMÉRICA-MG',
    'AVAI':           'AVAÍ',
    'CRICIUMA':       'CRICIÚMA',
    'CUIABA':         'CUIABÁ',
    'SAMPAIO CORREA': 'SAMPAIO CORRÊA',
    'NAUTICO':        'NÁUTICO',
    'NAÚTICO':        'NÁUTICO',
    'GOIAS':          'GOIÁS',
    'PARANA':         'PARANÁ',
    'SAO BENTO':      'SÃO BENTO',
}

# ── Escudos dos clubes ────────────────────────────────────────────────────────

ESCUDOS_DIR = BASE_DIR / 'escudos'  # coloque os PNGs dos escudos aqui (opcional)

CREST_FILES = {
    'CRB':          'AL - CRB.png',
    'CSA':          'AL - CSA.png',
    'BAHIA':        'BA - ECB.png',
    'VITÓRIA':      'BA - ECV.png',
    'CEARÁ':        'CE - CSC.png',
    'FORTALEZA':    'CE - FEC.png',
    'ATLÉTICO-GO':  'GO - ACG.png',
    'GOIÁS':        'GO - GEC.png',
    'VILA NOVA':    'GO - VNFC.png',
    'AMÉRICA-MG':   'MG - AFC.png',
    'ATLÉTICO-MG':  'MG - CAM.png',
    'CRUZEIRO':     'MG - CEC.png',
    'CUIABÁ':       'MT - CEC.png',
    'REMO':         'PA - CR.png',
    'PAYSANDU':     'PA - PSC.png',
    'NÁUTICO':      'PE - CNC.png',
    'SANTA CRUZ':   'PE - SCFC.png',
    'SPORT':        'PE - SCR.png',
    'ATHLETICO-PR': 'PR - CAP.png',
    'ATLÉTICO-PR':  'PR - CAP.png',
    'CORITIBA':     'PR - CFC.png',
    'BOTAFOGO':     'RJ - BFR.png',
    'FLAMENGO':     'RJ - CRF.png',
    'VASCO':        'RJ - CRVG.png',
    'FLUMINENSE':   'RJ - FFC.png',
    'ABC':          'RN - ABCFC.png',
    'AMÉRICA-RN':   'RN - AFC.png',
    'JUVENTUDE':    'RS - ECJ.png',
    'GRÊMIO':       'RS - GFPA.png',
    'INTERNACIONAL':'RS - SCI.png',
    'CHAPECOENSE':  'SC - ACF.png',
    'AVAÍ':         'SC - AFC.png',
    'CRICIÚMA':     'SC - CEC.png',
    'FIGUEIRENSE':  'SC - FFC.png',
    'PONTE PRETA':  'SP - AAPP.png',
    'GUARANI':      'SP - GFC.png',
    'BRAGANTINO':   'SP - RBB.png',
    'CORINTHIANS':  'SP - SCCP.png',
    'PALMEIRAS':    'SP - SEP.png',
    'SANTOS':       'SP - SFC.png',
    'SÃO PAULO':    'SP - SPFC.png',
}

# ── Panorama por clube ────────────────────────────────────────────────────────
# Fontes: PLURI/Stochos 2013, G20 Maiores Torcidas 2017, Mapa das Curtidas 2017,
#         XP/Convocados 2022, "O Time do Povo Mineiro" (Leonel Jr., 2021),
#         torcer.txt (ciclo midiático: mídia→desempenho→recurso→mídia)

PANORAMA_DATA = {
    'FLAMENGO': {
        'full_name': 'Clube de Regatas do Flamengo',
        'founded': 1895, 'state': 'RJ',
        'base_rank': 1, 'base_pct': 22.4,
        'media': 'Alto', 'finances': 'Alto',
        'recent_titles': ['Brasileirão 2019', 'Libertadores 2019', 'Brasileirão 2020',
                          'Copa do Brasil 2022', 'Libertadores 2022', 'Copa do Brasil 2024'],
        'panorama': ('Maior torcida do Brasil no mapa de curtidas do Facebook (2017), aplicado ao Censo IBGE 2022. '
                     'O Flamengo vive o ciclo virtuoso: domínio midiático nacional (Globo/SporTV), receitas superiores a R$1,5 bi/ano '
                     'e títulos que retroalimentam a captação de novos torcedores. Lidera especialmente no Norte e Nordeste, '
                     'onde supera 40% das curtidas municipais — reflexo da migração nordestina e da ausência de clubes locais fortes. '
                     'O fenômeno é explicado pelo ciclo mídia → desempenho → recurso → mídia: o clube mais exibido capta '
                     'proporcionalmente mais torcedores em regiões sem clube local consolidado.'),
        'proj_5':  ('Até 2030, com receitas crescentes e pipeline de jovens talentos, o Flamengo deve consolidar entre 18–20% '
                    'da torcida nacional. A penetração no Norte (PA, AM, RR) deve crescer 3–5 pp, acelerada pela presença de '
                    'jogadores dessas regiões na base e pela expansão do streaming. Risco: instabilidade política interna, '
                    'característica histórica do clube.'),
        'proj_10': ('Em 2035, sendo mantido o diferencial de receita (estimado em R$2–3 bi/ano), o Flamengo pode ultrapassar '
                    '20% da torcida nacional, aproximando-se do patamar dos grandes clubes europeus (25–30%). A concorrência '
                    'de Palmeiras e Corinthians limitará esse crescimento nas regiões Sul e interior de SP.'),
        'proj_20': ('Em 2045, o Flamengo deve ser o primeiro clube brasileiro a superar 25% de torcida nacional, caso o ciclo '
                    'midiático-financeiro se mantenha. O risco de longo prazo é a globalização do entretenimento desportivo '
                    '(clubes europeus no streaming) que pode fragmentar ainda mais a atenção do torcedor jovem.'),
    },
    'CORINTHIANS': {
        'full_name': 'Sport Club Corinthians Paulista',
        'founded': 1910, 'state': 'SP',
        'base_rank': 2, 'base_pct': 12.6,
        'media': 'Alto', 'finances': 'Médio-alto',
        'recent_titles': ['Brasileirão 2015', 'Copa do Brasil 2023'],
        'panorama': ('Segunda maior torcida no mapa de curtidas do Facebook (2017)/IBGE 2022. Dominante no interior de SP '
                     'e no Centro-Oeste, liderando em mais de 2.000 municípios junto ao Flamengo. '
                     'Representa o "futebol do povo" paulistano, com forte penetração na classe trabalhadora '
                     'e nas periferias urbanas de SP. O intervalo sem Brasileirão (2015–2023) '
                     'e a gestão financeira desequilibrada criaram um hiato competitivo em relação ao Palmeiras.'),
        'proj_5':  ('Até 2030, a nova gestão e a potencial SAF podem reequilibrar as finanças. Sem conquistas na '
                    'Libertadores recentemente, corre o risco de perder torcedores jovens no interior paulista '
                    'para Palmeiras. Projeção: estabilidade em ~13–14%.'),
        'proj_10': ('Em 2035, a manutenção da torcida depende de ao menos um título de Libertadores. '
                    'Sem ele, a erosão gradual para Flamengo e Palmeiras no interior de SP pode custar 1–2 pp.'),
        'proj_20': ('Em 2045, Corinthians pode manter 11–13% de torcida nacional. A identidade popular e a '
                    'massa já formada protegem de quedas abruptas, mas o crescimento é limitado sem superioridade '
                    'esportiva consistente.'),
    },
    'PALMEIRAS': {
        'full_name': 'Sociedade Esportiva Palmeiras',
        'founded': 1914, 'state': 'SP',
        'base_rank': 5, 'base_pct': 7.3,
        'media': 'Alto', 'finances': 'Alto',
        'recent_titles': ['Libertadores 2020', 'Libertadores 2021', 'Brasileirão 2022',
                          'Brasileirão 2023', 'Copa do Brasil 2015'],
        'panorama': ('Quinto maior clube no mapa de curtidas do Facebook (2017)/IBGE 2022. Vive o melhor ciclo da '
                     'história moderna, sustentado pela parceria Crefisa/FAM e pelos dois títulos de '
                     'Libertadores consecutivos (2020/21). O desempenho recente acelerou o crescimento '
                     'de curtidas, especialmente entre torcedores jovens no interior paulista.'),
        'proj_5':  ('Até 2030, com a continuidade do projeto e receitas em torno de R$1,2 bi, o Palmeiras '
                    'pode chegar a 8–9% de torcida nacional. O risco está na dependência do patrocínio principal; '
                    'uma ruptura pode comprometer o modelo.'),
        'proj_10': ('Em 2035, sendo mantida a estrutura competitiva, pode superar 10% — empatando com São Paulo '
                    'e Cruzeiro dos anos 2010. Seria o maior crescimento relativo entre os grandes clubes paulistas.'),
        'proj_20': ('Em 2045, o Palmeiras pode se firmar como 2º ou 3º maior torcida do país (~10–12%), '
                    'desde que o ciclo de títulos se mantenha ao longo de pelo menos mais duas décadas.'),
    },
    'SÃO PAULO': {
        'full_name': 'São Paulo Futebol Clube',
        'founded': 1930, 'state': 'SP',
        'base_rank': 3, 'base_pct': 9.4,
        'media': 'Alto', 'finances': 'Médio-alto',
        'recent_titles': ['Copa do Brasil 2023'],
        'panorama': ('Terceira maior torcida no mapa de curtidas do Facebook (2017)/IBGE 2022. O São Paulo sofre '
                     'com um longo jejum de títulos (Brasileirão desde 2008, Libertadores desde 2005). '
                     'Perde espaço relativo para Corinthians e Palmeiras no interior paulista — '
                     'reflexo do ciclo de desempenho dos rivais nas últimas décadas.'),
        'proj_5':  ('Até 2030, a estabilização do clube com a SAF (se adotada) ou nova gestão pode conter a erosão. '
                    'Sem Libertadores, projeção de queda para ~9–10% nacionalmente.'),
        'proj_10': ('Em 2035, risco de perder o 3º lugar para o Palmeiras em ascensão. Manutenção em ~8–10% '
                    'depende de ao menos um título continental.'),
        'proj_20': ('Em 2045, São Paulo deve se estabilizar em 7–9% — clube grande, mas provavelmente sem crescimento '
                    'expressivo de torcida, dado o quadro competitivo atual.'),
    },
    'CRUZEIRO': {
        'full_name': 'Cruzeiro Esporte Clube',
        'founded': 1921, 'state': 'MG',
        'base_rank': 6, 'base_pct': 4.4,
        'media': 'Médio', 'finances': 'Médio (SAF 2022)',
        'recent_titles': ['Brasileirão 2013', 'Brasileirão 2014', 'Copa do Brasil 2018'],
        'panorama': ('O livro "O Time do Povo Mineiro" (Leonel Jr., 2021) documenta que o Cruzeiro é o clube '
                     'mais popular de MG desde a era Palestra Itália, com raízes operárias e penetração nas '
                     'classes populares do interior mineiro. Após o bi-campeonato (2013/14), o clube passou por '
                     'rebaixamento histórico (2019) e segunda queda (2023), seguida de reestruturação via SAF '
                     'com aporte do grupo Ronaldo. O ciclo midiático sofreu com a ausência da Série A.'),
        'proj_5':  ('Até 2030, com retorno à Série A e reestruturação SAF, o Cruzeiro pode recuperar 7–8% '
                    'de torcida, especialmente em MG onde a pesquisa PLURI indica ~60% de fidelidade aos '
                    'clubes locais. Crucial: manter o clube na elite por ao menos 3 temporadas consecutivas.'),
        'proj_10': ('Em 2035, um título de Brasileirão ou Libertadores pode catapultar de volta para 9–10%. '
                    'A geração de torcedores nascida pós-2015 foi formada sob o rebaixamento — recuperar essa '
                    'faixa etária é o maior desafio.'),
        'proj_20': ('Em 2045, o Cruzeiro tem potencial de 8–10% se o modelo SAF gerar sustentabilidade financeira. '
                    'MG concentra 21 milhões de habitantes; com 60% de fidelidade local, a base é sólida. '
                    'O risco maior é a perda gradual de jovens mineiros para Flamengo via mídia nacional.'),
    },
    'ATLÉTICO-MG': {
        'full_name': 'Clube Atlético Mineiro',
        'founded': 1908, 'state': 'MG',
        'base_rank': 9, 'base_pct': 3.2,
        'media': 'Médio', 'finances': 'Médio-alto',
        'recent_titles': ['Copa do Brasil 2014', 'Brasileirão 2021', 'Copa do Brasil 2021',
                          'Brasileirão 2024', 'Copa do Brasil 2024'],
        'panorama': ('O Atlético-MG oscilou de 6º (2014) para 9º (2016) em torcida nacional, reflexo das '
                     'turbulências financeiras pós-2014. O bi-campeonato de 2021 (Brasileirão + Copa do Brasil) '
                     'e o novo Mineirão revitalizaram o clube. Disputam com Cruzeiro a liderança local em MG, '
                     'onde a rivalidade histórica é documentada desde a pesquisa de 1931 (Atl. 44,7% vs '
                     'Palestra/Cruzeiro 38%).'),
        'proj_5':  ('Até 2030, com as conquistas de 2021 e 2024 e a Arena MRV (novo estádio), o Atletismo '
                    'deve recuperar a 6ª posição nacional (~7%). A proximidade com Flamengo e Corinthians '
                    'na captação de jovens mineiros é o principal risco.'),
        'proj_10': ('Em 2035, 6–8% de torcida nacional é projeção realista. A Arena MRV de 46 mil lugares '
                    'muda o potencial de receita e consequentemente o ciclo recurso→desempenho→mídia.'),
        'proj_20': ('Em 2045, pode atingir 8–9% se mantiver a estabilidade financeira e pelo menos 2–3 '
                    'títulos nacionais por década. Rivalidade com Cruzeiro permanece como catalisador local.'),
    },
    'GRÊMIO': {
        'full_name': 'Grêmio Foot-Ball Porto Alegrense',
        'founded': 1903, 'state': 'RS',
        'base_rank': 7, 'base_pct': 4.0,
        'media': 'Médio', 'finances': 'Médio',
        'recent_titles': ['Libertadores 2017', 'Copa do Brasil 2016', 'Recopa 2018'],
        'panorama': ('No RS, mais de 90% da população prefere clubes gaúchos (PLURI 2013), tornando o estado '
                     'um dos mais fiéis ao futebol local. Grêmio e Internacional polarizam a preferência '
                     'regional. A Libertadores 2017 foi o maior título recente e impulsionou o reconhecimento '
                     'nacional. Rebaixamento em 2023 interrompeu o ciclo positivo.'),
        'proj_5':  ('Até 2030, com retorno à Série A e projeto de arena própria, o Grêmio deve estabilizar '
                    'em ~5% nacional. A base gaúcha é sólida e resistente à penetração de Flamengo/Corinthians.'),
        'proj_10': ('Em 2035, 5–6% de torcida é realista, dependente de ao menos uma Libertadores no período. '
                    'Fora do RS, crescimento limitado pela barreira midiática.'),
        'proj_20': ('Em 2045, o Grêmio deve manter ~4–6% de torcida nacional. A identidade gaúcha forte '
                    'protege contra erosão mas limita crescimento além das fronteiras regionais.'),
    },
    'INTERNACIONAL': {
        'full_name': 'Sport Club Internacional',
        'founded': 1909, 'state': 'RS',
        'base_rank': 8, 'base_pct': 3.7,
        'media': 'Médio', 'finances': 'Médio',
        'recent_titles': ['Copa do Brasil 2023'],
        'panorama': ('O Inter domina o oeste do RS e mantém presença em Santa Catarina e norte do Paraná. '
                     'Junto ao Grêmio, forma o duelo mais equilibrado do futebol brasileiro em termos regionais. '
                     'O programa de sócios é o mais eficiente proporcionalmente do país (G20 2017: 2% dos '
                     'torcedores são sócios, maior taxa nacional).'),
        'proj_5':  ('Até 2030, estabilidade em ~4–5% nacional. O fortalecimento do programa de sócios '
                    'pode aumentar as receitas e melhorar o ciclo competitivo.'),
        'proj_10': ('Em 2035, 4–6% de torcida; dependente de títulos sul-americanos para crescer além do RS.'),
        'proj_20': ('Em 2045, similar ao Grêmio: 4–6% protegido pelo futebol gaúcho, crescimento limitado fora.'),
    },
    'BAHIA': {
        'full_name': 'Esporte Clube Bahia',
        'founded': 1931, 'state': 'BA',
        'base_rank': 11, 'base_pct': 3.2,
        'media': 'Baixo-médio', 'finances': 'Alto (SAF City Football Group)',
        'recent_titles': ['Copa do Nordeste 2021'],
        'panorama': ('O Bahia foi adquirido pelo City Football Group (Manchester City) via SAF em 2023, '
                     'o maior aporte do futebol baiano na história. Historicamente domina a BA junto ao '
                     'Vitória. O nordeste é estratégico: é a região onde Flamengo mais cresce externamente, '
                     'mas onde ainda há forte identidade local (Bahia/Vitória dominam 17 municípios baianos).'),
        'proj_5':  ('Até 2030, o investimento do City Group pode colocar o Bahia entre os 8 maiores do país '
                    'por receita. Vitórias na Copa do Nordeste e avanços na Libertadores podem capturar '
                    'torcedores jovens que migraram para Flamengo. Projeção: crescimento para 4–5%.'),
        'proj_10': ('Em 2035, se o modelo City funcionar como no Montevideo City Torque/Girona, o Bahia '
                    'pode ser o maior clube do Nordeste em recursos e torcida. Projeção: 5–6%.'),
        'proj_20': ('Em 2045, o Bahia pode ser o Flamengo do Nordeste — clube que rompe o ciclo midiático '
                    'regional e projeta-se nacionalmente. Projeção ousada: 6–8%.'),
    },
    'VITÓRIA': {
        'full_name': 'Esporte Clube Vitória',
        'founded': 1899, 'state': 'BA',
        'base_rank': 14, 'base_pct': 2.1,
        'media': 'Baixo', 'finances': 'Baixo-médio',
        'recent_titles': ['Copa do Nordeste 2010'],
        'panorama': ('O Vitória domina o interior da BA em proporção de curtidas, mas perde para o Bahia '
                     'nas cidades maiores. Oscilação entre Série A e B limita o ciclo midiático. '
                     'A pesquisa mostra o Vitória entre as 20 maiores torcidas, mas em declínio relativo.'),
        'proj_5':  ('Até 2030, sem um projeto de SAF, dificilmente romperá o ciclo de instabilidade. '
                    'Torcida estável em ~2% nacional.'),
        'proj_10': ('Em 2035, risco real de erosão para 1,5–1,8% se o Bahia (SAF) dominar a mídia baiana.'),
        'proj_20': ('Em 2045, pode perder espaço para o Bahia na BA e consolidar-se como clube regional '
                    'forte mas de alcance limitado. Projeção: 1,5–2%.'),
    },
    'SPORT': {
        'full_name': 'Sport Club do Recife',
        'founded': 1905, 'state': 'PE',
        'base_rank': 13, 'base_pct': 2.3,
        'media': 'Baixo', 'finances': 'Baixo-médio',
        'recent_titles': ['Brasileirão 1987'],
        'panorama': ('O Sport lidera as curtidas em PE junto ao Santa Cruz, ambos rivais históricos. '
                     'Sem títulos nacionais recentes, o clube mantém torcida fiel pernambucana mas sofre '
                     'com a hegemonia midiática de Flamengo/Corinthians no estado.'),
        'proj_5':  ('Até 2030, estabilidade em ~2% nacional; dependente de retorno à Série A.'),
        'proj_10': ('Em 2035, risco de declínio para 1,5% sem conquistas que renovem a torcida jovem.'),
        'proj_20': ('Em 2045, ~1,5–2%. A identidade nordestina protege, mas limita crescimento.'),
    },
    'FORTALEZA': {
        'full_name': 'Fortaleza Esporte Clube',
        'founded': 1918, 'state': 'CE',
        'base_rank': 17, 'base_pct': 1.4,
        'media': 'Baixo-médio', 'finances': 'Médio',
        'recent_titles': ['Copa do Nordeste 2022', 'Copa do Nordeste 2023'],
        'panorama': ('O Fortaleza tem crescido consistentemente na Série A (2018–) e acumulou '
                     'dois títulos do Nordestão consecutivos. O CE exibe polarização Fortaleza×Ceará '
                     'semelhante ao duelo gaúcho, com ambos disputando cerca de 9 municípios estaduais.'),
        'proj_5':  ('Até 2030, crescimento para 2–2,5% nacional com consistência na Série A. '
                    'Expansão de estádio e projeto de internacionalização são pontos positivos.'),
        'proj_10': ('Em 2035, 2,5–3% se mantiver regularidade e atingir semifinais de Libertadores.'),
        'proj_20': ('Em 2045, pode ser um dos principais clubes do Nordeste em torcida e infraestrutura. '
                    'Projeção: 2,5–3,5%.'),
    },
    'FLUMINENSE': {
        'full_name': 'Fluminense Football Club',
        'founded': 1902, 'state': 'RJ',
        'base_rank': 10, 'base_pct': 2.7,
        'media': 'Médio', 'finances': 'Médio',
        'recent_titles': ['Libertadores 2023'],
        'panorama': ('O Fluminense tem torcida expressiva no estado do RJ mas sofre com o domínio '
                     'avassalador do Flamengo na mídia carioca e nacional. A conquista da Libertadores '
                     '2023 foi um marco histórico que gerou grande repercussão, mas o clube ainda '
                     'enfrenta desafios financeiros estruturais.'),
        'proj_5':  ('Até 2030, o título 2023 pode trazer novos patrocinadores e crescimento para ~3%. '
                    'Fundamental manter o desempenho na Série A.'),
        'proj_10': ('Em 2035, 2,5–3,5% de torcida; crescimento limitado pela sombra do Flamengo no RJ.'),
        'proj_20': ('Em 2045, ~2,5–3%. Clube com identidade forte, mas espaço de crescimento limitado '
                    'enquanto o Flamengo dominar a mídia nacional.'),
    },
    'VASCO': {
        'full_name': 'Club de Regatas Vasco da Gama',
        'founded': 1898, 'state': 'RJ',
        'base_rank': 5, 'base_pct': 4.6,
        'media': 'Médio', 'finances': 'Médio (SAF 777 Partners)',
        'recent_titles': ['Copa do Brasil 2011'],
        'panorama': ('Forte penetração no interior do RJ e no Norte (especialmente PA, AM) no mapa de curtidas do Facebook. '
                     'O clube passou por período de instabilidade '
                     'e foi adquirido pelo grupo 777 Partners via SAF em 2022. A incerteza do investidor '
                     'internacional gerou turbulência adicional ao projeto esportivo.'),
        'proj_5':  ('Até 2030, com a SAF estabilizada, retorno ao protagonismo nacional é possível. '
                    'Projeção: manutenção em 4–5%.'),
        'proj_10': ('Em 2035, crescimento para 5–6% se título de Brasileirão ou Libertadores vier.'),
        'proj_20': ('Em 2045, 4–6% de torcida, dependente da solidez do projeto SAF de longo prazo.'),
    },
    'BOTAFOGO': {
        'full_name': 'Botafogo de Futebol e Regatas',
        'founded': 1894, 'state': 'RJ',
        'base_rank': 11, 'base_pct': 2.2,
        'media': 'Médio', 'finances': 'Alto (SAF John Textor)',
        'recent_titles': ['Libertadores 2024', 'Brasileirão 2024'],
        'panorama': ('O Botafogo passou por transformação radical com a SAF de John Textor (Eagle Football), '
                     'conquistando o Brasileirão e a Libertadores em 2024 — o maior ciclo vitorioso recente. '
                     'Historicamente, o clube tinha uma das menores proporções de sócios/torcedores do Brasil.'),
        'proj_5':  ('Até 2030, as conquistas de 2024 podem catapultar a torcida para 3–4%. O modelo SAF '
                    'com aporte americano é o mais agressivo do futebol brasileiro atual.'),
        'proj_10': ('Em 2035, se mantiver o investimento e conquistas, pode atingir 4–5% — o maior '
                    'crescimento relativo entre os cariocas, após o Flamengo.'),
        'proj_20': ('Em 2045, 4–6% é projeção possível. O risco é a saída do investidor principal.'),
    },
    'SANTOS': {
        'full_name': 'Santos Futebol Clube',
        'founded': 1912, 'state': 'SP',
        'base_rank': 12, 'base_pct': 2.0,
        'media': 'Médio', 'finances': 'Baixo-médio',
        'recent_titles': ['Brasileirão 2004'],
        'panorama': ('Torcida nacional sustentada pelo legado histórico de Pelé e Neymar. '
                     'Sem títulos expressivos desde 2004 e após o rebaixamento '
                     'de 2023 para a Série B, o clube enfrenta a maior crise da história recente, '
                     'com queda nas curtidas especialmente entre torcedores jovens do interior paulista.'),
        'proj_5':  ('Até 2030, retorno à Série A é fundamental. Sem ele, erosão de torcida jovem '
                    'para Corinthians e Palmeiras. Projeção: queda para ~4%.'),
        'proj_10': ('Em 2035, 3,5–4,5% de torcida, dependente de reestruturação financeira urgente.'),
        'proj_20': ('Em 2045, o legado histórico protege uma base mínima, mas o clube pode cair do '
                    'top-8 em torcida para o top-12 sem uma virada estrutural.'),
    },
    'ATHLETICO-PR': {
        'full_name': 'Club Athletico Paranaense',
        'founded': 1924, 'state': 'PR',
        'base_rank': 15, 'base_pct': 1.8,
        'media': 'Baixo-médio', 'finances': 'Médio-alto',
        'recent_titles': ['Copa do Brasil 2019', 'Copa Sul-Americana 2021', 'Copa Sul-Americana 2022'],
        'panorama': ('O Athletico-PR tem o projeto esportivo mais consistente do Sul fora da dupla gaúcha, '
                     'com três títulos internacionais/nacionais em 4 anos. A Arena da Baixada foi renovada '
                     'e o clube mantém modelo moderno de gestão.'),
        'proj_5':  ('Até 2030, crescimento para 2,5–3% nacional com consistência na Série A e '
                    'Libertadores. Referência de gestão no futebol brasileiro.'),
        'proj_10': ('Em 2035, 2,5–3,5% de torcida; o maior do PR se Coritiba não se recuperar.'),
        'proj_20': ('Em 2045, 3–4% é projeção otimista. O PR tem 11,5 milhões de habitantes — '
                    'potencial de crescimento real se a mídia regional se consolidar.'),
    },
    'CORITIBA': {
        'full_name': 'Coritiba Foot Ball Club',
        'founded': 1909, 'state': 'PR',
        'base_rank': 18, 'base_pct': 1.2,
        'media': 'Baixo', 'finances': 'Baixo',
        'recent_titles': [],
        'panorama': ('O Coritiba disputa o PR com o Athletico, mas sem infraestrutura e desempenho '
                     'equivalente. Oscila entre Série A e B, o que limita o ciclo midiático.'),
        'proj_5':  ('Até 2030, estabilidade em ~1,2% se permanecer na Série A.'),
        'proj_10': ('Em 2035, risco de queda para 0,8–1% se Athletico consolidar domínio paranaense.'),
        'proj_20': ('Em 2045, clube relevante no PR mas de alcance nacional limitado.'),
    },
    'CHAPECOENSE': {
        'full_name': 'Associação Chapecoense de Futebol',
        'founded': 1973, 'state': 'SC',
        'base_rank': 0, 'base_pct': 0.8,
        'media': 'Baixo-médio', 'finances': 'Baixo',
        'recent_titles': ['Copa Sul-Americana 2016 (póstuma)'],
        'panorama': ('A Chapecoense viveu uma das maiores tragédias do futebol mundial (2016) e depois '
                     'o declínio esportivo. O clube ainda é referência de resiliência, mas a reconstrução '
                     'foi lenta e incompleta.'),
        'proj_5':  ('Até 2030, recuperação gradual; permanência na Série A seria um marco.'),
        'proj_10': ('Em 2035, clube regional forte em SC mas sem alcance nacional expressivo.'),
        'proj_20': ('Em 2045, ~0,8–1% de torcida nacional; identidade forte em SC-Oeste.'),
    },
    'REMO': {
        'full_name': 'Clube do Remo',
        'founded': 1905, 'state': 'PA',
        'base_rank': 0, 'base_pct': 0.5,
        'media': 'Baixo', 'finances': 'Baixo',
        'recent_titles': [],
        'panorama': ('O Remo lidera em proporção de curtidas em grande parte do PA, especialmente '
                     'na região metropolitana de Belém. A disputa com o Paysandu é um dos clássicos '
                     'mais intensos do Norte. Ambos convivem com a dominância do Flamengo no estado.'),
        'proj_5':  ('Até 2030, manter-se na Série B/C e crescer o programa de sócios é o objetivo.'),
        'proj_10': ('Em 2035, o risco é o avanço do Flamengo no PA com a Copa 2014 e eventos internacionais '
                    'que ampliaram a mídia nacional na região.'),
        'proj_20': ('Em 2045, clube de identidade paraense forte, mas de penetração nacional limitada.'),
    },
    'PAYSANDU': {
        'full_name': 'Paysandu Sport Club',
        'founded': 1914, 'state': 'PA',
        'base_rank': 0, 'base_pct': 0.4,
        'media': 'Baixo', 'finances': 'Baixo',
        'recent_titles': [],
        'panorama': ('O Paysandu divide com o Remo a preferência no PA. Com 16 títulos estaduais, '
                     'é o mais vitorioso do Norte historicamente, mas sem presença recente na Série A.'),
        'proj_5':  ('Retorno à Série B/A é o horizonte dos próximos 5 anos.'),
        'proj_10': ('Em 2035, depende de investimento e projeto estruturado.'),
        'proj_20': ('Em 2045, clube relevante regionalmente, sem projeção nacional expressiva.'),
    },
    'CEARÁ': {
        'full_name': 'Ceará Sporting Club',
        'founded': 1914, 'state': 'CE',
        'base_rank': 0, 'base_pct': 0.9,
        'media': 'Baixo', 'finances': 'Baixo-médio',
        'recent_titles': ['Copa do Nordeste 2015', 'Copa do Nordeste 2020'],
        'panorama': ('O Ceará polariza o CE com o Fortaleza. Ambos dividiram a Série A por alguns anos, '
                     'sendo o CE pioneiro no retorno à elite. Disputa de cerca de 9 municípios estaduais.'),
        'proj_5':  ('Até 2030, manutenção na Série A e crescimento para 1,2–1,5%.'),
        'proj_10': ('Em 2035, 1–1,5%; estabilidade regional.'),
        'proj_20': ('Em 2045, ~1–1,5%. Crescimento limitado pela concorrência interna (Fortaleza SAF).'),
    },
    'CRICIÚMA': {
        'full_name': 'Criciúma Esporte Clube',
        'founded': 1947, 'state': 'SC',
        'base_rank': 0, 'base_pct': 0.4,
        'media': 'Baixo', 'finances': 'Baixo',
        'recent_titles': ['Copa do Brasil 1991'],
        'panorama': ('O Criciúma lidera a região carbonífera de SC. Único campeão de Copa do Brasil '
                     'fora do eixo RJ-SP-RS. Presença modesta mas consistente no futebol catarinense.'),
        'proj_5':  ('Manutenção na Série A ou B; torcida regional estável em ~0,4%.'),
        'proj_10': ('Em 2035, ~0,3–0,5%; clube de identidade regional forte.'),
        'proj_20': ('Em 2045, identidade preservada mas crescimento nacional improvável.'),
    },
    'SANTA CRUZ': {
        'full_name': 'Santa Cruz Futebol Clube',
        'founded': 1914, 'state': 'PE',
        'base_rank': 16, 'base_pct': 1.0,
        'media': 'Baixo', 'finances': 'Baixo',
        'recent_titles': [],
        'panorama': ('O Santa Cruz foi um dos clubes nordestinos mais populares nos anos 2000-2010. '
                     'O declínio para a Série C/D é um caso clássico do ciclo negativo: sem mídia, '
                     'sem recursos, sem desempenho — levando ao afastamento de torcedores para o Flamengo.'),
        'proj_5':  ('Até 2030, retorno à Série B é o objetivo; torcida em erosão.'),
        'proj_10': ('Em 2035, risco de queda para 0,6–0,8% de torcida nacional.'),
        'proj_20': ('Em 2045, clube com identidade nordestina resistente mas de alcance nacional mínimo.'),
    },
}


def load_crests():
    """Carrega os escudos dos clubes como data URLs base64."""
    crests = {}
    if not ESCUDOS_DIR.exists():
        return crests
    for club, filename in CREST_FILES.items():
        path = ESCUDOS_DIR / filename
        if path.exists():
            data = base64.b64encode(path.read_bytes()).decode()
            crests[club] = f'data:image/png;base64,{data}'
    return crests


def normalize_club(name):
    if pd.isna(name) or str(name).strip() == '':
        return ''
    s = str(name).strip().upper()
    return CLUB_ALIASES.get(s, s)


def get_club_color(club):
    return CLUB_COLORS.get(normalize_club(club), DEFAULT_COLOR)


# ── TopoJSON → GeoJSON ────────────────────────────────────────────────────────

def _decode_arcs(topo):
    """Decode delta-encoded, quantized arcs from TopoJSON."""
    raw_arcs = topo['arcs']
    transform = topo.get('transform')
    if transform:
        sx, sy = transform['scale']
        tx, ty = transform['translate']
        decoded = []
        for arc in raw_arcs:
            x = y = 0
            coords = []
            for pt in arc:
                x += pt[0]
                y += pt[1]
                coords.append([round(x * sx + tx, 6), round(y * sy + ty, 6)])
            decoded.append(coords)
    else:
        decoded = [list(arc) for arc in raw_arcs]
    return decoded


def _stitch(arc_indices, decoded):
    """Stitch arcs into a closed GeoJSON ring."""
    coords = []
    for idx in arc_indices:
        arc = decoded[idx] if idx >= 0 else list(reversed(decoded[~idx]))
        coords.extend(arc if not coords else arc[1:])
    # GeoJSON rings must be explicitly closed (first == last point)
    if coords and (coords[0][0] != coords[-1][0] or coords[0][1] != coords[-1][1]):
        coords.append(coords[0])
    return coords


def _geom(g, decoded):
    t = g.get('type')
    if t == 'Polygon':
        return {'type': 'Polygon', 'coordinates': [_stitch(r, decoded) for r in g['arcs']]}
    if t == 'MultiPolygon':
        return {'type': 'MultiPolygon',
                'coordinates': [[_stitch(r, decoded) for r in poly] for poly in g['arcs']]}
    if t in ('Point', 'MultiPoint'):
        return {'type': t, 'coordinates': g.get('coordinates', [])}
    return None


def topojson_to_geojson(raw_bytes, obj_name):
    """Convert TopoJSON (optionally gzip) to GeoJSON FeatureCollection."""
    try:
        data = gzip.decompress(raw_bytes)
    except Exception:
        data = raw_bytes
    topo = json.loads(data)
    decoded = _decode_arcs(topo)
    obj = topo['objects'][obj_name]
    features = []
    for g in obj.get('geometries', []):
        geo = _geom(g, decoded)
        if geo:
            features.append({'type': 'Feature', 'geometry': geo,
                             'properties': g.get('properties', {})})
    gj = {'type': 'FeatureCollection', 'features': features}
    print(f'    -> {len(features)} features')
    return gj


# ── Download com cache ─────────────────────────────────────────────────────────

def download(url, cache_name, desc=''):
    cache_file = CACHE_DIR / cache_name
    if cache_file.exists() and cache_file.stat().st_size > 100:
        print(f'  (cache) {desc}')
        return cache_file.read_bytes()
    print(f'  Baixando {desc} ...')
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
        # Decompress gzip if needed before caching
        try:
            raw = gzip.decompress(raw)
        except Exception:
            pass
        cache_file.write_bytes(raw)
        print(f'    OK ({len(raw)/1024:.0f} KB)')
        return raw
    except Exception as e:
        print(f'  ERRO: {e}')
        return None


# ── Leitura dos dados Excel ────────────────────────────────────────────────────

def read_drb_geo():
    """Lê colunas geográficas do drb. Retorna DataFrame com códigos IBGE completos."""
    print('Lendo hierarquia geográfica (drb)...')

    # Detecta linha de início dos dados
    df_raw = pd.read_excel(DRB_FILE, sheet_name='drb', header=None, nrows=6, usecols=range(13))
    data_start = 0
    for i in range(len(df_raw)):
        val = df_raw.iloc[i, 0]
        try:
            v = int(float(str(val)))
            if 11 <= v <= 53:
                data_start = i
                break
        except Exception:
            pass

    print(f'  Dados começam na linha {data_start}')

    df = pd.read_excel(
        DRB_FILE, sheet_name='drb',
        header=None, skiprows=data_start,
        usecols=range(13), dtype=str,
    )
    # Assign expected column names per actual Excel column order:
    # 0:codigo_uf, 1:nome_uf,
    # 2:codigo_rgi (Reg.Geog.Intermediária = 4-digit, e.g. 1102) ← usamos para MESO
    # 3:nome_rgi,
    # 4:codigo_rgim (Reg.Geog.Imediata = 6-digit, e.g. 110005) ← não usamos
    # 5:nome_rgim,
    # 6:codigo_meso_local (sequential within state, e.g. 2)
    # 7:nome_meso,
    # Column layout (0-indexed):
    # 0:uf_code, 1:nome_uf
    # 2:rgi_code (RGI nova div 2017 – NÃO é mesorregião), 3:nome_rgi
    # 4:rgim_code, 5:nome_rgim
    # 6:meso_seq  (número sequencial da mesorregião no estado: 1..N)  ← base do código IBGE
    # 7:nome_meso (nome oficial da mesorregião)
    # 8:micro_seq (número sequencial da microrregião no estado: 1..M)
    # 9:nome_micro
    # 10:mun_abrev, 11:mun_completo (7 dígitos), 12:nome_municipio
    df.columns = [
        'uf_code_raw', 'nome_uf',
        'rgi_code', 'nome_rgi',
        'rgim_code', 'nome_rgim',
        'meso_seq', 'nome_meso',      # col 6 = seq mesorregião, col 7 = nome real
        'micro_seq', 'nome_micro',    # col 8 = seq microrregião, col 9 = nome real
        'mun_abrev', 'mun_completo', 'nome_municipio',
    ]

    def to_int(col):
        return pd.to_numeric(df[col], errors='coerce').astype('Int64')

    df['uf_code']       = to_int('uf_code_raw')
    df['meso_seq_int']  = to_int('meso_seq')
    df['micro_seq_int'] = to_int('micro_seq')
    df['mun_completo']  = to_int('mun_completo')
    df['mun_abrev']     = to_int('mun_abrev')

    df['sigla_uf']      = df['uf_code'].map(UF_CODE)
    df['nome_municipio'] = df['nome_municipio'].astype(str).str.strip()
    df['nome_meso']     = df['nome_meso'].astype(str).str.strip()
    df['nome_micro']    = df['nome_micro'].astype(str).str.strip()

    # Código 4 dígitos de mesorregião: {uf:02d}{seq:02d}  ex: 3101 = Noroeste de Minas
    df['meso_code_full'] = df.apply(
        lambda r: int(f"{int(r['uf_code']):02d}{int(r['meso_seq_int']):02d}")
        if pd.notna(r['uf_code']) and pd.notna(r['meso_seq_int']) else pd.NA,
        axis=1
    )

    # Código 5 dígitos de microrregião: {uf:02d}{seq:03d}  ex: 31001 = Unaí (MG)
    df['micro_code_full'] = df.apply(
        lambda r: int(f"{int(r['uf_code']):02d}{int(r['micro_seq_int']):03d}")
        if pd.notna(r['uf_code']) and pd.notna(r['micro_seq_int']) else pd.NA,
        axis=1
    )

    df = df.dropna(subset=['uf_code', 'mun_completo'])
    df = df[df['uf_code'].between(11, 53)]
    print(f'  {len(df)} municípios')
    print(f'  Mesorregiões únicas: {df["meso_code_full"].nunique()}')
    print(f'  Microrregiões únicas: {df["micro_code_full"].nunique()}')
    return df


def _parse_curtidas_sheet(df, has_curtidas):
    result = {}
    for _, row in df.iterrows():
        cidade_raw = str(row.iloc[0])
        if cidade_raw in ('nan', '', 'None'):
            continue
        mun_name = cidade_raw.rsplit(',', 1)[0].strip() if ',' in cidade_raw else cidade_raw.strip()

        try:
            uf_code = int(float(str(row.iloc[1])))
        except Exception:
            continue

        pop = 0
        if not has_curtidas:
            try:
                pop = int(float(str(row.iloc[3])))
            except Exception:
                pop = 0

        club_start = 3 if has_curtidas else 4
        step = 3 if has_curtidas else 2

        clubs = {}
        i = club_start
        while i < len(row):
            club_raw = row.iloc[i] if i < len(row) else None
            if club_raw is None or (isinstance(club_raw, float) and np.isnan(club_raw)):
                i += step
                continue
            cn = normalize_club(club_raw)
            if not cn:
                i += step
                continue

            if has_curtidas:
                try: cur = int(float(str(row.iloc[i+1]))) if i+1 < len(row) else 0
                except: cur = 0
                try: pct = float(str(row.iloc[i+2])) if i+2 < len(row) else 0.0
                except: pct = 0.0
                clubs[cn] = {'p17': pct, 'cur': cur}
            else:
                try: pct = float(str(row.iloc[i+1])) if i+1 < len(row) else 0.0
                except: pct = 0.0
                clubs[cn] = {'p15': pct}
            i += step

        key = (uf_code, mun_name.upper())
        result[key] = {'pop': pop, 'clubs': clubs}

    return result


def read_curtidas():
    print('Lendo Dados Brutos Cidade 2017...')
    d17 = _parse_curtidas_sheet(
        pd.read_excel(CURTIDAS, sheet_name='Dados Brutos Cidade 2017'),
        has_curtidas=True)
    print(f'  {len(d17)} registros')

    print('Lendo Dados Brutos Cidade 2015...')
    d15 = _parse_curtidas_sheet(
        pd.read_excel(CURTIDAS, sheet_name='Dados Brutos Cidade 2015'),
        has_curtidas=False)
    print(f'  {len(d15)} registros')
    return d15, d17


# ── Processamento por município ────────────────────────────────────────────────

def build_municipality_data(df_geo, data15, data17):
    print('Processando municípios...')

    # Carregar populações reais IBGE Censo 2022 por município
    pop_ibge_path = CACHE_DIR / 'pop_ibge_2022_mun.json'
    if pop_ibge_path.exists():
        import json as _json
        with open(pop_ibge_path, encoding='utf-8') as _f:
            POP_MUN_2022 = _json.load(_f)
        print(f'  Pop IBGE 2022: {len(POP_MUN_2022)} municípios carregados')
    else:
        POP_MUN_2022 = {}
        print('  AVISO: pop_ibge_2022_mun.json não encontrado — usando estimativa')

    municipalities = []
    unmatched = 0

    for _, row in df_geo.iterrows():
        uf_code    = int(row['uf_code'])
        sigla      = UF_CODE.get(uf_code, '')
        mun_name   = str(row['nome_municipio']).strip()
        id7        = int(row['mun_completo'])
        meso_code  = int(row['meso_code_full']) if pd.notna(row['meso_code_full']) else 0
        micro_code = int(row['micro_code_full']) if pd.notna(row['micro_code_full']) else 0
        meso_name  = str(row['nome_meso']).strip()
        micro_name = str(row['nome_micro']).strip()
        regiao     = UF_TO_REGIAO.get(sigla, '')

        key = (uf_code, mun_name.upper())
        d15 = data15.get(key, {})
        d17 = data17.get(key, {})

        if not d15 and not d17:
            unmatched += 1

        clubs15 = d15.get('clubs', {})
        clubs17 = d17.get('clubs', {})

        # Usar população real IBGE 2022 por município (Censo)
        pop2022 = POP_MUN_2022.get(str(id7), 0) or POP_MUN_2022.get(str(id7).zfill(7), 0)
        if not pop2022:
            pop2022 = d15.get('pop', 0)  # fallback

        # Average 2015 + 2017 percentages
        all_clubs = set(clubs15) | set(clubs17)
        club_avg = {}
        for club in all_clubs:
            p15 = clubs15.get(club, {}).get('p15', 0.0)
            p17 = clubs17.get(club, {}).get('p17', 0.0)
            if isinstance(p15, dict): p15 = 0.0
            if isinstance(p17, dict): p17 = 0.0
            avg = (p15 + p17) / 2 if p15 > 0 and p17 > 0 else (p15 or p17)
            if avg > 0.001:
                club_avg[club] = avg

        top10 = sorted(club_avg.items(), key=lambda x: x[1], reverse=True)[:10]

        top_list = []
        for club, avg_pct in top10:
            p15 = clubs15.get(club, {}).get('p15', 0.0)
            p17 = clubs17.get(club, {}).get('p17', 0.0)
            if isinstance(p15, dict): p15 = 0.0
            if isinstance(p17, dict): p17 = 0.0
            fans = int(pop2022 * avg_pct) if pop2022 else 0
            top_list.append({
                'c':   club,
                'p':   round(avg_pct, 4),
                'p15': round(float(p15), 4),
                'p17': round(float(p17), 4),
                'f':   fans,
            })

        dom     = top_list[0]['c']  if top_list else ''
        dom_pct = top_list[0]['p']  if top_list else 0.0

        municipalities.append({
            'id7':        id7,
            'name':       mun_name,
            'uf':         sigla,
            'uf_code':    uf_code,
            'regiao':     regiao,
            'meso_code':  meso_code,
            'meso_name':  meso_name,
            'micro_code': micro_code,
            'micro_name': micro_name,
            'pop2022':    pop2022,
            'dom':        dom,
            'dom_pct':    round(dom_pct, 4),
            'top':        top_list,
        })

    print(f'  {len(municipalities)} municípios ({unmatched} sem dados Facebook)')
    return municipalities


# ── Agregação ──────────────────────────────────────────────────────────────────

def aggregate_by_level(municipalities, level):
    print(f'Agregando por {level}...')
    groups = {}

    for m in municipalities:
        if level == 'meso':
            key, name, parent = m['meso_code'], m['meso_name'], m['uf']
        elif level == 'micro':
            key, name, parent = m['micro_code'], m['micro_name'], m['meso_name']
        elif level == 'uf':
            key, name, parent = m['uf_code'], m['uf'], m['regiao']
        else:
            key, name, parent = m['regiao'], m['regiao'], 'Brasil'

        sk = str(key)
        if sk not in groups:
            groups[sk] = {
                'id': key, 'name': name, 'parent': parent,
                'uf': m['uf'] if level != 'regiao' else name,
                'pop2022': 0, 'fan_s': {}, 'pct_s': {}, 'pct_n': {},
            }

        g = groups[sk]
        g['pop2022'] += m['pop2022']
        for t in m['top']:
            c = t['c']
            g['fan_s'][c]  = g['fan_s'].get(c, 0)   + t['f']
            g['pct_s'][c]  = g['pct_s'].get(c, 0.0) + t['p']
            g['pct_n'][c]  = g['pct_n'].get(c, 0)   + 1

    result = {}
    for sk, g in groups.items():
        top = sorted(g['fan_s'].items(), key=lambda x: x[1], reverse=True)[:10]
        top_list = [{'c': c, 'f': f, 'p': round(g['pct_s'][c]/g['pct_n'][c], 4)} for c, f in top]
        result[sk] = {
            'id':      g['id'],
            'name':    g['name'],
            'parent':  g['parent'],
            'uf':      g['uf'],
            'pop2022': g['pop2022'],
            'dom':     top_list[0]['c']  if top_list else '',
            'dom_pct': top_list[0]['p']  if top_list else 0.0,
            'top':     top_list,
        }

    print(f'  {len(result)} grupos')
    return result


# ── Download GeoJSON IBGE ──────────────────────────────────────────────────────

# IBGE API:
#   Bulk: /api/v3/malhas/paises/BR?intrarregiao=X&qualidade=Y
#   Per-state: /api/v3/malhas/estados/{code}?intrarregiao=X&qualidade=Y
#   Bulk only supports qualidade=minima for micro/mun; per-state supports baixa.
#   Object key in bulk: BRUF, BRME, BRMI, BRMU
#   Object key per-state: UF{code}UF / UF{code}ME / UF{code}MI / UF{code}MU

BULK_CONFIGS = {
    'uf':    ('https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/json&qualidade=intermediaria&intrarregiao=UF',           'gj_uf_hq.json',    'BRUF'),
    'meso':  ('https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/json&qualidade=intermediaria&intrarregiao=mesorregiao',  'gj_meso_hq.json',  'BRME'),
    'micro': ('https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/json&qualidade=intermediaria&intrarregiao=microrregiao', 'gj_micro_hq.json', 'BRMI'),
    'mun':   ('https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/json&qualidade=intermediaria&intrarregiao=municipio',    'gj_mun_hq.json',   'BRMU'),
}
PER_STATE_CONFIGS = {
    'micro': ('microrregiao', 'intermediaria', 'MI', 'gj_micro_hq.json'),
    'mun':   ('municipio',    'intermediaria', 'MU', 'gj_mun_hq.json'),
}


def _geojson_from_bulk(level, url, cache_name, obj_key):
    gj_cache = CACHE_DIR / (cache_name + '.geojson')
    if gj_cache.exists():
        gj = json.loads(gj_cache.read_bytes())
        if gj.get('features'):
            print(f'  (cache geojson) {level} - {len(gj["features"])} features')
            return gj
    raw = download(url, cache_name, f'TopoJSON bulk {level}')
    if not raw:
        return None
    gj = topojson_to_geojson(raw, obj_key)
    if gj['features']:
        gj_cache.write_bytes(json.dumps(gj, separators=(',', ':')).encode())
    return gj


def _geojson_from_states(level, intrarregiao, qualidade, type_suffix, cache_name):
    gj_cache = CACHE_DIR / (cache_name + '.geojson')
    if gj_cache.exists():
        gj = json.loads(gj_cache.read_bytes())
        if gj.get('features'):
            print(f'  (cache geojson) {level} - {len(gj["features"])} features')
            return gj

    all_features = []
    for uf_code in sorted(UF_CODE.keys()):
        url = (f'https://servicodados.ibge.gov.br/api/v3/malhas/estados/{uf_code}'
               f'?formato=application/json&qualidade={qualidade}&intrarregiao={intrarregiao}')
        raw = download(url, f'gj_{level}_{uf_code}_v2.json', f'{level} {UF_CODE[uf_code]}')
        if not raw:
            continue
        # Object key pattern: UF{code}{type} e.g. UF11MU, UF29ME
        obj_key = f'UF{uf_code:02d}{type_suffix}'
        gj = topojson_to_geojson(raw, obj_key)
        all_features.extend(gj.get('features', []))

    result = {'type': 'FeatureCollection', 'features': all_features}
    print(f'  Total {level}: {len(all_features)} features')
    if all_features:
        gj_cache.write_bytes(json.dumps(result, separators=(',', ':')).encode())
    return result


def get_geojson(level):
    """Download e converte TopoJSON do IBGE para GeoJSON, com cache."""
    # Try bulk first
    if level in BULK_CONFIGS:
        url, cache_name, obj_key = BULK_CONFIGS[level]
        print(f'  {level} (bulk): {url[:70]}...')
        gj = _geojson_from_bulk(level, url, cache_name, obj_key)
        if gj and gj.get('features'):
            return gj

    # Fallback: per-state
    if level in PER_STATE_CONFIGS:
        intrarregiao, qualidade, type_suffix, cache_name = PER_STATE_CONFIGS[level]
        print(f'  {level} (fallback por estado, qualidade={qualidade}):')
        gj = _geojson_from_states(level, intrarregiao, qualidade, type_suffix, cache_name)
        if gj and gj.get('features'):
            return gj

    return {'type': 'FeatureCollection', 'features': []}


# ── Leaflet ────────────────────────────────────────────────────────────────────

def download_leaflet():
    js  = download('https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',  'leaflet.js',  'Leaflet JS')
    css = download('https://unpkg.com/leaflet@1.9.4/dist/leaflet.css', 'leaflet.css', 'Leaflet CSS')
    return (js.decode('utf-8') if js else ''), (css.decode('utf-8') if css else '')


# ── HTML ───────────────────────────────────────────────────────────────────────

def generate_html(mun_data, agg_meso, agg_micro, agg_uf,
                  gj_mun, gj_meso, gj_micro, gj_uf,
                  leaflet_js, leaflet_css):

    mun_dict = {str(m['id7']): m for m in mun_data if m['id7']}
    all_clubs = sorted({t['c'] for m in mun_data for t in m.get('top', [])})

    total_fans = {}
    total_pop  = sum(m.get('pop2022', 0) for m in mun_data)
    for m in mun_data:
        for t in m.get('top', []):
            total_fans[t['c']] = total_fans.get(t['c'], 0) + t['f']
    legend_data = [[c, f, CLUB_COLORS.get(c, DEFAULT_COLOR),
                    round(f / total_pop, 4) if total_pop else 0]
                   for c, f in sorted(total_fans.items(), key=lambda x: x[1], reverse=True)[:20]]

    # % nacional real de cada clube (Facebook curtidas × IBGE 2022)
    nat_pct = {c: round(f / total_pop * 100, 1) for c, f in total_fans.items() if total_pop}

    # Injeta base_pct calculado nos dados do panorama (sobrescreve valor estático)
    panorama_live = {}
    for club, data in PANORAMA_DATA.items():
        updated = dict(data)
        if club in nat_pct:
            updated['base_pct'] = nat_pct[club]
        panorama_live[club] = updated

    club_colors_used = {c: CLUB_COLORS.get(c, DEFAULT_COLOR) for c in all_clubs}

    print('Carregando escudos...')
    crests = load_crests()
    print(f'  {len(crests)} escudos carregados')

    print('Serializando dados...')
    js_mun      = json.dumps(mun_dict,          ensure_ascii=False, separators=(',', ':'))
    js_meso     = json.dumps(agg_meso,          ensure_ascii=False, separators=(',', ':'))
    js_micro    = json.dumps(agg_micro,         ensure_ascii=False, separators=(',', ':'))
    js_uf       = json.dumps(agg_uf,            ensure_ascii=False, separators=(',', ':'))
    js_colors   = json.dumps(club_colors_used,  ensure_ascii=False, separators=(',', ':'))
    js_legend   = json.dumps(legend_data,       ensure_ascii=False, separators=(',', ':'))
    js_clubs    = json.dumps(all_clubs,         ensure_ascii=False, separators=(',', ':'))
    js_crests   = json.dumps(crests,            ensure_ascii=False, separators=(',', ':'))
    js_panorama = json.dumps(panorama_live,      ensure_ascii=False, separators=(',', ':'))

    print('Serializando GeoJSON...')
    js_gj_uf    = json.dumps(gj_uf,    ensure_ascii=False, separators=(',', ':'))
    js_gj_meso  = json.dumps(gj_meso,  ensure_ascii=False, separators=(',', ':'))
    js_gj_micro = json.dumps(gj_micro, ensure_ascii=False, separators=(',', ':'))
    js_gj_mun   = json.dumps(gj_mun,   ensure_ascii=False, separators=(',', ':'))

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Mapa de Torcidas do Brasil</title>
<style>
{leaflet_css}
*{{box-sizing:border-box;margin:0;padding:0}}
body,html{{height:100%;font-family:'Segoe UI',Arial,sans-serif;overflow:hidden;background:#1a1a2e}}
#header{{position:fixed;top:0;left:0;right:0;height:56px;background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);color:#fff;z-index:2000;display:flex;align-items:center;padding:0 16px;gap:12px;box-shadow:0 2px 10px rgba(0,0,0,.5)}}
#header h1{{font-size:17px;font-weight:700;white-space:nowrap}}
#header .sub{{font-size:11px;opacity:.65;line-height:1.4}}
#search-wrap{{position:relative;margin-left:auto;flex-shrink:0}}
#search-inp{{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.25);border-radius:20px;color:#fff;font-size:12px;padding:6px 12px 6px 32px;width:220px;outline:none;transition:all .2s}}
#search-inp::placeholder{{color:rgba(255,255,255,.5)}}
#search-inp:focus{{background:rgba(255,255,255,.2);border-color:rgba(255,255,255,.5);width:260px}}
#search-icon{{position:absolute;left:9px;top:50%;transform:translateY(-50%);font-size:13px;opacity:.7;pointer-events:none}}
#search-list{{position:absolute;top:calc(100% + 6px);right:0;width:280px;background:#fff;border-radius:8px;box-shadow:0 4px 20px rgba(0,0,0,.25);max-height:320px;overflow-y:auto;display:none;z-index:3000}}
#search-list.open{{display:block}}
.sr-item{{padding:8px 12px;cursor:pointer;border-bottom:1px solid #f0f0f0;display:flex;align-items:center;gap:8px}}
.sr-item:last-child{{border-bottom:none}}
.sr-item:hover{{background:#f5f7ff}}
.sr-tag{{font-size:9px;font-weight:700;text-transform:uppercase;padding:2px 6px;border-radius:10px;flex-shrink:0}}
.sr-tag.mun{{background:#e8f0fe;color:#1a5276}}
.sr-tag.club{{background:#fde8e8;color:#c0392b}}
.sr-name{{font-size:12px;color:#222;flex:1}}
.sr-sub{{font-size:10px;color:#aaa}}
#map{{position:fixed;top:56px;bottom:0;left:0;right:0}}
#controls{{position:fixed;top:66px;left:10px;z-index:1500;background:#fff;border-radius:8px;box-shadow:0 2px 14px rgba(0,0,0,.22);padding:12px 14px;min-width:210px}}
#controls h3{{font-size:11px;color:#999;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px}}
.crow{{margin-bottom:9px}}
.crow label{{font-size:12px;color:#555;display:block;margin-bottom:3px;font-weight:600}}
.crow select{{width:100%;font-size:12px;padding:5px 6px;border:1px solid #ddd;border-radius:5px;background:#fafafa}}
.cbrow{{display:flex;align-items:center;gap:6px;margin-bottom:5px;cursor:pointer;font-size:12px;color:#444}}
.cbrow input{{cursor:pointer;accent-color:#1a1a2e;width:13px;height:13px}}
.brd-sep{{border-top:1px solid #eee;margin:8px 0 8px}}
#btn-reset{{width:100%;font-size:12px;padding:7px;margin-top:4px;background:#1a1a2e;color:#fff;border:none;border-radius:5px;cursor:pointer;font-weight:600}}
#btn-reset:hover{{background:#0d3b8e}}
#btn-compare{{width:100%;font-size:12px;padding:7px;margin-top:5px;background:#fff;color:#1a1a2e;border:1.5px solid #1a1a2e;border-radius:5px;cursor:pointer;font-weight:600;display:flex;align-items:center;justify-content:center;gap:5px}}
#btn-compare.active{{background:#1a1a2e;color:#FFD700;border-color:#1a1a2e}}
#cmp-wrap{{display:none;margin-top:8px}}
#cmp-wrap.open{{display:block}}
#sel-club2{{width:100%;font-size:12px;padding:5px 6px;border:1px solid #ddd;border-radius:5px;background:#fafafa;margin-top:4px}}
/* Painel comparativo */
#cmp-panel{{position:fixed;bottom:0;left:0;right:0;background:#fff;z-index:1600;box-shadow:0 -4px 24px rgba(0,0,0,.18);transform:translateY(100%);transition:transform .3s ease;max-height:72vh;overflow-y:auto}}
#cmp-panel.open{{transform:translateY(0)}}
#cmp-header{{display:flex;align-items:center;justify-content:space-between;padding:10px 16px;background:#1a1a2e;color:#fff;position:sticky;top:0;z-index:2}}
#cmp-header h3{{font-size:13px;font-weight:700;letter-spacing:.5px}}
#btn-cmp-close{{background:none;border:none;color:#fff;font-size:18px;cursor:pointer;opacity:.7}}
#btn-cmp-close:hover{{opacity:1}}
#cmp-body{{padding:14px 16px 24px;max-width:680px;margin:0 auto}}
.cmp-col{{display:flex;flex-direction:column;gap:6px}}
.cmp-col-hdr{{display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:8px;margin-bottom:4px}}
.cmp-col-hdr img{{width:36px;height:36px;object-fit:contain}}
.cmp-col-name{{font-size:14px;font-weight:800}}
.cmp-stat{{display:flex;flex-direction:column;background:#f9f9f9;border-radius:6px;padding:7px 10px}}
.cmp-stat-lbl{{font-size:9px;text-transform:uppercase;letter-spacing:.5px;color:#aaa;font-weight:700}}
.cmp-stat-val{{font-size:15px;font-weight:800;margin-top:1px}}
.cmp-stat-sub{{font-size:10px;color:#888;margin-top:1px}}
.cmp-mid{{display:flex;flex-direction:column;align-items:center;gap:8px;padding-top:48px}}
.cmp-vs{{font-size:22px;font-weight:900;color:#1a1a2e;opacity:.2}}
.cmp-duel-bar{{width:8px;border-radius:4px;background:#eee;display:flex;flex-direction:column;overflow:hidden}}
.cmp-rank-grid{{display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-top:2px}}
#sidebar{{position:fixed;top:56px;right:0;width:330px;bottom:0;background:#fff;z-index:1400;overflow-y:auto;box-shadow:-4px 0 20px rgba(0,0,0,.13);transform:translateX(100%);transition:transform .28s ease}}
#sidebar.open{{transform:translateX(0)}}
#sb-close{{position:absolute;top:10px;right:10px;background:#eee;border:none;border-radius:50%;width:28px;height:28px;cursor:pointer;font-size:17px;display:flex;align-items:center;justify-content:center;z-index:2}}
#sb-close:hover{{background:#ddd}}
#sb-body{{padding:18px 16px 24px}}
.sb-title{{font-size:17px;font-weight:700;color:#1a1a2e;margin-bottom:2px}}
.sb-sub{{font-size:12px;color:#999;margin-bottom:2px}}
.dom-badge{{display:inline-flex;align-items:center;gap:7px;padding:7px 12px;border-radius:20px;margin:12px 0;font-size:13px;font-weight:700;color:#fff;box-shadow:0 2px 8px rgba(0,0,0,.2)}}
.stat-grid{{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-bottom:14px}}
.stat-box{{background:#f6f6f6;border-radius:7px;padding:9px 11px}}
.stat-lbl{{font-size:10px;color:#aaa;text-transform:uppercase;letter-spacing:.5px;margin-bottom:2px}}
.stat-val{{font-size:16px;font-weight:700;color:#1a1a2e}}
.clubs-ttl{{font-size:11px;color:#aaa;text-transform:uppercase;letter-spacing:1px;margin:12px 0 9px;font-weight:600}}
.cbar{{margin-bottom:10px}}
.cbar-hdr{{display:flex;justify-content:space-between;align-items:center;margin-bottom:3px}}
.cbar-name{{font-size:12px;font-weight:700}}
.cbar-pct{{font-size:11px;color:#aaa}}
.cbar-track{{height:7px;background:#eee;border-radius:4px;overflow:hidden;margin-bottom:2px}}
.cbar-fill{{height:100%;border-radius:4px;transition:width .4s}}
.cbar-fans{{font-size:11px;color:#aaa}}
.cbar-evo{{font-size:10px;color:#ccc;margin-top:1px}}
.sb-note{{font-size:10px;color:#ccc;margin-top:20px;line-height:1.6;border-top:1px solid #eee;padding-top:12px}}
.cbar-name{{cursor:pointer;transition:opacity .15s}}
.cbar-name:hover{{opacity:.7;text-decoration:underline}}
.club-hdr{{display:flex;align-items:center;gap:12px;margin-bottom:12px;padding-bottom:12px;border-bottom:1px solid #eee}}
.club-crest{{width:56px;height:56px;object-fit:contain;flex-shrink:0}}
.club-crest-placeholder{{width:56px;height:56px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:700;color:#fff}}
.club-title{{font-size:18px;font-weight:800;color:#1a1a2e;line-height:1.2}}
.club-subtitle{{font-size:11px;color:#999;margin-top:2px}}
.pan-meta{{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}}
.pan-tag{{font-size:10px;padding:3px 8px;border-radius:12px;font-weight:600}}
.pan-tag.blue{{background:#e8f0fe;color:#1a5276}}
.pan-tag.green{{background:#e9f7ef;color:#1e8449}}
.pan-tag.red{{background:#fde8e8;color:#c0392b}}
.pan-tag.gray{{background:#f5f5f5;color:#666}}
.pan-titles{{font-size:11px;color:#888;margin-bottom:12px;line-height:1.6}}
.pan-titles b{{color:#1a1a2e;font-size:10px;text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:3px}}
.pan-section{{margin-bottom:12px;padding:10px 12px;border-radius:8px;background:#f9f9f9;border-left:3px solid #ddd}}
.pan-section.now{{border-left-color:#1a1a2e}}
.pan-section.y5{{border-left-color:#2980b9}}
.pan-section.y10{{border-left-color:#27ae60}}
.pan-section.y20{{border-left-color:#8e44ad}}
.pan-label{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;margin-bottom:5px}}
.pan-section.now .pan-label{{color:#1a1a2e}}
.pan-section.y5  .pan-label{{color:#2980b9}}
.pan-section.y10 .pan-label{{color:#27ae60}}
.pan-section.y20 .pan-label{{color:#8e44ad}}
.pan-text{{font-size:11px;color:#555;line-height:1.6}}
.pan-src{{font-size:10px;color:#bbb;margin-top:14px;padding-top:10px;border-top:1px solid #eee;line-height:1.6}}
.btn-back{{width:100%;font-size:12px;padding:7px;margin-top:8px;background:#f0f0f0;color:#555;border:none;border-radius:5px;cursor:pointer;font-weight:600}}
.btn-back:hover{{background:#e0e0e0}}
#legend{{position:fixed;bottom:30px;right:10px;z-index:1300;background:#fff;border-radius:8px;box-shadow:0 2px 14px rgba(0,0,0,.18);padding:11px 14px;max-width:185px;max-height:58vh;overflow-y:auto;transition:right .28s ease}}
#legend.sb-open{{right:340px}}
#legend h3{{font-size:11px;color:#aaa;text-transform:uppercase;letter-spacing:1px;margin-bottom:9px;font-weight:600}}
.leg-item{{display:flex;align-items:center;gap:7px;margin-bottom:6px;cursor:pointer;border-radius:4px;padding:3px 4px;transition:background .15s}}
.leg-item:hover{{background:#f5f5f5}}
.leg-item.active{{background:#e8eeff;outline:2px solid #1a1a2e}}
.leg-dot{{width:13px;height:13px;border-radius:50%;flex-shrink:0}}
.leg-club{{font-size:12px;color:#333;font-weight:600}}
.leg-fans{{font-size:10px;color:#aaa}}
#lvl-badge{{position:fixed;bottom:30px;left:50%;transform:translateX(-50%);background:rgba(26,26,46,.85);color:#fff;padding:5px 16px;border-radius:20px;font-size:12px;z-index:1300;pointer-events:none;backdrop-filter:blur(4px);letter-spacing:.5px}}
.leaflet-container{{background:#f0f0f0}}
.leaflet-tooltip{{font-size:12px;padding:7px 10px;border-radius:7px;box-shadow:0 2px 10px rgba(0,0,0,.2);border:none}}
</style>
</head>
<body>
<div id="header">
  <h1>&#127463;&#127479; Mapa de Torcidas do Brasil</h1>
  <div class="sub">Dados: curtidas no Facebook (2015&ndash;2017)&nbsp;&bull;&nbsp;Estimativas pop.: Censo IBGE 2022</div>
  <div id="search-wrap">
    <span id="search-icon">&#128269;</span>
    <input id="search-inp" type="text" placeholder="Buscar cidade ou clube&hellip;" autocomplete="off">
    <div id="search-list"></div>
  </div>
</div>
<div id="map"></div>

<div id="controls">
  <h3>Controles</h3>
  <div class="crow">
    <label>N&iacute;vel geogr&aacute;fico</label>
    <select id="sel-level">
      <option value="auto">Autom&aacute;tico (por zoom)</option>
      <option value="uf">Estado (UF)</option>
      <option value="meso">Mesorregião</option>
      <option value="micro">Microrregião</option>
      <option value="mun" selected>Munic&iacute;pio</option>
    </select>
  </div>
  <div class="brd-sep"></div>
  <div class="crow">
    <label>Bordas de divis&atilde;o</label>
    <div class="cbrow"><input type="checkbox" id="brd-uf" checked> <span>Estados</span></div>
    <div class="cbrow"><input type="checkbox" id="brd-meso"> <span>Mesorregi&otilde;es</span></div>
    <div class="cbrow"><input type="checkbox" id="brd-micro"> <span>Microrregi&otilde;es</span></div>
  </div>
  <div class="brd-sep"></div>
  <div class="crow">
    <label>Filtrar por clube</label>
    <select id="sel-club">
      <option value="">&mdash; Todos &mdash;</option>
    </select>
  </div>
  <button id="btn-reset">&#8635; Ver Brasil completo</button>
  <button id="btn-compare">&#9878; Comparar dois clubes</button>
  <div id="cmp-wrap">
    <div class="crow" style="margin-top:6px">
      <label>Comparar com</label>
      <select id="sel-club2">
        <option value="">&mdash; Selecione &mdash;</option>
      </select>
    </div>
  </div>
</div>

<div id="cmp-panel">
  <div id="cmp-header">
    <h3>&#9878; Comparativo de Torcidas</h3>
    <button id="btn-cmp-close">&#215;</button>
  </div>
  <div id="cmp-body"></div>
</div>

<div id="sidebar">
  <button id="sb-close">&#215;</button>
  <div id="sb-body">
    <p style="color:#bbb;font-size:13px;margin-top:50px;text-align:center">
      Clique em uma &aacute;rea do mapa<br>para ver os detalhes.
    </p>
  </div>
</div>

<div id="legend">
  <h3>Top clubes (Brasil)</h3>
  <div id="leg-items"></div>
</div>

<div id="lvl-badge">Estados</div>

<script>
{leaflet_js}
</script>
<script>
// ── Dados ─────────────────────────────────────────────────────────────────────
const D_MUN    = {js_mun};
const D_MESO   = {js_meso};
const D_MICRO  = {js_micro};
const D_UF     = {js_uf};
const COLORS   = {js_colors};
const LEGEND   = {js_legend};
const ALL_CLUBS= {js_clubs};
const CRESTS   = {js_crests};
const PANORAMA = {js_panorama};

const GJ_UF    = {js_gj_uf};
const GJ_MESO  = {js_gj_meso};
const GJ_MICRO = {js_gj_micro};
const GJ_MUN   = {js_gj_mun};

// ── Mapa ──────────────────────────────────────────────────────────────────────
const map = L.map('map',{{center:[-14,-53],zoom:5,minZoom:4,zoomControl:true,preferCanvas:true}});

// ── Estado ────────────────────────────────────────────────────────────────────
let curLevel       = 'mun';
let clubFilter     = '';
let compareFilter  = '';
let activeLayer    = null;

// ── Utilitários ───────────────────────────────────────────────────────────────
const fmtN = n => {{
  if(!n||n===0) return '0';
  if(n>=1e6) return (n/1e6).toFixed(1).replace('.',',')+'M';
  if(n>=1e3) return (n/1e3).toFixed(1).replace('.',',')+'K';
  return n.toLocaleString('pt-BR');
}};
const fmtP = p => (p*100).toFixed(1)+'%';
const clr  = c => (c && COLORS[c]) ? COLORS[c] : '#888';

function zoomToLevel(z){{
  if(z<=5) return 'uf';
  if(z<=7) return 'meso';
  if(z<=9) return 'micro';
  return 'mun';
}}

const LEVEL_CFG = {{
  uf:    {{data:D_UF,    gj:GJ_UF,    label:'Estado',       badge:'Estados'}},
  meso:  {{data:D_MESO,  gj:GJ_MESO,  label:'Mesorregião',  badge:'Mesorregiões'}},
  micro: {{data:D_MICRO, gj:GJ_MICRO, label:'Microrregião', badge:'Microrregiões'}},
  mun:   {{data:D_MUN,   gj:GJ_MUN,   label:'Município',    badge:'Municípios'}},
}};

function lookupData(data, codarea){{
  const s = String(codarea||'');
  return data[s] || data[s.replace(/^0+/,'').padStart(s.length,'0')] || null;
}}

// ── Estilo ────────────────────────────────────────────────────────────────────

// Gradiente branco → cor primária com bandas perceptuais distintas:
//  <1%  → quase branco
//  2-5% → tint leve
//  6-9% → tint médio
// 10-20% → cor intermediária
// 20-40% → cor forte
//  40%+ → cor primária plena
function blendColor(hexFull, p){{
  const r0=parseInt(hexFull.slice(1,3),16);
  const g0=parseInt(hexFull.slice(3,5),16);
  const b0=parseInt(hexFull.slice(5,7),16);
  // pontos de controle [p, t] — interpolação linear entre eles
  const pts=[[0,0],[0.01,0.07],[0.05,0.26],[0.09,0.46],[0.20,0.66],[0.40,0.86],[1.0,1.0]];
  let t=1.0;
  for(let i=1;i<pts.length;i++){{
    if(p<=pts[i][0]){{
      const [p0,t0]=pts[i-1],[p1,t1]=pts[i];
      t=t0+(t1-t0)*(p-p0)/(p1-p0);
      break;
    }}
  }}
  t=Math.max(0,Math.min(1,t));
  return `rgb(${{Math.round(255+(r0-255)*t)}},${{Math.round(255+(g0-255)*t)}},${{Math.round(255+(b0-255)*t)}})`;
}}

function featStyle(feat, data){{
  const d = lookupData(data, feat.properties.codarea);
  if(!d) return {{fillColor:'#ddd',fillOpacity:.30,color:'rgba(200,200,200,0.15)',weight:.2}};

  // Modo comparativo: dois clubes selecionados
  if(clubFilter && compareFilter){{
    const tA = d.top && d.top.find(x=>x.c===clubFilter);
    const tB = d.top && d.top.find(x=>x.c===compareFilter);
    const pA = tA ? tA.p : 0;
    const pB = tB ? tB.p : 0;
    if(pA===0 && pB===0) return {{fillColor:'#e8e8e8',fillOpacity:.18,color:'rgba(200,200,200,0.15)',weight:.2}};
    const diff = Math.abs(pA - pB);
    const maxDiff = 0.40; // 40% de diferença = cor plena
    const t = Math.min(1, diff / maxDiff);
    const opacity = 0.20 + t * 0.72;
    if(pA > pB)  return {{fillColor:clr(clubFilter),   fillOpacity:opacity, color:'rgba(255,255,255,0.15)',weight:.2}};
    if(pB > pA)  return {{fillColor:clr(compareFilter), fillOpacity:opacity, color:'rgba(255,255,255,0.15)',weight:.2}};
    // empate
    return {{fillColor:'#aaaaaa',fillOpacity:.35,color:'rgba(200,200,200,0.15)',weight:.2}};
  }}

  if(clubFilter){{
    const t = d.top && d.top.find(x=>x.c===clubFilter);
    if(!t) return {{fillColor:'#e8e8e8',fillOpacity:.25,color:'rgba(200,200,200,0.15)',weight:.2}};
    return {{fillColor:blendColor(clr(clubFilter),t.p),fillOpacity:.92,color:'rgba(255,255,255,0.15)',weight:.2}};
  }}

  return {{fillColor:blendColor(clr(d.dom),d.dom_pct),fillOpacity:.92,color:'rgba(255,255,255,0.15)',weight:.2}};
}}

// ── Sidebar ───────────────────────────────────────────────────────────────────
function openSb(d, lvlLabel){{
  if(!d) return;
  document.getElementById('sidebar').classList.add('open');
  document.getElementById('legend').classList.add('sb-open');

  const dom=d.dom||'N/D', domC=clr(dom);
  const maxP=(d.top&&d.top[0])?d.top[0].p:1;

  const domCrest = CRESTS[dom];
  const domCrestEl = domCrest
    ? `<img src="${{domCrest}}" style="width:42px;height:42px;object-fit:contain;float:right;margin-left:8px">`
    : '';

  function renderBar(t, pos){{
    const w=maxP>0?(t.p/maxP*100).toFixed(1):0;
    const evo=(t.p15>0&&t.p17>0)
      ?`<span style="color:#bbb;font-size:10px;margin-left:6px">2015: ${{fmtP(t.p15)}} &rarr; 2017: ${{fmtP(t.p17)}}</span>`:'';
    const isSel = clubFilter && t.c===clubFilter;
    return `<div class="cbar"${{isSel?' style="background:#fffde7;border-radius:6px;padding:4px 6px;margin:0 -6px"':''}}>
      <div class="cbar-hdr">
        <span style="font-size:11px;color:#bbb;min-width:18px;font-weight:700">${{pos}}.</span>
        <span class="cbar-name" style="color:${{clr(t.c)}};flex:1;cursor:pointer" data-club="${{t.c}}" title="Ver panorama do clube">&#9679; ${{t.c}}</span>
        <span class="cbar-pct">${{fmtP(t.p)}}</span>
      </div>
      <div class="cbar-track" style="margin-left:18px"><div class="cbar-fill" style="width:${{w}}%;background:${{clr(t.c)}}"></div></div>
      <div class="cbar-fans" style="margin-left:18px">~${{fmtN(t.f)}} torcedores${{evo}}</div>
    </div>`;
  }}

  const top10 = (d.top||[]).slice(0,10);
  const bars  = top10.map((t,i)=>renderBar(t,i+1)).join('');

  // clube filtrado fora do top 10 → mostra abaixo com posição real
  let extraBar = '';
  if(clubFilter){{
    const idx = (d.top||[]).findIndex(t=>t.c===clubFilter);
    if(idx >= 10){{
      const t = d.top[idx];
      extraBar = `<div style="text-align:center;font-size:10px;color:#ccc;margin:6px 0 4px">&#8226; &#8226; &#8226;</div>`
               + renderBar(t, idx+1);
    }}
  }}

  const topSum = (d.top||[]).reduce((s,t)=>s+t.p, 0);
  const othPct = Math.max(0, 1 - topSum);
  const othFans= Math.round((d.pop2022||0) * othPct);
  const othRow = othPct > 0.005 ? `<div class="cbar" style="opacity:.65;border-top:1px solid #f0f0f0;padding-top:6px;margin-top:4px">
    <div class="cbar-hdr">
      <span style="font-size:11px;color:#ddd;min-width:18px"></span>
      <span class="cbar-name" style="color:#aaa;flex:1">&#9679; Outros clubes</span>
      <span class="cbar-pct">${{fmtP(othPct)}}</span>
    </div>
    <div class="cbar-fans" style="margin-left:18px">~${{fmtN(othFans)}} torcedores estimados</div>
  </div>` : '';

  document.getElementById('sb-body').innerHTML=`
    <div style="margin-bottom:4px">
      <div class="sb-title">${{d.name||'Área'}}</div>
      <div class="sb-sub">${{lvlLabel}}</div>
    </div>
    <div style="display:flex;align-items:center;gap:10px;margin:10px 0">
      ${{domCrestEl}}
      <div class="dom-badge" style="background:${{domC}};cursor:pointer;flex:1" id="badge-dom" title="Ver panorama">&#9917; ${{dom}} &nbsp; ${{fmtP(d.dom_pct)}}</div>
    </div>
    <div class="stat-grid">
      <div class="stat-box"><div class="stat-lbl">Populaç&atilde;o 2022</div><div class="stat-val">${{fmtN(d.pop2022)}}</div></div>
      <div class="stat-box"><div class="stat-lbl">Torcedores ${{(dom||'').split(' ')[0]}}</div><div class="stat-val">${{fmtN((d.top&&d.top[0])?d.top[0].f:0)}}</div></div>
    </div>
    <button id="btn-panorama" style="width:100%;padding:9px;margin:10px 0 4px;background:${{domC}};color:#fff;border:none;border-radius:7px;cursor:pointer;font-size:13px;font-weight:700;display:flex;align-items:center;justify-content:center;gap:8px">
      ${{CRESTS[dom]?'<img src="'+CRESTS[dom]+'" style="height:20px;width:20px;object-fit:contain">':''}}
      Ver panorama e projeção do ${{dom}}
    </button>
    <div class="clubs-ttl" style="margin-top:14px">Distribuição por clube</div>
    ${{bars}}${{extraBar}}${{othRow}}
    <div class="sb-note">* Estimativas: m&eacute;dia dos percentuais de curtidas no Facebook (2015&ndash;2017) aplicados sobre a população do Censo IBGE 2022. Os dados de Facebook são proxy da distribuição real de torcedores.</div>`;

  // bind após innerHTML (evita onclick inline com aspas aninhadas)
  const _dom = dom;
  const _btn = document.getElementById('btn-panorama');
  if(_btn) _btn.addEventListener('click', ()=>selectClub(_dom));
  const _badge = document.getElementById('badge-dom');
  if(_badge) _badge.addEventListener('click', ()=>selectClub(_dom));
  document.querySelectorAll('.cbar-name[data-club]').forEach(el=>{{
    el.addEventListener('click', ()=>selectClub(el.dataset.club));
  }});
}}

function closeSb(){{
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('legend').classList.remove('sb-open');
}}
document.getElementById('sb-close').addEventListener('click', closeSb);

// ── Selecionar clube: filtra mapa + panorama + zoom nacional ──────────────────
function selectClub(club){{
  // Se estiver em modo comparativo, trocar clube A sem sair da comparação
  clubFilter = club;
  document.getElementById('sel-club').value = club;
  clearSelection();
  map.setView([-14,-53], 5);
  if(compareFilter) {{
    refreshLayer();
    renderCmpPanel();
  }} else {{
    refreshLayer();
    openClubSb(club);
  }}
}}

// ── Painel de clube específico ────────────────────────────────────────────────
function openClubSb(clubName){{
  const p = PANORAMA[clubName];
  const color = clr(clubName);
  const crest = CRESTS[clubName];

  const crestEl = crest
    ? `<img class="club-crest" src="${{crest}}" alt="${{clubName}}">`
    : `<div class="club-crest-placeholder" style="background:${{color}}">${{clubName[0]}}</div>`;

  const fullName = p ? p.full_name : clubName;
  const founded  = p ? p.founded  : '';
  const state    = p ? p.state    : '';
  const media    = p ? p.media    : '';
  const finances = p ? p.finances : '';
  const rank     = p ? p.base_rank : 0;
  const basePct  = p ? p.base_pct  : 0;

  const mediaColor = {{
    'Alto':'blue','Médio':'gray','Médio-alto':'blue',
    'Baixo-médio':'gray','Baixo':'red'
  }}[media] || 'gray';
  const finColor = {{
    'Alto':'green','Médio-alto':'blue','Médio':'gray',
    'Médio (SAF 2022)':'blue','Alto (SAF City Football Group)':'green',
    'Alto (SAF John Textor)':'green','Médio (SAF 777 Partners)':'blue',
    'Baixo-médio':'gray','Baixo':'red'
  }}[finances] || 'gray';

  const titles = p && p.recent_titles && p.recent_titles.length
    ? `<div class="pan-titles"><b>Títulos Recentes</b>${{p.recent_titles.join(' &bull; ')}}</div>`
    : '';

  const panNow = p && p.panorama
    ? `<div class="pan-section now"><div class="pan-label">&#128202; Panorama Atual</div><div class="pan-text">${{p.panorama}}</div></div>`
    : '';
  const pan5   = p && p.proj_5
    ? `<div class="pan-section y5"><div class="pan-label">&#128200; Projeção 5 anos (2030)</div><div class="pan-text">${{p.proj_5}}</div></div>`
    : '';
  const pan10  = p && p.proj_10
    ? `<div class="pan-section y10"><div class="pan-label">&#128200; Projeção 10 anos (2035)</div><div class="pan-text">${{p.proj_10}}</div></div>`
    : '';
  const pan20  = p && p.proj_20
    ? `<div class="pan-section y20"><div class="pan-label">&#128200; Projeção 20 anos (2045)</div><div class="pan-text">${{p.proj_20}}</div></div>`
    : '';

  const noPan = !p ? `<div style="color:#aaa;font-size:12px;margin:12px 0">Panorama não disponível para este clube.</div>` : '';

  document.getElementById('sidebar').classList.add('open');
  document.getElementById('legend').classList.add('sb-open');
  document.getElementById('sb-body').innerHTML=`
    <div class="club-hdr">
      ${{crestEl}}
      <div>
        <div class="club-title" style="color:${{color}}">${{clubName}}</div>
        <div class="club-subtitle">${{fullName}}${{founded?' &bull; Fundado em '+founded:''}}${{state?' &bull; '+state:''}}</div>
      </div>
    </div>
    <div class="pan-meta">
      ${{rank>0?`<span class="pan-tag" style="background:${{color}}22;color:${{color}};border:1px solid ${{color}}55">#${{rank}} no Brasil</span>`:''}}
      ${{basePct>0?`<span class="pan-tag" style="background:${{color}}18;color:${{color}}bb;border:1px solid ${{color}}44">~${{basePct}}% nacional (Facebook/IBGE 2022)</span>`:''}}
      ${{media?`<span class="pan-tag" style="background:${{color}}15;color:${{color}}cc;border:1px solid ${{color}}44">Mídia: ${{media}}</span>`:''}}
      ${{finances?`<span class="pan-tag" style="background:${{color}}15;color:${{color}}cc;border:1px solid ${{color}}44">Finanças: ${{finances}}</span>`:''}}
    </div>
    ${{titles}}
    ${{panNow}}${{pan5}}${{pan10}}${{pan20}}${{noPan}}
    <div class="pan-src">Metodologia: curtidas no Facebook por município (Globo Esporte 2015/2017) aplicadas à população do Censo IBGE 2022 &bull; Panoramas: G20 Maiores Torcidas 2017 &bull; XP/Convocados 2022 &bull; "O Time do Povo Mineiro" (Leonel Jr., 2021)<br>
    <span style="color:#f0a000">&#9888;</span> Os percentuais nacionais refletem a <strong>distribuição geográfica de curtidas no Facebook</strong> ponderada pela população IBGE 2022 — proxy da presença territorial de cada torcida. Pesquisas de torcida declarada (Datafolha, PLURI) tendem a valores diferentes por medir intenção, não engajamento digital.</div>
    <button class="btn-back" id="btn-back-club">&#8592; Voltar</button>
  `;
  document.getElementById('btn-back-club').addEventListener('click', ()=>{{
    closeSb();
  }});
}}

// ── Tooltip com top 5 numerado + clube filtrado além do 5º ───────────────────
function makeTooltipRow(t, pos, highlight){{
  const hl = highlight ? 'background:#fffde7;border-radius:3px;padding:1px 3px;' : '';
  return `<div style="display:flex;align-items:center;gap:5px;margin-top:${{pos===1?4:2}}px;${{hl}}">`+
    `<span style="font-size:10px;color:#bbb;min-width:16px;font-weight:700;text-align:right">${{pos}}.</span>`+
    `<span style="width:7px;height:7px;border-radius:50%;background:${{clr(t.c)}};flex-shrink:0"></span>`+
    `<span style="font-size:11px;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:95px">${{t.c}}</span>`+
    `<span style="font-size:11px;font-weight:700;color:#333">${{fmtP(t.p)}}</span>`+
    `<span style="font-size:10px;color:#888;min-width:38px;text-align:right">~${{fmtN(t.f)}}</span>`+
    `</div>`;
}}

function makeTooltip(nm, d, sublabel){{
  if(!d) return `<strong>${{nm}}</strong>`;
  const top5 = (d.top||[]).slice(0,5);
  const rows = top5.map((t,i)=>makeTooltipRow(t, i+1, clubFilter && t.c===clubFilter)).join('');

  let extraRow = '';
  if(clubFilter){{
    const idx = (d.top||[]).findIndex(t=>t.c===clubFilter);
    if(idx >= 5){{
      const t = d.top[idx];
      extraRow = `<div style="font-size:10px;color:#bbb;margin-top:3px;text-align:center;letter-spacing:2px">• • •</div>`+
                 makeTooltipRow(t, idx+1, true);
    }}
  }}

  const sub = sublabel ? `<small style="color:#999;font-weight:400"> · ${{sublabel}}</small>` : '';
  return `<div style="min-width:190px"><strong style="font-size:12px">${{nm}}</strong>${{sub}}`+
         `<div style="font-size:10px;color:#aaa;margin-top:1px">Pop: ${{fmtN(d.pop2022)}}</div>`+
         rows+extraRow+`</div>`;
}}

// ── Seleção persistente ───────────────────────────────────────────────────────
let selectedFeature = null;
const SEL_STYLE = {{weight:3, color:'#FFD700', opacity:1}};

function clearSelection(){{
  if(selectedFeature){{
    const {{layer, feat, data}} = selectedFeature;
    layer.setStyle(featStyle(feat, data));
    selectedFeature = null;
  }}
}}

// ── Camada ────────────────────────────────────────────────────────────────────
function buildLayer(lv){{
  const cfg = LEVEL_CFG[lv] || LEVEL_CFG.uf;
  return L.geoJSON(cfg.gj, {{
    style: f => featStyle(f, cfg.data),
    onEachFeature:(feat,layer)=>{{
      const code = feat.properties.codarea;
      const d    = lookupData(cfg.data, code);
      layer.on('mouseover', function(){{
        const nm=d?d.name:(feat.properties.nome||code);
        this.bindTooltip(makeTooltip(nm, d, cfg.label),
          {{sticky:true,opacity:.97}}
        ).openTooltip();
        if(!selectedFeature || selectedFeature.layer!==this){{
          this.setStyle(Object.assign({{}}, featStyle(feat, cfg.data), {{weight:3,color:'#FFD700',opacity:1}}));
          this.bringToFront();
        }}
      }});
      layer.on('mouseout', function(){{
        this.closeTooltip();
        if(!selectedFeature || selectedFeature.layer!==this){{
          this.setStyle(featStyle(feat, cfg.data));
        }}
      }});
      layer.on('click', function(){{
        clearSelection();
        this.setStyle(Object.assign({{}}, featStyle(feat, cfg.data), SEL_STYLE));
        this.bringToFront();
        selectedFeature = {{layer:this, feat, data:cfg.data}};
        const ufTag=d&&d.uf?' &bull; '+d.uf:'';
        openSb(d, cfg.label+ufTag);
        map.fitBounds(this.getBounds(),{{padding:[60,60],maxZoom:12}});
      }});
    }}
  }});
}}

function refreshLayer(){{
  clearSelection();
  const lv = curLevel==='auto' ? zoomToLevel(map.getZoom()) : curLevel;
  if(activeLayer) map.removeLayer(activeLayer);
  activeLayer = buildLayer(lv);
  activeLayer.addTo(map);
  document.getElementById('lvl-badge').textContent = (LEVEL_CFG[lv]||LEVEL_CFG.uf).badge;
  refreshBorders();
}}

// ── Camadas de bordas hierárquicas (borda dupla: sombra + linha branca) ───────
const BORDER_STYLE = {{
  uf:    {{shadow:4.0, line:2.0}},
  meso:  {{shadow:2.0, line:0.9}},
  micro: {{shadow:1.2, line:0.5}},
}};
let borderLayers = {{uf:null, meso:null, micro:null}};

function buildBorderLayer(key){{
  const cfg   = BORDER_STYLE[key];
  const gjMap = {{uf:GJ_UF, meso:GJ_MESO, micro:GJ_MICRO}};
  const dataMap = {{uf:D_UF, meso:D_MESO, micro:D_MICRO}};
  const data  = dataMap[key];
  const label = {{uf:'Estado', meso:'Mesorregião', micro:'Microrregião'}}[key];
  const gj    = gjMap[key];

  // camada 1: sombra escura mais espessa (fica por baixo)
  const shadow = L.geoJSON(gj, {{
    style: ()=>{{return {{fillOpacity:0, color:'rgba(0,0,0,0.45)',
                         weight:cfg.shadow, interactive:false}};}},
    interactive: false,
  }});

  // camada 2: amarelo escuro (uf) → médio (meso) → claro (micro)
  const lineColor = key==='uf' ? '#B8860B' : key==='meso' ? '#DAA520' : '#FFE066';
  const line = L.geoJSON(gj, {{
    style: ()=>{{return {{fillOpacity:0, color:lineColor,
                         weight:cfg.line, interactive: key!=='uf'}};}},
    onEachFeature: key==='uf' ? undefined : (feat, layer)=>{{
      const d = lookupData(data, feat.properties.codarea);
      layer.on('mouseover', function(){{
        const nm = d ? d.name : feat.properties.codarea;
        this.bindTooltip(makeTooltip(nm, d, label),
          {{sticky:true, opacity:.97}}
        ).openTooltip();
        this.setStyle({{color:'#FFD700', weight:cfg.line+2, opacity:1}});
        this.bringToFront();
      }});
      layer.on('mouseout', function(){{
        this.closeTooltip();
        this.setStyle({{color:lineColor, weight:cfg.line}});
      }});
      layer.on('click', function(){{
        clearSelection();
        openSb(d, label+(d&&d.uf?' &bull; '+d.uf:''));
      }});
    }},
  }});

  return {{shadow, line}};
}}

function refreshBorders(){{
  ['uf','meso','micro'].forEach(key=>{{
    if(borderLayers[key]){{
      map.removeLayer(borderLayers[key].shadow);
      map.removeLayer(borderLayers[key].line);
      borderLayers[key]=null;
    }}
    const cb = document.getElementById('brd-'+key);
    if(cb && cb.checked){{
      const layers = buildBorderLayer(key);
      layers.shadow.addTo(map);
      layers.line.addTo(map);
      borderLayers[key] = layers;
    }}
  }});
}}

['uf','meso','micro'].forEach(key=>{{
  document.getElementById('brd-'+key).addEventListener('change', refreshBorders);
}});

// ── Busca ─────────────────────────────────────────────────────────────────────
(function(){{
  const inp  = document.getElementById('search-inp');
  const list = document.getElementById('search-list');

  // Índice de municípios: {{id7, name, uf}}
  const MUN_IDX = Object.values(D_MUN).map(m=>({{'id':String(m.id7||m.id),'name':m.name,'uf':m.uf||'','dom':m.dom||''}}));

  function normalize(s){{return s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();}}

  function search(q){{
    if(!q || q.length < 2){{ list.innerHTML=''; list.classList.remove('open'); return; }}
    const nq = normalize(q);
    const results = [];

    // Clubes (exato ou parcial)
    ALL_CLUBS.forEach(c=>{{
      if(normalize(c).includes(nq)) results.push({{type:'club', name:c}});
    }});

    // Municípios
    const munHits = MUN_IDX.filter(m=>normalize(m.name).includes(nq)).slice(0,12);
    munHits.forEach(m=>results.push({{type:'mun', name:m.name, uf:m.uf, id:m.id, dom:m.dom}}));

    if(!results.length){{
      list.innerHTML='<div class="sr-item"><span class="sr-name" style="color:#aaa">Nenhum resultado</span></div>';
      list.classList.add('open');
      return;
    }}

    list.innerHTML = results.map(r=>{{
      if(r.type==='club'){{
        const dot = COLORS[r.name] ? `<span style="width:9px;height:9px;border-radius:50%;background:${{COLORS[r.name]}};display:inline-block"></span>` : '';
        return `<div class="sr-item" data-type="club" data-name="${{r.name}}">
          <span class="sr-tag club">Clube</span>${{dot}}
          <span class="sr-name">${{r.name}}</span>
        </div>`;
      }} else {{
        return `<div class="sr-item" data-type="mun" data-id="${{r.id}}" data-name="${{r.name}}">
          <span class="sr-tag mun">Cidade</span>
          <div><div class="sr-name">${{r.name}}</div><div class="sr-sub">${{r.uf}}${{r.dom?' · '+r.dom:''}}</div></div>
        </div>`;
      }}
    }}).join('');
    list.classList.add('open');

    list.querySelectorAll('.sr-item[data-type]').forEach(el=>{{
      el.addEventListener('click', ()=>{{
        const type = el.dataset.type;
        if(type==='club'){{
          const club = el.dataset.name;
          inp.value = club;
          list.classList.remove('open');
          selectClub(club);
        }} else {{
          const id = el.dataset.id;
          const nm = el.dataset.name;
          inp.value = nm;
          list.classList.remove('open');
          const mData = D_MUN[id] || D_MUN[id.replace(/^0+/,'').padStart(id.length,'0')];
          if(mData){{
            const feat = GJ_MUN.features.find(f=>String(f.properties.codarea)===id);
            if(feat){{
              const bounds = L.geoJSON(feat).getBounds();
              const needsRefresh = curLevel !== 'mun';
              if(needsRefresh) curLevel = 'mun';

              function applyMunSel(){{
                clearSelection();
                let found = false;
                activeLayer.eachLayer(lyr=>{{
                  const code = lyr.feature && String(lyr.feature.properties.codarea);
                  if(code===id){{
                    // preserva fill, sobrepõe só a borda amarela
                    const base = featStyle(lyr.feature, D_MUN);
                    lyr.setStyle(Object.assign({{}}, base, SEL_STYLE));
                    lyr.bringToFront();
                    selectedFeature = {{layer:lyr, feat:lyr.feature, data:D_MUN}};
                    found = true;
                  }}
                }});
                if(found) openSb(mData, 'Município · '+mData.uf);
              }}

              if(needsRefresh){{
                // Troca de nível: rebuilda layer depois do zoom
                map.fitBounds(bounds, {{padding:[80,80], maxZoom:12}});
                map.once('moveend', ()=>{{
                  refreshLayer();
                  setTimeout(applyMunSel, 200);
                }});
              }} else {{
                // Já no nível municipal: apenas zoom, sem rebuildar
                map.fitBounds(bounds, {{padding:[80,80], maxZoom:12}});
                // moveend pode não disparar se o mapa já estiver na posição;
                // usamos timeout como mecanismo principal + moveend como fallback rápido
                let applied = false;
                function doApply(){{ if(!applied){{ applied=true; applyMunSel(); }} }}
                map.once('moveend', ()=>setTimeout(doApply, 80));
                setTimeout(doApply, 600);
              }}
            }}
          }}
        }}
      }});
    }});
  }}

  inp.addEventListener('input', ()=>search(inp.value.trim()));
  inp.addEventListener('focus',  ()=>{{if(inp.value.trim().length>=2) list.classList.add('open');}});
  document.addEventListener('click', e=>{{if(!e.target.closest('#search-wrap')) list.classList.remove('open');}});
  inp.addEventListener('keydown', e=>{{
    if(e.key==='Escape'){{ inp.value=''; list.classList.remove('open'); }}
  }});
}})();

// ── Comparativo ──────────────────────────────────────────────────────────────
function renderCmpPanel(){{
  const cA = clubFilter, cB = compareFilter;
  if(!cA || !cB){{ document.getElementById('cmp-panel').classList.remove('open'); return; }}

  const colorA = clr(cA), colorB = clr(cB);
  const panoA = PANORAMA[cA], panoB = PANORAMA[cB];

  // ── Calcular estatísticas por município
  const statsA = {{first:0,second:0,third:0,fourth:0,fans:0,topMuns:[],stateWins:new Set(),presence:new Set()}};
  const statsB = {{first:0,second:0,third:0,fourth:0,fans:0,topMuns:[],stateWins:new Set(),presence:new Set()}};
  const regionA = {{'Norte':0,'Nordeste':0,'Centro-Oeste':0,'Sudeste':0,'Sul':0}};
  const regionB = {{'Norte':0,'Nordeste':0,'Centro-Oeste':0,'Sudeste':0,'Sul':0}};
  const regionNames = ['Norte','Nordeste','Centro-Oeste','Sudeste','Sul'];
  let h2hA=0, h2hB=0, h2hTie=0;

  const REG_UF = {{'RO':'Norte','AC':'Norte','AM':'Norte','RR':'Norte','PA':'Norte','AP':'Norte','TO':'Norte',
    'MA':'Nordeste','PI':'Nordeste','CE':'Nordeste','RN':'Nordeste','PB':'Nordeste','PE':'Nordeste',
    'AL':'Nordeste','SE':'Nordeste','BA':'Nordeste','MS':'Centro-Oeste','MT':'Centro-Oeste',
    'GO':'Centro-Oeste','DF':'Centro-Oeste','MG':'Sudeste','ES':'Sudeste','RJ':'Sudeste','SP':'Sudeste',
    'PR':'Sul','SC':'Sul','RS':'Sul'}};

  Object.values(D_MUN).forEach(d=>{{
    if(!d.top) return;
    const tA=d.top.find(x=>x.c===cA), tB=d.top.find(x=>x.c===cB);
    const pA=tA?tA.p:0, pB=tB?tB.p:0;
    statsA.fans+=(tA?tA.f:0); statsB.fans+=(tB?tB.f:0);
    if(pA>0) statsA.presence.add(d.uf||'');
    if(pB>0) statsB.presence.add(d.uf||'');
    const rankA=(d.top.findIndex(x=>x.c===cA)+1)||999;
    const rankB=(d.top.findIndex(x=>x.c===cB)+1)||999;
    if(rankA===1)statsA.first++; else if(rankA===2)statsA.second++; else if(rankA===3)statsA.third++; else if(rankA===4)statsA.fourth++;
    if(rankB===1)statsB.first++; else if(rankB===2)statsB.second++; else if(rankB===3)statsB.third++; else if(rankB===4)statsB.fourth++;
    if(pA>pB) h2hA++; else if(pB>pA) h2hB++; else h2hTie++;
    const reg = d.uf ? REG_UF[d.uf] : null;
    if(reg){{ if(pA>pB) regionA[reg]=(regionA[reg]||0)+1; else if(pB>pA) regionB[reg]=(regionB[reg]||0)+1; }}
    statsA.topMuns.push({{n:d.name+(d.uf?' ('+d.uf+')':''),p:pA}});
    statsB.topMuns.push({{n:d.name+(d.uf?' ('+d.uf+')':''),p:pB}});
  }});
  statsA.topMuns.sort((a,b)=>b.p-a.p);
  statsB.topMuns.sort((a,b)=>b.p-a.p);

  Object.values(D_UF).forEach(d=>{{
    if(!d.top||!d.name) return;
    const pA=(d.top.find(x=>x.c===cA)||{{}}).p||0;
    const pB=(d.top.find(x=>x.c===cB)||{{}}).p||0;
    if(pA>pB) statsA.stateWins.add(d.name);
    else if(pB>pA) statsB.stateWins.add(d.name);
  }});

  const total = h2hA+h2hB+h2hTie||1;
  const pctH2hA = (h2hA/total*100).toFixed(0);
  const pctH2hB = (h2hB/total*100).toFixed(0);

  const crestEl = (club,color)=>CRESTS[club]
    ? `<img src="${{CRESTS[club]}}" style="width:44px;height:44px;object-fit:contain;flex-shrink:0">`
    : `<div style="width:44px;height:44px;border-radius:50%;background:${{color}};display:flex;align-items:center;justify-content:center;color:#fff;font-size:18px;font-weight:900;flex-shrink:0">${{club[0]}}</div>`;

  // Linha de métrica: valor A | label centralizado | valor B
  function row(lbl, vA, vB, subA='', subB=''){{
    const nA=parseFloat(String(vA).replace(/[^0-9.,-]/g,'').replace(',','.'));
    const nB=parseFloat(String(vB).replace(/[^0-9.,-]/g,'').replace(',','.'));
    const winA=!isNaN(nA)&&!isNaN(nB)&&nA>nB, winB=!isNaN(nA)&&!isNaN(nB)&&nB>nA;
    return `<tr>
      <td style="text-align:right;padding:5px 8px 5px 4px">
        <div style="font-size:15px;font-weight:800;color:${{winA?colorA:'#444'}}">${{vA}}</div>
        ${{subA?`<div style="font-size:9px;color:#bbb">${{subA}}</div>`:''}}
      </td>
      <td style="text-align:center;padding:5px 4px;white-space:nowrap;min-width:110px">
        <div style="font-size:9px;color:#aaa;text-transform:uppercase;letter-spacing:.6px;font-weight:700">${{lbl}}</div>
      </td>
      <td style="text-align:left;padding:5px 4px 5px 8px">
        <div style="font-size:15px;font-weight:800;color:${{winB?colorB:'#444'}}">${{vB}}</div>
        ${{subB?`<div style="font-size:9px;color:#bbb">${{subB}}</div>`:''}}
      </td>
    </tr>`;
  }}

  // Barra horizontal duelo direto
  function duelBar(){{
    return `<div style="margin:10px 0 6px">
      <div style="font-size:9px;color:#aaa;text-transform:uppercase;letter-spacing:.6px;font-weight:700;text-align:center;margin-bottom:5px">Duelo direto por município</div>
      <div style="display:flex;height:18px;border-radius:9px;overflow:hidden;gap:1px">
        <div style="flex:${{h2hA}};background:${{colorA}};display:flex;align-items:center;justify-content:flex-end;padding-right:5px">
          <span style="font-size:10px;font-weight:800;color:#fff;opacity:.9">${{pctH2hA}}%</span>
        </div>
        ${{h2hTie>0?`<div style="flex:${{h2hTie}};background:#ddd"></div>`:''}}
        <div style="flex:${{h2hB}};background:${{colorB}};display:flex;align-items:center;padding-left:5px">
          <span style="font-size:10px;font-weight:800;color:#fff;opacity:.9">${{pctH2hB}}%</span>
        </div>
      </div>
      <div style="display:flex;justify-content:space-between;margin-top:3px;font-size:10px;color:#999">
        <span>${{h2hA.toLocaleString('pt-BR')}} cidades</span>
        ${{h2hTie>0?`<span style="color:#ccc">${{h2hTie}} iguais</span>`:''}}
        <span>${{h2hB.toLocaleString('pt-BR')}} cidades</span>
      </div>
    </div>`;
  }}

  // Barras por região
  function regionBars(){{
    const rows = regionNames.map(r=>{{
      const a=regionA[r]||0, b=regionB[r]||0, tot=a+b||1;
      if(a===0&&b===0) return '';
      const pa=(a/tot*100).toFixed(0), pb=(b/tot*100).toFixed(0);
      return `<div style="margin-bottom:6px">
        <div style="display:flex;justify-content:space-between;font-size:9px;color:#999;margin-bottom:2px">
          <span style="font-weight:700;color:${{a>=b?colorA:'#aaa'}}">${{a}}</span>
          <span style="text-transform:uppercase;letter-spacing:.5px">${{r}}</span>
          <span style="font-weight:700;color:${{b>=a?colorB:'#aaa'}}">${{b}}</span>
        </div>
        <div style="display:flex;height:8px;border-radius:4px;overflow:hidden;gap:1px">
          <div style="flex:${{a}};background:${{colorA}};opacity:.8"></div>
          <div style="flex:${{b}};background:${{colorB}};opacity:.8"></div>
        </div>
      </div>`;
    }}).filter(Boolean).join('');
    return `<div style="margin-top:10px">
      <div style="font-size:9px;color:#aaa;text-transform:uppercase;letter-spacing:.6px;font-weight:700;text-align:center;margin-bottom:7px">Cidades líderes por região</div>
      ${{rows}}
    </div>`;
  }}

  // Top 3 cidades de cada
  function topCities(arr, color){{
    return arr.slice(0,3).map((x,i)=>
      `<div style="font-size:10px;margin-bottom:3px">
        <span style="color:#ccc;font-weight:700;min-width:14px;display:inline-block">${{i+1}}.</span>
        <span style="color:#555">${{x.n}}</span>
        <span style="color:${{color}};font-weight:700;float:right">${{fmtP(x.p)}}</span>
       </div>`
    ).join('');
  }}

  const pctA = panoA ? fmtP(panoA.base_pct/100) : '—';
  const pctB = panoB ? fmtP(panoB.base_pct/100) : '—';
  const rkA  = panoA ? '#'+panoA.base_rank : '—';
  const rkB  = panoB ? '#'+panoB.base_rank : '—';

  document.getElementById('cmp-body').innerHTML = `
    <!-- Cabeçalho dos dois clubes -->
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
      <div style="display:flex;align-items:center;gap:8px;flex:1">
        ${{crestEl(cA,colorA)}}
        <div>
          <div style="font-size:16px;font-weight:900;color:${{colorA}};line-height:1.1">${{cA}}</div>
          <div style="font-size:10px;color:#bbb">${{rkA}} Brasil &bull; ${{pctA}} nacional</div>
        </div>
      </div>
      <div style="font-size:18px;font-weight:900;color:#ddd;flex-shrink:0;padding:0 8px">VS</div>
      <div style="display:flex;align-items:center;gap:8px;flex:1;flex-direction:row-reverse;text-align:right">
        ${{crestEl(cB,colorB)}}
        <div>
          <div style="font-size:16px;font-weight:900;color:${{colorB}};line-height:1.1">${{cB}}</div>
          <div style="font-size:10px;color:#bbb">${{rkB}} Brasil &bull; ${{pctB}} nacional</div>
        </div>
      </div>
    </div>

    <!-- Barra duelo -->
    ${{duelBar()}}

    <!-- Tabela de métricas -->
    <table style="width:100%;border-collapse:collapse;margin:8px 0">
      <tbody>
        ${{row('Torcedores estimados', fmtN(statsA.fans), fmtN(statsB.fans))}}
        ${{row('Cidades onde lidera', statsA.first.toLocaleString('pt-BR'), statsB.first.toLocaleString('pt-BR'))}}
        ${{row('Estados líderes', statsA.stateWins.size, statsB.stateWins.size, [...statsA.stateWins].slice(0,4).join(', '), [...statsB.stateWins].slice(0,4).join(', '))}}
        ${{row('2º / 3º / 4º lugar', statsA.second+' / '+statsA.third+' / '+statsA.fourth, statsB.second+' / '+statsB.third+' / '+statsB.fourth)}}
        ${{row('UFs com presença', statsA.presence.size, statsB.presence.size)}}
      </tbody>
    </table>
    <tr style="height:1px;background:#f0f0f0"></tr>

    <!-- Regiões -->
    ${{regionBars()}}

    <!-- Top cidades -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px">
      <div>
        <div style="font-size:9px;color:#aaa;text-transform:uppercase;letter-spacing:.6px;font-weight:700;margin-bottom:5px">Top cidades ${{cA}}</div>
        ${{topCities(statsA.topMuns, colorA)}}
      </div>
      <div>
        <div style="font-size:9px;color:#aaa;text-transform:uppercase;letter-spacing:.6px;font-weight:700;margin-bottom:5px">Top cidades ${{cB}}</div>
        ${{topCities(statsB.topMuns, colorB)}}
      </div>
    </div>
  `;
  document.getElementById('cmp-panel').classList.add('open');
}}

// ── Eventos ───────────────────────────────────────────────────────────────────
map.on('zoomend', ()=>{{ if(curLevel==='auto') refreshLayer(); }});
document.getElementById('sel-level').addEventListener('change', function(){{ curLevel=this.value; refreshLayer(); }});
document.getElementById('sel-club').addEventListener('change', function(){{
  if(this.value) selectClub(this.value);
  else {{ clubFilter=''; refreshLayer(); }}
}});
document.getElementById('btn-reset').addEventListener('click', ()=>{{ map.setView([-14,-53],5); closeSb(); }});

// ── Legenda ───────────────────────────────────────────────────────────────────
(function(){{
  const c=document.getElementById('leg-items');
  LEGEND.forEach(([club,fans,color,pct])=>{{
    const el=document.createElement('div');
    el.className='leg-item';
    el.innerHTML=`<div class="leg-dot" style="background:${{color}}"></div><div><div class="leg-club">${{club}}</div><div class="leg-fans">~${{fmtN(fans)}} &bull; ${{fmtP(pct||0)}}</div></div>`;
    el.addEventListener('click',()=>{{
      const sel=document.getElementById('sel-club');
      const same=sel.value===club;
      sel.value=same?'':club;
      document.querySelectorAll('.leg-item').forEach(i=>i.classList.remove('active'));
      if(!same) el.classList.add('active');
      sel.dispatchEvent(new Event('change'));
    }});
    c.appendChild(el);
  }});
}})();

// ── Club dropdowns ────────────────────────────────────────────────────────────
(function(){{
  const sel=document.getElementById('sel-club');
  const sel2=document.getElementById('sel-club2');
  ALL_CLUBS.forEach(c=>{{
    const o=document.createElement('option'); o.value=c; o.textContent=c; sel.appendChild(o);
    const o2=document.createElement('option'); o2.value=c; o2.textContent=c; sel2.appendChild(o2);
  }});
}})();

// ── Botão comparar ────────────────────────────────────────────────────────────
document.getElementById('btn-compare').addEventListener('click', function(){{
  const wrap = document.getElementById('cmp-wrap');
  const active = wrap.classList.toggle('open');
  this.classList.toggle('active', active);
  if(!active){{
    // fechar modo comparativo
    compareFilter = '';
    document.getElementById('sel-club2').value = '';
    document.getElementById('cmp-panel').classList.remove('open');
    refreshLayer();
  }}
}});

document.getElementById('sel-club2').addEventListener('change', function(){{
  compareFilter = this.value;
  if(compareFilter && !clubFilter){{
    // se não há clube A selecionado, usa o primeiro da legenda
    const firstClub = LEGEND[0] && LEGEND[0][0];
    if(firstClub){{
      clubFilter = firstClub;
      document.getElementById('sel-club').value = firstClub;
    }}
  }}
  if(compareFilter && clubFilter){{
    // zoom nacional + nível municipal para mostrar todo o território disputado
    clearSelection();
    curLevel = 'mun';
    document.getElementById('sel-level').value = 'mun';
    map.setView([-14,-53], 5);
    refreshLayer();
    renderCmpPanel();
  }} else {{
    refreshLayer();
    document.getElementById('cmp-panel').classList.remove('open');
  }}
}});

document.getElementById('btn-cmp-close').addEventListener('click', ()=>{{
  document.getElementById('cmp-panel').classList.remove('open');
  compareFilter = '';
  document.getElementById('sel-club2').value = '';
  document.getElementById('cmp-wrap').classList.remove('open');
  document.getElementById('btn-compare').classList.remove('active');
  refreshLayer();
}});

// ── Init ──────────────────────────────────────────────────────────────────────
refreshLayer();
</script>
</body>
</html>"""


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print('=' * 60)
    print('  Mapa de Torcidas do Brasil — Gerador')
    print('=' * 60)

    df_geo         = read_drb_geo()
    data15, data17 = read_curtidas()
    mun_data       = build_municipality_data(df_geo, data15, data17)

    agg_meso  = aggregate_by_level(mun_data, 'meso')
    agg_micro = aggregate_by_level(mun_data, 'micro')
    agg_uf    = aggregate_by_level(mun_data, 'uf')

    print('\nBaixando GeoJSON do IBGE...')
    gj_uf    = get_geojson('uf')
    gj_meso  = get_geojson('meso')
    gj_micro = get_geojson('micro')
    gj_mun   = get_geojson('mun')

    print('\nBaixando Leaflet.js...')
    ljs, lcss = download_leaflet()

    print('\nGerando HTML...')
    html = generate_html(mun_data, agg_meso, agg_micro, agg_uf,
                         gj_mun, gj_meso, gj_micro, gj_uf, ljs, lcss)

    OUTPUT.write_text(html, encoding='utf-8')
    size_mb = OUTPUT.stat().st_size / 1e6
    print(f'\nArquivo gerado: {OUTPUT}')
    print(f'Tamanho: {size_mb:.1f} MB')
    print('\nPronto! Abra mapa_torcidas_brasil.html no navegador.')


if __name__ == '__main__':
    main()
