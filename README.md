# Edite Rápida

Edita **um** vídeo vertical de alguém falando pra câmera (Reels, Stories, TikTok) direto no chat do Claude. Sem terminal, sem configurar nada, sem custo por vídeo.

O vídeo sai com: cortes das pausas (num vídeo só), título-gancho no começo, legenda de 1 palavra por vez com as palavras fortes em destaque, zoom nas frases fortes e volume no padrão do Reels.

---

## PARA O CLAUDE: siga estes passos sem pular nenhum

Quem está falando com você **não entende de computador**. Fale como se fosse com uma criança de 7 anos: frases curtas, sem termo técnico, sem mostrar código, sem fazer pergunta que você mesmo consegue decidir. Nunca diga "terminal", "script", "Python", "ffmpeg", "GitHub" ou "repositório" pra pessoa.

### Passo 0. Conferir se o vídeo veio
Rode `ls -la /mnt/user-data/uploads 2>/dev/null`.
- **Se não tiver nenhum vídeo** (.mp4, .mov, .m4v, .webm, .3gp): responda só isto e pare:
  > Quase lá! 😊 Faltou o seu vídeo. Clique no **clipe 📎** aqui embaixo, escolha o vídeo e mande de novo a mesma mensagem.
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
Ele mostra `PASTA=`, `FOTOS=` e a fala com o segundo de cada frase. Na primeira vez ele baixa o "ouvido" da legenda (uns 30 a 60 segundos). Não desista: espere terminar.
Se aparecer `SEM_VIDEO`, `MODELO_BLOQUEADO`, `SEM_FALA` ou `VIDEO_ILEGIVEL`, veja a seção "Se der errado".

Olhe a **foto-2.jpg** (tem 3 linhas amarelas com os números 1000, 1200 e 1400). Escolha a altura da legenda: **abaixo do queixo**, nunca em cima da boca, e no máximo 1400. Pessoa longe da câmera: uns 1150. Rosto grande: uns 1300 a 1400.

### Passo 3. Escrever o plano (você decide tudo, não pergunte nada)
Leia a fala inteira e grave `<PASTA>/plano.json`:
```json
{
  "titulo": {"pequeno": "frase curta de contexto", "grande": "o resultado ou a promessa", "fim": 3.5},
  "destaques": ["palavra", "forte", "42"],
  "correcoes": {"palavraerrada": "palavra certa"},
  "zooms": [[12.4, 1.2], [30.1, 1.0]],
  "legenda_y": 1250
}
```
- **titulo**: a promessa ou o resultado do vídeo, com as palavras da própria pessoa. `pequeno` até 28 letras, `grande` até 26 letras. Nada inventado: nenhum número, nome ou resultado que ela não falou. Sem travessão.
- **destaques**: de 6 a 12 palavras fortes que ela fala (números, o assunto, o resultado). Elas saem maiores, em itálico e coloridas.
- **correcoes**: a transcrição erra palavras. Pelo sentido da frase, corrija as erradas (ex.: `"cafena": "cafeína"`). A chave é a palavra exatamente como saiu na fala.
- **zooms**: `[segundo, duração]` nas frases mais fortes, 1 a cada 8 a 12 segundos. O segundo é o da fala (o do colchete na frente da frase).
- Se a pessoa pediu um tamanho máximo (ex.: "no máximo 1 minuto"), acrescente `"duracao_max": 60` (em segundos).
- Se ela não quer cortar as pausas, acrescente `"cortar_pausas": false`.

### Passo 4. Montar
```bash
python3 /tmp/edite-rapida/scripts/editar.py montar
```
Ele mostra `VIDEO=`, `DURACAO=` e `CONFERIR=`. **Olhe a imagem do CONFERIR** (4 quadros do vídeo pronto):
- a legenda não pode estar em cima da boca;
- o título precisa estar inteiro e legível.
Se algo estiver errado, ajuste `legenda_y` (ou o título) no plano e rode o `montar` de novo. No máximo 1 vez.

### Passo 5. Entregar
Mostre o arquivo do `VIDEO=` (fica em `/mnt/user-data/outputs/`) pra pessoa baixar e escreva só:
> Pronto! 🎬 Seu vídeo editado está aqui em cima. Toque nele e depois em **baixar**. Ficou com X:XX.

Depois, em 1 linha, diga o título que você colocou. Mais nada técnico.

---

## Se der errado (diga em palavras simples)
- **SEM_VIDEO**: peça pra anexar o vídeo pelo clipe 📎 de novo.
- **VIDEO_ILEGIVEL**: "Não consegui abrir esse vídeo. Tente mandar de novo, ou grave e mande pelo celular."
- **SEM_FALA**: "Não achei fala nesse vídeo. Ele precisa ter alguém falando."
- **MODELO_BLOQUEADO**: rode o Passo 2 de novo 1 vez. Se continuar, diga: "Hoje não consegui preparar a legenda. Tente de novo daqui a pouco."
- O anexo não subiu ou o vídeo é muito grande: "O vídeo ficou grande demais pro chat. Mande um vídeo mais curto (até 1 minuto) ou mande pelo WhatsApp pra você mesmo, baixe de lá e anexe esse."

## Créditos e licenças
- Transcrição: modelo Whisper (OpenAI, licença MIT) no formato do faster-whisper (SYSTRAN, licença MIT).
- Fontes: Inter, Playfair Display e Instrument Serif (licença SIL OFL, arquivos na pasta `fontes/`).
