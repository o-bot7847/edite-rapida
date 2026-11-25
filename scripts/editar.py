#!/usr/bin/env python3
"""Edite Rapida: edita UM video vertical de pessoa falando, rapido e simples.

Duas etapas:
  python3 editar.py preparar [video] [pasta]   -> transcreve e tira fotos do video
  python3 editar.py montar [pasta]             -> le plano.json e entrega o MP4 pronto

O que o video final recebe:
  - corte das pausas (sem cortar palavra), num video so
  - titulo-gancho nos primeiros segundos
  - legenda de 1 palavra por vez, com as palavras fortes em destaque
  - efeitos escolhidos pelo plano (numero gigante, capitulo, topicos, lista riscada,
    mensagens, tela cheia, congelar, glitch, zoom, bilhete, fechamento...) com sons
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
        for y in (400, 600, 800, 1000, 1200, 1400))
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


def uniao(intervalos):
    return "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b in intervalos) or "0"


def dentro(t, intervalos):
    return any(a - 0.05 <= t <= b for a, b in intervalos)


def montar(pasta=None):
    sys.path.insert(0, AQUI)
    import efeitos as fx
    import sons as sn
    pasta = os.path.abspath(pasta or max(glob.glob(os.path.expanduser("~/edite-rapida/*/")), key=os.path.getmtime))
    ff = achar_ffmpeg()
    info = json.load(open(os.path.join(pasta, "info.json")))
    palavras = json.load(open(os.path.join(pasta, "palavras.json"), encoding="utf-8"))
    plano_f = os.path.join(pasta, "plano.json")
    plano = json.load(open(plano_f, encoding="utf-8")) if os.path.exists(plano_f) else {}
    video, dur = info["video"], info["duracao"]
    if not os.path.exists(video):
        pare("SEM_VIDEO", "o video sumiu da pasta. Peca pra anexar de novo.")

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

    cor_dest = plano.get("cor", fx.CREME)
    ly = min(max(int(plano.get("legenda_y", 1250)), 900), 1400)
    c = fx.Ctx(novo, final, cor_dest, ly, int(plano.get("descer_cartoes", 0)))

    # 2. efeitos
    efs = list(plano.get("efeitos", []))
    for z in plano.get("zooms", []):  # formato antigo
        t0 = float(z[0] if isinstance(z, list) else z)
        d0 = float(z[1]) if isinstance(z, list) and len(z) > 1 else 1.3
        efs.append({"tipo": "zoom", "t": t0, "fim": t0 + d0})
    for e in sorted(efs, key=lambda x: float(x.get("t", 0))):
        try:
            fx.aplicar(c, e, float(e.get("t", 0)))
        except Exception as erro:  # noqa: BLE001
            c.avisos.append(f"efeito {e.get('tipo')} em {e.get('t')}s deu erro ({erro}): pulei")

    # 3. titulo-gancho
    cc, _ = fx.cor(cor_dest)
    tit = plano.get("titulo") or {}
    if tit.get("grande"):
        tfim = min(float(tit.get("fim", 3.5)), final)
        partes = [rf"{{\fnInter\b1\fs58\c&HFFFFFF&}}{fx.esc(x)}" for x in fx.quebrar(tit.get("pequeno", ""), 28)]
        partes += [rf"{{\fnPlayfair Display\b1\fs120\c{cc}}}{fx.esc(x)}" for x in fx.quebrar(tit["grande"], 13)]
        c.add(4, 0, tfim, rf"{{\an8\pos(540,330)\bord5\shad4\3c&H101010&\4a&H60&\fad(0,250)}}" + r"\N".join(partes))
        c.som(0.05, "whoosh")

    # 4. legenda (1 palavra por vez)
    tam = int(plano.get("legenda_tamanho", 108))
    dest = {limpa(d) for d in plano.get("destaques", [])}
    pop = r"\fscx82\fscy82\t(0,90,\fscx106\fscy106)\t(90,170,\fscx100\fscy100)"
    for i, (t, s, e) in enumerate(palavras):
        ini = novo(s) - 0.08
        prox = novo(palavras[i + 1][1]) - 0.08 if i + 1 < len(palavras) else novo(e) + 0.5
        fim = max(ini + 0.1, min(prox, novo(e) + 0.6))
        if dentro(ini + 0.05, c.sem_legenda):
            continue
        for a0, b0 in c.sem_legenda:
            if ini < a0 < fim:
                fim = a0
        txt = fx.esc(re.sub(r"^[\"'(]+|[\"'),.;:!…]+$", "", t))
        if not txt:
            continue
        y = ly
        for a0, b0, d0 in c.descer:
            if a0 <= ini <= b0:
                y = min(1400, ly + d0 // 2)
        # zona segura do Reels: a palavra cabe entre x 180 e 900 (botoes de curtir na direita)
        if limpa(t) in dest:
            fs = min(int(tam * 1.3), int(720 / max(1, len(txt) * 0.47)))
            estilo = rf"{{\an5\pos(540,{y})\fnInstrument Serif\i1\fs{fs}\c{cc}\bord5\shad3{pop}}}"
        else:
            fs = min(tam, int(720 / max(1, len(txt) * 0.6)))
            estilo = rf"{{\an5\pos(540,{y})\fnInter\b1\fs{fs}\c&HFFFFFF&\bord5\shad3{pop}}}"
        c.add(1, ini, fim, estilo + txt)

    cab = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Base,Inter,60,&H00FFFFFF,&H00FFFFFF,&H00101010,&H64000000,-1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    linhas = [f"Dialogue: {ca},{fx.ts(a)},{fx.ts(b)},Base,,0,0,0,,{tx}" for ca, a, b, tx in sorted(c.ev, key=lambda x: (x[1], x[0]))]
    with open(os.path.join(pasta, "legenda.ass"), "w", encoding="utf-8") as f:
        f.write(cab + "\n".join(linhas) + "\n")
    os.makedirs(os.path.join(pasta, "fontes"), exist_ok=True)
    for f in glob.glob(os.path.join(FONTES, "*.ttf")):
        shutil.copy(f, os.path.join(pasta, "fontes"))

    # 5. sons
    usar_sons = plano.get("sons", True)
    if usar_sons and c.sons:
        sn.faixa(c.sons, final, os.path.join(pasta, "sons.wav"), float(plano.get("volume_sons", 0.6)))

    # 6. video: um filtro so
    entradas = ["-i", video]
    idx = 1
    if usar_sons and c.sons:
        entradas += ["-i", "sons.wav"]
        i_sons = idx
        idx += 1
    congelas = []
    for k, (a, b, t_orig) in enumerate(c.congela):
        png = f"congela{k}.png"
        rodar([ff, "-v", "error", "-y", "-ss", f"{max(0, t_orig):.2f}", "-i", video, "-frames:v", "1",
               "-vf", ENQUADRAR, os.path.join(pasta, png)])
        entradas += ["-loop", "1", "-t", f"{final + 1:.2f}", "-i", png]
        congelas.append((idx, a, b))
        idx += 1

    sel = "+".join(f"between(t,{x:.3f},{y:.3f})" for x, y in fica)
    vel_v = f",setpts=PTS/{vel:.4f}" if vel > 1.0001 else ""
    vel_a = f",atempo={vel:.4f}" if vel > 1.0001 else ""
    g = [f"[0:v]fps={FPS},{ENQUADRAR},select='{sel}',setpts=N/{FPS}/TB{vel_v}[v0]"]
    atual = "v0"
    if c.zooms:
        esc_z = max(z[2] for z in c.zooms)
        zw, zh = int(W * esc_z) // 2 * 2, int(H * esc_z) // 2 * 2
        g.append(f"[{atual}]split[zb][zz];[zz]scale={zw}:{zh},crop={W}:{H}:(iw-{W})/2:(ih-{H})*0.42[zs];"
                 f"[zb][zs]overlay=0:0:enable='{uniao([(a, b) for a, b, _ in c.zooms])}'[vz]")
        atual = "vz"
    for d in sorted({d for _, _, d in c.descer}):
        tr = [(a, b) for a, b, dd in c.descer if dd == d]
        en = uniao(tr)
        g.append(f"[{atual}]split=3[db][dd][dg];[dg]boxblur=28:2:enable='{en}',eq=brightness=-0.22:enable='{en}'[dfundo];"
                 f"[dd]crop={W}:{H - d}:0:0[dfrente];[dfundo][dfrente]overlay=0:{d}[ds];"
                 f"[db][ds]overlay=0:0:enable='{en}'[vd{d}]")
        atual = f"vd{d}"
    for k, (i_png, a, b) in enumerate(congelas):
        g.append(f"[{i_png}:v]setsar=1,format=yuv420p[cg{k}];[{atual}][cg{k}]overlay=0:0:enable='between(t,{a:.2f},{b:.2f})'[vc{k}]")
        atual = f"vc{k}"
    extra = []
    if c.blur:
        extra.append(f"boxblur=22:2:enable='{uniao(c.blur)}'")
    for a, b, op in c.escuro:
        extra.append(f"drawbox=x=0:y=0:w=iw:h=ih:color=black@{op:.2f}:t=fill:enable='between(t,{a:.2f},{b:.2f})'")
    extra.append("ass=legenda.ass:fontsdir=fontes")
    extra.append("format=yuv420p")
    g.append(f"[{atual}]" + ",".join(extra) + "[v]")
    voz = f"[0:a]aselect='{sel}',asetpts=N/SR/TB{vel_a}"
    if usar_sons and c.sons:
        g.append(voz + "[voz]")
        g.append(f"[{i_sons}:a]aresample=48000,volume=1.0[sfx];[voz]aresample=48000[voz2];"
                 f"[voz2][sfx]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]")
    else:
        g.append(voz + ",loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]")
    filtro = ";".join(g)
    with open(os.path.join(pasta, "filtro.txt"), "w") as f:
        f.write(filtro)

    base = re.sub(r"[^a-zA-Z0-9]+", "-", os.path.splitext(os.path.basename(video))[0]).strip("-")[:40]
    destino_dir = SAIDA_CHAT if os.path.isdir(os.path.dirname(SAIDA_CHAT)) else pasta
    os.makedirs(destino_dir, exist_ok=True)
    saida = os.path.join(destino_dir, f"{base}-editado.mp4")
    for aviso in c.avisos:
        log("aviso: " + aviso)
    log(f"montando: {len(fica) - 1} pausas cortadas, velocidade {vel:.2f}x, {len(efs)} efeitos, "
        f"{len(c.sons)} sons, {dur:.1f}s -> {final:.1f}s")
    rodar([ff, "-v", "error", "-y", *entradas, "-filter_complex", filtro,
           "-map", "[v]", "-map", "[a]", "-r", str(FPS), "-t", f"{final:.2f}", "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "21", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", saida], cwd=pasta)

    # 7. conferencia: 1 foto no meio de cada efeito (ate 8) + inicio
    pts = [0.8] + [round((a + b) / 2, 2) for _, a, b, _ in sorted(c.ev, key=lambda x: x[1]) if b - a > 0.8][::3]
    pts = sorted(set(min(final - 0.2, p) for p in pts))[:8]
    for f in glob.glob(os.path.join(pasta, "c*.jpg")):
        os.remove(f)
    for i, t in enumerate(pts):
        rodar([ff, "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", saida, "-frames:v", "1",
               "-vf", "scale=240:-2", os.path.join(pasta, f"c{i}.jpg")])
    conf = os.path.join(pasta, "conferir.jpg")
    rodar([ff, "-v", "error", "-y", "-i", os.path.join(pasta, "c%d.jpg"), "-vf", f"tile={len(pts)}x1", conf])
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
