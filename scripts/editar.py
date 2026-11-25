#!/usr/bin/env python3
"""Edite Rapida: edita UM video vertical de pessoa falando, rapido e simples.

Duas etapas:
  python3 editar.py preparar [video] [pasta]   -> transcreve e tira fotos do video
  python3 editar.py montar [pasta]             -> le plano.json e entrega o MP4 pronto

O que o video final recebe (o "arroz com feijao"):
  - corte das pausas (sem cortar palavra), num video so
  - titulo-gancho nos primeiros segundos
  - legenda de 1 palavra por vez, com as palavras fortes em destaque
  - zoom seco nas frases fortes
  - volume no padrao do Reels (-14 LUFS)
So precisa de Python e ffmpeg. Instala o que faltar sozinho.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
FONTES = os.path.join(os.path.dirname(AQUI), "fontes")
SAIDA_CHAT = "/mnt/user-data/outputs"
ENTRADAS = ["/mnt/user-data/uploads", "/mnt/data"]  # so a pasta de anexos do chat
EXT = (".mp4", ".mov", ".m4v", ".webm", ".mkv", ".3gp", ".avi")
W, H, FPS = 1080, 1920, 30
T0 = time.time()


def log(msg):
    print(f"[{time.time() - T0:5.0f}s] {msg}", flush=True)


def pare(codigo, msg):
    print("\n" + codigo + ": " + msg, flush=True)
    sys.exit(3)


def pip(*pacotes):
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--disable-pip-version-check", "--break-system-packages",
                    *pacotes], check=True)


def tem_legenda(ff):
    try:
        out = subprocess.run([ff, "-hide_banner", "-filters"], capture_output=True, text=True).stdout
        return " ass " in out and "loudnorm" in out
    except OSError:
        return False


def achar_ffmpeg():
    sistema = shutil.which("ffmpeg")
    if sistema and tem_legenda(sistema):
        return sistema
    try:
        import imageio_ffmpeg
    except ImportError:
        log("instalando ffmpeg...")
        pip("imageio-ffmpeg")
        import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    if tem_legenda(ff):
        return ff
    if sistema:
        return sistema
    pare("SEM_FFMPEG", "nao consegui um ffmpeg com legenda. Avise a pessoa.")


def rodar(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-3000:], flush=True)
        raise SystemExit("ffmpeg falhou (veja a mensagem acima)")
    return r


def duracao(ff, video):
    err = subprocess.run([ff, "-hide_banner", "-i", video], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    if not m:
        pare("VIDEO_ILEGIVEL", "nao consegui ler esse arquivo de video.")
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def achar_video(arg):
    if arg:
        if os.path.isfile(arg):
            return os.path.abspath(arg)
        pare("SEM_VIDEO", "nao achei o video " + arg + ". Peca pra pessoa anexar o video de novo.")
    achados = []
    for pasta in ENTRADAS:
        if os.path.isdir(pasta):
            for f in glob.glob(os.path.join(pasta, "**", "*"), recursive=True):
                if f.lower().endswith(EXT) and "-editado" not in f and "/edite-rapida/" not in f.replace("\\", "/"):
                    achados.append(f)
    if not achados:
        pare("SEM_VIDEO", "nenhum video anexado. Peca pra pessoa anexar o video no clipe e mandar de novo.")
    return max(achados, key=os.path.getmtime)


MODELO_URL = "https://github.com/o-bot7847/edite-rapida/releases/download/modelo-v1/whisper-{}.tar"


def baixar_modelo(nome):
    """O 'ouvido' da legenda. O chat do Claude bloqueia o site de origem, entao vem do GitHub."""
    pasta = os.path.join(os.path.expanduser("~"), ".edite-rapida", "whisper-" + nome)
    if os.path.exists(os.path.join(pasta, "model.bin")):
        return pasta
    import tarfile
    import urllib.request
    log("baixando o ouvido da legenda (so na primeira vez)...")
    os.makedirs(os.path.dirname(pasta), exist_ok=True)
    tmp = pasta + ".tar"
    try:
        urllib.request.urlretrieve(MODELO_URL.format(nome), tmp)
        with tarfile.open(tmp) as t:
            for membro in t.getmembers():
                if not membro.isfile() or "/" in membro.name.strip("./") or ".." in membro.name:
                    continue
                t.extract(membro, pasta)
        os.remove(tmp)
    except Exception as e:  # noqa: BLE001
        pare("MODELO_BLOQUEADO", "nao consegui baixar o ouvido da legenda (" + str(e)[:200] + ").")
    if not os.path.exists(os.path.join(pasta, "model.bin")):
        pare("MODELO_BLOQUEADO", "o arquivo do ouvido da legenda veio incompleto.")
    return pasta


ENQUADRAR = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1"


def preparar(video_arg=None, pasta=None):
    ff = achar_ffmpeg()
    video = achar_video(video_arg)
    nome = re.sub(r"[^a-zA-Z0-9]+", "-", os.path.splitext(os.path.basename(video))[0]).strip("-")[:40] or "video"
    pasta = os.path.abspath(pasta or os.path.join(os.path.expanduser("~"), "edite-rapida", nome))
    os.makedirs(pasta, exist_ok=True)
    dur = duracao(ff, video)
    log(f"video: {os.path.basename(video)} ({dur:.1f}s)")

    # fotos pra escolher a altura da legenda (com regua: 1000, 1200 e 1400)
    fonte = os.path.join(FONTES, "Inter.ttf").replace("\\", "/").replace(":", "\\:")
    regua = ",".join(
        f"drawbox=y={y}:x=0:w={W}:h=4:color=yellow@0.9:t=fill,"
        f"drawtext=fontfile='{fonte}':text='{y}':x=12:y={y - 46}:fontsize=40:fontcolor=yellow:borderw=3"
        for y in (1000, 1200, 1400))
    fotos = []
    for i, frac in enumerate((0.2, 0.5, 0.8), 1):
        f = os.path.join(pasta, f"foto-{i}.jpg")
        rodar([ff, "-v", "error", "-y", "-ss", f"{dur * frac:.2f}", "-i", video, "-frames:v", "1",
               "-vf", f"{ENQUADRAR},{regua},scale=360:-2", f])
        fotos.append(f)

    # transcricao palavra por palavra
    wav = os.path.join(pasta, "audio.wav")
    rodar([ff, "-v", "error", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000", wav])
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        log("instalando o transcritor (so na primeira vez)...")
        pip("faster-whisper")
        from faster_whisper import WhisperModel
    modelo = os.environ.get("EDITE_MODELO", "small")
    m = WhisperModel(baixar_modelo(modelo), device="cpu", compute_type="int8",
                     cpu_threads=os.cpu_count() or 2)
    log(f"transcrevendo (modelo {modelo})...")
    idioma = os.environ.get("EDITE_IDIOMA", "pt")
    segs, _ = m.transcribe(wav, language=idioma, word_timestamps=True, vad_filter=True,
                           beam_size=1, condition_on_previous_text=False)
    palavras = []
    for s in segs:
        for w in s.words or []:
            t = w.word.strip()
            if t:
                palavras.append([t, round(w.start, 2), round(w.end, 2)])
    os.remove(wav)
    if not palavras:
        pare("SEM_FALA", "nao achei fala nesse video.")

    # fala em frases com o segundo, pra escrever o plano
    linhas, atual, ini = [], [], None
    for i, (t, s, e) in enumerate(palavras):
        ini = s if ini is None else ini
        atual.append(t)
        prox = palavras[i + 1][1] if i + 1 < len(palavras) else None
        if re.search(r"[.?!]$", t) or prox is None or prox - e > 0.6 or len(atual) >= 16:
            linhas.append(f"[{ini:6.2f}] " + " ".join(atual))
            atual, ini = [], None
    with open(os.path.join(pasta, "fala.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")
    json.dump(palavras, open(os.path.join(pasta, "palavras.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump({"video": video, "duracao": round(dur, 2)}, open(os.path.join(pasta, "info.json"), "w"))
    log("pronto")
    print("\nPASTA=" + pasta)
    print("FOTOS=" + " ".join(fotos))
    print("\n--- FALA (segundo: frase) ---")
    print("\n".join(linhas))


# ---------------------------------------------------------------- montar

def limpa(p):
    return re.sub(r"[^\wà-ÿ]", "", p.lower())


def cor_ass(hexcor):
    h = hexcor.lstrip("#")
    return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def esc(t):
    return t.replace("\\", "").replace("{", "(").replace("}", ")")


def quebrar(texto, maximo):
    linhas, atual = [], ""
    for w in texto.split():
        if atual and len(atual) + 1 + len(w) > maximo:
            linhas.append(atual)
            atual = w
        else:
            atual = (atual + " " + w).strip()
    if atual:
        linhas.append(atual)
    return linhas


def tempo_ass(t):
    t = max(0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def montar(pasta=None):
    pasta = os.path.abspath(pasta or max(glob.glob(os.path.expanduser("~/edite-rapida/*/")), key=os.path.getmtime))
    ff = achar_ffmpeg()
    info = json.load(open(os.path.join(pasta, "info.json")))
    palavras = json.load(open(os.path.join(pasta, "palavras.json"), encoding="utf-8"))
    plano_f = os.path.join(pasta, "plano.json")
    plano = json.load(open(plano_f, encoding="utf-8")) if os.path.exists(plano_f) else {}
    video, dur = info["video"], info["duracao"]
    if not os.path.exists(video):
        pare("SEM_VIDEO", "o video sumiu da pasta. Peca pra anexar de novo.")

    # correcoes de transcricao
    corr = {limpa(k): v for k, v in (plano.get("correcoes") or {}).items()}
    palavras = [[corr.get(limpa(t), t), s, e] for t, s, e in palavras]

    # 1. trechos que ficam (corta so as pausas, nunca palavra)
    if plano.get("cortar_pausas", True):
        pausa = float(plano.get("pausa_max", 0.4))
        fica = []
        a, b = max(0.0, palavras[0][1] - 0.12), palavras[0][2]
        for _, s, e in palavras[1:]:
            if s - b > pausa:
                fica.append([a, b + 0.15])
                a = s - 0.10
            b = max(b, e)
        fica.append([a, min(dur, b + 0.4)])
    else:
        fica = [[0.0, dur]]
    restante = sum(y - x for x, y in fica)
    vel = float(plano.get("velocidade", 1.0))
    if plano.get("duracao_max") and restante / vel > float(plano["duracao_max"]):
        vel = restante / float(plano["duracao_max"]) + 0.003
    vel = min(max(vel, 1.0), 1.25)
    final = restante / vel

    def novo(t):
        acc = 0.0
        for x, y in fica:
            if t < x:
                return acc / vel
            if t <= y:
                return (acc + t - x) / vel
            acc += y - x
        return acc / vel

    # 2. legenda (arquivo .ass)
    cor = cor_ass(plano.get("cor", "#FFF3C6"))
    ly = int(plano.get("legenda_y", 1250))
    ly = min(max(ly, 900), 1400)
    tam = int(plano.get("legenda_tamanho", 108))
    dest = {limpa(d) for d in plano.get("destaques", [])}
    ev = []
    pop = r"\fscx82\fscy82\t(0,90,\fscx106\fscy106)\t(90,170,\fscx100\fscy100)"
    for i, (t, s, e) in enumerate(palavras):
        ini = novo(s) - 0.05
        prox = novo(palavras[i + 1][1]) - 0.05 if i + 1 < len(palavras) else novo(e) + 0.5
        fim = min(prox, novo(e) + 0.6)
        if fim - ini < 0.1:
            fim = ini + 0.1
        txt = esc(re.sub(r"^[\"'(]+|[\"'),.;:!…]+$", "", t))
        if not txt:
            continue
        if limpa(t) in dest:
            estilo = rf"{{\an5\pos(540,{ly})\fnInstrument Serif\i1\fs{int(tam * 1.3)}\c{cor}{pop}}}"
        else:
            estilo = rf"{{\an5\pos(540,{ly})\fnInter\b1\fs{tam}{pop}}}"
        ev.append(f"Dialogue: 1,{tempo_ass(ini)},{tempo_ass(fim)},Leg,,0,0,0,,{estilo}{txt}")

    tit = plano.get("titulo") or {}
    if tit.get("grande"):
        tfim = min(float(tit.get("fim", 3.5)), final)
        partes = []
        for ln in quebrar(tit.get("pequeno", ""), 28):
            partes.append(rf"{{\fnInter\b1\fs58\c&H00FFFFFF&}}{esc(ln)}")
        for ln in quebrar(tit["grande"], 13):
            partes.append(rf"{{\fnPlayfair Display\b1\fs120\c{cor}}}{esc(ln)}")
        ev.insert(0, f"Dialogue: 2,{tempo_ass(0)},{tempo_ass(tfim)},Tit,,0,0,0,,"
                     + rf"{{\an8\pos(540,330)\fad(120,250)}}" + r"\N".join(partes))

    cab = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Leg,Inter,{tam},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,5,3,5,80,80,0,1
Style: Tit,Inter,48,&H00FFFFFF,&H00FFFFFF,&H00000000,&H78000000,-1,0,0,0,100,100,0,0,1,5,4,8,80,80,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(os.path.join(pasta, "legenda.ass"), "w", encoding="utf-8") as f:
        f.write(cab + "\n".join(ev) + "\n")
    os.makedirs(os.path.join(pasta, "fontes"), exist_ok=True)
    for f in glob.glob(os.path.join(FONTES, "*.ttf")):
        shutil.copy(f, os.path.join(pasta, "fontes"))

    # 3. zoom seco nas frases fortes (no tempo novo)
    zooms = []
    for z in plano.get("zooms", []):
        t = float(z[0] if isinstance(z, list) else z)
        d = float(z[1]) if isinstance(z, list) and len(z) > 1 else 1.4
        zooms.append((novo(t) - 0.03, novo(t) - 0.03 + d / vel))
    zexpr = "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b in zooms) or "0"
    esc_z = float(plano.get("zoom_escala", 1.15))
    zw, zh = int(W * esc_z) // 2 * 2, int(H * esc_z) // 2 * 2

    sel = "+".join(f"between(t,{x:.3f},{y:.3f})" for x, y in fica)
    vel_v = f",setpts=PTS/{vel:.4f}" if vel > 1.0001 else ""
    vel_a = f",atempo={vel:.4f}" if vel > 1.0001 else ""
    with open(os.path.join(pasta, "sel.txt"), "w") as f:
        f.write(sel)
    filtro = (
        f"[0:v]fps={FPS},{ENQUADRAR},select='{sel}',setpts=N/{FPS}/TB{vel_v},split[b][z];"
        f"[z]scale={zw}:{zh},crop={W}:{H}:(iw-{W})/2:(ih-{H})*0.42[zz];"
        f"[b][zz]overlay=0:0:enable='{zexpr}',ass=legenda.ass:fontsdir=fontes,format=yuv420p[v];"
        f"[0:a]aselect='{sel}',asetpts=N/SR/TB{vel_a},loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]"
    )
    with open(os.path.join(pasta, "filtro.txt"), "w") as f:
        f.write(filtro)
    base = re.sub(r"[^a-zA-Z0-9]+", "-", os.path.splitext(os.path.basename(video))[0]).strip("-")[:40]
    destino_dir = SAIDA_CHAT if os.path.isdir(os.path.dirname(SAIDA_CHAT)) else pasta
    os.makedirs(destino_dir, exist_ok=True)
    saida = os.path.join(destino_dir, f"{base}-editado.mp4")
    log(f"montando: {len(fica) - 1} pausas cortadas, velocidade {vel:.2f}x, {len(zooms)} zooms, "
        f"{dur:.1f}s -> {final:.1f}s")
    rodar([ff, "-v", "error", "-y", "-i", video, "-filter_complex", filtro,
           "-map", "[v]", "-map", "[a]", "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "21", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", saida], cwd=pasta)

    # 4. conferencia: 4 fotos do arquivo entregue
    conf = os.path.join(pasta, "conferir.jpg")
    pts = [0.8, final * 0.33, final * 0.66, max(0.5, final - 1.5)]
    for i, t in enumerate(pts):
        rodar([ff, "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", saida, "-frames:v", "1",
               "-vf", "scale=270:-2", os.path.join(pasta, f"c{i}.jpg")])
    rodar([ff, "-v", "error", "-y", "-i", os.path.join(pasta, "c%d.jpg"), "-vf", "tile=4x1", conf])
    m, s = divmod(round(duracao(ff, saida)), 60)
    log("pronto")
    print(f"\nVIDEO={saida}\nDURACAO={m}:{s:02d}\nCONFERIR={conf}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] not in ("preparar", "montar"):
        print(__doc__)
        sys.exit(1)
    if args[0] == "preparar":
        preparar(*(args[1:3]))
    else:
        montar(*(args[1:2]))
