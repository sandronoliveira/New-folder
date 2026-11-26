"""
Alarme da Caixa Misteriosa - Webcontinental

Fica olhando a página da caixa misteriosa de tempos em tempos e
toca um alarme (e opcionalmente manda notificação pro celular)
quando parecer que a caixa foi liberada.

Como usar:
    python alarme_caixa_misteriosa.py

Notificação no celular (opcional, grátis):
    1. Instale o app "ntfy" no celular (Android/iPhone).
    2. No app, assine um tópico com um nome difícil de adivinhar,
       por exemplo: caixa-sandron-8x7k2
    3. Coloque esse mesmo nome em NTFY_TOPICO abaixo.

Só usa a biblioteca padrão do Python (não precisa instalar nada).
"""

import hashlib
import html
import re
import sys
import time
import urllib.request
from datetime import datetime

# ------------------------- CONFIGURAÇÃO -------------------------
URL = "https://www.webcontinental.com.br/caixa-misteriosa"
INTERVALO_SEGUNDOS = 60          # de quanto em quanto tempo checar
NTFY_TOPICO = ""                 # ex: "caixa-sandron-8x7k2" (vazio = sem celular)

# Palavras que indicam que a caixa AINDA NÃO está à venda
SINAIS_INDISPONIVEL = [
    "esgotad", "indisponível", "indisponivel", "em breve", "aguarde",
    "avise-me", "avise me", "volte em breve", "não disponível",
]
# Palavras que indicam que a caixa ESTÁ à venda
SINAIS_DISPONIVEL = [
    "comprar", "adicionar ao carrinho", "adicionar à sacola",
    "compre agora", "garanta a sua", "garanta já",
]
# ----------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}


def agora():
    return datetime.now().strftime("%H:%M:%S")


def baixar_pagina():
    req = urllib.request.Request(URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def texto_visivel(pagina_html):
    """Tira scripts, estilos e tags, deixando só o texto da página."""
    s = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", pagina_html)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip().lower()


def contar(texto, palavras):
    return {p: texto.count(p) for p in palavras if p in texto}


def tocar_alarme(segundos=15):
    print("\a", end="", flush=True)
    try:
        import winsound  # só existe no Windows
        fim = time.time() + segundos
        while time.time() < fim:
            winsound.Beep(1500, 400)
            winsound.Beep(1000, 400)
    except ImportError:
        for _ in range(segundos):
            print("\a", end="", flush=True)  # bipe do terminal
            time.sleep(1)


def avisar_celular(mensagem):
    if not NTFY_TOPICO:
        return
    try:
        req = urllib.request.Request(
            f"https://ntfy.sh/{NTFY_TOPICO}",
            data=mensagem.encode("utf-8"),
            headers={
                "Title": "Caixa Misteriosa liberada?",
                "Priority": "urgent",
                "Tags": "rotating_light,gift",
                "Click": URL,
            },
        )
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        print(f"[{agora()}] Não consegui mandar pro celular: {e}")


def disparar(motivo):
    msg = f"{motivo}\nCorre: {URL}"
    print("\n" + "!" * 60)
    print(f"[{agora()}] ALARME! {motivo}")
    print(f"Abra agora: {URL}")
    print("!" * 60 + "\n")
    avisar_celular(msg)
    tocar_alarme()


def main():
    print(f"Monitorando {URL} a cada {INTERVALO_SEGUNDOS}s. Ctrl+C para parar.")
    if NTFY_TOPICO:
        avisar_celular("Teste: o alarme da caixa misteriosa está ligado.")

    hash_inicial = None
    indisp_inicial = None
    disp_inicial = None
    ja_alarmou = False

    while True:
        try:
            texto = texto_visivel(baixar_pagina())
            h = hashlib.md5(texto.encode()).hexdigest()
            indisp = contar(texto, SINAIS_INDISPONIVEL)
            disp = contar(texto, SINAIS_DISPONIVEL)

            if hash_inicial is None:
                hash_inicial, indisp_inicial, disp_inicial = h, indisp, disp
                print(f"[{agora()}] Situação inicial registrada.")
                print(f"   sinais de indisponível: {indisp or 'nenhum'}")
                print(f"   sinais de disponível:   {disp or 'nenhum'}")
            else:
                motivo = None
                if indisp_inicial and not indisp:
                    motivo = "Sumiu o aviso de esgotado/em breve da página!"
                elif any(disp.get(p, 0) > disp_inicial.get(p, 0) for p in disp):
                    motivo = "Apareceu botão/texto de compra novo na página!"
                elif h != hash_inicial:
                    print(f"[{agora()}] A página mudou um pouco (sem sinal claro de venda).")
                    hash_inicial = h
                else:
                    print(f"[{agora()}] Nada mudou ainda.")

                if motivo and not ja_alarmou:
                    disparar(motivo)
                    ja_alarmou = True
                elif not motivo:
                    ja_alarmou = False

        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"[{agora()}] Erro ao acessar o site ({e}). Tentando de novo...")

        time.sleep(INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    if "--testar-alarme" in sys.argv:
        disparar("Teste do alarme")
    else:
        try:
            main()
        except KeyboardInterrupt:
            print("\nAlarme desligado.")
