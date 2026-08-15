# ai_engine.py
import json
import math
from typing import Dict, List, Optional, Any
import numpy as np

def calcular_forma(partidas: List[Dict], num_jogos: int = 5) -> float:
    if not partidas:
        return 1.5
    ultimas = partidas[-num_jogos:] if len(partidas) >= num_jogos else partidas
    pontos = 0
    for jogo in ultimas:
        gm = jogo.get('golos_marcados', 0)
        gs = jogo.get('golos_sofridos', 0)
        if gm > gs:
            pontos += 3
        elif gm == gs:
            pontos += 1
    return pontos / len(ultimas)

def media_golos(marcados: List[int], sofridos: List[int]) -> tuple:
    media_marc = sum(marcados) / len(marcados) if marcados else 1.2
    media_sofr = sum(sofridos) / len(sofridos) if sofridos else 1.2
    return media_marc, media_sofr

def calcular_expectativa_golos(media_marcados_casa, media_sofridos_fora,
                               media_marcados_fora, media_sofridos_casa):
    xg_casa = (media_marcados_casa + media_sofridos_fora) / 2
    xg_fora = (media_marcados_fora + media_sofridos_casa) / 2
    return xg_casa, xg_fora

def prob_poisson(golos_esperados, max_golos=6):
    return [np.exp(-golos_esperados) * (golos_esperados ** k) / math.factorial(k)
            for k in range(max_golos + 1)]

def avaliar_resultado_final(xg_casa, xg_fora):
    prob_casa = prob_empate = prob_fora = 0
    for i in range(7):
        for j in range(7):
            p = prob_poisson(xg_casa)[i] * prob_poisson(xg_fora)[j]
            if i > j:
                prob_casa += p
            elif i == j:
                prob_empate += p
            else:
                prob_fora += p
    return {'casa': round(prob_casa, 3), 'empate': round(prob_empate, 3), 'fora': round(prob_fora, 3)}

def avaliar_over_under(xg_casa, xg_fora, linha=2.5):
    prob_over = 0
    for i in range(7):
        for j in range(7):
            if i + j > linha:
                prob_over += prob_poisson(xg_casa)[i] * prob_poisson(xg_fora)[j]
    return round(prob_over, 3)

def avaliar_btts(xg_casa, xg_fora):
    prob_casa_marca = 1 - prob_poisson(xg_casa)[0]
    prob_fora_marca = 1 - prob_poisson(xg_fora)[0]
    return round(prob_casa_marca * prob_fora_marca, 3)

def avaliar_cantos(media_cantos_casa, media_cantos_fora, linha=8.5):
    total_esperado = media_cantos_casa + media_cantos_fora
    desvio_padrao = 3.0
    if total_esperado <= 0:
        return 0.0
    z = (linha - total_esperado) / desvio_padrao
    return round(1 - 0.5 * (1 + math.erf(z / np.sqrt(2))), 3)

def avaliar_cartoes(media_cartoes_casa, media_cartoes_fora, linha=3.5):
    total_esperado = media_cartoes_casa + media_cartoes_fora
    desvio_padrao = 1.8
    if total_esperado <= 0:
        return 0.0
    z = (linha - total_esperado) / desvio_padrao
    return round(1 - 0.5 * (1 + math.erf(z / np.sqrt(2))), 3)

def analisar_jogo(dados_jogo: Dict) -> Dict:
    event_id = dados_jogo.get('event_id')
    home = dados_jogo.get('home_team', '?')
    away = dados_jogo.get('away_team', '?')

    forma_casa = calcular_forma(dados_jogo.get('forma_casa', []))
    forma_fora = calcular_forma(dados_jogo.get('forma_fora', []))

    media_golos_casa, media_sofridos_casa = media_golos(
        dados_jogo.get('golos_casa', []), dados_jogo.get('golos_sofridos_casa', []))
    media_golos_fora, media_sofridos_fora = media_golos(
        dados_jogo.get('golos_fora', []), dados_jogo.get('golos_sofridos_fora', []))

    # Tratamento seguro das posições
    pos_casa = dados_jogo.get('posicao_casa')
    pos_fora = dados_jogo.get('posicao_fora')
    try:
        pos_casa = int(pos_casa) if pos_casa is not None else 10
    except (ValueError, TypeError):
        pos_casa = 10
    try:
        pos_fora = int(pos_fora) if pos_fora is not None else 10
    except (ValueError, TypeError):
        pos_fora = 10

    ajuste_posicao = (pos_fora - pos_casa) * 0.05
    xg_casa, xg_fora = calcular_expectativa_golos(
        media_golos_casa + max(0, ajuste_posicao),
        media_sofridos_fora,
        media_golos_fora + max(0, -ajuste_posicao),
        media_sofridos_casa
    )

    xg_casa *= (0.9 + forma_casa * 0.2)
    xg_fora *= (0.9 + forma_fora * 0.2)
    xg_casa = max(0.3, min(4.5, xg_casa))
    xg_fora = max(0.3, min(4.5, xg_fora))

    probs_resultado = avaliar_resultado_final(xg_casa, xg_fora)
    prob_over_15 = avaliar_over_under(xg_casa, xg_fora, 1.5)
    prob_over_25 = avaliar_over_under(xg_casa, xg_fora, 2.5)
    prob_btts = avaliar_btts(xg_casa, xg_fora)

    media_cantos_casa = dados_jogo.get('media_cantos_casa', 4.5)
    media_cantos_fora = dados_jogo.get('media_cantos_fora', 4.0)
    prob_over_7_cantos = avaliar_cantos(media_cantos_casa, media_cantos_fora, 7.0)
    prob_over_85_cantos = avaliar_cantos(media_cantos_casa, media_cantos_fora, 8.5)

    media_cartoes_casa = dados_jogo.get('media_cartoes_casa', 2.0)
    media_cartoes_fora = dados_jogo.get('media_cartoes_fora', 2.0)
    prob_over_2_cartoes = avaliar_cartoes(media_cartoes_casa, media_cartoes_fora, 2.0)
    prob_over_3_cartoes = avaliar_cartoes(media_cartoes_casa, media_cartoes_fora, 3.0)

    odds = dados_jogo.get('odds', {})
    previsoes = []

    def adicionar_previsao(mercado, selecao, probabilidade, odd=None):
        if odd and odd > 1.0:
            valor = (probabilidade * odd - 1) * 100
            pontuacao = min(95, max(20, probabilidade * 80 + valor * 20))
        else:
            pontuacao = probabilidade * 80
        previsoes.append({
            'mercado': mercado,
            'selecao': selecao,
            'probabilidade': round(probabilidade, 3),
            'odd': odd,
            'pontuacao': round(pontuacao, 1)
        })

    melhor_resultado = max(probs_resultado, key=probs_resultado.get)
    odd_resultado = None
    if '1x2' in odds:
        odd_resultado = odds['1x2'].get(melhor_resultado)
    adicionar_previsao('Resultado Final', melhor_resultado.capitalize(), probs_resultado[melhor_resultado], odd_resultado)

    prob_casa_empate = probs_resultado['casa'] + probs_resultado['empate']
    prob_fora_empate = probs_resultado['fora'] + probs_resultado['empate']
    if prob_casa_empate >= prob_fora_empate:
        adicionar_previsao('Dupla Hipótese', 'Casa ou Empate', prob_casa_empate)
    else:
        adicionar_previsao('Dupla Hipótese', 'Fora ou Empate', prob_fora_empate)

    adicionar_previsao('Over 1.5', 'Sim', prob_over_15, odds.get('over_1_5'))
    adicionar_previsao('Over 2.5', 'Sim', prob_over_25, odds.get('over_2_5'))
    adicionar_previsao('BTTS', 'Sim', prob_btts, odds.get('btts'))
    adicionar_previsao('Over 7 Cantos', 'Sim', prob_over_7_cantos, odds.get('over_7_cantos'))
    adicionar_previsao('Over 8.5 Cantos', 'Sim', prob_over_85_cantos, odds.get('over_8_5_cantos'))
    adicionar_previsao('Over 2 Cartões', 'Sim', prob_over_2_cartoes, odds.get('over_2_cartoes'))
    adicionar_previsao('Over 3 Cartões', 'Sim', prob_over_3_cartoes, odds.get('over_3_cartoes'))

    previsoes.sort(key=lambda x: x['pontuacao'], reverse=True)
    confianca = int(np.mean([p['pontuacao'] for p in previsoes[:3]]))

    return {
        'event_id': event_id,
        'home_team': home,
        'away_team': away,
        'xg_casa': round(xg_casa, 2),
        'xg_fora': round(xg_fora, 2),
        'previsoes': previsoes,
        'confianca_geral': confianca
    }
