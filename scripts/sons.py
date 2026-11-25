"""Sons de efeito da Edite Rapida, criados por calculo (nenhum arquivo de terceiros).

faixa(eventos, duracao, arquivo, volume): grava um .wav com cada som no seu segundo.
eventos = [(segundo, "nome"), ...]
Nomes: whoosh, whoosh_curto, pop, bolha, impacto, ding, sino, tic, risco, foto, glitch, subida.
"""
import math
import wave

SR = 48000


def _np():
    try:
        import numpy as np
    except ImportError:
        import subprocess
        import sys
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--disable-pip-version-check",
                        "--break-system-packages", "numpy"], check=True)
        import numpy as np
    return np


def _env(np, n, ataque, queda):
    t = np.arange(n) / SR
    sobe = np.clip(t / max(ataque, 1e-4), 0, 1)
    return sobe * np.exp(-t / max(queda, 1e-4))


def _suaviza(np, x, k):
    if k <= 1:
        return x
    return np.convolve(x, np.ones(k) / k, mode="same")


def gerar(nome):
    np = _np()
    rng = np.random.default_rng(len(nome) * 7919)
    if nome in ("whoosh", "whoosh_curto"):
        d = 0.55 if nome == "whoosh" else 0.3
        n = int(d * SR)
        t = np.arange(n) / n
        ruido = rng.standard_normal(n)
        # passa por um "filtro" que abre e fecha (ar passando)
        grave = _suaviza(np, ruido, 24)
        agudo = ruido - _suaviza(np, ruido, 6)
        x = grave * (1 - t) + agudo * t * 0.6
        env = np.sin(np.pi * np.clip(t, 0, 1)) ** 2
        return x * env
    if nome in ("pop", "bolha"):
        d = 0.14 if nome == "pop" else 0.18
        n = int(d * SR)
        t = np.arange(n) / SR
        f0, f1 = (950, 320) if nome == "pop" else (520, 1150)
        f = f1 + (f0 - f1) * np.exp(-t * 38)
        fase = 2 * np.pi * np.cumsum(f) / SR
        return np.sin(fase) * _env(np, n, 0.002, 0.035)
    if nome == "impacto":
        n = int(0.9 * SR)
        t = np.arange(n) / SR
        f = 42 + 130 * np.exp(-t * 16)
        corpo = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5.2)
        estalo = rng.standard_normal(n) * np.exp(-t * 70) * 0.35
        return np.tanh((corpo + estalo) * 1.6)
    if nome in ("ding", "sino"):
        d = 1.1 if nome == "ding" else 1.5
        n = int(d * SR)
        t = np.arange(n) / SR
        base = 1320 if nome == "ding" else 1046
        x = (np.sin(2 * np.pi * base * t) + 0.42 * np.sin(2 * np.pi * base * 2.01 * t)
             + 0.18 * np.sin(2 * np.pi * base * 3.02 * t))
        return x * _env(np, n, 0.003, 0.32 if nome == "ding" else 0.5)
    if nome == "tic":
        n = int(0.04 * SR)
        t = np.arange(n) / SR
        return np.sin(2 * np.pi * 2300 * t) * np.exp(-t * 130)
    if nome == "risco":
        n = int(0.28 * SR)
        t = np.arange(n) / n
        ruido = rng.standard_normal(n)
        x = ruido - _suaviza(np, ruido, 3)
        return x * np.sin(np.pi * t) * 0.7
    if nome == "foto":
        n = int(0.18 * SR)
        t = np.arange(n) / SR
        ruido = rng.standard_normal(n)
        return ruido * (np.exp(-t * 160) + np.exp(-np.abs(t - 0.075) * 160) * (t > 0.075)) * 0.9
    if nome == "glitch":
        n = int(0.5 * SR)
        t = np.arange(n) / SR
        porta = (np.sin(2 * np.pi * 15 * t) > 0.15).astype(float)
        x = np.sign(np.sin(2 * np.pi * 95 * t)) * 0.5 + rng.standard_normal(n) * 0.5
        x = np.round(x * 6) / 6
        return x * porta * np.exp(-t * 3)
    if nome == "subida":
        n = int(0.9 * SR)
        t = np.arange(n) / SR
        f = 220 + 700 * (t / 0.9) ** 2
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * (t / 0.9) * 0.5
        return x * (1 - np.clip((t - 0.8) / 0.1, 0, 1))
    raise ValueError("som desconhecido: " + nome)


# volume de cada som (relativo), pra nenhum gritar mais que a voz
NIVEL = {"whoosh": 0.42, "whoosh_curto": 0.38, "pop": 0.45, "bolha": 0.4, "impacto": 0.6,
         "ding": 0.26, "sino": 0.26, "tic": 0.3, "risco": 0.3, "foto": 0.4, "glitch": 0.3,
         "subida": 0.28}


def faixa(eventos, duracao, arquivo, volume=1.0):
    np = _np()
    total = np.zeros(int((duracao + 2) * SR))
    cache = {}
    for seg, nome in eventos:
        if nome not in NIVEL or seg < 0 or seg > duracao:
            continue
        if nome not in cache:
            x = gerar(nome)
            pico = float(np.max(np.abs(x))) or 1.0
            cache[nome] = x / pico * NIVEL[nome]
        x = cache[nome]
        i = int(seg * SR)
        fim = min(len(total), i + len(x))
        total[i:fim] += x[: fim - i]
    total = np.clip(total * volume, -0.98, 0.98)
    dados = (total * 32767).astype("<i2").tobytes()
    with wave.open(arquivo, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(dados)
    return arquivo


if __name__ == "__main__":
    import sys
    faixa([(0.2 + i * 1.0, n) for i, n in enumerate(NIVEL)], len(NIVEL) + 1, sys.argv[1] if len(sys.argv) > 1 else "sons.wav")
    print("ok")
