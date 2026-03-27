// ══════════════════════════════════════════════════════════════════════
//  ETP — Estudo Técnico Preliminar
//  Aquisição de Materiais de Limpeza e Higiene — ARP
//  Secretaria Municipal de Saúde de Borba/AM
//  Lei n.º 14.133/2021
// ══════════════════════════════════════════════════════════════════════

// ── Cores (DEVE vir antes de #set page) ───────────────────────────────
#let navy      = rgb("#1A3A5C")
#let medblue   = rgb("#2E75B6")
#let ltblue    = rgb("#D6E4F0")
#let rowalt    = rgb("#EBF3FB")
#let formulabg = rgb("#EEF4FB")
#let alertbg   = rgb("#FFF8E1")
#let alertbdr  = rgb("#E59C0A")
#let legalbg   = rgb("#F0FDF4")
#let legalbdr  = rgb("#16A34A")
#let warnbg    = rgb("#FEF2F2")
#let warnbdr   = rgb("#DC2626")

// ── Metadados ─────────────────────────────────────────────────────────
#set document(
  title:  "ETP-SMS/BORBA-001/2025 — Materiais de Limpeza e Higiene",
  author: "Secretaria Municipal de Saúde de Borba/AM",
)

// ── Página ────────────────────────────────────────────────────────────
#set page(
  paper:  "a4",
  margin: (top: 2.8cm, bottom: 2.8cm, left: 3.0cm, right: 2.5cm),
  header: context {
    if counter(page).get().first() > 1 {
      set text(size: 9pt, fill: navy)
      grid(
        columns: (1fr, 1fr),
        align: (left, right),
        [*ETP* — Aquisição de Material de Limpeza e Higiene],
        [Borba/AM • Lei n.º 14.133/2021],
      )
      line(length: 100%, stroke: 0.5pt + medblue)
    }
  },
  footer: context {
    if counter(page).get().first() > 1 {
      set text(size: 9pt, fill: luma(120))
      align(center)[#counter(page).display("1 / 1", both: true)]
    }
  },
)

// ── Tipografia ────────────────────────────────────────────────────────
#set text(size: 11pt, lang: "pt")
#set par(justify: true, leading: 0.75em, spacing: 1.1em)

// ── Títulos ───────────────────────────────────────────────────────────
#show heading.where(level: 1): it => {
  v(1.2em)
  block(width: 100%)[
    #set text(size: 13pt, weight: "bold", fill: navy)
    #it.body
    #line(length: 100%, stroke: 1pt + navy)
  ]
  v(0.4em)
}
#show heading.where(level: 2): it => {
  v(0.9em)
  set text(size: 11.5pt, weight: "bold", fill: medblue)
  it.body
  v(0.3em)
}
#show heading.where(level: 3): it => {
  v(0.7em)
  set text(size: 11pt, weight: "bold", fill: navy.lighten(15%))
  it.body
  v(0.2em)
}

// ── Componentes ───────────────────────────────────────────────────────

// Caixa colorida genérica
#let caixa(titulo: "", bg: white, bdr: navy, fg: white, corpo) = {
  block(
    width: 100%,
    stroke: 1pt + bdr,
    radius: 4pt,
    inset: 0pt,
    breakable: true,
    fill: bg,
  )[
    #block(
      width: 100%,
      fill: bdr,
      inset: (x: 10pt, y: 5pt),
      radius: (top-left: 4pt, top-right: 4pt),
    )[
      #set text(size: 9.5pt, weight: "bold", fill: fg)
      #titulo
    ]
    #block(inset: (x: 12pt, y: 8pt))[
      #set text(size: 10pt)
      #corpo
    ]
  ]
}

#let legalbox(titulo: "Base Legal", corpo) = caixa(
  titulo: titulo, bg: legalbg, bdr: legalbdr, fg: white, corpo,
)
#let alertbox(titulo: "Atenção", corpo) = caixa(
  titulo: titulo, bg: alertbg, bdr: alertbdr, fg: navy, corpo,
)
#let warnbox(titulo: "Requisito Obrigatório", corpo) = caixa(
  titulo: titulo, bg: warnbg, bdr: warnbdr, fg: white, corpo,
)

// Caixa de fórmula
#let formulabox(corpo) = block(
  width: 100%,
  fill: formulabg,
  stroke: 1pt + medblue,
  radius: 4pt,
  inset: (x: 20pt, y: 10pt),
)[
  #align(center)[#corpo]
]

// Caixa de conclusão
#let conclusabox(corpo) = block(
  width: 100%,
  fill: navy.lighten(88%),
  stroke: 1.5pt + navy,
  radius: 5pt,
  inset: (x: 16pt, y: 12pt),
)[#corpo]

// Cabeçalho de tabela (linha azul)
#let thdr(body) = {
  set text(size: 9.5pt, weight: "bold", fill: white)
  align(center)[#body]
}

// Célula de tabela centralizada
#let tc(body) = align(center)[#set text(size: 9.5pt); #body]

// Dados do processo
#let etpnum  = "ETP-SMS/BORBA-001/2025"
#let procnum = "[NÚMERO DO PROCESSO SEI/E-DOC]"
#let resp    = "[NOME, CARGO E MATRÍCULA DO SERVIDOR]"

// ══════════════════════════════════════════════════════════════════════
//  CAPA
// ══════════════════════════════════════════════════════════════════════
#page(
  margin: (top: 0pt, bottom: 0pt, left: 0pt, right: 0pt),
  header: none,
  footer: none,
  background: rect(width: 100%, height: 100%, fill: navy),
)[
  #set text(fill: white)
  #align(center)[
    #v(2.8cm)
    #text(size: 10pt, fill: ltblue, weight: "bold")[PREFEITURA MUNICIPAL DE BORBA]
    #linebreak()
    #text(size: 9pt, fill: ltblue.lighten(20%))[SECRETARIA MUNICIPAL DE SAÚDE]
    #v(0.5cm)
    #line(length: 80%, stroke: 0.8pt + ltblue.transparentize(40%))
    #v(0.5cm)
    #text(size: 11pt, fill: ltblue.lighten(10%), weight: "bold")[
      ESTUDO TÉCNICO PRELIMINAR — ETP
    ]
    #v(0.3cm)
    #text(size: 24pt, weight: "bold")[
      Aquisição de Materiais de \
      Limpeza e Higiene
    ]
    #v(0.2cm)
    #text(size: 13pt, fill: ltblue.lighten(10%))[Ata de Registro de Preços]
    #v(0.5cm)
    #line(length: 80%, stroke: 0.8pt + ltblue.transparentize(40%))
    #v(1cm)
    #block(
      width: 78%,
      fill: navy.lighten(8%),
      stroke: 0.5pt + ltblue.transparentize(50%),
      radius: 5pt,
      inset: (x: 18pt, y: 12pt),
    )[
      #set text(size: 9pt)
      #grid(
        columns: (auto, 1fr),
        column-gutter: 8pt,
        row-gutter: 6pt,
        text(fill: ltblue, weight: "bold")[N.º do ETP:],      [#etpnum],
        text(fill: ltblue, weight: "bold")[Processo:],         [#procnum],
        text(fill: ltblue, weight: "bold")[Modalidade:],       [Pregão Eletrônico — Sistema de Registro de Preços],
        text(fill: ltblue, weight: "bold")[Unidade:],          [Secretaria Municipal de Saúde de Borba/AM],
        text(fill: ltblue, weight: "bold")[Responsável:],      [#resp],
        text(fill: ltblue, weight: "bold")[Base Legal:],       [Lei n.º 14.133, de 1.º de abril de 2021],
        text(fill: ltblue, weight: "bold")[Valor Estimado:],   [R\$ 2.000.000,00 (dois milhões de reais)],
        text(fill: ltblue, weight: "bold")[Vigência da ARP:],  [12 meses, prorrogáveis (art. 84, §1.º)],
      )
    ]
    #v(1fr)
    #line(length: 80%, stroke: 0.4pt + ltblue.transparentize(60%))
    #v(0.3cm)
    #text(size: 8pt, fill: ltblue.transparentize(30%))[
      Elaborado em conformidade com o art. 18 e incisos da Lei n.º 14.133/2021 • Borba/AM, 2025
    ]
    #v(0.6cm)
  ]
]

// ── Sumário ───────────────────────────────────────────────────────────
#set page(numbering: "1 / 1")
#counter(page).update(1)

#outline(
  title: text(size: 14pt, weight: "bold", fill: navy)[Sumário],
  indent: 1.5em,
  depth: 2,
)
#pagebreak()

// ── Ficha de Identificação ────────────────────────────────────────────
#align(center)[
  #text(size: 12pt, weight: "bold", fill: navy)[FICHA DE IDENTIFICAÇÃO DO ESTUDO TÉCNICO PRELIMINAR]
]
#v(0.4em)
#table(
  columns: (4cm, 1fr),
  stroke: 0.5pt + luma(190),
  fill: (col, row) => if col == 0 { ltblue } else if calc.odd(row) { rowalt } else { white },
  [#text(weight: "bold", fill: navy, size: 9.5pt)[N.º do ETP]],           [#etpnum],
  [#text(weight: "bold", fill: navy, size: 9.5pt)[N.º do Processo]],      [#procnum],
  [#text(weight: "bold", fill: navy, size: 9.5pt)[Unidade Requisitante]], [Secretaria Municipal de Saúde de Borba/AM],
  [#text(weight: "bold", fill: navy, size: 9.5pt)[Unidade Orçamentária]], [\[UNIDADE ORÇAMENTÁRIA E FONTE DE RECURSOS\]],
  [#text(weight: "bold", fill: navy, size: 9.5pt)[Objeto]],               [Aquisição de materiais de limpeza e higiene para a Rede de Atenção à Saúde de Borba/AM, via Ata de Registro de Preços],
  [#text(weight: "bold", fill: navy, size: 9.5pt)[Modalidade]],           [Pregão Eletrônico — art. 17, Lei n.º 14.133/2021],
  [#text(weight: "bold", fill: navy, size: 9.5pt)[Instrumento]],          [Ata de Registro de Preços — art. 82, Lei n.º 14.133/2021],
  [#text(weight: "bold", fill: navy, size: 9.5pt)[Valor Estimado]],       [R\$ 2.000.000,00 (dois milhões de reais)],
  [#text(weight: "bold", fill: navy, size: 9.5pt)[Vigência da ARP]],      [12 meses, prorrogável por igual período (art. 84, §1.º)],
  [#text(weight: "bold", fill: navy, size: 9.5pt)[Elaborado por]],        [#resp],
)
#pagebreak()

// ══════════════════════════════════════════════════════════════════════
= 1. Descrição da Necessidade da Contratação
// ══════════════════════════════════════════════════════════════════════

#legalbox(titulo: "Base Legal — Art. 18, I, Lei n.º 14.133/2021")[
  A contratação deve ser precedida e instruída com ETP, evidenciando o *problema a ser
  resolvido* e sua melhor solução, demonstrando a necessidade da contratação,
  fundamentada no planejamento estratégico ou no PCA, e nas necessidades da sociedade.
]

== 1.1 Contextualização e Identificação do Problema

O Município de Borba, situado no estado do Amazonas, possui população estimada de
*34.869 habitantes* (IBGE, 2025) e conta com *10 unidades assistenciais* de saúde:
9 Unidades Básicas de Saúde (UBS) e o *Hospital Municipal Vó Mundoca*, único serviço
de internação do território, com 40 leitos operacionais.

A manutenção da *salubridade ambiental* das unidades é obrigação legal irrenunciável,
nos termos da RDC ANVISA n.º 216/2004, RDC n.º 15/2012, NR-32 (MTE) e do Programa
Nacional de Segurança do Paciente (PNSP/MS, 2013). A ausência ou insuficiência de
materiais de limpeza e higiene acarreta:

- Aumento das taxas de *Infecções Relacionadas à Assistência à Saúde (IRAS)*,
  principal evento adverso evitável em serviços hospitalares;
- Risco de *interdição administrativa* pela Vigilância Sanitária Municipal e Estadual,
  em caso de descumprimento das normas sanitárias vigentes;
- Exposição do trabalhador da saúde a agentes biológicos, em violação à *NR-32* e
  à responsabilidade civil e trabalhista do Município;
- Impacto direto na saúde dos 34.869 habitantes atendidos pela rede municipal.

== 1.2 Identificação da Área Técnica Demandante

A área demandante é a *Secretaria Municipal de Saúde de Borba/AM*, por intermédio da
Gerência de Infraestrutura e Serviços de Saúde, responsável pela gestão dos insumos
não farmacológicos da rede assistencial, conforme organograma institucional vigente.

== 1.3 Vinculação ao Planejamento Institucional

A contratação encontra-se prevista no *Plano de Contratações Anual (PCA) — Exercício
2025*, conforme art. 12, VII, da Lei n.º 14.133/2021, e está alinhada ao objetivo
estratégico do Plano Municipal de Saúde 2022–2025: _"Garantir as condições estruturais
mínimas para o funcionamento adequado da rede de atenção à saúde, com foco na segurança
do paciente e na prevenção de doenças infecciosas."_

// ══════════════════════════════════════════════════════════════════════
= 2. Estimativa das Quantidades a Contratar
// ══════════════════════════════════════════════════════════════════════

#legalbox(titulo: "Base Legal — Art. 18, II, Lei n.º 14.133/2021")[
  O ETP deve conter a estimativa das *quantidades para a contratação*, acompanhada
  das memórias de cálculo e dos documentos que lhe dão suporte, considerando a
  interdependência com outras contratações.
]

== 2.1 Modelagem Matemática da Demanda

=== Área Total de Higienização ($A_H$)

A área total sob gestão da intendência é a soma das áreas de todas as unidades da rede:

#formulabox[
  $A_H = sum_(i=1)^(9) "UBS"_i + "Area"_"Hosp"
       = (9 times 350) + 2000 = bold(5150 space "m"^2)$
]

#figure(
  caption: [Subclassificação das áreas de higienização — Borba/AM],
  table(
    columns: (1fr, 1.2fr, 1.2fr, 2fr),
    stroke: 0.4pt + luma(180),
    fill: (col, row) => if row == 0 { navy } else if row == 3 { ltblue }
                        else if calc.odd(row) { rowalt } else { white },
    thdr[Tipo de Área], thdr[Área (m²)], thdr[% do Total], thdr[Exemplos / Unidades],
    [Crítica ($A_C$)],       tc[2.500], tc[48,5%],
      [Cirurgia, UTI, parto, urgência, expurgo — Hosp. Vó Mundoca.],
    [Não Crítica ($A_(n c)$)], tc[2.650], tc[51,5%],
      [Corredores, recepção, almoxarifado, salas de espera.],
    [*Total* ($A_H$)], tc[*5.150*], tc[*100%*], [],
  ),
)

=== Consumo Diário de Saneantes ($Q_d$)

#formulabox[
  $Q_d = (A_C / p_c + A_(n c) / p_(n c)) dot delta
       quad ["L de concentrado/dia"]$
]

Onde $p_c = 200 "m"^2\/"dia"$ (área crítica), $p_(n c) = 400 "m"^2\/"dia"$ (área
não crítica) e $delta$ é o coeficiente de diluição específico de cada produto
(ex.: $delta = 0{,}005$ para detergente enzimático a 1:200).

== 2.2 Parâmetros de Estoque — Logística Fluvial

=== Estoque de Segurança ($E S$)

A dependência exclusiva do transporte fluvial, com prazo de reposição médio
$T R = 20$ dias e $sigma_(T R) = plus.minus 4$ dias (cheia) a $plus.minus 6$ dias
(seca), impõe o cálculo estocástico:

#formulabox[
  $E S = Z dot sqrt(T R dot sigma_d^2 + overline(d)^2 dot sigma_(T R)^2)$
]

Para itens de criticidade máxima (Classe A): $Z = 3{,}09$, correspondente a
*99,9% de nível de serviço* na distribuição normal padrão.

#alertbox(titulo: "Nota Técnica — Valor de Z")[
  $Z = 3{,}09$ é o valor correto para 99,9% de disponibilidade (tabela normal padrão).
  *Não confundir* com $Z = 3{,}4$, que representa 3,4 defeitos por milhão no modelo
  Seis Sigma — métrica de qualidade de processo, inaplicável ao dimensionamento de
  estoque.
]

=== Ponto de Pedido ($P P$)

#formulabox[
  $P P = (C M M times T R_"meses") + E S$
]

Com $T R_"meses" = 20\/30 approx 0{,}667$ (período cheia) e
$T R_"meses" = 1{,}000$ mês durante a estiagem do Rio Madeira (julho–outubro).

=== Necessidade Real de Aquisição ($N_R$) — Ciclo de 12 Meses

#formulabox[
  $N_R = (C M M times 12) + E S - E_"atual"$
]

== 2.3 Quantitativos Estimados por Item

#alertbox(titulo: "Metodologia de Estimativa")[
  Os quantitativos derivam de: (i) série histórica de consumo dos últimos 12 meses;
  (ii) parâmetros leito/dia do Hospital Vó Mundoca; (iii) parâmetros m²/dia por área.
  Devem ser ratificados pelo Almoxarifado antes da publicação do edital (art. 18, §1.º).
]

#figure(
  caption: [Quantitativos estimados para o ciclo de 12 meses — teto máximo da ARP],
  table(
    columns: (0.5cm, 1fr, 1.1cm, 1.5cm, 1.6cm, 2.2cm),
    stroke: 0.4pt + luma(180),
    fill: (col, row) => if row == 0 { navy } else if calc.odd(row) { rowalt } else { white },
    thdr[Cl.], thdr[Descrição do Item],
    thdr[Un.], thdr[Qtde./mês], thdr[Qtde. anual], thdr[Preço ref. (R\$)],

    tc[*A*], [#set text(size: 9pt); Álcool Etílico 70% — frasco 500 mL],
      tc[Fr], tc[1.680], tc[20.160], tc[7,50],
    tc[*A*], [#set text(size: 9pt); Álcool Etílico 70% — galão 5 L],
      tc[Gl], tc[168], tc[2.016], tc[36,00],
    tc[*A*], [#set text(size: 9pt); Detergente Enzimático concentrado 1 L],
      tc[Fr], tc[30], tc[360], tc[42,94],
    tc[*A*], [#set text(size: 9pt); Hipoclorito de Sódio 1% — emb. 5 L],
      tc[Fr], tc[280], tc[3.360], tc[5,80],
    tc[*A*], [#set text(size: 9pt); Glutaraldeído 2% — frasco 1 L],
      tc[Fr], tc[12], tc[144], tc[65,00],
    tc[*A*], [#set text(size: 9pt); Sabonete Antisséptico clorexidina 2% 1 L],
      tc[Fr], tc[90], tc[1.080], tc[18,50],
    tc[*A*], [#set text(size: 9pt); Papel Toalha branco 2 dobras (pct 1.000 fls.)],
      tc[Pct], tc[36], tc[432], tc[22,00],
    tc[*A*], [#set text(size: 9pt); Luva de procedimento látex M (cx 100 un.)],
      tc[Cx], tc[80], tc[960], tc[38,00],
    tc[*A*], [#set text(size: 9pt); Avental descartável TNT (cx 50 un.)],
      tc[Cx], tc[30], tc[360], tc[55,00],
    tc[*B*], [#set text(size: 9pt); Saco p/ lixo infectante vermelho 100 L (rl 100 un.)],
      tc[Rl], tc[60], tc[720], tc[95,00],
    tc[*B*], [#set text(size: 9pt); Saco p/ lixo comum preto 100 L (rl 100 un.)],
      tc[Rl], tc[40], tc[480], tc[42,00],
    tc[*B*], [#set text(size: 9pt); Desinfetante quaternário de amônio 5 L],
      tc[Fr], tc[45], tc[540], tc[28,00],
    tc[*B*], [#set text(size: 9pt); Álcool Isopropílico 70% — 1 L],
      tc[Fr], tc[25], tc[300], tc[19,00],
    tc[*B*], [#set text(size: 9pt); Sabão em pó multiuso 1 kg],
      tc[Pct], tc[50], tc[600], tc[9,50],
    tc[*C*], [#set text(size: 9pt); Detergente líquido neutro 500 mL],
      tc[Fr], tc[60], tc[720], tc[3,80],
    tc[*C*], [#set text(size: 9pt); Água sanitária 2 L],
      tc[Fr], tc[120], tc[1.440], tc[5,20],
    tc[*C*], [#set text(size: 9pt); Vassoura nylon profissional],
      tc[Un], tc[12], tc[144], tc[18,00],
    tc[*C*], [#set text(size: 9pt); Rodo 60 cm — cabo alumínio],
      tc[Un], tc[10], tc[120], tc[22,00],
    tc[*C*], [#set text(size: 9pt); Pano de chão algodão 55×75 cm],
      tc[Un], tc[30], tc[360], tc[7,50],
    tc[*C*], [#set text(size: 9pt); Balde plástico 20 L],
      tc[Un], tc[5], tc[60], tc[25,00],
    tc[*C*], [#set text(size: 9pt); Esponja dupla face],
      tc[Un], tc[40], tc[480], tc[3,50],
  ),
)

#alertbox(titulo: "Nota sobre Registro de Preços")[
  A ARP não obriga o Município a adquirir o total estimado (art. 83 da Lei
  n.º 14.133/2021). As quantidades representam o *teto máximo* registrado. A
  contratação efetiva ocorrerá por ordens de fornecimento conforme a necessidade da rede.
]

// ══════════════════════════════════════════════════════════════════════
= 3. Levantamento de Mercado e Justificativa da Solução
// ══════════════════════════════════════════════════════════════════════

#legalbox(titulo: "Base Legal — Art. 18, III, Lei n.º 14.133/2021")[
  O ETP deve apresentar o *levantamento de mercado*, com a prospecção e análise das
  alternativas de solução existentes, e a justificativa técnica da solução escolhida.
]

== 3.1 Alternativas de Solução Analisadas

#figure(
  caption: [Matriz de análise das alternativas de solução],
  table(
    columns: (2.5cm, 1fr, 1fr),
    stroke: 0.4pt + luma(180),
    fill: (col, row) => if row == 0 { navy } else if row == 4 { ltblue }
                        else if calc.odd(row) { rowalt } else { white },
    thdr[Alternativa], thdr[Vantagens], thdr[Desvantagens / Inviabilidade],
    [#set text(size: 9.5pt); Contrato de Fornecimento Contínuo],
      [#set text(size: 9.5pt); Previsibilidade de preço e fornecedor.],
      [#set text(size: 9.5pt); Exige demanda certa; inflexível em quantidades; superdimensionamento frequente.],
    [#set text(size: 9.5pt); Compra Direta (dispensa)],
      [#set text(size: 9.5pt); Agilidade em emergências.],
      [#set text(size: 9.5pt); Limitada ao teto do art. 75; não supre demanda anual da rede.],
    [#set text(size: 9.5pt); Consórcio Intermunicipal],
      [#set text(size: 9.5pt); Economia de escala; redução de frete.],
      [#set text(size: 9.5pt); Inexistência de consórcio operante na região do Rio Madeira para este objeto.],
    [#set text(size: 9.5pt, weight: "bold"); Ata de Registro de Preços ✓],
      [#set text(size: 9.5pt, weight: "bold"); Flexibilidade de quantidades; preço registrado por 12 meses; compras parceladas alinhadas ao TR fluvial; recomendada pelo Ministério da Saúde.],
      [#set text(size: 9.5pt); Requer planejamento prévio robusto para estimativa das quantidades-teto.],
  ),
)

== 3.2 Justificativa da Ata de Registro de Preços

A ARP é a solução mais adequada pelos seguintes fundamentos:

+ *Adequação ao art. 82, I*: o fornecimento parcelado ao longo do exercício enquadra-se
  na hipótese de "necessidade de contratações frequentes".
+ *Flexibilidade ao ciclo hidrológico*: permite emitir ordens de fornecimento em
  volumes calibrados ao $T R$ vigente (cheia vs. seca do Rio Madeira).
+ *Economia de escala*: o preço registrado por 12 meses protege o Município contra
  a sazonalidade de preços dos insumos em Manaus no período de estiagem.
+ *Conformidade com o Ministério da Saúde*: o PAVS recomenda o uso de ARP para
  insumos de saúde em municípios de difícil acesso.

== 3.3 Pesquisa de Mercado

A pesquisa de preços foi realizada nos termos da IN SEGES/MGI n.º 65/2021 (aplicada por
analogia), mediante: (i) consulta ao *Painel de Preços do Governo Federal*; (ii) consulta
ao *BPS — Banco de Preços em Saúde* do MS; (iii) cotações diretas com *3 fornecedores*
do mercado de Manaus; (iv) análise dos contratos anteriores da SMS (2022–2024).

O valor estimado de *R\$ 2.000.000,00* resultou da média aritmética dos preços apurados,
acrescida dos custos logísticos fluviais, conforme a matriz de custo por m²:

#formulabox[
  $C_(m^2) =
    (sum_j (P_"Manaus,j" + F_"Borba,j" + "Perdas"_j) dot Q_j) / A_H$
]

// ══════════════════════════════════════════════════════════════════════
= 4. Estimativa do Valor da Contratação
// ══════════════════════════════════════════════════════════════════════

#legalbox(titulo: "Base Legal — Art. 18, IV e Art. 23, Lei n.º 14.133/2021")[
  O ETP deve trazer a estimativa do valor da contratação, por preço de mercado,
  devidamente justificada nos autos do processo administrativo.
]

#figure(
  caption: [Composição do valor estimado por classe ABC],
  table(
    columns: (1.5cm, 1fr, 2.8cm, 2cm),
    stroke: 0.4pt + luma(180),
    fill: (col, row) => if row == 0 { navy } else if row == 4 { ltblue }
                        else if calc.odd(row) { rowalt } else { white },
    thdr[Classe], thdr[Grupo de Itens], thdr[Valor Est. (R\$)], thdr[% Total],
    tc[A], [Saneantes críticos, EPI de limpeza, papel toalha hospitalar],
      tc[1.600.000,00], tc[80%],
    tc[B], [Sacos para lixo, desinfetantes, sabonetes antissépticos],
      tc[300.000,00], tc[15%],
    tc[C], [Utensílios de limpeza, água sanitária, detergente neutro],
      tc[100.000,00], tc[5%],
    tc[*Total*], [*TOTAL GERAL*], tc[*2.000.000,00*], tc[*100%*],
  ),
)

#alertbox(titulo: "Frete Fluvial Incluso — Preço CIF Borba")[
  O valor estimado já incorpora o *frete fluvial Manaus–Borba* (8–15% do preço FOB
  Manaus) e perdas de transporte (1–3%). O edital exigirá propostas em preço
  *CIF Borba*, vedada a oferta FOB Manaus, sob pena de desclassificação.
]

// ══════════════════════════════════════════════════════════════════════
= 5. Justificativa para o Parcelamento da Solução
// ══════════════════════════════════════════════════════════════════════

#legalbox(titulo: "Base Legal — Art. 18, V, Lei n.º 14.133/2021")[
  O ETP deve conter a justificativa para o *parcelamento ou não* da solução de
  contratação, conforme art. 40, §1.º da mesma Lei.
]

== 5.1 Estrutura de Lotes

A contratação será dividida em *6 lotes* por afinidade técnica e compatibilidade de
fornecimento, nos termos do art. 40, §1.º da Lei n.º 14.133/2021:

#figure(
  caption: [Estrutura de lotes proposta para o Pregão Eletrônico],
  table(
    columns: (1.2cm, 1fr, 1.5cm, 2.6cm),
    stroke: 0.4pt + luma(180),
    fill: (col, row) => if row == 0 { navy } else if row == 7 { ltblue }
                        else if calc.odd(row) { rowalt } else { white },
    thdr[Lote], thdr[Descrição], thdr[Classe], thdr[Valor Est. (R\$)],
    tc[01], [Álcoois e antissépticos para mãos e superfícies], tc[A], tc[820.000,00],
    tc[02], [Saneantes hospitalares (enzimático, glutaraldeído, hipoclorito)], tc[A], tc[480.000,00],
    tc[03], [EPI de limpeza e materiais descartáveis], tc[A], tc[300.000,00],
    tc[04], [Sacos para resíduos de saúde e comuns], tc[B], tc[180.000,00],
    tc[05], [Desinfetantes, sabonetes e complementares], tc[B], tc[120.000,00],
    tc[06], [Utensílios de limpeza e consumíveis domésticos], tc[C], tc[100.000,00],
    tc[—], [*TOTAL*], [], tc[*2.000.000,00*],
  ),
)

== 5.2 Fundamentos do Parcelamento

+ *Compatibilidade de fornecimento*: cada lote é comercializado pelos mesmos
  distribuidores, permitindo participação de empresas especializadas sem formação
  de consórcios;
+ *Viabilidade técnica e econômica*: cada lote tem dimensão suficiente para atrair
  competição de mercado (art. 40, §1.º, I);
+ *Gestão de risco*: a independência dos lotes evita que a inadimplência de um
  fornecedor comprometa toda a cadeia de suprimentos;
+ *Vedação ao fracionamento artificial*: os lotes não subdividem o objeto de forma a
  burlar os limites de dispensa de licitação (art. 34, §3.º).

// ══════════════════════════════════════════════════════════════════════
= 6. Contratações Correlatas e Interdependentes
// ══════════════════════════════════════════════════════════════════════

#legalbox(titulo: "Base Legal — Art. 18, VI, Lei n.º 14.133/2021")[
  O ETP deve identificar as contratações correlatas ou interdependentes, de modo a
  possibilitar o planejamento conjunto das contratações.
]

#figure(
  caption: [Mapeamento de contratações correlatas e interdependentes],
  table(
    columns: (1fr, 1fr, 1fr),
    stroke: 0.4pt + luma(180),
    fill: (col, row) => if row == 0 { navy } else if calc.odd(row) { rowalt } else { white },
    thdr[Contratação], thdr[Natureza da Relação], thdr[Status],
    [#set text(size: 9.5pt); Serviços de limpeza hospitalar (Hosp. Vó Mundoca)],
      [#set text(size: 9.5pt); *Interdependente*: materiais deste ETP são utilizados pelo prestador contratado],
      [#set text(size: 9.5pt); Verificar prazo de renovação],
    [#set text(size: 9.5pt); Coleta e transporte de resíduos de saúde (RSS)],
      [#set text(size: 9.5pt); *Correlata*: sacos infectantes (Lote 04) integram o fluxo de RSS],
      [#set text(size: 9.5pt); Vigente ou a contratar],
    [#set text(size: 9.5pt); Aquisição de EPI geral para trabalhadores da saúde],
      [#set text(size: 9.5pt); *Correlata*: verificar sobreposição de objeto com EPI de limpeza],
      [#set text(size: 9.5pt); Verificar sobreposição],
    [#set text(size: 9.5pt); Manutenção de equipamentos de limpeza],
      [#set text(size: 9.5pt); *Correlata*: lavadoras, aspiradores, enceradeiras],
      [#set text(size: 9.5pt); Verificar manutenção vigente],
  ),
)

#warnbox(titulo: "Vedação à Sobreposição de Objeto")[
  Antes da publicação do edital, confirmar que os itens deste ETP não estão cobertos
  por contratos vigentes, sob pena de *duplicidade de despesa* e responsabilização do
  gestor (art. 148, Lei n.º 14.133/2021).
]

// ══════════════════════════════════════════════════════════════════════
= 7. Resultados Pretendidos
// ══════════════════════════════════════════════════════════════════════

#legalbox(titulo: "Base Legal — Art. 18, VII, Lei n.º 14.133/2021")[
  O ETP deve demonstrar os *resultados pretendidos* em termos de qualidade e efetividade
  da contratação, com indicadores que possibilitem mensurar o grau de cumprimento dos
  objetivos.
]

== 7.1 Resultados Esperados

+ *Cobertura ininterrupta*: abastecimento de saneantes Classe A para os
  5.150 m² da rede durante os 12 meses da ARP, incluindo o período de estiagem;
+ *Redução de IRAS*: taxas de infecção hospitalar abaixo das metas do PNSP/MS;
+ *Conformidade sanitária*: zero não conformidades em auditorias da Visa relacionadas
  à deficiência de insumos de limpeza e higiene;
+ *Eficiência orçamentária*: custo por m² higienizado $lt.eq$ R\$ 8,50/m², com redução
  mínima de 10% frente à contratação anterior.

== 7.2 Indicadores de Desempenho (KPIs)

#figure(
  caption: [Indicadores de desempenho da contratação],
  table(
    columns: (1fr, 1fr, 1.6cm, 1.8cm),
    stroke: 0.4pt + luma(180),
    fill: (col, row) => if row == 0 { navy } else if calc.odd(row) { rowalt } else { white },
    thdr[Indicador (KPI)], thdr[Fórmula], thdr[Meta], thdr[Período],
    [#set text(size: 9.5pt); Taxa de Ruptura de Estoque],
      [#set text(size: 9.5pt); Dias em falta / Dias do período], tc[< 0,1%], tc[Mensal],
    [#set text(size: 9.5pt); Custo por m² Higienizado],
      [#set text(size: 9.5pt); Custo total / $A_H$], tc[$lt.eq$ R\$8,50], tc[Trimestral],
    [#set text(size: 9.5pt); Aderência ao Ponto de Pedido],
      [#set text(size: 9.5pt); Pedidos no prazo / Total], tc[> 95%], tc[Mensal],
    [#set text(size: 9.5pt); Perda por Validade/Deterioração],
      [#set text(size: 9.5pt); Valor descartado / Valor adquirido], tc[< 2%], tc[Semestral],
    [#set text(size: 9.5pt); Cobertura do $E S$],
      [#set text(size: 9.5pt); $E_"atual" \/ E S_"calc."$], tc[> 100%], tc[Quinzenal],
  ),
)

// ══════════════════════════════════════════════════════════════════════
= 8. Providências para Adequação do Ambiente Organizacional
// ══════════════════════════════════════════════════════════════════════

#legalbox(titulo: "Base Legal — Art. 18, VIII, Lei n.º 14.133/2021")[
  O ETP deve apontar as providências necessárias à adequação do ambiente organizacional,
  de infraestrutura e de pessoal para receber o objeto da contratação.
]

+ *Infraestrutura de armazenagem*: adequação do almoxarifado do Hospital Vó Mundoca
  (prateleiras $gt.eq$ 50 cm do solo; ventilação adequada; separação de inflamáveis e
  corrosivos — ABNT NBR 14.725 e 7.500);
+ *Capacitação*: treinamento em recebimento, verificação de registro ANVISA, controle
  FEFO (#emph[First Expiry, First Out]) e emissão de ordens de fornecimento;
+ *Sistema de controle de estoque*: atualização do módulo de insumos na SMS,
  alimentando os parâmetros $C M M$, $E S$, $P P$ e $N_R$ deste ETP;
+ *Gestor e Fiscal da ARP*: nomeação formal com publicação em Diário Oficial, nos
  termos dos arts. 117 a 120 da Lei n.º 14.133/2021;
+ *Calendário de pedidos*: elaboração de calendário anual de ordens de fornecimento,
  alinhado ao ciclo hidrológico do Rio Madeira e aos parâmetros de $P P$ calculados.

// ══════════════════════════════════════════════════════════════════════
= 9. Impossibilidade de Suprimento Interno
// ══════════════════════════════════════════════════════════════════════

#legalbox(titulo: "Base Legal — Art. 18, IX, Lei n.º 14.133/2021")[
  O ETP deve demonstrar que a necessidade não pode ser suprida pela execução direta
  por órgãos e entidades da Administração Pública.
]

O Município de Borba *não dispõe de capacidade produtiva própria* para fabricação de
saneantes, insumos químicos ou materiais de higiene. Trata-se de objeto de mercado com
ampla concorrência no segmento atacadista de Manaus, cujas empresas detêm autorização
de funcionamento pela ANVISA e estão aptas a participar de pregão eletrônico. A
contratação com terceiros é, portanto, a *única solução tecnicamente viável*.

// ══════════════════════════════════════════════════════════════════════
= 10. Análise de Riscos da Contratação
// ══════════════════════════════════════════════════════════════════════

#legalbox(titulo: "Base Legal — Art. 18, X e Anexo I, Lei n.º 14.133/2021")[
  O planejamento deve contemplar a *análise dos riscos* que possam comprometer o
  sucesso da contratação e o alcance dos resultados pretendidos.
]

#figure(
  caption: [Matriz de riscos da contratação],
  table(
    columns: (0.6cm, 1fr, 1.4cm, 1.4cm, 1.5cm, 1fr),
    stroke: 0.4pt + luma(180),
    fill: (col, row) => if row == 0 { navy } else if calc.odd(row) { rowalt } else { white },
    thdr[\#], thdr[Risco Identificado], thdr[Prob.], thdr[Impacto], thdr[Nível], thdr[Mitigação],

    tc[R1],
      [#set text(size: 8.5pt); Atraso ou suspensão de balsa no período de seca do Rio Madeira],
      tc[Alta], tc[Alto],
      [#align(center)[#text(size: 8.5pt, fill: red, weight: "bold")[Crítico]]],
      [#set text(size: 8.5pt); ERE de 60 dias para Classe A; $P P$ ajustado a $T R = 30$ dias de jul. a out.],

    tc[R2],
      [#set text(size: 8.5pt); Fornecedor sem capacidade de entrega CIF Borba],
      tc[Média], tc[Alto],
      [#align(center)[#text(size: 8.5pt, fill: rgb("#C05000"), weight: "bold")[Alto]]],
      [#set text(size: 8.5pt); Exigir comprovação de logística fluvial na habilitação.],

    tc[R3],
      [#set text(size: 8.5pt); Perda de validade por superdimensionamento ou armazenagem inadequada],
      tc[Média], tc[Médio],
      [#align(center)[#text(size: 8.5pt, fill: rgb("#C05000"), weight: "bold")[Médio]]],
      [#set text(size: 8.5pt); Sistema FEFO; limitar pedidos a 2 meses de consumo; treinamento.],

    tc[R4],
      [#set text(size: 8.5pt); Subdimensionamento dos quantitativos-teto na ARP],
      tc[Baixa], tc[Alto],
      [#align(center)[#text(size: 8.5pt, fill: rgb("#C05000"), weight: "bold")[Médio]]],
      [#set text(size: 8.5pt); Usar série histórica e parâmetros matemáticos deste ETP.],

    tc[R5],
      [#set text(size: 8.5pt); Aumento de preço acima do IPCA durante vigência da ARP],
      tc[Média], tc[Baixo],
      [#align(center)[#text(size: 8.5pt, fill: medblue, weight: "bold")[Baixo]]],
      [#set text(size: 8.5pt); Cláusula de reequilíbrio econômico-financeiro (art. 124).],

    tc[R6],
      [#set text(size: 8.5pt); Cancelamento de registro ANVISA durante a vigência],
      tc[Baixa], tc[Médio],
      [#align(center)[#text(size: 8.5pt, fill: medblue, weight: "bold")[Baixo]]],
      [#set text(size: 8.5pt); Confirmação trimestral do registro; sanção por produto irregular.],

    tc[R7],
      [#set text(size: 8.5pt); Impugnações ao edital por restrições de habilitação],
      tc[Baixa], tc[Baixo],
      [#align(center)[#text(size: 8.5pt, fill: luma(100), weight: "bold")[Mínimo]]],
      [#set text(size: 8.5pt); Adequar exigências ao mínimo necessário; submeter minuta à PGM.],
  ),
)

// ══════════════════════════════════════════════════════════════════════
= 11. Sustentabilidade e Desenvolvimento Nacional
// ══════════════════════════════════════════════════════════════════════

#legalbox(titulo: "Base Legal — Art. 11, IV, Lei n.º 14.133/2021")[
  A Administração deve considerar, nas contratações, a *promoção do desenvolvimento
  nacional sustentável*, incluindo critérios de sustentabilidade ambiental (art. 5.º
  do Decreto n.º 7.746/2012).
]

As especificações técnicas do Termo de Referência incorporarão:

- *Saneantes biodegradáveis*: preferência por produtos com laudo de biodegradabilidade
  emitido por laboratório acreditado pelo INMETRO (RDC ANVISA n.º 59/2021);
- *Embalagens com menor geração de resíduos*: preferência por refis e embalagens
  recicláveis; vedação a embalagens unitárias desnecessárias;
- *Microempresas e EPP*: aplicação dos arts. 44 e 45 da LC n.º 123/2006 (empate ficto),
  promovendo o desenvolvimento econômico local e regional;
- *Destinação de embalagens*: obrigação contratual de recolha e destinação
  ambientalmente adequada (Lei n.º 12.305/2010 — PNRS).

// ══════════════════════════════════════════════════════════════════════
= 12. Modalidade, Tipo de Licitação e Regime de Execução
// ══════════════════════════════════════════════════════════════════════

#figure(
  caption: [Configuração da licitação],
  table(
    columns: (4cm, 1fr),
    stroke: 0.5pt + luma(190),
    fill: (col, row) => if col == 0 { ltblue } else if calc.odd(row) { rowalt } else { white },
    [#text(weight: "bold", fill: navy, size: 9.5pt)[Modalidade]],
      [Pregão Eletrônico (art. 17 c/c art. 28, I)],
    [#text(weight: "bold", fill: navy, size: 9.5pt)[Critério de julgamento]],
      [Menor Preço (art. 33, I)],
    [#text(weight: "bold", fill: navy, size: 9.5pt)[Modo de disputa]],
      [Aberto (art. 56, I) — lances sucessivos com intervalo mínimo de 30 s],
    [#text(weight: "bold", fill: navy, size: 9.5pt)[Instrumento]],
      [Ata de Registro de Preços (art. 82)],
    [#text(weight: "bold", fill: navy, size: 9.5pt)[Vigência da ARP]],
      [12 meses, prorrogável por igual período (art. 84, §1.º)],
    [#text(weight: "bold", fill: navy, size: 9.5pt)[Regime de execução]],
      [Fornecimento parcelado mediante ordens de fornecimento emitidas pelo órgão gerenciador],
    [#text(weight: "bold", fill: navy, size: 9.5pt)[Participação]],
      [Ampla; ME/EPP com benefícios da LC n.º 123/2006],
    [#text(weight: "bold", fill: navy, size: 9.5pt)[Sistema eletrônico]],
      [PNCP — Portal Nacional de Contratações Públicas (art. 174)],
  ),
)

// ══════════════════════════════════════════════════════════════════════
= 13. Requisitos de Habilitação
// ══════════════════════════════════════════════════════════════════════

Em conformidade com os arts. 62 a 70 da Lei n.º 14.133/2021, são requisitos mínimos:

+ *Jurídica*: ato constitutivo, estatuto ou contrato social em vigor;
+ *Fiscal e Trabalhista*: certidões negativas de débitos federais, estaduais, municipais,
  FGTS e trabalhistas (TST);
+ *Técnica*:
  - Autorização de Funcionamento expedida pela ANVISA para distribuição de saneantes
    (Lotes 01 a 05);
  - Comprovação de capacidade logística fluvial para entrega em Borba/AM (carta ou
    contrato com empresa de navegação que opere no trecho Manaus–Borba);
  - Atestado de capacidade técnica em objeto compatível em características e quantidades
    (art. 67, I);
+ *Econômico-financeira*: capital social ou patrimônio líquido mínimo de 10% do valor
  do lote (art. 69, I); certidão negativa de falência.

#warnbox(titulo: "Registro ANVISA — Habilitação Técnica Obrigatória")[
  Nos termos da Lei n.º 6.360/1976 e RDC ANVISA n.º 59/2021, *todos* os saneantes dos
  Lotes 01 a 05 devem possuir registro ou notificação ANVISA vigente. A entrega de
  produto com registro vencido ou inexistente configura infração sanitária e enseja:
  (i) rescisão unilateral da Ata; (ii) sanção ao fornecedor (art. 156); e
  (iii) responsabilização do agente público que atestou o recebimento.
]

// ══════════════════════════════════════════════════════════════════════
= 14. Declaração de Viabilidade da Contratação
// ══════════════════════════════════════════════════════════════════════

#legalbox(titulo: "Base Legal — Art. 18, §3.º, Lei n.º 14.133/2021")[
  O ETP deverá concluir com a *declaração de viabilidade ou inviabilidade* da
  contratação. Concluindo pela viabilidade, deverá indicar a solução mais vantajosa.
]

#conclusabox[
  #align(center)[
    #text(size: 13pt, weight: "bold", fill: navy)[DECLARAÇÃO DE VIABILIDADE]
  ]
  #v(0.5em)

  Com base nas análises realizadas neste Estudo Técnico Preliminar, conclui-se pela
  *VIABILIDADE* da contratação, pelos seguintes fundamentos:

  + A necessidade é *real, urgente e continuada*, derivando de obrigação legal
    irrenunciável de manutenção da salubridade da rede de saúde que atende 34.869
    habitantes;
  + A solução via *Ata de Registro de Preços — Pregão Eletrônico* é a mais adequada,
    flexível e economicamente vantajosa para a realidade logística fluvial de Borba/AM;
  + A pesquisa de preços atesta a existência de *mercado competitivo* compatível com o
    orçamento de R\$ 2.000.000,00 (dois milhões de reais);
  + Os riscos foram identificados e suas mitigações planejadas, incluindo o
    *Estoque de Reserva Estratégica (ERE)* para o período de estiagem do Rio Madeira;
  + A contratação atende aos princípios da *eficiência, economicidade e
    sustentabilidade* exigidos pela Lei n.º 14.133/2021.

  #v(0.5em)
  *Solução mais vantajosa:* Pregão Eletrônico, modo aberto, julgamento por menor preço,
  dividido em 6 lotes, com Ata de Registro de Preços de 12 meses prorrogáveis,
  com entrega *CIF Borba/AM*.
]

#v(2cm)

// ── Assinaturas ───────────────────────────────────────────────────────
#grid(
  columns: (1fr, 1fr),
  column-gutter: 2cm,
  align(center)[
    #line(length: 100%, stroke: 0.5pt + luma(120))
    #v(0.3em)
    *\[Nome e Cargo\]*\
    Responsável pela Elaboração do ETP\
    #text(size: 9pt)[Matrícula: ________________]\
    #text(size: 9pt)[Secretaria Municipal de Saúde de Borba/AM]
  ],
  align(center)[
    #line(length: 100%, stroke: 0.5pt + luma(120))
    #v(0.3em)
    *\[Nome e Cargo\]*\
    Autoridade Competente — Aprovação\
    #text(size: 9pt)[Matrícula: ________________]\
    #text(size: 9pt)[Secretaria Municipal de Saúde de Borba/AM]
  ],
)

#v(1cm)
#align(right)[Borba/AM, 2025]

#v(1.5cm)
#line(length: 100%, stroke: 0.4pt + luma(200))
#v(0.3em)
#text(size: 8pt, fill: luma(110))[
  *Referências normativas:* Lei n.º 14.133/2021 (NLLCA) • Decreto n.º 11.462/2023 (SRP) •
  IN SEGES/MGI n.º 65/2021 • RDC ANVISA n.º 15/2012 • RDC ANVISA n.º 59/2021 •
  RDC ANVISA n.º 216/2004 • NR-32 (MTE) • LC n.º 123/2006 • Lei n.º 6.360/1976 •
  Lei n.º 12.305/2010 (PNRS) • ABNT NBR 7.500 e 7.501.
]
