// ══════════════════════════════════════════════════════════════════════
//  JUSTIFICATIVA DE SITUAÇÃO EMERGENCIAL
//  Autoclave Hospitalar — CME — Hospital Central de Borba
//  Processo 2026.00003 — Art. 75, VIII, Lei 14.133/2021
// ══════════════════════════════════════════════════════════════════════

// ── Paleta ─────────────────────────────────────────────────────────────
#let c-navy    = rgb("#1A3A5C")
#let c-blue    = rgb("#2E75B6")
#let c-lblue   = rgb("#EBF3FB")
#let c-green   = rgb("#15803D")
#let c-gbg     = rgb("#F0FDF4")
#let c-amber   = rgb("#B45309")
#let c-abg     = rgb("#FFFBEB")
#let c-red     = rgb("#B91C1C")
#let c-rbg     = rgb("#FEF2F2")
#let c-ibdr    = rgb("#1D4ED8")
#let c-ibg     = rgb("#EFF6FF")
#let c-stripe  = rgb("#F3F8FC")
#let c-rule    = rgb("#CBD5E1")
#let c-muted   = rgb("#64748B")

// ── Página ──────────────────────────────────────────────────────────────
#set page(
  paper: "a4",
  margin: (top: 2.6cm, bottom: 2.6cm, left: 3.0cm, right: 2.6cm),
  header: context {
    if counter(page).get().first() > 1 {
      set text(font: "Fira Sans", size: 8pt, fill: c-muted)
      grid(columns: (1fr, auto), gutter: 0pt,
        [*Justificativa de Situação Emergencial* — Autoclave Hospitalar — Processo 2026.00003],
        [Art. 75, VIII — Lei 14.133/2021],
      )
      v(-4pt)
      line(length: 100%, stroke: (paint: c-rule, thickness: 0.5pt))
    }
  },
  footer: context {
    if counter(page).get().first() > 1 {
      set text(font: "Fira Sans", size: 8pt, fill: c-muted)
      line(length: 100%, stroke: (paint: c-rule, thickness: 0.5pt))
      v(-4pt)
      align(center)[Página #counter(page).display() de #counter(page).final().first()]
    }
  },
)

// ── Tipografia base ─────────────────────────────────────────────────────
#set text(font: "Fira Sans", size: 10.5pt, lang: "pt", fallback: true)
#set par(justify: true, leading: 0.65em, spacing: 0.85em)
#set list(indent: 1.4em, spacing: 0.4em, body-indent: 0.5em)
#set enum(indent: 1.4em, spacing: 0.4em, body-indent: 0.5em)

// ── Headings ────────────────────────────────────────────────────────────
#show heading.where(level: 1): it => {
  v(1.4em)
  text(font: "Fira Sans", size: 11.5pt, weight: "semibold", fill: c-navy)[
    #it.body
  ]
  v(2pt)
  line(length: 100%, stroke: (paint: c-navy, thickness: 1pt))
  v(0.5em)
}

#show heading.where(level: 2): it => {
  v(0.9em)
  text(font: "Fira Sans", size: 10.5pt, weight: "semibold", fill: c-blue)[#it.body]
  v(0.3em)
}

#show heading.where(level: 3): it => {
  v(0.7em)
  text(font: "Fira Sans", size: 10.5pt, weight: "medium", fill: c-navy,
    style: "italic")[#it.body]
  v(0.2em)
}

// ── Componentes ─────────────────────────────────────────────────────────

// Caixa genérica com tarja colorida lateral
#let caixa(cor, titulo, corpo) = block(
  width: 100%,
  inset: 0pt,
  spacing: 0.8em,
)[
  #grid(
    columns: (4pt, 1fr),
    block(fill: cor, width: 4pt, height: 100%)[],
    block(
      fill: cor.lighten(90%),
      inset: (left: 12pt, right: 12pt, top: 9pt, bottom: 9pt),
      width: 100%,
    )[
      #if titulo != "" {
        text(weight: "semibold", size: 9.5pt, fill: cor)[#titulo]
        linebreak()
        v(2pt)
      }
      #text(size: 10pt)[#corpo]
    ],
  )
]

#let legal(corpo)  = caixa(c-green, "BASE LEGAL", corpo)
#let alerta(corpo) = caixa(c-amber, "ATENÇÃO", corpo)
#let aviso(titulo, corpo)  = caixa(c-red, titulo, corpo)
#let info(titulo, corpo)   = caixa(c-ibdr, titulo, corpo)

// Tabela de ficha (label | valor, linhas alternadas)
#let ficha(..pares) = {
  let rows = pares.pos()
  block(
    width: 100%,
    stroke: (paint: c-rule, thickness: 0.5pt),
    radius: 3pt,
    clip: true,
    spacing: 0.8em,
  )[
    #for (i, par) in rows.enumerate() {
      let bg = if calc.even(i) { white } else { c-stripe }
      grid(
        columns: (4.4cm, 1fr),
        block(
          fill: bg, inset: (x: 10pt, y: 7pt), width: 100%,
        )[
          #text(size: 9.5pt, weight: "medium", fill: c-navy)[#par.at(0)]
        ],
        block(
          fill: white, inset: (x: 10pt, y: 7pt), width: 100%,
        )[
          #text(size: 9.5pt)[#par.at(1)]
        ],
      )
      if i < rows.len() - 1 {
        line(length: 100%, stroke: (paint: c-rule, thickness: 0.4pt))
      }
    }
  ]
}

// Tabela genérica com header navy
#let tabela(colunas, header, ..linhas) = {
  block(
    width: 100%,
    stroke: none,
    spacing: 0.8em,
  )[
    // Header
    #block(
      fill: c-navy,
      width: 100%,
      inset: (x: 9pt, y: 7pt),
      radius: (top-left: 3pt, top-right: 3pt),
    )[
      #grid(
        columns: colunas,
        ..header.map(h =>
          text(fill: white, size: 9pt, weight: "semibold")[#h]
        )
      )
    ]
    // Rows
    #for (i, linha) in linhas.pos().enumerate() {
      let bg = if calc.even(i) { c-stripe } else { white }
      let is-last = i == linhas.pos().len() - 1
      block(
        fill: bg,
        width: 100%,
        inset: (x: 9pt, y: 6pt),
        stroke: (paint: c-rule, thickness: 0.4pt),
        radius: if is-last { (bottom-left: 3pt, bottom-right: 3pt) } else { 0pt },
      )[
        #grid(
          columns: colunas,
          ..linha.map(c => text(size: 9.5pt)[#c])
        )
      ]
    }
  ]
}

// Bullet com ícone colorido
#let check(corpo) = grid(
  columns: (1.2em, 1fr),
  column-gutter: 6pt,
  align: (top, top),
  text(fill: c-green, weight: "bold")[✓],
  text(size: 10.5pt)[#corpo],
)

// ──────────────────────────────────────────────────────────────────────
//  CAPA
// ──────────────────────────────────────────────────────────────────────
#page(
  header: none,
  footer: none,
  background: rect(fill: c-navy, width: 100%, height: 100%),
  margin: (top: 0pt, bottom: 0pt, left: 0pt, right: 0pt),
)[
  #set text(font: "Fira Sans", fill: white)

  // Barra superior colorida
  #block(fill: c-blue, width: 100%, height: 1.2cm, inset: (x: 3.2cm, y: 0pt))[
    #align(horizon)[
      #text(size: 9pt, weight: "semibold")[
        PREFEITURA MUNICIPAL DE BORBA — SECRETARIA MUNICIPAL DE SAÚDE
      ]
    ]
  ]

  #v(3.5cm)
  #pad(left: 3.2cm, right: 3.2cm)[
    #text(size: 9.5pt, fill: c-blue.lighten(40%))[
      DISPENSA DE LICITAÇÃO — ART. 75, VIII, LEI N.º 14.133/2021
    ]
    #v(0.5em)
    #text(size: 9pt, fill: rgb("#7BAFD4"))[Processo Administrativo n.º 2026.00003]

    #v(1.2cm)
    #line(length: 100%, stroke: (paint: c-blue.lighten(20%), thickness: 0.8pt))
    #v(0.5cm)

    #text(size: 30pt, weight: "light", fill: white)[
      Justificativa de\
      Situação\
      Emergencial
    ]
    #v(0.4cm)
    #line(length: 100%, stroke: (paint: c-blue.lighten(20%), thickness: 0.8pt))
    #v(0.6cm)

    #text(size: 13pt, fill: rgb("#93C5DE"), weight: "light")[
      Aquisição de Autoclave Hospitalar a Vapor\
      Central de Material e Esterilização — CME\
      Hospital Central de Borba
    ]

    #v(2.5cm)

    // Tabela de metadados
    #set text(size: 9pt)
    #let meta(label, valor) = {
      grid(
        columns: (3.5cm, 1fr),
        text(fill: rgb("#7BAFD4"))[#label],
        text(fill: white)[#valor],
      )
      v(4pt)
    }

    #meta("Responsável:", "Cíntia Felipe Roque")
    #meta("Diretor Hospitalar:", "Daniel Gomes Vinhote — Decreto n.º 0630/2026")
    #meta("Valor estimado:", "R\$ 200.000,00 — Emenda Parlamentar Estadual — ALEAM")
    #meta("Rel. técnico-base:", "05 de março de 2026")
    #meta("Elaborado em:", "Borba/AM, 15 de março de 2026")
  ]

  #v(1fr)
  #block(fill: c-blue.darken(20%), width: 100%, height: 0.8cm, inset: (x: 3.2cm, y: 0pt))[
    #align(horizon)[
      #text(size: 8pt, fill: rgb("#7BAFD4"))[
        RDC ANVISA 15/2012  •  ISO 17665-1:2006  •  EN 285:2015  •  Lei 14.133/2021
      ]
    ]
  ]
]

// ──────────────────────────────────────────────────────────────────────
//  QUADRO DE IDENTIFICAÇÃO
// ──────────────────────────────────────────────────────────────────────
#v(0.4em)
#ficha(
  ("Processo",               "2026.00003"),
  ("Unidade solicitante",    "Secretaria Municipal de Saúde — Borba/AM"),
  ("Setor / local",          "Central de Material e Esterilização (CME) — Hospital Central de Borba"),
  ("Responsável",            "Cíntia Felipe Roque"),
  ("Objeto",                 "Aquisição de autoclave hospitalar a vapor, tipo B (pré-vácuo), câmara ≥ 100 L, com periféricos, logística CIF Borba/AM, qualificações QI/QO/QD e treinamento"),
  ("Equip. substituído",     "Autoclave nº 6897 — Phoenix Luferco — fab. 2019 (~6 anos de uso)"),
  ("Fundamentação legal",    "Art. 75, VIII, Lei n.º 14.133/2021 — Dispensa por emergência"),
  ("Fonte de recursos",      "Emenda Parlamentar Estadual — Assembleia Legislativa do Amazonas (ALEAM)"),
  ("Valor estimado",         "R\$ 200.000,00 (duzentos mil reais)"),
  ("Data do rel. técnico",   "05 de março de 2026"),
)

// ──────────────────────────────────────────────────────────────────────
= 1. Fundamento Legal
// ──────────────────────────────────────────────────────────────────────

#legal[
  Art. 75, VIII — _"É dispensável a licitação [...] nos casos de emergência ou de calamidade pública, quando caracterizada urgência de atendimento de situação que possa ocasionar prejuízo ou comprometer a continuidade dos serviços públicos ou a segurança de pessoas [...] e somente para os bens necessários ao atendimento da situação emergencial."_
]

A presente Justificativa fundamenta-se no art. 75, VIII, da Lei Federal n.º 14.133/2021, que autoriza a dispensa de licitação em situações de emergência que comprometam a continuidade de serviço público essencial ou a segurança de pessoas. Os elementos fáticos expostos nas seções seguintes demonstram o preenchimento *cumulativo* dos três requisitos legais:

+ *Situação emergencial concreta e documentada,* não provocada por omissão da Administração;
+ *Risco direto à segurança de pacientes e profissionais de saúde;*
+ *Objeto delimitado ao estritamente necessário* ao atendimento da emergência.

// ──────────────────────────────────────────────────────────────────────
= 2. Fato Gerador — Diagnóstico do Equipamento
// ──────────────────────────────────────────────────────────────────────

== 2.1 Identificação do Equipamento Inoperante

O Hospital Central de Borba dispõe de *uma única autoclave* instalada na CME. O equipamento encontra-se *inoperante por falha sistêmica múltipla*, conforme relatório técnico formal lavrado pelo Diretor Hospitalar.

#v(0.4em)
#ficha(
  ("Nº de patrimônio",       "6897"),
  ("Fabricante",             "Phoenix Luferco"),
  ("Ano de fabricação",      "2019 (aproximadamente 6 anos de uso)"),
  ("Tipo",                   "Autoclave hospitalar a vapor — câmara única"),
  ("Localização",            "CME — Hospital Central de Borba"),
  ("Status atual",           [#text(weight: "semibold", fill: c-red)[INOPERANTE — falha sistêmica múltipla]]),
  ("Laudo técnico",          "Relatório formal lavrado pelo Diretor Hospitalar Daniel Gomes Vinhote (Decreto n.º 0630/2026) — Anexo I deste processo"),
)

#v(0.8em)

== 2.2 Falhas Técnicas Identificadas

O diagnóstico técnico formalizado em 05 de março de 2026 identificou quatro falhas de natureza grave, com impacto direto na segurança do processo de esterilização:

#v(0.4em)

// Falha 1
#block(
  width: 100%, spacing: 0.5em,
  stroke: (paint: c-rule, thickness: 0.5pt), radius: 3pt, clip: true,
)[
  #grid(
    columns: (0.9cm, 1fr),
    block(fill: c-red, inset: (x: 0pt, y: 10pt), width: 100%)[
      #align(center)[#text(fill: white, weight: "bold", size: 10pt)[F1]]
    ],
    block(inset: (x: 12pt, y: 10pt))[
      #text(weight: "semibold", fill: c-navy)[Salto de etapas do ciclo de esterilização]\
      #v(3pt)
      O equipamento passa diretamente da fase de esterilização para a secagem sem concluir o processo. Essa falha invalida a garantia de esterilidade pois o tempo de _plateau_ — exposição contínua na temperatura alvo — não é respeitado, impedindo o alcance do Nível de Garantia de Esterilidade (SAL) de $10^(-6)$ exigido pela RDC ANVISA 15/2012.
    ],
  )
]

#v(0.25em)

// Falha 2
#block(
  width: 100%, spacing: 0.5em,
  stroke: (paint: c-rule, thickness: 0.5pt), radius: 3pt, clip: true,
)[
  #grid(
    columns: (0.9cm, 1fr),
    block(fill: c-red, inset: (x: 0pt, y: 10pt), width: 100%)[
      #align(center)[#text(fill: white, weight: "bold", size: 10pt)[F2]]
    ],
    block(inset: (x: 12pt, y: 10pt))[
      #text(weight: "semibold", fill: c-navy)[Não atingimento da temperatura mínima de esterilização]\
      #v(3pt)
      O equipamento falha em alcançar *134 °C ± 1 °C* nos ciclos de pré-vácuo. A esterilidade a vapor é matematicamente expressa pelo Valor F₀:
      #v(4pt)
      #align(center)[
        #block(fill: c-ibg, stroke: (paint: c-ibdr, thickness: 0.4pt), radius: 3pt,
               inset: (x: 16pt, y: 8pt), width: auto)[
          $F_0 = integral_0^t 10^((T - 121.1) / z) dif t$
          #h(1em)
          #text(size: 8.5pt, fill: c-muted)[_T_ = temperatura (°C);  _z_ = 10 °C  (_G. stearothermophilus_)]
        ]
      ]
      #v(4pt)
      Com temperatura insuficiente, o F₀ calculado fica abaixo do mínimo de *15 minutos*, tornando os artigos processados microbiologicamente inseguros.
    ],
  )
]

#v(0.25em)

// Falha 3
#block(
  width: 100%, spacing: 0.5em,
  stroke: (paint: c-rule, thickness: 0.5pt), radius: 3pt, clip: true,
)[
  #grid(
    columns: (0.9cm, 1fr),
    block(fill: c-red, inset: (x: 0pt, y: 10pt), width: 100%)[
      #align(center)[#text(fill: white, weight: "bold", size: 10pt)[F3]]
    ],
    block(inset: (x: 12pt, y: 10pt))[
      #text(weight: "semibold", fill: c-navy)[Falha no sistema hidráulico de abastecimento automático]\
      #v(3pt)
      O sistema de entrada de água autônoma está inoperante, exigindo intervenção manual a cada ciclo. Isso compromete: (i) a padronização dos ciclos; (ii) a rastreabilidade do processo (RDC 15/2012, art. 34); e (iii) a segurança do operador, exposto a componentes aquecidos durante a manipulação.
    ],
  )
]

#v(0.25em)

// Falha 4
#block(
  width: 100%, spacing: 0.5em,
  stroke: (paint: c-rule, thickness: 0.5pt), radius: 3pt, clip: true,
)[
  #grid(
    columns: (0.9cm, 1fr),
    block(fill: c-red, inset: (x: 0pt, y: 10pt), width: 100%)[
      #align(center)[#text(fill: white, weight: "bold", size: 10pt)[F4]]
    ],
    block(inset: (x: 12pt, y: 10pt))[
      #text(weight: "semibold", fill: c-navy)[Instabilidade geral — falha sistêmica múltipla]\
      #v(3pt)
      Comportamento errático com parâmetros de pressão e temperatura inconsistentes ao longo dos ciclos, indicativo de falha simultânea em múltiplos subsistemas (controle eletrônico, sensores, válvulas). A coexistência de F1 a F3 descarta a hipótese de pane isolada e confirma degradação sistêmica irreversível do equipamento.
    ],
  )
]

// ──────────────────────────────────────────────────────────────────────
= 3. Caracterização da Situação de Emergência
// ──────────────────────────────────────────────────────────────────────

== 3.1 Impactos Operacionais Imediatos

A inoperância da única autoclave do CME produz impactos diretos e imediatos na operação assistencial, insuperáveis por qualquer solução alternativa interna:

- *Redução crítica da capacidade de esterilização* de instrumentais médico-cirúrgicos utilizados em cirurgias, curativos e procedimentos invasivos;
- *Risco de desabastecimento de materiais esterilizados* para o centro cirúrgico, pronto-socorro e unidades de internação;
- *Impossibilidade de garantia da eficácia da esterilização,* com potencial uso de artigos inadequadamente estéreis — violação direta dos arts. 5.º, 6.º e 34 da RDC ANVISA 15/2012;
- *Exposição dos profissionais de saúde* a materiais potencialmente contaminados durante o reprocessamento manual emergencial.

== 3.2 Risco Sanitário Direto ao Paciente

O processamento inadequado de artigos críticos é a principal causa de Infecções Relacionadas à Assistência à Saúde (IRAS) de origem instrumental. No Hospital Central de Borba — único hospital de referência para *34.869 habitantes* (IBGE 2025) em área de acesso predominantemente fluvial — a falha de esterilização tem consequências amplificadas:

#v(0.4em)
#aviso("CADEIA CAUSAL — FALHA DE ESTERILIZAÇÃO → DANO AO PACIENTE")[
  Falha sistêmica do equipamento → SAL > 10⁻⁶ → *artigo crítico inseguro* → contato com sítio cirúrgico → *Infecção de Sítio Cirúrgico (ISC)* ou IRAS sistêmica → morbidade, internação prolongada, sepse, *óbito evitável.*

  #v(4pt)
  No interior do Amazonas, onde o tempo de acesso a centros de referência em Manaus pode superar 24 horas por via fluvial, a evolução de uma ISC grave sem tratamento imediato disponível configura risco de morte diretamente atribuível à falha de esterilização.
]

#v(0.8em)

== 3.3 Impossibilidade de Aguardar o Rito Licitatório Regular

Um Pregão Eletrônico para aquisição deste bem demandaria, em condições normais, o seguinte prazo mínimo até a Entrega Técnica:

#v(0.4em)
#tabela(
  (1fr, 2cm, 3.2cm),
  ("Etapa", "Prazo mín.", "Observação"),
  ("ETP + TR + pesquisa de preços", "15 dias", "Já concluídos"),
  ("Elaboração e revisão do edital (CPL + PGM)", "10 dias", ""),
  ("Publicação no PNCP até abertura", "8 dias", "Art. 55, § 2.º"),
  ("Prazo de propostas + sessão + habilitação", "15 dias", ""),
  ("Recursos + homologação + assinatura", "10 dias", ""),
  ("Entrega Técnica — período de seca", "90 dias", "Ago–Nov: balsas de menor calado"),
)
#block(
  fill: c-rbg,
  stroke: (paint: c-red, thickness: 0.5pt),
  width: 100%, inset: (x: 10pt, y: 7pt), radius: (bottom: 3pt),
)[
  #grid(
    columns: (1fr, 2cm, 3.2cm),
    text(weight: "semibold", fill: c-red)[Total estimado até Entrega Técnica],
    text(weight: "semibold", fill: c-red)[≈ 148 dias],
    text(size: 9pt, fill: c-red)[Quase 5 meses sem esterilização segura],
  )
]

#v(0.5em)

Cinco meses de operação hospitalar sem autoclave funcional — em hospital de referência regional, realizando cirurgias e atendimentos de urgência — configura risco inaceitável à vida humana, incompatível com o princípio da eficiência (CF/88, art. 37) e com o dever de cautela sanitária.

// ──────────────────────────────────────────────────────────────────────
= 4. Inviabilidade da Manutenção Corretiva
// ──────────────────────────────────────────────────────────────────────

A natureza *múltipla e sistêmica* das falhas F1 a F4 torna a manutenção corretiva economicamente inviável e tecnicamente insuficiente como solução definitiva, pelos seguintes fundamentos:

+ *Falha simultânea em quatro subsistemas críticos* (controle de ciclos, sistema térmico, sistema hidráulico e estabilidade operacional geral), indicativa de degradação estrutural — não pane pontual reparável;

+ *Obsolescência funcional acelerada:* o equipamento tem ~6 anos de uso em CME de média complexidade com alta rotatividade de ciclos. As condições amazônicas — umidade relativa ≥ 80%, temperatura ambiente 26–34 °C — aceleram a degradação de componentes eletrônicos, guarnições e resistências;

+ *Custo de reparo economicamente inviável:* a restauração dos quatro subsistemas no interior do Amazonas representa custo estimado de *60–75% do valor de substituição*, sem garantia de desempenho equivalente e sem recomposição do período de garantia;

+ *Ausência de qualificação pós-reparo:* mesmo reparado, o equipamento não seria submetido a nova qualificação documentada (QI/QO/QD) com resultados auditáveis, mantendo incerteza sobre o SAL efetivamente alcançado.

#info("POR QUE ESTA EMERGÊNCIA NÃO DECORRE DE OMISSÃO ADMINISTRATIVA")[
  A jurisprudência do TCU e do TCE-AM exige que a emergência *não seja fruto de negligência do gestor.* No presente caso: (i) o equipamento foi adquirido regularmente em 2019; (ii) a falha sistêmica apresentou-se de forma progressiva e imprevisível, abaixo do horizonte de vida útil esperado (10–15 anos); (iii) a Emenda Parlamentar estava disponível; e (iv) a falha foi documentada tempestivamente pelo Diretor Hospitalar. O gestor agiu com diligência ao identificar, formalizar e imediatamente encaminhar a solução.
]

// ──────────────────────────────────────────────────────────────────────
= 5. Especificação Técnica Justificada
// ──────────────────────────────────────────────────────────────────────

A especificação foi elaborada com base na RDC ANVISA 15/2012, ISO 17665-1:2006 e EN 285:2015, nas características operacionais do CME (40 leitos, cirurgias de urgência e eletivas) e nas condições climáticas da Amazônia.

#v(0.4em)
#tabela(
  (3.6cm, 1fr),
  ("Especificação", "Requisito e Justificativa"),
  ("Tipo", "Autoclave hospitalar a vapor saturado, *Tipo B (pré-vácuo)*, horizontal — obrigatório para artigos porosos (campos, uniformes) e artigos com lúmens (RDC 15/2012, art. 15)"),
  ("Câmara", "Capacidade útil *≥ 100 litros*; aço inoxidável *AISI 316L* polido internamente — resistência superior a cloretos e à umidade ≥ 80% do clima amazônico"),
  ("Sistema de vácuo", "Bomba de anel líquido; pressão absoluta *≤ 30 mbar*; *mínimo 3 pulsos* alternados de vácuo e vapor — único método eficaz para remoção de ar em porosos e lúmens (EN 285:2015, item 8)"),
  ("Temperatura", "105 °C a 135 °C com precisão *± 1 °C* — necessária para F₀ ≥ 15 min e SAL 10⁻⁶ (ISO 17665-1:2006)"),
  ("Programas", "Mínimo *13 programas* pré-configurados: poroso 134 °C, sólido 134 °C, líquido 121 °C, Bowie-Dick e Leak Test"),
  ("Interface e rastreabilidade", "Tela colorida *touchscreen*, gestão de usuários com senha, *impressora integrada* de etiquetas de ciclo — atende ao art. 34 da RDC ANVISA 15/2012"),
  ("Registro eletrônico", "Memória interna de ciclos + saída USB para exportação de relatórios auditáveis pelo TCE-AM e Transferegov"),
  ("Proteção elétrica", "Gabinete elétrico *IP 54* (mínimo) — essencial dado UR ≥ 80% em Borba/AM"),
  ("Segurança", "Mínimo *10 sistemas de segurança,* incluindo antiesmagamento de porta, bloqueio sob pressão, alarmes sonoros e visuais de falha"),
  ("Periféricos incluídos", "Osmose reversa 60 L/h (condutividade ≤ 1,3 µS/cm); compressor de ar médico isento de óleo ≥ 50 L (ABNT NBR ISO 7396-1:2011); racks AISI 316L (≥ 3 un.); carro de transporte inox; IB G. stearothermophilus (cx 50 un.); IC Cl. 5 (cx 200 un.); peças de desgaste para 12 meses"),
  ("Qualificações", "*QI + QO + QD* (ISO 17665-1:2006) realizadas no CME do Hospital, com Relatório de Qualificação em 2 vias impressas + PDF assinado como condição do TRD"),
  ("Logística", "*CIF Borba/AM + Entrega Técnica* — frete fluvial Manaus–Borba, seguro Ad Valorem, embalagem antivibração e antiumpidade para transporte fluvial"),
  ("Treinamento", "Mínimo *8 horas* presenciais no CME, com certificados nominais — operação, manutenção preventiva, monitoramento biológico/químico, rastreabilidade RDC 15/2012"),
  ("Garantia", "Mínimo *24 meses* a contar do TRD; atendimento técnico no Amazonas em ≤ *72 horas*; solução definitiva em ≤ *15 dias corridos*"),
  ("Registro ANVISA", "Obrigatório — fabricante ou importador com registro ativo para o equipamento ofertado"),
  ("RENEM", "Equipamento deve constar da RENEM com código CATMAT — exigência das Portarias GM/MS 6.870 e 6.904/2025 (Emenda Parlamentar)"),
)

// ──────────────────────────────────────────────────────────────────────
= 6. Dotação Orçamentária e Fonte de Recursos
// ──────────────────────────────────────────────────────────────────────

A aquisição é custeada com *Emenda Parlamentar Estadual* aprovada pela Assembleia Legislativa do Amazonas (ALEAM), destinada à Secretaria Municipal de Saúde para equipamentos hospitalares. A execução financeira ocorrerá via *Transferegov* (Ministério da Saúde), observadas as Portarias GM/MS n.º 6.870 e 6.904/2025.

#v(0.4em)
#tabela(
  (1fr, 2.6cm, 1.5cm),
  ("Componente", "Valor (R\$)", "%"),
  ("Autoclave hospitalar ≥ 100 L com barreira sanitária",    "120.000,00", "60,0%"),
  ("Periféricos (osmose, compressor, racks, carro, IB, IC)", " 35.000,00", "17,5%"),
  ("Logística CIF Borba/AM + seguro Ad Valorem",             " 15.000,00", " 7,5%"),
  ("Entrega Técnica (QI/QO/QD) + Treinamento (8h)",          " 10.000,00", " 5,0%"),
  ("Peças de desgaste e consumíveis — 12 meses",             " 15.000,00", " 7,5%"),
  ("Contingência logística (sazonalidade Rio Madeira)",       "  5.000,00", " 2,5%"),
)
#block(
  fill: c-navy, width: 100%, inset: (x: 9pt, y: 7pt),
  radius: (bottom: 3pt),
)[
  #grid(
    columns: (1fr, 2.6cm, 1.5cm),
    text(fill: white, weight: "semibold")[Total — Emenda Parlamentar 2025],
    text(fill: white, weight: "semibold")[200.000,00],
    text(fill: white, weight: "semibold")[100%],
  )
]

#v(0.5em)

A reserva de *R\$ 20.000,00* para adequação da infraestrutura do CME (rede elétrica trifásica, ponto hidráulico e exaustão de vapor) é *recurso municipal próprio, adicional e segregado* da Emenda Parlamentar — executado em processo administrativo distinto, para não contaminar a prestação de contas via Transferegov/SICONV.

Os recursos são de aplicação vinculada à saúde, em plena conformidade com as finalidades da transferência parlamentar, sem desvio de objeto.

// ──────────────────────────────────────────────────────────────────────
= 7. Prazo da Contratação
// ──────────────────────────────────────────────────────────────────────

Nos termos do art. 75, VIII, da Lei n.º 14.133/2021, a contratação emergencial é limitada ao prazo de *1 (um) ano*, suficiente para entrega, instalação, comissionamento e início de operação regular. O prazo de entrega será estipulado conforme o período hidrológico do Rio Madeira vigente na data de assinatura do contrato:

#v(0.4em)
#tabela(
  (2.5cm, 1.8cm, 1fr, 2.5cm),
  ("Período", "Meses", "Condição Hidrológica", "Prazo Máximo"),
  ("Cheia plena",  "Jan–Mai", "Navegação plena; balsas de grande calado",          "60 dias corridos"),
  ("Vazante",      "Jun–Jul", "Restrições incipientes; monitoramento necessário",   "75 dias corridos"),
  ("Seca extrema", "Ago–Nov", "Balsas de menor calado obrigatórias (ANA)",          "90 dias corridos"),
  ("Enchente",     "Dez",     "Normalização progressiva da navegabilidade",          "75 dias corridos"),
)

#v(0.5em)

Atraso comprovadamente causado por seca extrema declarada pela ANA não configurará mora do fornecedor, desde que comunicado ao Gestor com ≥ 15 dias de antecedência e comprovado com declaração da empresa de navegação e boletim da ANA. É *vedada a prorrogação* do contrato emergencial e a recontratação do mesmo fornecedor sob esta hipótese (_in fine_ do art. 75, VIII).

// ──────────────────────────────────────────────────────────────────────
= 8. Requisitos Formais da Dispensa
// ──────────────────────────────────────────────────────────────────────

Em cumprimento ao art. 72 da Lei n.º 14.133/2021, o processo deve ser instruído com:

#v(0.4em)
#tabela(
  (0.6cm, 1fr, 1.8cm, 3cm),
  ("", "Documento", "Artigo", "Status"),
  ("①", "Esta Justificativa de Situação Emergencial",         "Art. 72, I",    "Elaborada — Anexo I"),
  ("②", "Laudo técnico do CME — Diretor Hospitalar",          "Art. 72, I",    "Elaborado — Anexo II"),
  ("③", "Termo de Referência com especificações técnicas",    "Art. 72, III",  "Elaborado — Anexo III"),
  ("④", "Pesquisa de preços — mínimo 3 cotações",             "Art. 72, IV",   "A realizar — modelo Anexo IV"),
  ("⑤", "Planilha comparativa e seleção do fornecedor",       "Art. 72, VII",  "A elaborar após cotações"),
  ("⑥", "Contrato de Fornecimento",                           "Art. 72, VIII", "Minuta — Anexo V"),
  ("⑦", "Publicação no PNCP em até 10 dias úteis",            "Art. 174",      "Após assinatura"),
)

#v(0.5em)

#alerta[
  *Dispensas por emergência de alto valor são alvo prioritário de auditoria pelo TCE-AM.* Os riscos mais comuns de glosa são: (i) ausência ou insuficiência da pesquisa de preços; (ii) urgência documentada apenas com declarações genéricas — sem laudo técnico; (iii) contratação de empresa sem capacidade técnica comprovada; (iv) ausência de publicação no PNCP no prazo legal. Esta Justificativa, acompanhada do laudo do Diretor Hospitalar e das 3 cotações de mercado, forma o conjunto mínimo para defesa sólida em eventual tomada de contas especial.
]

// ──────────────────────────────────────────────────────────────────────
= 9. Conclusão e Recomendação
// ──────────────────────────────────────────────────────────────────────

Estão configurados *cumulativamente* todos os pressupostos legais para a contratação direta por emergência, nos termos do art. 75, VIII, da Lei n.º 14.133/2021:

#v(0.4em)
#block(
  width: 100%,
  fill: c-gbg,
  stroke: (paint: c-green, thickness: 0.5pt),
  radius: 3pt,
  inset: (x: 14pt, y: 12pt),
)[
  #check[*Situação emergencial concreta e documentada,* não provocada por omissão: a autoclave nº 6897 (Phoenix Luferco, 2019) apresentou falha sistêmica em múltiplos subsistemas, formalmente documentada pelo Diretor Hospitalar Daniel Gomes Vinhote (Decreto n.º 0630/2026).]
  #v(6pt)
  #check[*Risco direto e imediato à segurança de pacientes e profissionais de saúde,* com potencial para ISC, IRAS sistêmica e óbito evitável, em hospital de referência regional para 34.869 habitantes com acesso fluvial predominante.]
  #v(6pt)
  #check[*Comprometimento da continuidade de serviço público essencial de saúde,* com risco iminente de desabastecimento de materiais esterilizados para todos os setores assistenciais.]
  #v(6pt)
  #check[*Inviabilidade técnica e econômica da manutenção corretiva,* demonstrada pela natureza sistêmica das falhas e pelo custo de reparo estimado em 60–75% do valor de substituição, sem garantia de desempenho.]
  #v(6pt)
  #check[*Objeto delimitado ao estritamente necessário,* sem excesso ou superdimensionamento, nos termos do art. 75, VIII, _in fine._]
]

#v(0.8em)

Recomenda-se a *imediata abertura do procedimento de contratação direta,* com as seguintes providências:

+ Publicação do aviso de dispensa no PNCP, nos termos do art. 72, III;
+ Instrução do processo com esta Justificativa, o Laudo Técnico (Anexo II), o Termo de Referência (Anexo III) e pesquisa de preços com mínimo de 3 cotações (Anexo IV);
+ Seleção do fornecedor com proposta mais vantajosa, compatível com as especificações técnicas e com o registro do equipamento na RENEM;
+ Assinatura do Contrato de Fornecimento com cláusula de Entrega Técnica (QI/QO/QD) e garantia mínima de *24 meses;*
+ Publicação da contratação no PNCP em até *10 dias úteis* da assinatura (art. 174).

// ──────────────────────────────────────────────────────────────────────
//  ASSINATURAS
// ──────────────────────────────────────────────────────────────────────

#v(1.8em)
#align(right)[#text(size: 10pt)[Borba – AM, 15 de março de 2026]]

#v(1.5em)
#grid(
  columns: (1fr, 1fr),
  column-gutter: 1.8cm,
  align: center,
  block(width: 100%)[
    #line(length: 100%, stroke: (paint: c-rule, thickness: 0.7pt))
    #v(5pt)
    #text(weight: "semibold")[Cíntia Felipe Roque]
    #v(2pt)
    #text(size: 9.5pt, fill: c-muted)[Responsável — CME\
    Secretaria Municipal de Saúde de Borba/AM]
  ],
  block(width: 100%)[
    #line(length: 100%, stroke: (paint: c-rule, thickness: 0.7pt))
    #v(5pt)
    #text(weight: "semibold")[Daniel Gomes Vinhote]
    #v(2pt)
    #text(size: 9.5pt, fill: c-muted)[Diretor Hospitalar\
    Hospital Central de Borba\
    Decreto n.º 0630/2026]
  ],
)

#v(1.8em)
#align(center)[
  #block(width: 65%)[
    #line(length: 100%, stroke: (paint: c-rule, thickness: 0.7pt))
    #v(5pt)
    #text(weight: "semibold")[[Nome e Cargo do(a) Secretário(a) Municipal de Saúde]]
    #v(2pt)
    #text(size: 9.5pt, fill: c-muted)[Secretário(a) Municipal de Saúde de Borba/AM]
    #v(4pt)
    #text(size: 9.5pt, fill: c-green, weight: "semibold")[
      APROVADO — Autorizo a abertura da contratação direta
    ]
  ]
]

// ──────────────────────────────────────────────────────────────────────
//  RODAPÉ NORMATIVO
// ──────────────────────────────────────────────────────────────────────
#v(2em)
#line(length: 100%, stroke: (paint: c-rule, thickness: 0.4pt))
#v(4pt)
#text(size: 8pt, fill: c-muted)[
  *Base normativa:* Lei n.º 14.133/2021, arts. 72 e 75, VIII •
  RDC ANVISA n.º 15/2012 •
  ISO 17665-1:2006 (validação calor úmido) •
  EN 285:2015 (esterilizadores a vapor) •
  ABNT NBR ISO 7396-1:2011 (ar médico) •
  IN SEGES/MGI n.º 65/2021 (pesquisa de preços) •
  Portarias GM/MS n.º 6.870 e 6.904/2025 (Emenda Parlamentar) •
  CF/88, arts. 37 e 196.
]
