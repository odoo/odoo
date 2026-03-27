// ══════════════════════════════════════════════════════════════════════
//  JUSTIFICATIVA DE SITUAÇÃO EMERGENCIAL — v4
//  Autoclave Hospitalar — CME — Hospital Vó Mundoca — Borba/AM
//  Processo 2026.00003 — Art. 75, VIII, Lei 14.133/2021
// ══════════════════════════════════════════════════════════════════════

#let c-navy     = rgb("#1A3A5C")
#let c-blue     = rgb("#2E75B6")
#let c-green    = rgb("#15803D")
#let c-gbg      = rgb("#F0FDF4")
#let c-amber    = rgb("#92400E")
#let c-red      = rgb("#991B1B")
#let c-rbg      = rgb("#FEF2F2")
#let c-ibdr     = rgb("#1E40AF")
#let c-ibg      = rgb("#EFF6FF")
#let c-stripe   = rgb("#F8FAFC")
#let c-rule     = rgb("#E2E8F0")
#let c-muted    = rgb("#64748B")
#let c-blue-lt  = rgb("#93C5DE")
#let c-blue-md  = rgb("#5B8DB8")
#let c-navy-dk  = rgb("#243F6A")
#let c-muted-lt = rgb("#94A3B8")

#set page(
  paper: "a4",
  margin: (top: 2.4cm, bottom: 2.4cm, left: 2.8cm, right: 2.8cm),
  header: context {
    if counter(page).get().first() > 1 [
      #set text(font: "Fira Sans", size: 7.8pt, fill: c-muted)
      #grid(
        columns: (1fr, auto),
        [*Justificativa de Situação Emergencial* — Autoclave Hospitalar — Processo 2026.00003],
        [Art. 75, VIII — Lei 14.133/2021],
      )
      #v(-4pt)
      #line(length: 100%, stroke: (paint: c-rule, thickness: 0.5pt))
    ]
  },
  footer: context {
    if counter(page).get().first() > 1 [
      #set text(font: "Fira Sans", size: 7.8pt, fill: c-muted)
      #line(length: 100%, stroke: (paint: c-rule, thickness: 0.5pt))
      #v(-4pt)
      #align(center)[Página #counter(page).display() de #counter(page).final().first()]
    ]
  },
)

#set text(font: "Fira Sans", size: 10.5pt, lang: "pt", fallback: true)
#set par(justify: true, leading: 0.68em, spacing: 0.95em)
#set list(indent: 1.4em, spacing: 0.45em, body-indent: 0.5em)
#set enum(indent: 1.4em, spacing: 0.45em, body-indent: 0.5em)

#show heading.where(level: 1): it => block(above: 1.6em, below: 0.6em)[
  #grid(
    columns: (auto, 1fr),
    column-gutter: 10pt,
    align: horizon,
    block(fill: c-blue, width: 4pt, height: 1.1em, radius: 1pt)[],
    text(size: 11.5pt, weight: "semibold", fill: c-navy)[#it.body],
  )
  #line(length: 100%, stroke: (paint: c-rule, thickness: 0.6pt))
]

#show heading.where(level: 2): it => block(above: 1.1em, below: 0.4em)[
  #text(size: 10.5pt, weight: "semibold", fill: c-blue)[#it.body]
]

// Caixa lateral
#let caixa(cor, titulo, corpo) = block(
  width: 100%,
  fill: cor.lighten(92%),
  stroke: (left: (paint: cor, thickness: 4pt)),
  inset: (left: 14pt, right: 12pt, top: 10pt, bottom: 10pt),
  radius: (right: 3pt),
  spacing: 0.9em,
)[
  #if titulo != "" [
    #text(weight: "semibold", size: 9pt, fill: cor, tracking: 0.5pt)[#upper(titulo)]
    #linebreak()
    #v(2pt)
  ]
  #set text(size: 10pt)
  #corpo
]

#let legal(corpo)       = caixa(c-green, "Base Legal", corpo)
#let alerta(corpo)      = caixa(c-amber, "Atenção", corpo)
#let aviso(tit, corpo)  = caixa(c-red, tit, corpo)
#let info(tit, corpo)   = caixa(c-ibdr, tit, corpo)

// Ficha
#let ficha(..pares) = {
  let rows = pares.pos()
  let n = rows.len()
  block(width: 100%, stroke: (paint: c-rule, thickness: 0.5pt), radius: 4pt, clip: true, spacing: 0.9em)[
    #for (i, par) in rows.enumerate() {
      grid(
        columns: (4.2cm, 1fr),
        block(fill: if calc.odd(i) { c-stripe } else { white }, inset: (x: 11pt, y: 7pt), width: 100%)[
          #text(size: 9pt, weight: "medium", fill: c-navy)[#par.at(0)]
        ],
        block(fill: white, inset: (x: 11pt, y: 7pt), width: 100%)[
          #text(size: 9pt)[#par.at(1)]
        ],
      )
      if i < n - 1 { line(length: 100%, stroke: (paint: c-rule, thickness: 0.4pt)) }
    }
  ]
}

// Tabela com header navy
#let tabela(colunas, header, ..linhas) = block(
  width: 100%, spacing: 0.9em, radius: 4pt, clip: true,
  stroke: (paint: c-rule, thickness: 0.5pt),
)[
  #block(fill: c-navy, width: 100%, inset: (x: 10pt, y: 7pt))[
    #grid(columns: colunas, column-gutter: 8pt,
      ..header.map(h => text(fill: white, size: 9pt, weight: "semibold")[#h]))
  ]
  #for (i, linha) in linhas.pos().enumerate() {
    block(fill: if calc.odd(i) { c-stripe } else { white }, width: 100%,
          inset: (x: 10pt, y: 6pt), stroke: (bottom: (paint: c-rule, thickness: 0.4pt)))[
      #grid(columns: colunas, column-gutter: 8pt,
        ..linha.map(c => text(size: 9.5pt)[#c]))
    ]
  }
]

// Card de falha
#let falha-card(num, titulo, corpo) = block(
  width: 100%, spacing: 0.4em, stroke: (paint: c-rule, thickness: 0.5pt), radius: 3pt, clip: true,
)[
  #grid(
    columns: (1.8cm, 1fr),
    block(fill: c-red, inset: (x: 6pt, y: 12pt), width: 100%)[
      #align(center)[#text(fill: white, weight: "bold", size: 10pt)[#num]]
    ],
    block(inset: (x: 13pt, y: 10pt))[
      #text(weight: "semibold", fill: c-navy, size: 10pt)[#titulo]
      #v(3pt)
      #set text(size: 10pt)
      #corpo
    ],
  )
]

// Checkmark
#let check(corpo) = grid(
  columns: (1.4em, 1fr), column-gutter: 5pt, align: (top, top),
  text(fill: c-green, weight: "bold")[✓],
  block()[#set text(size: 10.5pt); #corpo],
)

// ──────────────────────────────────────────────────────────────────────
//  CAPA — `val` não `v` para evitar shadow de v()
// ──────────────────────────────────────────────────────────────────────
#page(
  header: none, footer: none,
  margin: (top: 0pt, bottom: 0pt, left: 0pt, right: 0pt),
  background: rect(fill: c-navy, width: 100%, height: 100%),
)[
  #set text(font: "Fira Sans", fill: white)
  #block(fill: c-blue, width: 100%, inset: (x: 3cm, y: 0pt), height: 1.1cm)[
    #align(horizon)[#text(size: 9pt, weight: "semibold", tracking: 0.3pt)[
      PREFEITURA MUNICIPAL DE BORBA — SECRETARIA MUNICIPAL DE SAÚDE
    ]]
  ]
  #v(3cm)
  #pad(left: 3cm, right: 3cm)[
    #text(size: 9pt, fill: c-blue-lt, tracking: 0.8pt)[
      DISPENSA DE LICITAÇÃO — ART. 75, VIII, LEI N.º 14.133/2021
    ]
    #v(4pt)
    #text(size: 8.5pt, fill: c-muted-lt)[Processo Administrativo n.º 2026.00003]
    #v(1cm)
    #line(length: 100%, stroke: (paint: c-blue-md, thickness: 0.7pt))
    #v(0.6cm)
    #text(size: 30pt, weight: "light", fill: white)[
      Justificativa de\
      Situação\
      Emergencial
    ]
    #v(0.5cm)
    #line(length: 100%, stroke: (paint: c-blue-md, thickness: 0.7pt))
    #v(0.7cm)
    #text(size: 12.5pt, fill: c-blue-lt, weight: "light")[
      Aquisição de Autoclave Hospitalar a Vapor\
      Central de Material e Esterilização — CME\
      Hospital Municipal Vó Mundoca — Borba/AM
    ]
    #v(2.5cm)
    #let meta(k, val) = {
      grid(columns: (3.7cm, 1fr),
        text(fill: c-blue-lt)[#k],
        text(fill: white)[#val],
      )
      v(5pt)
    }
    #set text(size: 9pt)
    #meta("Secretária de Saúde:", "Cíntia Roque da Silva Felipe — Decreto n.º 0004/2025-GPMB")
    #meta("Diretor Hospitalar:", "Daniel Gomes Vinhote — Decreto n.º 0630/2026")
    #meta("Valor estimado:", "R\$ 200.000,00 — Emenda Parlamentar Estadual (ALEAM)")
    #meta("Rel. de Inoperância:", "05 de março de 2026")
    #meta("Elaborado em:", "Borba/AM, 15 de março de 2026")
  ]
  #v(1fr)
  #block(fill: c-navy-dk, width: 100%, inset: (x: 3cm, y: 0pt), height: 0.9cm)[
    #align(horizon)[#text(size: 8pt, fill: c-blue-md)[
      RDC ANVISA 15/2012 • ISO 17665-1:2006 • EN 285:2015 • Lei 14.133/2021
    ]]
  ]
]

// ──────────────────────────────────────────────────────────────────────
//  QUADRO DE IDENTIFICAÇÃO — página isolada
// ──────────────────────────────────────────────────────────────────────
#block(below: 0.7em)[
  #grid(columns: (auto, 1fr), column-gutter: 10pt, align: horizon,
    block(fill: c-navy, width: 4pt, height: 1.1em, radius: 1pt)[],
    text(size: 11.5pt, weight: "semibold", fill: c-navy)[Quadro de Identificação do Processo],
  )
  #line(length: 100%, stroke: (paint: c-rule, thickness: 0.6pt))
]

#ficha(
  ("Processo",            "2026.00003"),
  ("Unidade solicitante", "Secretaria Municipal de Saúde — Borba/AM"),
  ("Setor / local",       "Central de Material e Esterilização (CME) — Hospital Municipal Vó Mundoca"),
  ("Secretária de Saúde", "Cíntia Roque da Silva Felipe — Decreto n.º 0004/2025-GPMB"),
  ("Diretor Hospitalar",  "Daniel Gomes Vinhote — Decreto n.º 0630/2026"),
  ("Objeto",              "Aquisição de autoclave hospitalar a vapor, tipo B (pré-vácuo), câmara ≥ 100 L, com periféricos, logística CIF Borba/AM, qualificações QI/QO/QD e treinamento"),
  ("Equip. substituído",  "Autoclave nº 6897 — Phoenix Luferco — fab. 2019 (~6 anos de uso)"),
  ("Fundamento legal",    "Art. 75, VIII, Lei n.º 14.133/2021 — Dispensa por emergência"),
  ("Fonte de recursos",   "Emenda Parlamentar Estadual — Assembleia Legislativa do Amazonas (ALEAM)"),
  ("Valor estimado",      "R\$ 200.000,00 (duzentos mil reais)"),
  ("Rel. de Inoperância", "05 de março de 2026 — Relatório Técnico de Inoperância/Insuficiência, assinado pelo Diretor Hospitalar"),
)

#pagebreak()

// ──────────────────────────────────────────────────────────────────────
= 1. Fundamento Legal
// ──────────────────────────────────────────────────────────────────────

#legal[
  Art. 75, VIII — _"É dispensável a licitação [...] nos casos de emergência ou de calamidade pública, quando caracterizada urgência de atendimento de situação que possa ocasionar prejuízo ou comprometer a continuidade dos serviços públicos ou a segurança de pessoas [...] e somente para os bens necessários ao atendimento da situação emergencial."_
]

A presente Justificativa fundamenta-se no art. 75, VIII, da Lei Federal n.º 14.133/2021. Os elementos fáticos demonstram o preenchimento *cumulativo* dos quatro requisitos legais que legitimam a contratação direta:

+ *Situação emergencial concreta e documentada,* não provocada por omissão da Administração;
+ *Risco direto à segurança de pacientes e profissionais de saúde;*
+ *Comprometimento da continuidade de serviço público essencial de saúde;* e
+ *Objeto delimitado ao estritamente necessário* ao atendimento da emergência.

// ──────────────────────────────────────────────────────────────────────
= 2. Caracterização do Município e Vulnerabilidade Geográfica
// ──────────────────────────────────────────────────────────────────────

O Município de Borba, situado na calha do Rio Madeira, possui *34.869 habitantes* no perímetro urbano (IBGE 2025), estendendo sua responsabilidade assistencial a uma área de influência de aproximadamente *44 mil pessoas*, incluindo comunidades ribeirinhas e aldeias dispersas ao longo do médio Madeira.

A realidade geográfica amazônica impõe ao *Hospital Municipal Vó Mundoca* o papel de *unidade de referência isolada* para toda essa população. A ausência de outro hospital no município e os elevados custos logísticos — remoções aeromédicas ou fluviais até Manaus frequentemente superam 24 horas — tornam a autossuficiência tecnológica da unidade não apenas uma meta administrativa, mas um *imperativo de Segurança Pública e Sanitária*.

#info("Isolamento e Irreversibilidade do Dano")[
  Em Borba, uma infecção cirúrgica grave decorrente de falha de esterilização não pode ser tratada por simples transferência a outro hospital. O tempo de translado fluvial até Manaus varia de *15 a 40 horas* conforme a sazonalidade do Rio Madeira. Uma sepse pós-operatória sem tratamento especializado imediato disponível representa *risco direto de óbito evitável* — risco inexistente em municípios com rede hospitalar plural ou com acesso terrestre rápido.
]

// ──────────────────────────────────────────────────────────────────────
= 3. Histórico Operacional e Dimensionamento da Demanda (2025)
// ──────────────────────────────────────────────────────────────────────

A necessidade de capacidade mínima de *100 litros* é diretamente ratificada pela expressiva atividade assistencial desenvolvida no exercício de 2025. O Hospital Vó Mundoca consolidou-se como polo resolutivo regional ao realizar:

- *4 (quatro) grandes mutirões de cirurgias,* abrangendo procedimentos de média complexidade, intervenções eletivas e *cirurgias oftalmológicas especializadas* — estas de alta demanda reprimida na região Norte;
- *Fluxo ininterrupto de partos* — o centro obstétrico é o único serviço de obstetrícia disponível para toda a área de influência municipal;
- *Urgências traumáticas e clínicas,* com demanda não programável que exige materiais esterilizados disponíveis 24 horas por dia.

Esse volume evidencia que a Central de Material e Esterilização opera em *regime de saturação operacional*. O parque tecnológico atual, embora tenha sustentado essas ações, atingiu seu *limite de fadiga material*, conforme documenta o Relatório Técnico de Inoperância/Insuficiência de 05/03/2026. A especificação de 100 litros não é restritiva — é requisito funcional demonstrado pela demanda real.

// ──────────────────────────────────────────────────────────────────────
= 4. Fato Gerador — Diagnóstico Técnico do Equipamento
// ──────────────────────────────────────────────────────────────────────

== 4.1 Identificação do Equipamento em Inoperância

#v(0.4em)
#ficha(
  ("Nº de patrimônio",   "6897"),
  ("Fabricante",         "Phoenix Luferco"),
  ("Ano de fabricação",  "2019 (~6 anos de uso em CME de alta demanda)"),
  ("Tipo",               "Autoclave hospitalar a vapor — câmara única"),
  ("Status atual",       [#text(weight: "semibold", fill: c-red)[INOPERANTE — falha sistêmica múltipla — uso inseguro]]),
  ("Relatório técnico",  "Relatório de Inoperância/Insuficiência — 05/03/2026 — Diretor Hospitalar Daniel Gomes Vinhote (Decreto n.º 0630/2026) — Anexo II"),
)

== 4.2 Falhas Técnicas Identificadas

#v(0.4em)
#falha-card("F1", "Salto de etapas do ciclo de esterilização")[
  O equipamento transita diretamente da fase de esterilização para a secagem sem concluir o tempo de _plateau_. Essa falha *invalida a garantia de esterilidade* de todos os artigos processados, impedindo o alcance do SAL de $10^(-6)$ exigido pela RDC ANVISA 15/2012.
]

#falha-card("F2", "Não atingimento da temperatura mínima de esterilização")[
  O equipamento falha em alcançar *134 °C ± 1 °C* nos ciclos de pré-vácuo. O Valor F₀:
  #v(5pt)
  #align(center)[
    #block(fill: c-ibg, stroke: (paint: c-ibdr, thickness: 0.4pt), radius: 3pt,
           inset: (x: 16pt, y: 8pt))[
      $F_0 = integral_0^t 10^((T - 121.1) / z) thin dif t$
      #h(1.5em)
      #text(size: 8.5pt, fill: c-muted)[_T_ = temperatura (°C) #h(0.5em) _z_ = 10 °C #h(0.5em) (_G. stearothermophilus_)]
    ]
  ]
  #v(4pt)
  Com temperatura insuficiente, o F₀ fica abaixo de *15 min*, tornando os artigos microbiologicamente inseguros após cada ciclo.
]

#falha-card("F3", "Falha no sistema hidráulico de abastecimento automático")[
  Entrada de água inoperante — exige intervenção manual a cada ciclo, comprometendo: (i) a *padronização* dos ciclos; (ii) a *rastreabilidade* (RDC 15/2012, art. 34); e (iii) a *segurança do operador*, exposto a componentes aquecidos.
]

#falha-card("F4", "Instabilidade geral — falha sistêmica múltipla")[
  Comportamento errático com parâmetros de pressão e temperatura inconsistentes. A coexistência de F1–F3 confirma *degradação estrutural simultânea* em múltiplos subsistemas, tornando o equipamento irrecuperável por manutenção pontual.
]

// ──────────────────────────────────────────────────────────────────────
= 5. Biossegurança, CCIH e Controle de Infecções
// ──────────────────────────────────────────────────────────────────────

A aquisição é condição técnica obrigatória para o cumprimento dos protocolos estabelecidos pela *Comissão de Controle de Infecção Hospitalar (CCIH)* e pelo *Núcleo de Segurança do Paciente (NSP)* do Hospital Vó Mundoca. A esterilização por vapor saturado sob pressão, com monitoramento microprocessado, é a *barreira primária* contra microrganismos multirresistentes no ambiente hospitalar.

A utilização de equipamentos em estado de inoperância compromete a eficácia dos indicadores biológicos e químicos, inviabilizando o monitoramento rigoroso exigido pela RDC ANVISA 15/2012. Sob a ótica da CCIH, a insuficiência do CME eleva o risco de:

- *Contaminação cruzada* entre artigos processados em ciclos falhos e artigos conformes;
- *Surtos infecciosos pós-operatórios,* com impacto direto na morbimortalidade cirúrgica e obstétrica;
- *Infecções por microrganismos multirresistentes* (MRSA, KPC, Acinetobacter), cujo tratamento exige antibióticos de alto custo e prolongamento expressivo de internação.

#aviso("Ônus Fiscal Indireto da Não Aquisição")[
  O custo de uma única internação prolongada por infecção de sítio cirúrgico multirresistente pode superar *R\$ 50.000,00* em antibioticoterapia e dias de UTI. Além do dano humano irreparável, a omissão na renovação do CME cria passivo fiscal e expõe o Município à *judicialização por dano ao paciente* — responsabilidade solidária do ente público (art. 37, § 6.º, CF/88).
]

// ──────────────────────────────────────────────────────────────────────
= 6. Caracterização da Situação de Emergência
// ──────────────────────────────────────────────────────────────────────

== 6.1 Impactos Operacionais e Risco de Desassistência

A inoperância da única autoclave da CME produz impactos diretos e imediatos em todos os setores assistenciais:

- *Redução crítica da capacidade de esterilização* de instrumentais médico-cirúrgicos;
- *Risco de desabastecimento* para o centro cirúrgico, *centro obstétrico,* pronto-socorro e unidades de internação;
- *Impossibilidade de garantia da eficácia do processo* — violação direta dos arts. 5.º, 6.º e 34 da RDC ANVISA 15/2012;
- Em caso de falha definitiva: *paralisação compulsória do centro cirúrgico e obstétrico,* gerando colapso assistencial em uma cidade onde *não há hospital alternativo.*

== 6.2 Risco Sanitário ao Paciente

#aviso("Cadeia Causal — Falha de Esterilização → Dano ao Paciente")[
  Falha sistêmica → SAL > 10⁻⁶ → *artigo crítico inseguro* → contato com sítio cirúrgico ou obstétrico → *ISC ou infecção puerperal* → morbidade, sepse, *óbito evitável.*

  #v(3pt)
  Em Borba, o translado fluvial até UTI de referência em Manaus supera 24 horas. A mortalidade por sepse sem tratamento especializado imediato pode ultrapassar 30% — risco amplificado pelo isolamento geográfico, único no contexto amazônico.
]

== 6.3 Conformidade Normativa e Responsabilidade Institucional

A operação da CME com equipamento inoperante configura *infração direta à RDC ANVISA 15/2012,* sujeitando o Município a:

- *Interdição sanitária* da CME pela Vigilância Sanitária, com paralisia imediata de todos os procedimentos cirúrgicos e obstétricos;
- *Sanções administrativas* ao gestor e à instituição por descumprimento de norma de biossegurança;
- *Responsabilidade civil solidária do ente público* por danos causados a pacientes em decorrência de falha de esterilização (art. 37, § 6.º, CF/88).

O *Princípio da Continuidade* do serviço público é igualmente afetado: a esterilização é atividade-meio essencial para a atividade-fim (preservação da vida). Sua interrupção fere o direito constitucional à saúde (CF/88, art. 196).

== 6.4 Impossibilidade de Aguardar o Rito Licitatório Regular

#tabela(
  (1fr, 2cm, 3cm),
  ("Etapa do Pregão Eletrônico", "Prazo mín.", "Observação"),
  ("ETP + TR + pesquisa de preços", "15 dias", "Já concluídos"),
  ("Elaboração e revisão do edital (CPL + PGM)", "10 dias", ""),
  ("Publicação no PNCP até abertura (art. 55, § 2.º)", "8 dias", ""),
  ("Prazo de propostas + sessão + habilitação", "15 dias", ""),
  ("Recursos + homologação + assinatura", "10 dias", ""),
  ("Entrega Técnica — período de seca (Ago–Nov)", "90 dias", "Balsas de menor calado"),
)
#block(
  fill: c-rbg, stroke: (left: (paint: c-red, thickness: 4pt)),
  radius: (right: 3pt), inset: (left: 14pt, right: 12pt, top: 9pt, bottom: 9pt), spacing: 0.9em,
)[
  #grid(columns: (1fr, auto), column-gutter: 12pt, align: horizon,
    text(size: 10pt)[*Total estimado até Entrega Técnica: ≈ 148 dias (≈ 5 meses)*],
    text(size: 9.5pt, fill: c-red)[CME sem esterilização segura],
  )
]

#v(0.3em)
O tempo de tramitação de um rito licitatório ordinário é *incompatível com a atual precariedade* do sistema de esterilização. Cirurgias e partos ocorrem diariamente no Hospital Vó Mundoca — qualquer falha definitiva do equipamento nesse intervalo implicaria paralisação imediata, sem alternativa local.

// ──────────────────────────────────────────────────────────────────────
= 7. Inviabilidade da Manutenção Corretiva
// ──────────────────────────────────────────────────────────────────────

A natureza *múltipla e sistêmica* das falhas F1 a F4 torna a manutenção corretiva tecnicamente insuficiente e economicamente inviável:

+ *Falha simultânea em quatro subsistemas críticos* — indica degradação estrutural, não pane pontual reparável;

+ *Paralisação adicional durante o reparo:* qualquer tentativa de manutenção corretiva implicaria a *paralisação prolongada do único equipamento de esterilização da unidade,* agravando o risco sanitário já existente durante todo o período de imobilização;

+ *Custo estimado em 60–75% do valor de substituição,* sem garantia de desempenho equivalente e sem recomposição do período de garantia;

+ *Ausência de qualificação pós-reparo:* mesmo reparado, o equipamento não seria submetido a nova QI/QO/QD auditável — mantendo incerteza sobre o SAL efetivamente alcançado;

+ *Fadiga material acelerada:* 6 anos de operação intensiva (4 mutirões + partos + urgências em 2025) em ambiente de alta umidade (≥ 80%) comprometem irreversivelmente guarnições, resistências e componentes eletrônicos.

#info("Por que esta emergência não decorre de omissão administrativa")[
  O TCU e o TCE-AM exigem que a emergência não seja fruto de negligência. No presente caso: (i) o equipamento foi adquirido regularmente em 2019; (ii) a falha sistêmica desenvolveu-se progressivamente, abaixo do horizonte de vida útil esperado; (iii) a Emenda Parlamentar foi ativada; e (iv) a falha foi *documentada tempestivamente* em Relatório Técnico formal em 05/03/2026. A Administração agiu com diligência ao identificar, formalizar e imediatamente encaminhar a solução.
]

// ──────────────────────────────────────────────────────────────────────
= 8. Eficiência e Economicidade
// ──────────────────────────────────────────────────────────────────────

Sob o princípio da *Eficiência* (art. 37, CF/88), a aquisição de equipamento novo é a *solução mais econômica em perspectiva sistêmica:*

- *Custo acumulado de manutenções paliativas* sem resolução definitiva, somado ao tempo de imobilização do serviço a cada intervenção;
- *Desperdício de insumos por ciclos falhos:* cada ciclo com SAL > 10⁻⁶ implica descarte de indicadores biológicos, indicadores químicos e potencialmente do conteúdo da câmara;
- *Passivo de responsabilização civil:* uma única internação prolongada por ISC multirresistente pode superar R\$ 50.000,00 — valor comparável ao custo total de periféricos do equipamento novo;
- *Garantia e previsibilidade:* ativo novo com garantia de 24 meses e QI/QO/QD documentada oferece *desempenho auditável e previsibilidade orçamentária* — inexistentes no equipamento em estado de fadiga sistêmica.

// ──────────────────────────────────────────────────────────────────────
= 9. Planejamento Estratégico e Metas para 2026
// ──────────────────────────────────────────────────────────────────────

Para 2026, a Secretaria Municipal de Saúde planejou a *expansão do acesso cirúrgico* e o aumento da oferta de procedimentos para reduzir as *filas reprimidas.* A manutenção desse cronograma depende diretamente da modernização da CME. A aquisição visa dotar o hospital da infraestrutura necessária para suportar o incremento de demanda planejado, assegurando:

- A continuidade das *políticas de saúde itinerante* (mutirões em comunidades ribeirinhas);
- A expansão da *resolutividade cirúrgica local,* reduzindo remoções onerosas para Manaus;
- O cumprimento das metas do *Plano Municipal de Saúde (PMS)* e dos contratos com o SUS.

// ──────────────────────────────────────────────────────────────────────
= 10. Especificação Técnica Justificada
// ──────────────────────────────────────────────────────────────────────

Baseada na RDC ANVISA 15/2012, ISO 17665-1:2006 e EN 285:2015. Todos os requisitos são necessários e suficientes — sem especificação restritiva à concorrência.

#v(0.4em)
#tabela(
  (3.4cm, 1fr),
  ("Especificação", "Requisito Mínimo e Justificativa"),
  ("Tipo", "Autoclave a vapor saturado, *Tipo B (pré-vácuo)*, horizontal — obrigatório para artigos porosos e artigos com lúmens (RDC 15/2012, art. 15)"),
  ("Câmara", "Capacidade útil *≥ 100 litros*; aço inoxidável *AISI 316L* polido — justificada pelo volume de 4 mutirões + partos + urgências em 2025; resistência a cloretos e UR ≥ 80%"),
  ("Sistema de vácuo", "Bomba de anel líquido; pressão absoluta *≤ 30 mbar*; *mínimo 3 pulsos* — único método eficaz para materiais porosos e lúmens (EN 285:2015, item 8)"),
  ("Temperatura", "105 °C a 135 °C com precisão *± 1 °C* — necessária para F₀ ≥ 15 min e SAL 10⁻⁶ (ISO 17665-1:2006)"),
  ("Programas", "Mínimo *13 programas* pré-configurados: poroso 134 °C, sólido 134 °C, líquido 121 °C, Bowie-Dick e Leak Test integrados"),
  ("Interface e rastreabilidade", "Tela colorida *touchscreen*, gestão de usuários com senha, *impressora integrada* de ciclos — cumpre art. 34 da RDC ANVISA 15/2012"),
  ("Abastecimento d'água", "*Automático* — elimina a falha F3 e garante padronização e rastreabilidade dos ciclos"),
  ("Registro eletrônico", "Memória interna + saída USB — exportação de relatórios para Transferegov/SIGEM e TCE-AM"),
  ("Segurança", "Mínimo *10 sistemas de segurança:* antiesmagamento de porta, bloqueio sob pressão, alarmes sonoros e visuais; gabinete elétrico *IP 54*"),
  ("Periféricos", "Osmose reversa 60 L/h (condutividade ≤ 1,3 µS/cm); compressor de ar médico isento de óleo ≥ 50 L (ABNT NBR ISO 7396-1:2011); cestos/racks AISI 316L ≥ 3 un.; carro de transporte inox; IB G. stearothermophilus (cx 50 un.); IC Cl. 5 (cx 200 un.); peças de desgaste para 12 meses"),
  ("Qualificações", "*QI + QO + QD* (ISO 17665-1:2006) no CME com carga plena; ΔT ≤ 2 °C; IB negativos; F₀ ≥ 15 min — condição inafastável do TRD e do pagamento"),
  ("Logística", "*CIF Borba/AM + Entrega Técnica* — frete fluvial Manaus–Borba, seguro Ad Valorem, embalagem antivibração e antiumpidade"),
  ("Treinamento", "Mínimo *8 horas* presenciais no CME — operação, manutenção preventiva de 1.º nível, monitoramento biológico/químico, rastreabilidade RDC 15/2012; certificados nominais"),
  ("Garantia", "Mínimo *24 meses* a contar do TRD; atendimento técnico no AM ≤ *72 horas*; solução definitiva ≤ *15 dias corridos*"),
  ("Registro ANVISA", "Obrigatório — fabricante ou importador com registro ativo"),
  ("RENEM", "Equipamento na RENEM com código CATMAT — exigência das Portarias GM/MS 6.870 e 6.904/2025"),
)

// ──────────────────────────────────────────────────────────────────────
= 11. Dotação Orçamentária e Fonte de Recursos
// ──────────────────────────────────────────────────────────────────────

Custeado com *Emenda Parlamentar Estadual* (ALEAM), execução via *Transferegov* (Portarias GM/MS 6.870 e 6.904/2025). Recursos vinculados à saúde — sem desvio de objeto.

#v(0.4em)
#tabela(
  (1fr, 2.8cm, 1.6cm),
  ("Componente", "Valor (R\$)", "%"),
  ("Autoclave hospitalar ≥ 100 L com barreira sanitária",    "120.000,00", "60,0%"),
  ("Periféricos (osmose, compressor, racks, carro, IB, IC)", " 35.000,00", "17,5%"),
  ("Logística CIF Borba/AM + seguro Ad Valorem",             " 15.000,00", " 7,5%"),
  ("Entrega Técnica (QI/QO/QD) + Treinamento (8h)",          " 10.000,00", " 5,0%"),
  ("Peças de desgaste e consumíveis — 12 meses",             " 15.000,00", " 7,5%"),
  ("Contingência logística — sazonalidade Rio Madeira",       "  5.000,00", " 2,5%"),
)
#block(fill: c-navy, width: 100%, inset: (x: 10pt, y: 8pt), radius: (bottom: 4pt))[
  #grid(columns: (1fr, 2.8cm, 1.6cm), column-gutter: 8pt,
    text(fill: white, weight: "semibold")[Total — Emenda Parlamentar],
    text(fill: white, weight: "semibold")[200.000,00],
    text(fill: white, weight: "semibold")[100%],
  )
]

#v(0.5em)
A reserva de *R\$ 20.000,00* para adequação da infraestrutura do CME (rede elétrica trifásica, ponto hidráulico e exaustão de vapor) é *recurso municipal próprio, adicional e segregado* da Emenda Parlamentar.

// ──────────────────────────────────────────────────────────────────────
= 12. Prazo da Contratação
// ──────────────────────────────────────────────────────────────────────

Trata-se de fornecimento de *bem permanente* — o contrato compreende entrega, instalação, QI/QO/QD, treinamento e entrada em operação, limitado a *1 (um) ano* (art. 75, VIII). Prazo de entrega conforme período hidrológico do Rio Madeira:

#tabela(
  (2.4cm, 1.8cm, 1fr, 2.4cm),
  ("Período", "Meses", "Condição Hidrológica", "Prazo Máximo"),
  ("Cheia plena",  "Jan–Mai", "Navegação plena; balsas de grande calado",        "60 dias corridos"),
  ("Vazante",      "Jun–Jul", "Restrições incipientes; monitoramento necessário", "75 dias corridos"),
  ("Seca extrema", "Ago–Nov", "Balsas de menor calado obrigatórias (ANA)",        "90 dias corridos"),
  ("Enchente",     "Dez",     "Normalização progressiva",                         "75 dias corridos"),
)

#v(0.4em)
É *vedada a prorrogação* do contrato emergencial e a recontratação do mesmo fornecedor sob esta hipótese (_in fine_ do art. 75, VIII).

// ──────────────────────────────────────────────────────────────────────
= 13. Requisitos Formais da Dispensa (Art. 72, Lei 14.133/2021)
// ──────────────────────────────────────────────────────────────────────

#tabela(
  (0.7cm, 1fr, 1.8cm, 3.2cm),
  ("", "Documento", "Artigo", "Status"),
  ("①", "Esta Justificativa de Situação Emergencial",              "Art. 72, I",    "Elaborada — Anexo I"),
  ("②", "Rel. Técnico de Inoperância — Diretor Hospitalar",        "Art. 72, I",    "Elaborado — Anexo II (05/03/2026)"),
  ("③", "Termo de Referência com especificações técnicas",         "Art. 72, III",  "Elaborado — Anexo III"),
  ("④", "Pesquisa de preços — mínimo 3 cotações formalizadas",     "Art. 72, IV",   "A realizar — modelo Anexo IV"),
  ("⑤", "Planilha comparativa e seleção fundamentada",             "Art. 72, VII",  "A elaborar após cotações"),
  ("⑥", "Confirmação de disponibilidade orçamentária da emenda",   "Art. 72, VI",   "A juntar — confirmação ALEAM"),
  ("⑦", "Contrato de Fornecimento",                                "Art. 72, VIII", "Minuta — Anexo V"),
  ("⑧", "Publicação no PNCP em até 10 dias úteis",                 "Art. 174",      "Após assinatura do contrato"),
)

#v(0.5em)
#alerta[
  *Dispensas por emergência de alto valor são alvo prioritário de auditoria pelo TCE-AM.* Os riscos mais comuns de glosa: (i) pesquisa de preços ausente ou com menos de 3 cotações válidas; (ii) urgência fundamentada apenas em declarações genéricas, sem Relatório Técnico objetivo; (iii) empresa sem o equipamento na RENEM; (iv) ausência de publicação no PNCP no prazo de 10 dias úteis. Esta Justificativa + Relatório de Inoperância + 3 cotações formalizadas formam o conjunto mínimo para defesa sólida em eventual tomada de contas especial.
]

// ──────────────────────────────────────────────────────────────────────
= 14. Conclusão e Recomendação
// ──────────────────────────────────────────────────────────────────────

A urgência aqui caracterizada é *objetiva, concreta e atual.* A aquisição da autoclave é o instrumento jurídico e técnico que permitirá ao Hospital Vó Mundoca continuar honrando o pacto do SUS com a população borbense — preservando a vida e mantendo a dignidade assistencial no interior do Amazonas.

#v(0.4em)
#block(
  width: 100%, fill: c-gbg,
  stroke: (left: (paint: c-green, thickness: 4pt)),
  radius: (right: 3pt), inset: (left: 14pt, right: 12pt, top: 12pt, bottom: 12pt), spacing: 0.9em,
)[
  #check[*Situação emergencial concreta, documentada e não provocada por omissão:* autoclave nº 6897 (Phoenix Luferco, 2019) em falha sistêmica múltipla — Relatório de Inoperância/Insuficiência de 05/03/2026 lavrado pelo Diretor Hospitalar Daniel Gomes Vinhote (Decreto n.º 0630/2026).]
  #v(7pt)
  #check[*Risco direto à segurança de pacientes e profissionais,* com potencial para ISC, infecção puerperal, IRAS por multirresistentes e óbito evitável — amplificado pelo isolamento geográfico amazônico e pelo translado de 15 a 40 horas até UTI de referência.]
  #v(7pt)
  #check[*Comprometimento da continuidade do serviço público essencial,* com risco iminente de paralisação do centro cirúrgico e obstétrico e colapso assistencial em município sem hospital alternativo.]
  #v(7pt)
  #check[*Inviabilidade técnica e econômica da manutenção corretiva,* inclusive pela paralisação adicional do único equipamento durante o reparo, confirmando a substituição como única solução definitiva.]
  #v(7pt)
  #check[*Eficiência demonstrada:* custo de manutenções paliativas + desperdício por ciclos falhos + passivo de responsabilização civil superam o investimento em ativo novo com garantia de 24 meses.]
  #v(7pt)
  #check[*Objeto delimitado ao estritamente necessário,* sem superdimensionamento — capacidade de 100 L ratificada por 4 mutirões cirúrgicos + partos + urgências em 2025.]
]

#v(0.8em)
Recomenda-se a *imediata abertura do procedimento de contratação direta,* com publicação do aviso de dispensa no PNCP (art. 72, III), instrução do processo com os documentos da Seção 13 e seleção do fornecedor com proposta mais vantajosa e equipamento na RENEM.

// ──────────────────────────────────────────────────────────────────────
//  ASSINATURAS + BASE NORMATIVA — bloco indivisível (sem página órfã)
// ──────────────────────────────────────────────────────────────────────
#block(breakable: false)[
  #v(1.8em)
  #align(right)[#text(size: 10pt)[Borba/AM, 15 de março de 2026]]

  #v(1.4em)
  #grid(
    columns: (1fr, 1fr),
    column-gutter: 1.8cm,
    align: center,
    block(width: 100%)[
      #line(length: 100%, stroke: (paint: c-rule, thickness: 0.7pt))
      #v(5pt)
      #text(weight: "semibold")[Cíntia Roque da Silva Felipe]
      #v(2pt)
      #text(size: 9pt, fill: c-muted)[Secretária Municipal de Saúde\
      Decreto n.º 0004/2025-GPMB]
    ],
    block(width: 100%)[
      #line(length: 100%, stroke: (paint: c-rule, thickness: 0.7pt))
      #v(5pt)
      #text(weight: "semibold")[Daniel Gomes Vinhote]
      #v(2pt)
      #text(size: 9pt, fill: c-muted)[Diretor Hospitalar\
      Hospital Municipal Vó Mundoca\
      Decreto n.º 0630/2026]
    ],
  )

  #v(2em)
  #line(length: 100%, stroke: (paint: c-rule, thickness: 0.5pt))
  #v(4pt)
  #text(size: 8pt, fill: c-muted)[
    *Base normativa:* Lei n.º 14.133/2021, arts. 72 e 75, VIII •
    RDC ANVISA n.º 15/2012 (processamento de produtos para saúde) •
    ISO 17665-1:2006 (validação esterilização por calor úmido) •
    EN 285:2015 (esterilizadores a vapor de grande porte) •
    ABNT NBR ISO 7396-1:2011 (ar médico) •
    IN SEGES/MGI n.º 65/2021 (pesquisa de preços) •
    Portarias GM/MS n.º 6.870 e 6.904/2025 (Emenda Parlamentar) •
    CF/88, arts. 37, § 6.º, e 196.
  ]
]
