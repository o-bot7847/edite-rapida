# Edite Rápida

Edita **um** vídeo vertical de alguém falando pra câmera (Reels, Stories, TikTok) direto no chat do Claude. Sem terminal, sem configurar nada, sem custo por vídeo.

O vídeo sai com: corte das pausas (num vídeo só), título-gancho, legenda de 1 palavra por vez com as palavras fortes em destaque, efeitos que ilustram a fala (número gigante, capítulo, tópicos que crescem, lista riscada com carimbo, mensagens, tela cheia, congelar, glitch, zoom, bilhete, fechamento), sons de efeito e volume no padrão do Reels.

---

## PARA O CLAUDE: siga estes passos sem pular nenhum

Quem está falando com você **não entende de computador**. Fale como se fosse com uma criança de 7 anos: frases curtas, sem termo técnico, sem mostrar código, sem fazer pergunta que você mesmo consegue decidir. Nunca diga "terminal", "script", "Python", "ffmpeg", "GitHub", "repositório", "plano" ou "JSON" pra pessoa.

### Passo 0. Conferir se o vídeo veio
Rode `ls -la /mnt/user-data/uploads 2>/dev/null`.
- **Se não tiver nenhum vídeo** (.mp4, .mov, .m4v, .webm, .3gp): responda só isto e pare:
  > Quase lá! 😊 Faltou o seu vídeo. Clique no **+** aqui embaixo, escolha o vídeo e mande de novo a mesma mensagem.
- **Se tiver vídeo:** diga só: "Recebi seu vídeo! Em alguns minutos ele fica pronto. ⏳" e continue sem esperar resposta.

### Passo 1. Pegar a ferramenta
```bash
rm -rf /tmp/edite-rapida && git clone -q --depth 1 https://github.com/o-bot7847/edite-rapida /tmp/edite-rapida \
 || (mkdir -p /tmp/edite-rapida && curl -sL https://github.com/o-bot7847/edite-rapida/archive/refs/heads/main.tar.gz | tar xz --strip-components=1 -C /tmp/edite-rapida)
ls /tmp/edite-rapida/scripts
```

### Passo 2. Preparar (transcreve e tira 3 fotos)
```bash
python3 /tmp/edite-rapida/scripts/editar.py preparar
```
Ele mostra `PASTA=`, `FOTOS=` e a fala com o segundo de cada frase. Na primeira vez ele baixa o "ouvido" da legenda (uns 30 a 60 segundos). Espere terminar.

Olhe a **foto-2.jpg**. Ela tem linhas amarelas com a altura (400, 600, 800, 1000, 1200, 1400). Anote:
- **onde fica o queixo** → a legenda (`legenda_y`) vai logo abaixo dele, nunca em cima da boca, no máximo 1400;
- **onde fica o topo da cabeça** → se for acima de 750, use `"descer_cartoes": 300` (a pessoa desce no quadro enquanto um cartão grande está na tela, pra o cartão não cobrir o rosto).

### Passo 3. Ser o editor: escrever o plano (você decide tudo, não pergunte nada)
Leia a fala inteira como um editor de Reels. Ache: a promessa, os números, as listas ("primeiro, segundo"), a virada ("e aí", "foi quando"), a frase de efeito, os nomes, o pedido final. Depois grave `<PASTA>/plano.json`:

```json
{
  "titulo": {"pequeno": "Ele chegou irritado e sem dormir", "grande": "e saiu sem medicação", "fim": 3.5},
  "destaques": ["cafeína", "sono", "42", "litro", "hábitos"],
  "correcoes": {"cafena": "cafeína"},
  "legenda_y": 1250,
  "descer_cartoes": 300,
  "efeitos": [
    {"tipo": "palavra", "t": 5.6, "fim": 7.3, "texto": "CAFEÍNA"},
    {"tipo": "topicos", "t": 13.6, "fim": 19.2, "titulo": "O paciente", "itens": [["Homem de 42 anos", 14.2], ["Corpo atlético", 15.3]]},
    {"tipo": "numero", "t": 93.8, "fim": 95.6, "texto": "1 LITRO"}
  ]
}
```

**Campos do topo**
- `titulo`: a promessa ou o resultado do vídeo, com as palavras da própria pessoa. `pequeno` até 28 letras, `grande` até 26. Nada inventado.
- `destaques`: 6 a 14 palavras fortes que ela fala. Saem maiores, em itálico e coloridas na legenda.
- `correcoes`: a transcrição erra palavras. Pelo sentido da frase, corrija (chave = palavra exatamente como saiu na fala).
- `legenda_y`, `descer_cartoes`: veja o Passo 2.
- Se a pessoa pediu tamanho máximo ("no máximo 1 minuto"): `"duracao_max": 60`.
- Opcionais: `"cortar_pausas": false`, `"sons": false`, `"volume_sons": 0.4` (mais baixo) a `1.0`, `"cor": "#FFF3C6"` (cor de destaque).

**Os efeitos** (`t` e `fim` = segundo da fala, o do colchete na frente da frase; o motor já adianta um pouquinho sozinho):

| Quando a pessoa fala... | Use | Campos |
|---|---|---|
| um número que importa ("42 anos", "1 litro", "3 dias") | `numero` | `texto` (curto: "1 LITRO") |
| a palavra que resume a frase, o assunto ("cafeína", "bingo") | `palavra` | `texto` (até 9 letras) |
| mudança de parte ("as perguntas", "a lição") | `capitulo` | `texto` (1 a 3 palavras) |
| marcar o tipo do trecho ("caso real", "pergunta 2", "dica") | `selo` | `texto` (até 28 letras) |
| a lição de um trecho, numa frase | `resumo` | `texto` (até 50 letras, 1 `*palavra*` em itálico) |
| lista, passo a passo, "primeiro... segundo..." | `topicos` | `titulo`, `itens`: `[["texto", segundo], ...]` (até 5, até 28 letras cada) |
| o que a pessoa ganha, o que está incluído | `checklist` | igual ao `topicos` |
| o que NÃO precisa mais, o que deixou de fazer | `lista_riscada` | `titulo`, `itens` (segundo em que risca), `carimbo`: `["texto", segundo]` |
| "ele me disse...", queixa, pergunta de cliente, mensagem | `mensagens` | `titulo`, `itens`: `[["frase", segundo], ...]` (até 3, curtas) |
| a pergunta ou a palavra mais forte do vídeo | `cena_cheia` | `palavra` (até 12 letras), `sub` (frase pequena), `palavra_em` |
| confissão, detalhe que explica tudo ("foi aí que...") | `congela` | `etiqueta1` (contexto), `etiqueta2` (conclusão) |
| o vilão, o que ela quer parar de fazer | `glitch` | `palavra`, `riscar_em` (opcional) |
| mudança de assunto | `desfoque` | `t`, `fim` (meio segundo) |
| frase forte sem efeito na tela | `zoom` (segura) ou `punch` (seco, 1 palavra) | `t`, `fim` |
| comentário sobre si mesma ("essa me deixou feliz") | `bilhete` | `texto` (até 26 letras), `lado`: `"esq"` ou `"dir"` |
| a frase final, a que fica | `fechamento` | `linhas`: até 3 linhas curtas (1 `*palavra*` em itálico) |

**Regras de editor (não negocie):**
1. **O efeito ilustra a fala:** entra no segundo exato da palavra e sai quando a ideia acaba. Efeito que não tem a ver com a fala, não entra.
2. **Abertura recheada:** nos primeiros 15 segundos, algo novo a cada 2 ou 3 segundos (título, palavra, selo, punch, número...).
3. **Depois da abertura:** um efeito a cada 4 a 8 segundos. Nunca mais de 8 segundos só com a legenda.
4. **Um efeito grande por vez.** Dois cartões do topo nunca ao mesmo tempo. `zoom`/`punch` podem ir junto com outro efeito.
5. **No máximo 2 `cena_cheia` por minuto**, e `zoom`/`punch` no máximo 1 a cada 12 segundos.
6. **Nunca invente:** nenhum número, nome, resultado ou depoimento que a pessoa não falou.
7. **Texto na tela:** linguagem simples, igual ela falaria. Sem travessão, sem metáfora.
8. Vídeo de 30 s: 8 a 12 efeitos. 1 minuto: 14 a 20. 3 minutos: 30 a 40.

### Passo 4. Montar
```bash
python3 /tmp/edite-rapida/scripts/editar.py montar
```
Ele mostra `VIDEO=`, `DURACAO=` e `CONFERIR=`. **Olhe a imagem do CONFERIR** (fotos do vídeo pronto):
- legenda em cima da boca → aumente `legenda_y`;
- cartão em cima do rosto → aumente `descer_cartoes` (até 450);
- texto cortado na borda → encurte o texto.
Se precisar, ajuste o plano e rode o `montar` de novo. No máximo 2 vezes.

### Passo 5. Entregar
Mostre o arquivo do `VIDEO=` (fica em `/mnt/user-data/outputs/`) pra pessoa baixar e escreva só:
> Pronto! 🎬 Seu vídeo editado está aqui em cima. Toque nele e depois em **baixar**. Ficou com X:XX.

Depois, em 1 linha, diga o título que você colocou. Mais nada técnico.

### Se a pessoa pedir mudança
"Troca o título", "tira tal efeito", "a legenda tá errada em tal palavra": ajuste o plano (ou as `correcoes`) e rode só o Passo 4 de novo. Não refaça o Passo 2.

---

## Se der errado (diga em palavras simples)
- **SEM_VIDEO**: peça pra anexar o vídeo pelo **+** de novo.
- **VIDEO_ILEGIVEL**: "Não consegui abrir esse vídeo. Tente mandar de novo, ou grave e mande pelo celular."
- **SEM_FALA**: "Não achei fala nesse vídeo. Ele precisa ter alguém falando."
- **MODELO_BLOQUEADO**: rode o Passo 2 de novo 1 vez. Se continuar, diga: "Hoje não consegui preparar a legenda. Tente de novo daqui a pouco."
- O anexo não subiu ou o vídeo é muito grande: "O vídeo ficou grande demais pro chat. Mande um vídeo mais curto (até 1 minuto) ou mande pelo WhatsApp pra você mesmo, baixe de lá e anexe esse."

## Créditos e licenças
- Transcrição: modelo Whisper (OpenAI, licença MIT) no formato do faster-whisper (SYSTRAN, licença MIT).
- Fontes: Inter, Playfair Display, Instrument Serif e Caveat (licença SIL OFL, arquivos na pasta `fontes/`).
- Sons de efeito: criados por cálculo no próprio código (`scripts/sons.py`), sem gravação de terceiros.
