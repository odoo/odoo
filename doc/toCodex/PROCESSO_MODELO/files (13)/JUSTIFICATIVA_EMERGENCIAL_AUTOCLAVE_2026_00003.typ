// ═══════════════════════════════════════════════════════════════════════════
//  JUSTIFICATIVA DE SITUAÇÃO EMERGENCIAL
//  Aquisição de Autoclave Hospitalar — CME — Hospital Central de Borba
//  Processo: 2026.00003 — Dispensa de Licitação, Art. 75, VIII, Lei 14.133/2021
// ═══════════════════════════════════════════════════════════════════════════

// ── Cores institucionais ────────────────────────────────────────────────────
#let navy     = rgb("#1A3A5C")
#let medblue  = rgb("#2E75B6")
#let ltblue   = rgb("#D6E4F0")
#let rowalt   = rgb("#EBF3FB")
#let legalbg  = rgb("#F0FDF4")
#let legalbdr = rgb("#16A34A")
#let alertbg  = rgb("#FFF8E1")
#let alertbdr = rgb("#E59C0A")
#let warnbg   = rgb("#FEF2F2")
#let warnbdr  = rgb("#DC2626")
#let infobg   = rgb("#EFF6FF")
#let infobdr  = rgb("#3B82F6")
#let white    = rgb("#FFFFFF")
#let corrbg   = rgb("#FFF0F6")
#let corrbdr  = rgb("#9333EA")

// ── Caixa colorida genérica ─────────────────────────────────────────────────
#let caixa(titulo, cor-fundo, cor-borda, corpo) = block(
  width: 100%,
  fill: cor-fundo,
  stroke: (paint: cor-borda, thickness: 0.8pt),
  radius: 4pt,
  inset: (top: 18pt, left: 12pt, right: 12pt, bottom: 10pt),
)[
  #place(top + left, dy: -12pt, dx: 10pt)[
    #box(fill: cor-fundo, stroke: (paint: cor-borda, thickness: 0.6pt),
         radius: 3pt, inset: (x: 6pt, y: 3pt))[
      #text(fill: cor-borda, weight: "bold", size: 9pt)[#titulo]
    ]
  ]
  #text(size: 10.5pt)[#corpo]
]

#let legal(titulo, corpo)  = caixa(titulo, legalbg, legalbdr, corpo)
#let alerta(titulo, corpo) = caixa(titulo, alertbg, alertbdr, corpo)
#let aviso(titulo, corpo)  = caixa(titulo, warnbg,  warnbdr,  corpo)
#let info(titulo, corpo)   = caixa(titulo, infobg,  infobdr,  corpo)
#let nota(titulo, corpo)   = caixa(titulo, corrbg,  corrbdr,  corpo)

// ── Página ──────────────────────────────────────────────────────────────────
#set page(
  paper: "a4",
  margin: (top: 2.8cm, bottom: 2.8cm, left: 3.2cm, right: 2.5cm),
  header: context {
    if counter(page).get().first() > 1 [
      #set text(size: 8pt, fill: navy)
      #grid(
        columns: (1fr, auto),
        [*Justificativa de Situação Emergencial* — Autoclave Hospitalar — Processo 2026.00003],
        [Art. 75, VIII — Lei 14.133/2021],
      )
      #line(length: 100%, stroke: (paint: medblue, thickness: 0.5pt))
    ]
  },
  footer: context {
    if counter(page).get().first() > 1 [
      #set text(size: 8pt, fill: luma(100))
      #align(center)[
        Página #counter(page).display() de #counter(page).final().first()
      ]
    ]
  },
)

#set text(font: "Liberation Serif", size: 11.5pt, lang: "pt")
#set par(justify: true, leading: 0.7em)
#set list(indent: 1.2em, spacing: 0.5em)
#set enum(indent: 1.2em, spacing: 0.5em)

// ── Headings ────────────────────────────────────────────────────────────────
#show heading.where(level: 1): it => {
  v(16pt)
  block(width: 100%)[
    #text(fill: navy, size: 12.5pt, weight: "bold")[#it.body]
    #line(length: 100%, stroke: (paint: navy, thickness: 0.6pt))
  ]
  v(6pt)
}

#show heading.where(level: 2): it => {
  v(10pt)
  text(fill: medblue, size: 11.5pt, weight: "bold")[#it.body]
  v(4pt)
}

#show heading.where(level: 3): it => {
  v(8pt)
  text(fill: navy, size: 11pt, weight: "bold", style: "italic")[#it.body]
  v(3pt)
}

// ───────────────────────────────────────────────────────────────────────────
//  FOLHA DE ROSTO
// ───────────────────────────────────────────────────────────────────────────
#page(
  header: none,
  footer: none,
  background: rect(fill: navy, width: 100%, height: 100%),
)[
  #set text(fill: white)
  #v(2.5cm)
  #align(center)[
    #text(size: 10pt, fill: ltblue, weight: "bold")[
      PREFEITURA MUNICIPAL DE BORBA — ESTADO DO AMAZONAS
    ]
    #v(2pt)
    #text(size: 9pt, fill: rgb("#A8C4E0"))[
      SECRETARIA MUNICIPAL DE SAÚDE
    ]
    #v(0.6cm)
    #line(length: 85%, stroke: (paint: rgb("#5B8DB8"), thickness: 0.8pt))
    #v(0.8cm)

    #text(size: 10.5pt, fill: rgb("#A8C4E0"), weight: "bold")[
      DISPENSA DE LICITAÇÃO — ART. 75, VIII, LEI N.º 14.133/2021
    ]
    #v(0.3cm)
    #text(size: 9.5pt, fill: rgb("#7BAFD4"))[
      Processo Administrativo n.º 2026.00003
    ]
    #v(0.8cm)

    #text(size: 26pt, weight: "bold", fill: white)[
      JUSTIFICATIVA DE\
      SITUAÇÃO EMERGENCIAL
    ]
    #v(0.3cm)
    #text(size: 14pt, fill: rgb("#A8C4E0"))[
      Aquisição de Autoclave Hospitalar a Vapor\
      Central de Material e Esterilização — CME
    ]
    #v(0.8cm)
    #line(length: 85%, stroke: (paint: rgb("#5B8DB8"), thickness: 0.8pt))
    #v(1.2cm)

    #block(width: 78%)[
      #grid(
        columns: (auto, 1fr),
        column-gutter: 12pt,
        row-gutter: 8pt,
        text(fill: rgb("#7BAFD4"), weight: "bold", size: 9.5pt)[Unidade demandante:],
        text(fill: ltblue, size: 9.5pt)[Secretaria Municipal de Saúde — CME],
        text(fill: rgb("#7BAFD4"), weight: "bold", size: 9.5pt)[Responsável:],
        text(fill: ltblue, size: 9.5pt)[Cíntia Felipe Roque],
        text(fill: rgb("#7BAFD4"), weight: "bold", size: 9.5pt)[Valor estimado:],
        text(fill: ltblue, size: 9.5pt)[R\$ 200.000,00 (duzentos mil reais)],
        text(fill: rgb("#7BAFD4"), weight: "bold", size: 9.5pt)[Fonte de recursos:],
        text(fill: ltblue, size: 9.5pt)[Emenda Parlamentar Estadual — ALEAM],
        text(fill: rgb("#7BAFD4"), weight: "bold", size: 9.5pt)[Data do relatório-base:],
        text(fill: ltblue, size: 9.5pt)[05 de março de 2026],
        text(fill: rgb("#7BAFD4"), weight: "bold", size: 9.5pt)[Elaborado em:],
        text(fill: ltblue, size: 9.5pt)[Borba/AM, 15 de março de 2026],
      )
    ]

    #v(1fr)
    #line(length: 85%, stroke: (paint: rgb("#3A5A7C"), thickness: 0.5pt))
    #v(0.3cm)
    #text(size: 7.5pt, fill: rgb("#5A7A9A"))[
      Documento elaborado nos termos dos arts. 72 e 75, VIII, da Lei n.º 14.133/2021 •
      RDC ANVISA 15/2012 • ISO 17665-1:2006 • EN 285:2015
    ]
    #v(0.5cm)
  ]
]

// ───────────────────────────────────────────────────────────────────────────
//  QUADRO DE IDENTIFICAÇÃO
// ───────────────────────────────────────────────────────────────────────────
#v(0.3cm)
#block(width: 100%,
  fill: navy,
  radius: (top: 4pt, bottom: 0pt),
  inset: (x: 12pt, y: 7pt),
)[
  #text(fill: white, weight: "bold", size: 10.5pt)[QUADRO DE IDENTIFICAÇÃO DO PROCESSO]
]
#block(width: 100%,
  fill: rgb("#F4F8FB"),
  stroke: (paint: navy, thickness: 0.5pt),
  radius: (top: 0pt, bottom: 4pt),
  inset: 0pt,
)[
  #let campo(label, valor, fundo) = grid(
    columns: (4.8cm, 1fr),
    block(fill: fundo, inset: (x: 10pt, y: 7pt), width: 100%)[
      #text(fill: navy, weight: "bold", size: 9.5pt)[#label]
    ],
    block(fill: white, inset: (x: 10pt, y: 7pt), width: 100%)[
      #text(size: 9.5pt)[#valor]
    ],
  )
  #campo("Processo:", "2026.00003", rowalt)
  #campo("Unidade solicitante:", "Secretaria Municipal de Saúde — Borba/AM", white)
  #campo("Setor / local:", "Central de Material e Esterilização (CME) — Hospital Central de Borba", rowalt)
  #campo("Responsável pela elaboração:", "Cíntia Felipe Roque", white)
  #campo("Objeto:", "Aquisição de autoclave hospitalar a vapor, tipo B (pré-vácuo), horizontal, câmara ≥ 100 L, com periféricos, logística CIF Borba/AM, qualificações QI/QO/QD e treinamento", rowalt)
  #campo("Equipamento inoperante (substituído):", "Autoclave nº 6897 — Phoenix Luferco — fab. 2019 (~6 anos de uso)", white)
  #campo("Fundamentação legal:", "Art. 75, VIII, Lei n.º 14.133/2021 — Dispensa por Emergência", rowalt)
  #campo("Fonte de recursos:", "Emenda Parlamentar Estadual — Assembleia Legislativa do Amazonas", white)
  #campo("Valor estimado:", "R\$ 200.000,00 (duzentos mil reais)", rowalt)
  #campo("Data do relatório técnico-base:", "05 de março de 2026", white)
]

#v(1em)

// ───────────────────────────────────────────────────────────────────────────
= 1. Fundamento Legal
// ───────────────────────────────────────────────────────────────────────────

#legal("Art. 75, VIII, Lei n.º 14.133/2021")[
  _"É dispensável a licitação: [...] *VIII* — nos casos de emergência ou de calamidade pública, quando caracterizada urgência de atendimento de situação que possa ocasionar prejuízo ou comprometer a continuidade dos serviços públicos ou a segurança de pessoas, obras, serviços, equipamentos e outros bens, públicos ou particulares, e somente para os bens necessários ao atendimento da situação emergencial ou calamitosa e às parcelas de obras e serviços que possam ser concluídas no prazo máximo de 1 (um) ano [...]"_
]

#v(0.5em)

A presente Justificativa de Situação Emergencial fundamenta-se no art. 75, VIII, da Lei Federal n.º 14.133, de 1.º de abril de 2021 (Nova Lei de Licitações e Contratos Administrativos), que autoriza a dispensa de licitação em situações de emergência caracterizada pela urgência de atendimento que possa comprometer a continuidade de serviço público essencial ou a segurança de pessoas.

Os elementos fáticos descritos nas seções seguintes demonstram o preenchimento *cumulativo* dos três requisitos legais que legitimam a contratação direta:

+ *Situação emergencial concreta e documentada*, não provocada por omissão ou desídia da Administração;
+ *Risco direto à segurança de pacientes e profissionais de saúde*, decorrente da falha sistêmica irreversível do equipamento; e
+ *Objeto delimitado ao estritamente necessário* ao atendimento da emergência, sem excesso ou superdimensionamento.

// ───────────────────────────────────────────────────────────────────────────
= 2. Fato Gerador — O Equipamento e Sua Falha
// ───────────────────────────────────────────────────────────────────────────

== 2.1 Identificação do Equipamento em Operação

O Hospital Central de Borba dispõe de *uma única autoclave hospitalar* instalada na sua Central de Material e Esterilização (CME). Trata-se do equipamento descrito a seguir:

#v(0.4em)
#block(width: 100%, fill: rgb("#F4F8FB"),
  stroke: (paint: medblue, thickness: 0.5pt), radius: 4pt, inset: 0pt)[
  #let li(l, v, alt) = grid(
    columns: (4.5cm, 1fr),
    block(fill: if alt { rowalt } else { white }, inset: (x:10pt, y:6pt), width:100%)[
      #text(fill:navy, weight:"bold", size:9.5pt)[#l]],
    block(fill: white, inset: (x:10pt, y:6pt), width:100%)[
      #text(size:9.5pt)[#v]],
  )
  #li("Número de patrimônio:", "6897", true)
  #li("Fabricante:", "Phoenix Luferco", false)
  #li("Ano de fabricação:", "2019 (aproximadamente 6 anos de uso)", true)
  #li("Tipo:", "Autoclave hospitalar a vapor — câmara única", false)
  #li("Localização:", "CME — Hospital Central de Borba", true)
  #li("Status atual:", [#text(fill: warnbdr, weight: "bold")[INOPERANTE — falha sistêmica múltipla]], false)
  #li("Laudo técnico:", "Relatório formal lavrado pelo Diretor Hospitalar Daniel Gomes Vinhote (Decreto n.º 0630/2026), conforme Anexo I deste processo", true)
]

#v(0.8em)

== 2.2 Descrição Técnica das Falhas Identificadas

O diagnóstico técnico, formalizado pelo Diretor Hospitalar em relatório datado de 05 de março de 2026, identificou as seguintes falhas, todas de natureza grave e com impacto direto na segurança do processo de esterilização:

#v(0.4em)
#block(width: 100%, stroke: (paint: warnbdr, thickness: 0.8pt),
  fill: rgb("#FFF9F9"), radius: 4pt, inset: (top:18pt, x:12pt, bottom:10pt))[
  #place(top+left, dy:-12pt, dx:10pt)[
    #box(fill: rgb("#FFF9F9"), stroke: (paint:warnbdr, thickness:0.6pt),
         radius:3pt, inset:(x:6pt,y:3pt))[
      #text(fill:warnbdr, weight:"bold", size:9pt)[Falhas Sistêmicas Identificadas — Autoclave nº 6897]
    ]
  ]

  #let falha(num, titulo, corpo) = {
    grid(
      columns: (1.4cm, 1fr),
      column-gutter: 8pt,
      box(fill: warnbdr, radius: 50%, width: 1.2cm, height: 1.2cm, inset: 0pt)[
        #align(center+horizon)[#text(fill:white, weight:"bold", size:11pt)[#num]]
      ],
      block(inset: (y: 4pt))[
        #text(weight:"bold", fill:navy)[#titulo]\
        #text(size:10.5pt)[#corpo]
      ]
    )
    v(6pt)
  }

  #falha("F1", "Salto de etapas do ciclo de esterilização",
    [O equipamento transita diretamente da fase de esterilização para a fase de secagem sem concluir o processo de forma íntegra. Essa falha invalida a garantia de esterilização, pois o tempo de _plateau_ — exposição contínua na temperatura alvo — não é respeitado, impedindo o alcance do *Nível de Garantia de Esterilidade (SAL) de 10⁻⁶*, exigido pela RDC ANVISA 15/2012.])

  #falha("F2", "Não atingimento da temperatura mínima de esterilização",
    [A autoclave falha em alcançar a temperatura de *134 °C ± 1 °C* prevista para ciclos de pré-vácuo com artigos porosos. A validação da esterilidade a vapor é matematicamente expressa pelo *Valor F₀*:
    #v(4pt)
    #align(center)[
      #box(fill: rgb("#F0F4FF"), stroke: (paint:medblue, thickness:0.5pt), radius:3pt, inset:8pt)[
        $ F_0 = integral_0^t 10^((T - 121.1)/z) dif t $
        #v(3pt)
        #text(size:9pt, fill:luma(50))[onde _T_ = temperatura instantânea (°C), _z_ = 10 °C (_G. stearothermophilus_)]
      ]
    ]
    #v(4pt)
    Com temperatura insuficiente, o F₀ calculado é sistematicamente inferior ao mínimo de *15 minutos* exigido, tornando os artigos processados microbiologicamente inseguros.])

  #falha("F3", "Falha no sistema hidráulico de abastecimento automático",
    [O sistema de entrada de água autônoma está inoperante, exigindo intervenção manual a cada ciclo. Isso compromete: (i) a *padronização dos ciclos* (cada operador intervém de forma diferente); (ii) a *rastreabilidade do processo* (RDC 15/2012, art. 34); e (iii) a *segurança do operador*, exposto ao risco de queimaduras durante a manipulação de componentes aquecidos.])

  #falha("F4", "Instabilidade geral — falha sistêmica múltipla",
    [O comportamento errático do equipamento ao longo dos ciclos, com parâmetros de pressão e temperatura inconsistentes, é indicativo de falha simultânea em múltiplos subsistemas (controle eletrônico, sensores, válvulas). A coexistência de F1, F2 e F3 descarta a hipótese de pane isolada e confirma a degradação sistêmica do equipamento.])
]

// ───────────────────────────────────────────────────────────────────────────
= 3. Caracterização da Situação de Emergência
// ───────────────────────────────────────────────────────────────────────────

== 3.1 Impactos Operacionais Imediatos

A inoperância da única autoclave do CME produz impactos diretos e imediatos na operação assistencial do Hospital Central de Borba, de forma que não podem ser supridos por solução alternativa interna:

- *Redução crítica da capacidade de esterilização* de instrumentais médico-cirúrgicos utilizados em cirurgias, curativos, procedimentos invasivos e emergências do pronto-socorro;
- *Risco de desabastecimento de materiais esterilizados* para todos os setores assistenciais, incluindo centro cirúrgico, pronto-socorro, UTI (quando operacional) e unidades de internação;
- *Impossibilidade de garantia da eficácia do processo* de esterilização, com risco concreto de utilização de artigos inadequadamente estéreis — violação direta dos arts. 5.º, 6.º e 34 da *RDC ANVISA n.º 15/2012*;
- *Exposição dos profissionais de saúde* a materiais potencialmente contaminados durante o processo de reprocessamento manual emergencial.

== 3.2 Risco Sanitário Direto ao Paciente

O processamento inadequado de artigos críticos e semicríticos é a principal causa de *Infecções Relacionadas à Assistência à Saúde (IRAS)* de origem instrumental. No contexto específico do Hospital Central de Borba, hospital de referência para uma população de *34.869 habitantes* (IBGE 2025) em área de acesso predominantemente fluvial, a ausência de esterilização adequada tem consequências amplificadas:

#alerta("Cadeia Causal de Risco — Falha de Esterilização → Dano ao Paciente")[
  *Falha sistêmica do equipamento* → processamento com SAL >  10⁻⁶ → *artigo crítico microbiologicamente inseguro* → contato com sítio cirúrgico ou tecido estéril → *Infecção de Sítio Cirúrgico (ISC)* ou IRAS sistêmica → morbidade, internação prolongada, sepse, *óbito evitável*.

  No interior do Amazonas, onde o tempo de acesso a centros de referência em Manaus pode superar 24 horas por via fluvial, a evolução de uma ISC grave sem tratamento imediato disponível configura *risco de morte* diretamente atribuível à falha de esterilização.
]

#v(0.5em)

A magnitude do risco é classificada na seguinte matriz:

#v(0.4em)
#table(
  columns: (3.5cm, 2.5cm, 2.5cm, 2.5cm, 2.5cm),
  fill: (x, y) => {
    if y == 0 { navy }
    else if x == 0 { rowalt }
    else if (x == 4 and y >= 3) or (x == 3 and y == 4) or (x == 4 and y == 4) { rgb("#FECACA") }
    else if (x == 3 and y == 3) or (x == 2 and y == 4) { rgb("#FED7AA") }
    else { white }
  },
  stroke: (paint: luma(200), thickness: 0.4pt),
  inset: (x: 8pt, y: 7pt),
  // Header
  table.header(
    text(fill: white, weight: "bold", size: 9pt)[Probabilidade ↓ \ Impacto →],
    text(fill: white, weight: "bold", size: 9pt)[Insignificante],
    text(fill: white, weight: "bold", size: 9pt)[Moderado],
    text(fill: white, weight: "bold", size: 9pt)[Grave],
    text(fill: white, weight: "bold", size: 9pt)[Catastrófico],
  ),
  // Rows
  text(weight: "bold", size: 9pt)[Improvável], [], [], [], [],
  text(weight: "bold", size: 9pt)[Possível], [], [], [], [],
  text(weight: "bold", size: 9pt)[Provável], [], [],
    box(fill: warnbdr, radius: 3pt, inset: (x:5pt, y:3pt))[
      #text(fill: white, size: 8pt, weight: "bold")[★ ISC GRAVE]
    ],
    [],
  text(weight: "bold", size: 9pt)[Quase Certa], [], [],
    box(fill: rgb("#EA580C"), radius: 3pt, inset: (x:5pt, y:3pt))[
      #text(fill: white, size: 8pt, weight: "bold")[★ IRAS/SEPSE]
    ],
    box(fill: warnbdr, radius: 3pt, inset: (x:5pt, y:3pt))[
      #text(fill: white, size: 8pt, weight: "bold")[★ ÓBITO]
    ],
)
#text(size: 8.5pt, fill: luma(90))[★ Posicionamento do risco: probabilidade "Quase Certa/Provável" × impacto "Grave/Catastrófico" — Zona Vermelha — exige ação imediata.]

#v(0.8em)

== 3.3 Impossibilidade de Aguardar o Rito Licitatório Regular

A realização de Pregão Eletrônico — modalidade regular para aquisição deste bem — demandaria, em condições normais, o seguinte prazo mínimo:

#v(0.4em)
#table(
  columns: (1fr, 2.2cm, 4cm),
  fill: (x, y) => {
    if y == 0 { navy }
    else if calc.even(y) { rowalt }
    else { white }
  },
  stroke: (paint: luma(200), thickness: 0.4pt),
  inset: (x: 8pt, y: 7pt),
  table.header(
    text(fill: white, weight: "bold", size: 9.5pt)[Etapa],
    text(fill: white, weight: "bold", size: 9.5pt)[Prazo Mín.],
    text(fill: white, weight: "bold", size: 9.5pt)[Observação],
  ),
  [ETP + TR + pesquisa de preços], [15 dias], [Já concluídos],
  [Elaboração e revisão do edital (CPL + PGM)], [10 dias], [],
  [Publicação no PNCP até abertura], [8 dias], [Art. 55, § 2.º],
  [Prazo de propostas + sessão + habilitação], [15 dias], [],
  [Recursos + homologação + assinatura], [10 dias], [],
  [Prazo de entrega — período de seca], [90 dias], [Ago–Nov: balsas de menor calado],
  table.cell(
    fill: rgb("#FEF2F2"),
    colspan: 1,
  )[#text(weight: "bold", fill: warnbdr)[TOTAL ATÉ ENTREGA TÉCNICA]],
  table.cell(fill: rgb("#FEF2F2"))[
    #text(weight: "bold", fill: warnbdr)[≈ 148 dias]
  ],
  table.cell(fill: rgb("#FEF2F2"))[
    #text(weight: "bold", fill: warnbdr)[Quase 5 meses sem esterilização segura]
  ],
)

#v(0.5em)

Cinco meses de operação hospitalar sem autoclave funcional, em um hospital de referência regional, configura risco inaceitável à vida humana e à continuidade de serviço público essencial — incompatível com qualquer interpretação razoável do princípio da eficiência (CF/88, art. 37) e do dever de cautela sanitária.

// ───────────────────────────────────────────────────────────────────────────
= 4. Inviabilidade da Manutenção Corretiva
// ───────────────────────────────────────────────────────────────────────────

== 4.1 Análise Técnica da Reparabilidade

A natureza *múltipla e sistêmica* das falhas identificadas (F1 a F4) torna a manutenção corretiva economicamente inviável e tecnicamente insuficiente como solução definitiva. Essa conclusão repousa nos seguintes fundamentos:

+ *Falha sistêmica simultânea em subsistemas críticos*: a coexistência de falhas no sistema de controle de ciclos (F1), no sistema térmico (F2), no sistema hidráulico (F3) e na estabilidade operacional geral (F4) indica degradação estrutural do equipamento, não falha pontual reparável;

+ *Critério de obsolescência funcional*: o equipamento tem *aproximadamente 6 anos de uso* em CME hospitalar de média complexidade com alta rotatividade de ciclos. O horizonte de vida útil de autoclaves deste padrão é de 10 a 15 anos, mas falhas sistêmicas múltiplas antes do décimo ano indicam degradação acelerada, provavelmente agravada pelas condições de umidade relativa elevada (UR ≥ 80%) características do clima amazônico;

+ *Custo de reparo x valor de substituição*: a restauração de quatro subsistemas (eletrônico, térmico, hidráulico e estrutural) em equipamento desta natureza, no interior do Amazonas, representa custo estimado superior a *60–75% do valor de um equipamento novo*, sem garantia de desempenho equivalente e sem recomposição do período de garantia — o que inviabiliza economicamente a opção pelo reparo;

+ *Ausência de garantia de desempenho pós-reparo*: mesmo reparado, o equipamento não seria submetido a novo processo de *qualificação documentada (QI/QO/QD)* com resultados auditáveis, mantendo a incerteza sobre o SAL efetivamente alcançado.

== 4.2 Ausência de Equipamento Substituto Interno

O Hospital Central de Borba não dispõe de autoclave reserva ou de acordo com outra unidade de saúde do município para esterilização emergencial. A esterilização terceirizada em Manaus, única alternativa disponível, implica *interrupção de 4 a 7 dias por remessa*, incompatível com a rotina cirúrgica e com a assistência de urgência e emergência.

#info("Por que esta situação não foi provocada por omissão da Administração")[
  A Lei 14.133/2021 e a jurisprudência do TCU/TCE-AM exigem que a emergência *não seja decorrente de negligência ou omissão* do gestor público. No presente caso: (i) o equipamento foi adquirido regularmente em 2019; (ii) a falha sistêmica apresentou-se de forma progressiva e tecnicamente imprevisível em horizonte inferior ao esperado; (iii) a Emenda Parlamentar destinada à substituição foi aprovada pela ALEAM e está disponível. O gestor agiu de forma diligente ao identificar e documentar a falha tempestivamente.
]

// ───────────────────────────────────────────────────────────────────────────
= 5. Especificação Técnica Justificada
// ───────────────────────────────────────────────────────────────────────────

A especificação foi elaborada com base nas normas regulatórias aplicáveis (RDC ANVISA n.º 15/2012; ISO 17665-1:2006; EN 285:2015), nas características operacionais do CME do Hospital Central de Borba (40 leitos, procedimentos cirúrgicos de urgência e eletivos) e nas condições ambientais da região amazônica.

#v(0.4em)
#table(
  columns: (4.5cm, 1fr),
  fill: (x, y) => {
    if y == 0 { navy }
    else if calc.even(y) { rowalt }
    else { white }
  },
  stroke: (paint: luma(200), thickness: 0.4pt),
  inset: (x: 8pt, y: 7pt),
  table.header(
    text(fill: white, weight: "bold", size: 9.5pt)[Especificação],
    text(fill: white, weight: "bold", size: 9.5pt)[Requisito Mínimo e Justificativa],
  ),
  [*Tipo*],
  [Autoclave hospitalar a vapor saturado, *Tipo B (pré-vácuo)*, horizontal — obrigatório para artigos porosos (campos, uniformes) e artigos com lúmens (RDC 15/2012, art. 15)],
  [*Capacidade mínima da câmara*],
  [*100 litros* — dimensionamento proporcional ao volume cirúrgico de hospital de 40 leitos; equipamento < 100 L geraria ciclos excessivos; > 250 L configuraria superdimensionamento e consumo elétrico incompatível com a rede local],
  [*Material da câmara*],
  [Aço inoxidável *AISI 316L*, polido internamente — resistência superior a cloretos (presente na água do Rio Madeira) e à umidade relativa ≥ 80% do clima amazônico],
  [*Sistema de vácuo*],
  [Bomba de anel líquido; pressão absoluta ≤ 30 mbar; *mínimo 3 pulsos* alternados de vácuo e vapor — único método eficaz para remoção de ar em materiais porosos e lúmens (EN 285:2015, item 8)],
  [*Temperatura e precisão*],
  [105 °C a 135 °C com precisão de *±1 °C* — necessária para atingir F₀ ≥ 15 min e SAL 10⁻⁶ em todos os ciclos (ISO 17665-1:2006)],
  [*Programas pré-configurados*],
  [Mínimo *13 programas*, incluindo: poroso 134 °C, sólido 134 °C, líquido 121 °C, Bowie-Dick e Leak Test — cobertura completa dos artigos processados no CME],
  [*Interface e rastreabilidade*],
  [Tela colorida *touchscreen*, gestão de usuários com senha, *impressora integrada* de etiquetas de ciclo — atende à rastreabilidade exigida pelo art. 34 da RDC ANVISA 15/2012],
  [*Registro eletrônico*],
  [Memória interna de ciclos + saída USB — exportação de relatórios para auditoria pelo TCE-AM e prestação de contas via Transferegov/SIGEM],
  [*Abastecimento de água*],
  [*Automático*, integrado ao sistema de osmose reversa (60 L/h; condutividade ≤ 1,3 µS/cm) — elimina a falha F3 do equipamento anterior e protege as resistências do gerador de vapor],
  [*Proteção IP do gabinete elétrico*],
  [*IP 54* (mínimo) — proteção contra poeira e respingos, essencial dado UR ≥ 80% em Borba],
  [*Sistemas de segurança*],
  [Mínimo *10 sistemas*, incluindo antiesmagamento de porta, bloqueio de abertura sob pressão, alarme sonoro/visual de falha de vácuo e temperatura — EN 285:2015],
  [*Qualificações documentadas*],
  [*QI + QO + QD* (ISO 17665-1:2006) realizadas e documentadas no CME do Hospital, com Relatório de Qualificação entregue em 2 vias impressas + PDF assinado, como condição do TRD],
  [*Periféricos incluídos*],
  [Sistema de osmose reversa 60 L/h; compressor de ar médico isento de óleo ≥ 50 L (ABNT NBR ISO 7396-1:2011); racks internos AISI 316L (≥ 3); carro de transporte inox; IB (_G. stearothermophilus_, cx 50 un.); IC Cl. 5 (cx 200 un.); peças de desgaste para 12 meses],
  [*Logística*],
  [*CIF Borba/AM + Entrega Técnica* no CME — frete fluvial Manaus–Borba (Rio Madeira), seguro _Ad Valorem_, embalagem antivibração e antiumpidade para transporte fluvial],
  [*Treinamento*],
  [Mínimo *8 horas* presenciais no CME do Hospital, com emissão de certificados nominais à equipe — operação, manutenção preventiva, monitoramento biológico/químico, rastreabilidade RDC 15/2012],
  [*Garantia*],
  [Mínimo *24 meses* a contar do Termo de Recebimento Definitivo (TRD), com atendimento técnico no Estado do Amazonas em até *72 horas* após chamado e solução definitiva em até *15 dias corridos*],
  [*Registro ANVISA*],
  [Obrigatório — fabricante ou importador com registro ativo na ANVISA para o equipamento ofertado],
  [*RENEM*],
  [Equipamento deve constar da Relação Nacional de Equipamentos e Materiais Permanentes (RENEM) com código CATMAT — exigência da Emenda Parlamentar (Portarias GM/MS 6.870 e 6.904/2025)],
  [*Normas*],
  [RDC ANVISA 15/2012; ISO 17665-1:2006; EN 285:2015; ABNT NBR ISO 7396-1:2011],
)

// ───────────────────────────────────────────────────────────────────────────
= 6. Dotação Orçamentária e Fonte de Recursos
// ───────────────────────────────────────────────────────────────────────────

A aquisição será custeada com recursos de *Emenda Parlamentar Estadual*, aprovada pela Assembleia Legislativa do Estado do Amazonas (ALEAM), destinados à Secretaria Municipal de Saúde do Município de Borba para aquisição de equipamentos hospitalares. A execução financeira ocorrerá via plataforma *Transferegov* (Ministério da Saúde), observadas as diretrizes das Portarias GM/MS n.º 6.870 e 6.904/2025.

#v(0.4em)
#table(
  columns: (1fr, 2.5cm, 2cm),
  fill: (x, y) => {
    if y == 0 { navy }
    else if calc.even(y) { rowalt }
    else { white }
  },
  stroke: (paint: luma(200), thickness: 0.4pt),
  inset: (x: 8pt, y: 7pt),
  table.header(
    text(fill: white, weight: "bold", size: 9.5pt)[Componente],
    text(fill: white, weight: "bold", size: 9.5pt)[Valor (R\$)],
    text(fill: white, weight: "bold", size: 9.5pt)[%],
  ),
  [Autoclave hospitalar 100–150 L com barreira sanitária], [120.000,00], [60,0%],
  [Periféricos (osmose reversa, compressor, racks, carro, IB, IC)], [35.000,00], [17,5%],
  [Logística CIF Borba/AM + seguro _Ad Valorem_], [15.000,00], [7,5%],
  [Entrega Técnica (QI/QO/QD) + Treinamento (8h)], [10.000,00], [5,0%],
  [Peças de desgaste e consumíveis para 12 meses de operação], [15.000,00], [7,5%],
  [Contingência logística (sazonalidade do Rio Madeira)], [5.000,00], [2,5%],
  table.cell(fill: rgb("#1A3A5C"))[
    #text(fill: white, weight: "bold")[TOTAL — Emenda Parlamentar]
  ],
  table.cell(fill: rgb("#1A3A5C"))[
    #text(fill: white, weight: "bold")[200.000,00]
  ],
  table.cell(fill: rgb("#1A3A5C"))[
    #text(fill: white, weight: "bold")[100%]
  ],
)

#v(0.5em)

A reserva de *R\$ 20.000,00* para adequação da infraestrutura do CME (rede elétrica trifásica, ponto hidráulico e sistema de exaustão de vapor) é *adicional e separada* da Emenda Parlamentar — custeada por recurso próprio municipal, em processo administrativo distinto. Essa segregação é obrigatória para evitar contaminação da prestação de contas via Transferegov/SICONV.

Os recursos são de *aplicação vinculada à saúde*, em plena conformidade com as finalidades da transferência parlamentar. O objeto descrito enquadra-se integralmente na categoria de equipamentos hospitalares elegíveis pela Emenda Parlamentar, não havendo desvio de finalidade.

// ───────────────────────────────────────────────────────────────────────────
= 7. Prazo da Contratação
// ───────────────────────────────────────────────────────────────────────────

#legal("Art. 75, § 3.º, Lei n.º 14.133/2021")[
  _"As contratações de que tratam os incisos [...] VIII [...] deste artigo serão limitadas, pelo valor, ao estritamente necessário para o atendimento da situação emergencial ou calamitosa."_
]

#v(0.5em)

Nos termos do art. 75, VIII, da Lei n.º 14.133/2021, a contratação emergencial é limitada ao prazo de *1 (um) ano*, suficiente para a entrega, instalação, comissionamento (QI/QO/QD), treinamento e início de operação regular da nova autoclave.

O prazo de entrega será estipulado conforme o *período hidrológico do Rio Madeira* na data de assinatura do contrato:

#v(0.4em)
#table(
  columns: (3cm, 2.2cm, 5cm, 3cm),
  fill: (x, y) => {
    if y == 0 { navy }
    else if calc.even(y) { rowalt }
    else { white }
  },
  stroke: (paint: luma(200), thickness: 0.4pt),
  inset: (x: 8pt, y: 7pt),
  table.header(
    text(fill: white, weight: "bold", size: 9.5pt)[Período],
    text(fill: white, weight: "bold", size: 9.5pt)[Meses],
    text(fill: white, weight: "bold", size: 9.5pt)[Condição Hidrológica],
    text(fill: white, weight: "bold", size: 9.5pt)[Prazo Máximo],
  ),
  [Cheia plena],  [Jan–Mai], [Navegação plena; balsas de grande calado], [60 dias corridos],
  [Vazante],      [Jun–Jul], [Restrições incipientes; monitorar], [75 dias corridos],
  [Seca extrema], [Ago–Nov], [Balsas de menor calado obrigatórias], [90 dias corridos],
  [Enchente],     [Dez],     [Normalização progressiva], [75 dias corridos],
)

#v(0.5em)

Eventual atraso comprovadamente causado por *seca extrema declarada pela ANA* (Agência Nacional de Águas e Saneamento Básico) não configurará mora do fornecedor, desde que: (i) a comunicação ao Gestor seja feita com antecedência mínima de 15 dias; (ii) o impedimento seja comprovado com declaração da empresa de navegação e boletim técnico da ANA; e (iii) a entrega seja realizada no prazo máximo de 30 dias após a retomada da navegabilidade.

É *vedada a prorrogação* do contrato emergencial e a recontratação do mesmo fornecedor sob esta hipótese legal, nos termos do art. 75, VIII, _in fine_, da Lei n.º 14.133/2021.

// ───────────────────────────────────────────────────────────────────────────
= 8. Requisitos Formais da Dispensa por Emergência
// ───────────────────────────────────────────────────────────────────────────

Em cumprimento ao art. 72 da Lei n.º 14.133/2021, o processo administrativo deverá ser instruído com os seguintes documentos:

#v(0.4em)
#table(
  columns: (0.6cm, 1fr, 2.5cm, 3.5cm),
  fill: (x, y) => {
    if y == 0 { navy }
    else if calc.even(y) { rowalt }
    else { white }
  },
  stroke: (paint: luma(200), thickness: 0.4pt),
  inset: (x: 8pt, y: 7pt),
  table.header(
    text(fill: white, weight: "bold", size: 9.5pt)[],
    text(fill: white, weight: "bold", size: 9.5pt)[Documento],
    text(fill: white, weight: "bold", size: 9.5pt)[Art. da Lei],
    text(fill: white, weight: "bold", size: 9.5pt)[Status],
  ),
  [①], [Esta Justificativa de Situação Emergencial],      [Art. 72, I],    [Elaborada — Anexo I],
  [②], [Laudo técnico do CME — Diretor Hospitalar],       [Art. 72, I],    [Elaborado — Anexo II],
  [③], [Termo de Referência (TR) com especificações],     [Art. 72, III],  [Elaborado — Anexo III],
  [④], [Pesquisa de preços — mínimo 3 cotações],          [Art. 72, IV],   [A realizar — modelo Anexo IV],
  [⑤], [Planilha comparativa e seleção do fornecedor],    [Art. 72, VII],  [A elaborar após cotações],
  [⑥], [Contrato de Fornecimento],                        [Art. 72, VIII], [Minuta — Anexo V],
  [⑦], [Publicação no PNCP em até 10 dias úteis],         [Art. 174],      [Após assinatura do contrato],
)

#v(0.5em)

#nota("Atenção ao TCE-AM — Blindagem Documental")[
  Dispensas por emergência de valor elevado são objeto prioritário de auditoria pelo Tribunal de Contas do Estado do Amazonas. Os riscos mais comuns de glosa são: (i) *ausência ou insuficiência da pesquisa de preços*; (ii) *urgência não documentada com evidências concretas* — declarações genéricas são insuficientes; (iii) *contratação de empresa sem capacidade técnica comprovada*; (iv) *falta de publicação no PNCP* no prazo legal. Esta Justificativa, acompanhada do laudo técnico do Diretor Hospitalar e das 3 cotações de mercado, constitui o conjunto mínimo necessário para uma defesa sólida em eventual tomada de contas especial.
]

// ───────────────────────────────────────────────────────────────────────────
= 9. Conclusão e Recomendação
// ───────────────────────────────────────────────────────────────────────────

Diante das circunstâncias objetivamente descritas e comprovadas nesta Justificativa, estão configurados *cumulativamente* todos os pressupostos legais para a contratação direta por emergência, nos termos do art. 75, VIII, da Lei Federal n.º 14.133/2021:

#v(0.4em)
#block(width: 100%, fill: legalbg,
  stroke: (paint: legalbdr, thickness: 0.8pt), radius: 4pt, inset: 12pt)[
  #let item(txt) = grid(
    columns: (1cm, 1fr),
    align(center+top)[#text(fill:legalbdr, weight:"bold", size:14pt)[✓]],
    block(inset:(left:4pt, y:3pt))[#text(size:10.5pt)[#txt]],
  )

  #item[*Situação emergencial concreta e documentada*, não provocada por omissão ou desídia da Administração: o equipamento (Autoclave nº 6897 — Phoenix Luferco, 2019) apresentou falha sistêmica progressiva em múltiplos subsistemas, tendo sido formalmente diagnosticado e documentado pelo Diretor Hospitalar Daniel Gomes Vinhote (Decreto n.º 0630/2026);]
  #v(4pt)
  #item[*Risco direto e imediato à segurança de pacientes e profissionais de saúde*, decorrente da impossibilidade de garantir a eficácia do processo de esterilização na única autoclave da unidade, com potencial para ISC, IRAS sistêmica e óbito evitável;]
  #v(4pt)
  #item[*Comprometimento da continuidade de serviço público essencial de saúde*, com risco iminente de desabastecimento de materiais esterilizados para todos os setores assistenciais do hospital de referência regional;]
  #v(4pt)
  #item[*Inviabilidade técnica e econômica da manutenção corretiva*, demonstrada pela natureza sistêmica e múltipla das falhas e pelo custo de reparo estimado em 60–75% do valor de substituição, sem garantia de desempenho; e]
  #v(4pt)
  #item[*Objeto delimitado ao estritamente necessário*, sem excesso ou superdimensionamento, nos termos do art. 75, VIII, _in fine_, da Lei n.º 14.133/2021.]
]

#v(0.8em)

Recomenda-se a *imediata abertura do procedimento de contratação direta por emergência*, nos seguintes termos:

+ Publicação do aviso de dispensa no PNCP, nos termos do art. 72, III, da Lei n.º 14.133/2021;
+ Instrução do processo com esta Justificativa, o Laudo Técnico do CME (Anexo II), o Termo de Referência (Anexo III) e a pesquisa de preços com mínimo de 3 cotações de mercado (Anexo IV);
+ Seleção do fornecedor que apresentar a *proposta mais vantajosa*, compatível com as especificações técnicas do Termo de Referência e com o registro do equipamento na *RENEM*;
+ Assinatura do Contrato de Fornecimento com cláusula de *Entrega Técnica* (QI/QO/QD) e *garantia mínima de 24 meses*;
+ Publicação da contratação no PNCP em até *10 dias úteis* da assinatura, nos termos do art. 174 da Lei n.º 14.133/2021.

// ───────────────────────────────────────────────────────────────────────────
//  ASSINATURAS
// ───────────────────────────────────────────────────────────────────────────
#v(1.5em)
#align(right)[Borba – AM, 15 de março de 2026]

#v(1.5em)
#grid(
  columns: (1fr, 1fr),
  column-gutter: 2cm,
  align: center,
  block(width: 100%)[
    #line(length: 100%, stroke: (paint: navy, thickness: 0.5pt))
    #v(4pt)
    *Cíntia Felipe Roque*
    #v(2pt)
    #text(size: 9.5pt)[Responsável pelo Setor]
    #v(2pt)
    #text(size: 9.5pt)[Central de Material e Esterilização — CME]
    #v(2pt)
    #text(size: 9.5pt)[Secretaria Municipal de Saúde de Borba/AM]
  ],
  block(width: 100%)[
    #line(length: 100%, stroke: (paint: navy, thickness: 0.5pt))
    #v(4pt)
    *Daniel Gomes Vinhote*
    #v(2pt)
    #text(size: 9.5pt)[Diretor Hospitalar]
    #v(2pt)
    #text(size: 9.5pt)[Hospital Central de Borba]
    #v(2pt)
    #text(size: 9.5pt)[Decreto n.º 0630/2026]
  ],
)

#v(1.5em)
#align(center)[
  #block(width: 60%)[
    #line(length: 100%, stroke: (paint: navy, thickness: 0.5pt))
    #v(4pt)
    *[Nome e Cargo do(a) Secretário(a) Municipal de Saúde]*
    #v(2pt)
    #text(size: 9.5pt)[Secretário(a) Municipal de Saúde de Borba/AM]
    #v(2pt)
    #text(size: 9.5pt, fill: legalbdr, weight: "bold")[APROVADO — Autorizo a abertura da contratação direta]
  ]
]

// ───────────────────────────────────────────────────────────────────────────
//  RODAPÉ NORMATIVO
// ───────────────────────────────────────────────────────────────────────────
#v(2em)
#line(length: 100%, stroke: (paint: luma(200), thickness: 0.5pt))
#v(4pt)
#text(size: 8pt, fill: luma(90), style: "italic")[
  *Base normativa:*
  Lei n.º 14.133/2021, arts. 72 e 75, VIII •
  RDC ANVISA n.º 15/2012 •
  ISO 17665-1:2006 (validação calor úmido) •
  EN 285:2015 (esterilizadores a vapor) •
  ABNT NBR ISO 7396-1:2011 (ar médico) •
  IN SEGES/MGI n.º 65/2021 (pesquisa de preços) •
  Portarias GM/MS n.º 6.870 e 6.904/2025 (Emenda Parlamentar) •
  CF/88, arts. 37 e 196.
]
