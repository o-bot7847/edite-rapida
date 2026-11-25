"""Efeitos da Edite Rapida: cada efeito do plano vira desenho na legenda (.ass), som e,
quando precisa, um ajuste no video (desfoque, escurecer, congelar, zoom, descer a pessoa).

Tipos: numero, palavra, capitulo, selo, resumo, topicos, checklist, lista_riscada, mensagens,
cena_cheia, congela, glitch, desfoque, zoom, punch, bilhete, fechamento.
"""
import re

W, H = 1080, 1920
CREME = "#FFF3C6"


def cor(hexcor, alpha=0):
    h = hexcor.lstrip("#")
    return f"&H{h[4:6]}{h[2:4]}{h[0:2]}&".upper(), f"&H{alpha:02X}&"


def esc(t):
    return str(t).replace("\\", "").replace("{", "(").replace("}", ")")


def ts(t):
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def larg(texto, fs, fonte="inter"):
    k = {"inter": 0.56, "inter_b": 0.6, "playfair": 0.62, "serif_i": 0.46, "caveat": 0.42}[fonte]
    return len(texto) * fs * k


def quebrar(texto, maximo):
    linhas, atual = [], ""
    for w in str(texto).split():
        if atual and len(atual) + 1 + len(w) > maximo:
            linhas.append(atual)
            atual = w
        else:
            atual = (atual + " " + w).strip()
    if atual:
        linhas.append(atual)
    return linhas


def caixa(w, h, r=24):
    w, h, r = int(w), int(h), int(min(r, w / 2, h / 2))
    return (f"m {r} 0 l {w - r} 0 b {w} 0 {w} 0 {w} {r} l {w} {h - r} b {w} {h} {w} {h} {w - r} {h} "
            f"l {r} {h} b 0 {h} 0 {h} 0 {h - r} l 0 {r} b 0 0 0 0 {r} 0")


def circulo(d):
    r = d / 2
    k = r * 0.5523
    return (f"m {r} 0 b {r + k} 0 {d} {r - k} {d} {r} b {d} {r + k} {r + k} {d} {r} {d} "
            f"b {r - k} {d} 0 {r + k} 0 {r} b 0 {r - k} {r - k} 0 {r} 0")


def italico(texto, cor_dest):
    """*palavra* vira italico serifado na cor de destaque."""
    c, _ = cor(cor_dest)
    return re.sub(r"\*([^*]+)\*", lambda m: r"{\fnInstrument Serif\i1\b0\c" + c + "}" + esc(m.group(1)) + r"{\r}", esc(texto))


class Ctx:
    def __init__(self, novo, final, cor_dest, ly, descer):
        self.novo = novo          # tempo do video original -> tempo do video final
        self.final = final
        self.cor = cor_dest
        self.ly = ly
        self.descer_padrao = descer
        self.ev = []              # (camada, inicio, fim, texto)
        self.sons = []            # (segundo, nome)
        self.blur, self.escuro, self.congela, self.zooms, self.descer, self.sem_legenda = [], [], [], [], [], []
        self.avisos = []

    def t(self, s, adiantar=0.2):
        return max(0.0, self.novo(float(s)) - adiantar)

    def add(self, camada, a, b, texto):
        b = min(b, self.final)
        if b - a >= 0.05:
            self.ev.append((camada, a, b, texto))

    def som(self, s, nome):
        self.sons.append((s, nome))

    def topo(self, e):
        """altura onde comecam os cartoes do topo (desce junto com a pessoa)."""
        return 310 + int(e.get("y_extra", 0))


def _cartao_lista(c, e, a, b, linhas_txt, tempos, marca, titulo):
    """caixa escura no topo com titulo e itens que aparecem no seu tempo."""
    fs, alt = 58, 92
    y0 = c.topo(e)
    cc, _ = cor(c.cor)
    largura = max([larg(x, fs) for x in linhas_txt] + [larg(titulo or "", 36, "inter_b")]) + 150
    largura = min(max(largura, 520), 920)
    x0 = 80
    h = 40 + (64 if titulo else 0) + alt * len(linhas_txt)
    c.add(5, a, b, rf"{{\an7\pos({x0},{y0})\p1\bord0\shad0\1c&H141414&\1a&H38&\fad(180,200)}}{caixa(largura, h, 30)}")
    y = y0 + 26
    if titulo:
        c.add(6, a, b, rf"{{\an7\pos({x0 + 34},{y})\fnInter\b1\fs40\fsp3\c{cc}\bord0\shad0\fad(180,200)}}{esc(titulo.upper())}")
        y += 64
    for i, (txt, tt) in enumerate(zip(linhas_txt, tempos)):
        ini = max(a, tt)
        yy = y + i * alt
        if marca == "numero":
            c.add(6, ini, b, rf"{{\an7\pos({x0 + 30},{yy})\p1\bord0\shad0\1c{cc}\fad(120,200)}}{circulo(56)}")
            c.add(7, ini, b, rf"{{\an5\pos({x0 + 58},{yy + 29})\fnInter\b1\fs34\c&H141414&\bord0\shad0\fad(120,200)}}{i + 1}")
        elif marca == "check":
            c.add(6, ini, b, rf"{{\an7\pos({x0 + 30},{yy})\p1\bord0\shad0\1c&H5CC46B&\fad(120,200)}}{circulo(56)}")
            c.add(7, ini, b, rf"{{\an5\pos({x0 + 58},{yy + 30})\fnInter\b1\fs36\c&HFFFFFF&\bord0\shad0\fad(120,200)}}✓")
        else:
            c.add(6, ini, b, rf"{{\an7\pos({x0 + 44},{yy + 16})\p1\bord0\shad0\1c{cc}\fad(120,200)}}{circulo(24)}")
        c.add(7, ini, b, rf"{{\an4\pos({x0 + 106},{yy + 29})\fnInter\b1\fs{fs}\c&HFFFFFF&\bord0\shad0"
                         rf"\fscx92\fscy92\t(0,140,\fscx100\fscy100)\fad(120,200)}}{esc(txt)}")
        c.som(ini, "pop")
    return x0, y, alt, largura


def numero(c, e, a, b, palavra=False):
    txt = str(e.get("texto", ""))
    fs = int(e.get("tamanho", 0)) or int(min(300 if not palavra else 260, 900 / max(1, len(txt) * 0.62)))
    y = int(e.get("y", 0)) or 560
    cc, _ = cor(c.cor)
    c.add(8, a, b, rf"{{\an5\pos(540,{y})\fnPlayfair Display\b1\fs{fs}\c{cc}\3c&H101010&\bord6\shad8\4a&H60&"
                   rf"\fscx55\fscy55\t(0,120,\fscx112\fscy112)\t(120,220,\fscx100\fscy100)\fad(0,200)}}{esc(txt)}")
    c.som(a, "impacto")


def capitulo(c, e, a, b):
    txt = esc(str(e.get("texto", "")).upper())
    y = int(e.get("y", 0)) or 380
    cc, _ = cor(c.cor)
    c.add(8, a, b, rf"{{\an5\pos(540,{y})\fnPlayfair Display\b1\fs72\fsp10\c&HFFFFFF&\3c&H101010&\bord3\shad4\4a&H70&\fad(250,250)}}{txt}")
    w = min(860, larg(txt, 72, "playfair") + 10 * len(txt))
    c.add(8, a + 0.15, b, rf"{{\an5\pos(540,{y + 62})\p1\bord0\shad0\1c{cc}\fscx0\t(0,350,\fscx100)\fad(0,250)}}{caixa(w, 5, 2)}")
    c.som(a, "whoosh")


def selo(c, e, a, b):
    txt = esc(e.get("texto", ""))
    y = int(e.get("y", 0)) or max(320, c.ly - 125)
    fs = 42 if larg(txt, 42) + 110 <= 700 else max(30, int(590 / max(1, len(txt) * 0.56)))
    w = larg(txt, fs) + 110
    cc, _ = cor(c.cor)
    c.add(8, a, b, rf"{{\an5\pos(540,{y})\p1\bord0\shad0\1c&H141414&\1a&H30&\fad(150,200)}}{caixa(w, 78, 39)}")
    c.add(9, a, b, rf"{{\an5\pos({540 - w / 2 + 40},{y})\p1\bord0\shad0\1c{cc}\fad(150,200)}}{circulo(18)}")
    c.add(9, a, b, rf"{{\an5\pos({540 + 18},{y})\fnInter\b1\fs{fs}\c&HFFFFFF&\bord0\shad0\fad(150,200)}}{txt}")
    c.som(a, "pop")


def resumo(c, e, a, b):
    y = int(e.get("y", 0)) or 400
    linhas = quebrar(e.get("texto", ""), 26)
    txt = r"\N".join(italico(x, c.cor) for x in linhas)
    c.add(8, a, b, rf"{{\an8\pos(540,{y})\fnInter\b1\fs62\c&HFFFFFF&\3c&H101010&\bord4\shad4\4a&H60&\fad(300,300)}}{txt}")
    c.som(a, "whoosh")


def topicos(c, e, a, b, marca="numero"):
    itens = e.get("itens", [])
    txts = [str(x[0]) for x in itens]
    tempos = [c.t(x[1]) for x in itens]
    _cartao_lista(c, e, a, b, txts, tempos, marca, e.get("titulo", ""))
    c.som(a, "whoosh")
    if marca == "check" and tempos:
        c.som(tempos[-1] + 0.3, "ding")


def lista_riscada(c, e, a, b):
    itens = e.get("itens", [])
    if e.get("carimbo"):
        b = max(b, c.t(e["carimbo"][1]) + 1.6)
    txts = [str(x[0]) for x in itens]
    entra = a
    risca = [c.t(x[1]) for x in itens]
    x0, y, alt, largura = _cartao_lista(c, e, a, b, txts, [entra + 0.15 * i for i in range(len(txts))], "ponto", e.get("titulo", ""))
    c.sons = [s for s in c.sons if not (s[1] == "pop" and a <= s[0] <= a + 1)]
    for i, (txt, tt) in enumerate(zip(txts, risca)):
        w = larg(txt, 58) + 10
        c.add(8, tt, b, rf"{{\an4\pos({x0 + 100},{y + i * alt + 31})\p1\bord0\shad0\1c&H3B3BE8&\fscx0\t(0,260,\fscx100)\fad(0,200)}}{caixa(w, 7, 3)}")
        c.som(tt, "risco")
    carimbo = e.get("carimbo")
    if carimbo:
        tc = c.t(carimbo[1])
        yy = y + alt * len(txts) + 70
        txt = esc(str(carimbo[0]).upper())
        c.add(10, tc, b, rf"{{\an5\pos(540,{yy})\fnInter\b1\fs66\fsp4\c&H3B3BE8&\3c&H3B3BE8&\bord0\shad0\frz-6"
                         rf"\fscx190\fscy190\t(0,130,\fscx100\fscy100)\fad(60,200)}}{txt}")
        w = larg(txt, 66, "inter_b") + 60
        c.add(9, tc, b, rf"{{\an5\pos(540,{yy})\p1\frz-6\1c&HF2F4F7&\1a&H08&\3c&H3B3BE8&\bord6\shad0"
                         rf"\fscx190\fscy190\t(0,130,\fscx100\fscy100)\fad(60,200)}}{caixa(w, 104, 14)}")
        c.som(tc, "impacto")
    c.som(a, "whoosh")


def mensagens(c, e, a, b):
    itens = e.get("itens", [])
    y = c.topo(e)
    cc, _ = cor(c.cor)
    titulo = esc(e.get("titulo", ""))
    if titulo:
        w = larg(titulo, 34, "inter_b") + 70
        c.add(8, a, b, rf"{{\an7\pos(80,{y})\p1\bord0\shad0\1c{cc}\fad(150,200)}}{caixa(w, 58, 29)}")
        c.add(9, a, b, rf"{{\an7\pos(115,{y + 10})\fnInter\b1\fs34\c&H141414&\bord0\shad0\fad(150,200)}}{titulo}")
        y += 80
    for txt, tt in [(x[0], x[1]) for x in itens]:
        ini = max(a, c.t(tt))
        linhas = quebrar(txt, 26)
        h = 34 + 60 * len(linhas)
        w = max(larg(x, 48) for x in linhas) + 70
        c.add(8, ini, b, rf"{{\an7\pos(80,{y})\p1\bord0\shad3\4a&H90&\1c&HFFFFFF&\fscx90\fscy90\t(0,140,\fscx100\fscy100)\fad(100,200)}}{caixa(w, h, 30)}")
        c.add(9, ini, b, rf"{{\an7\pos(115,{y + 18})\fnInter\fs48\c&H1E1E1E&\bord0\shad0\fad(100,200)}}" + r"\N".join(esc(x) for x in linhas))
        c.som(ini, "bolha")
        y += h + 22


def cena_cheia(c, e, a, b):
    palavra = str(e.get("palavra", ""))
    sub = esc(e.get("sub", ""))
    cc, _ = cor(c.cor)
    c.blur.append((a, b))
    c.escuro.append((a, b, 0.62))
    c.sem_legenda.append((a, b))
    passo = float(e.get("passo", 0.07))
    pe = c.t(e["palavra_em"]) if e.get("palavra_em") is not None else a + 0.2
    fs = int(min(190, 940 / max(1, len(palavra) * 0.46)))
    for i in range(1, len(palavra) + 1):
        ini = pe + (i - 1) * passo
        fim = pe + i * passo if i < len(palavra) else b
        c.add(9, ini, fim, rf"{{\an5\pos(540,940)\fnInstrument Serif\i1\fs{fs}\c{cc}\bord0\shad0}}{esc(palavra[:i])}")
    if sub:
        c.add(9, pe + len(palavra) * passo + 0.1, b, rf"{{\an5\pos(540,{940 + fs * 0.62 + 30})\fnInter\fs46\c&HFFFFFF&\bord0\shad0\fad(250,150)}}{sub}")
    c.som(a, "whoosh")


def congela(c, e, a, b, t_orig):
    c.congela.append((a, b, t_orig))
    c.escuro.append((a, b, 0.35))
    c.sem_legenda.append((a, b))
    y = c.ly - 40
    for i, (chave, fundo, letra) in enumerate((("etiqueta1", "&HFFFFFF&", "&H141414&"), ("etiqueta2", "&H3B3BE8&", "&HFFFFFF&"))):
        txt = esc(e.get(chave, ""))
        if not txt:
            continue
        ini = a + 0.15 + i * 0.35
        w = larg(txt, 54, "inter_b") + 70
        yy = y + i * 104
        c.add(9, ini, b, rf"{{\an5\pos(540,{yy})\p1\bord0\shad0\1c{fundo}\frz{2 - i * 4}\fscx80\fscy80\t(0,120,\fscx100\fscy100)}}{caixa(w, 88, 12)}")
        c.add(10, ini, b, rf"{{\an5\pos(540,{yy})\fnInter\b1\fs54\c{letra}\bord0\shad0\frz{2 - i * 4}\fscx80\fscy80\t(0,120,\fscx100\fscy100)}}{txt}")
    c.som(a, "foto")


def glitch(c, e, a, b):
    txt = esc(str(e.get("palavra", "")).upper())
    fs = int(e.get("tamanho", 0)) or int(min(240, 920 / max(1, len(txt) * 0.62)))
    y = int(e.get("y", 0)) or 560
    passo = 0.06
    tt = a
    k = 0
    while tt < b:
        fim = min(b, tt + passo) if tt < a + 0.6 else b
        dx = [6, -9, 4, -5, 10, -3][k % 6] if tt < a + 0.6 else 0
        c.add(8, tt, fim, rf"{{\an5\pos({540 + dx + 7},{y + 3})\fnInter\b1\fs{fs}\c&H3B3BFF&\alpha&H50&\bord0\shad0}}{txt}")
        c.add(8, tt, fim, rf"{{\an5\pos({540 - dx - 7},{y - 3})\fnInter\b1\fs{fs}\c&HFFE000&\alpha&H50&\bord0\shad0}}{txt}")
        c.add(9, tt, fim, rf"{{\an5\pos({540 + dx // 2},{y})\fnInter\b1\fs{fs}\c&HFFFFFF&\3c&H101010&\bord3\shad0}}{txt}")
        tt, k = fim, k + 1
    if e.get("riscar_em") is not None:
        tr = max(a, c.t(e["riscar_em"]))
        w = larg(txt, fs, "inter_b") + 30
        c.add(10, tr, b, rf"{{\an5\pos(540,{y})\p1\bord0\shad0\1c&H3B3BE8&\frz-4\fscx0\t(0,220,\fscx100)}}{caixa(w, max(10, fs // 14), 4)}")
        c.som(tr, "risco")
    c.som(a, "glitch")


def bilhete(c, e, a, b):
    txt = esc(e.get("texto", ""))
    lado = e.get("lado", "esq")
    y = int(e.get("y", 0)) or 380
    cc, _ = cor(c.cor)
    x = 110 if lado == "esq" else 970
    an = 7 if lado == "esq" else 9
    c.add(9, a, b, rf"{{\an{an}\pos({x},{y})\fnCaveat\b1\fs78\c{cc}\3c&H101010&\bord3\shad3\4a&H70&\frz4\fad(200,200)}}{txt}")
    w = larg(txt, 78, "caveat")
    xs = x if lado == "esq" else x - w
    c.add(9, a + 0.25, b, rf"{{\an7\pos({xs},{y + 92})\p1\bord0\shad0\1c{cc}\frz4\fscx0\t(0,300,\fscx100)\fad(0,200)}}{caixa(w, 6, 3)}")
    c.som(a, "pop")


def fechamento(c, e, a, b):
    linhas = e.get("linhas") or quebrar(e.get("texto", ""), 16)
    y = int(e.get("y", 0)) or 380
    cc, _ = cor(c.cor)
    for i, ln in enumerate(linhas[:3]):
        ini = a + i * 0.35
        c.add(8, ini, b, rf"{{\an8\pos(540,{y + i * 120})\fnPlayfair Display\b1\fs104\c{cc if i == len(linhas) - 1 else '&HFFFFFF&'}"
                         rf"\3c&H101010&\bord4\shad5\4a&H60&\fad(350,0)\fscx94\fscy94\t(0,400,\fscx100\fscy100)}}{italico(ln, c.cor)}")
    c.som(a, "sino")


def aplicar(c, e, t_orig_ini):
    tipo = e.get("tipo")
    if "t" not in e:
        c.avisos.append(f"efeito {tipo} sem 't': pulei")
        return
    a = c.t(e["t"])
    b = c.t(e["fim"], 0.0) if e.get("fim") is not None else a + 2.5
    if b <= a:
        b = a + 1.5
    if e.get("descer") or (tipo in ("topicos", "checklist", "lista_riscada", "mensagens") and c.descer_padrao):
        d = int(e.get("descer", c.descer_padrao))
        c.descer.append((a, b, d))
        e = dict(e, y_extra=0)
    if tipo == "numero":
        numero(c, e, a, b)
    elif tipo == "palavra":
        numero(c, e, a, b, palavra=True)
    elif tipo == "capitulo":
        capitulo(c, e, a, b)
    elif tipo == "selo":
        selo(c, e, a, b)
    elif tipo == "resumo":
        resumo(c, e, a, b)
    elif tipo == "topicos":
        topicos(c, e, a, b, "numero")
    elif tipo == "checklist":
        topicos(c, e, a, b, "check")
    elif tipo == "lista_riscada":
        lista_riscada(c, e, a, b)
    elif tipo == "mensagens":
        mensagens(c, e, a, b)
    elif tipo == "cena_cheia":
        cena_cheia(c, e, a, b)
    elif tipo == "congela":
        congela(c, e, a, b, t_orig_ini)
    elif tipo == "glitch":
        glitch(c, e, a, b)
    elif tipo == "desfoque":
        c.blur.append((a, min(b, a + 1.0)))
        c.som(a, "whoosh_curto")
    elif tipo in ("zoom", "punch"):
        c.zooms.append((a, b, float(e.get("escala", 1.15 if tipo == "zoom" else 1.2))))
        c.som(a, "whoosh_curto")
    elif tipo == "bilhete":
        bilhete(c, e, a, b)
    elif tipo == "fechamento":
        fechamento(c, e, a, b)
    else:
        c.avisos.append(f"tipo desconhecido '{tipo}': pulei")
