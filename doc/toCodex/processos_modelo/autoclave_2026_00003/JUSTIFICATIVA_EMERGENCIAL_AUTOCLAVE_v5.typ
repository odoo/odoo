// ══════════════════════════════════════════════════════════════════════
//  JUSTIFICATIVA DE SITUAÇÃO EMERGENCIAL — v5
//  Autoclave Hospitalar — CME — Hospital Vó Mundoca — Borba/AM
//  Processo 2026.00003 — Art. 75, VIII, Lei 14.133/2021
// ══════════════════════════════════════════════════════════════════════

#import "timbre.typ": *

// ── Imagens do timbre declaradas aqui (escopo raiz = funciona em header) ─
#let _b = timbre-brasao
#let _h = timbre-header-text
#let _f = timbre-footer

// ── Referência do documento (aparece abaixo da linha do cabeçalho) ──────
#let _ref = "Justificativa de Situação Emergencial — Processo 2026.00003"
#let _lei = "Art. 75, VIII — Lei 14.133/2021"

// ── Configuração de página com timbre institucional ─────────────────────
#set page(
  paper: "a4",
  margin: (top: 3.6cm, bottom: 3.2cm, left: 2.5cm, right: 2.5cm),
  header: context {
    if counter(page).get().first() > 1 [
      #grid(
        columns: (auto, 1fr),
        column-gutter: 12pt,
        align: horizon,
        _b,
        _h,
      )
      #v(3pt)
      #line(length: 100%, stroke: (paint: c-rule, thickness: 0.6pt))
      #v(1pt)
      #set text(font: "Fira Sans", size: 7.5pt, fill: c-muted)
      #grid(
        columns: (1fr, auto),
        strong[#_ref],
        [#_lei],
      )
    ]
  },
  footer: context {
    if counter(page).get().first() > 1 [
      #line(length: 100%, stroke: (paint: c-rule, thickness: 0.4pt))
      #v(2pt)
      #_f
      #v(-5pt)
      #align(center)[
        #set text(font: "Fira Sans", size: 7pt, fill: c-muted)
        Página #counter(page).display() de #counter(page).final().first()
      ]
    ]
  },
)

// ── Tipografia ───────────────────────────────────────────────────────────
#set text(font: "Fira Sans", size: 10.5pt, lang: "pt", fallback: true)
#set par(justify: true, leading: 0.68em, spacing: 0.95em)
#set list(indent: 1.4em, spacing: 0.45em, body-indent: 0.5em)
#set enum(indent: 1.4em, spacing: 0.45em, body-indent: 0.5em)

// ── Headings ─────────────────────────────────────────────────────────────
#show heading.where(level: 1): it => block(above: 1.6em, below: 0.6em)[
  #grid(
    columns: (auto, 1fr), column-gutter: 10pt, align: horizon,
    block(fill: c-blue, width: 4pt, height: 1.1em, radius: 1pt)[],
    text(size: 11.5pt, weight: "semibold", fill: c-navy)[#it.body],
  )
  #line(length: 100%, stroke: (paint: c-rule, thickness: 0.6pt))
]

#show heading.where(level: 2): it => block(above: 1.1em, below: 0.4em)[
  #text(size: 10.5pt, weight: "semibold", fill: c-blue)[#it.body]
]

// ══════════════════════════════════════════════════════════════════════
//  CAPA
// ══════════════════════════════════════════════════════════════════════
#page(
  header: none,
  footer: none,
  margin: (top: 0pt, bottom: 0pt, left: 0pt, right: 0pt),
  background: rect(fill: c-navy, width: 100%, height: 100%),
)[
  #set text(font: "Fira Sans", fill: white)

  #block(fill: c-blue, width: 100%, inset: (x: 3cm, y: 0pt), height: 1.1cm)[
    #align(horizon)[
      #text(size: 9pt, weight: "semibold", tracking: 0.3pt)[
        PREFEITURA MUNICIPAL DE BORBA — SECRETARIA MUNICIPAL DE SAÚDE
      ]
    ]
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
    // `val` evita shadow de v()
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
    #align(horizon)[
      #text(size: 8pt, fill: c-blue-md)[
        RDC ANVISA 15/2012 • ISO 17665-1:2006 • EN 285:2015 • Lei 14.133/2021
      ]
    ]
  ]
]

// ══════════════════════════════════════════════════════════════════════
//  QUADRO DE IDENTIFICAÇÃO — página isolada
// ══════════════════════════════════════════════════════════════════════
#block(below: 0.7em)[
  #grid(
    columns: (auto, 1fr), column-gutter: 10pt, align: horizon,
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
  ("Rel. de Inoperância", "05 de março de 2026 — Relatório Técnico de Inoperância/Insuficiência, Diretor Hospitalar"),
)

#pagebreak()

// ══════════════════════════════════════════════════════════════════════
//  SEÇÕES
// ══════════════════════════════════════════════════════════════════════

= 1. Fundamento Legal

#legal[
  Art. 75, VIII — _"É dispensável a licitação [...] nos casos de emergência ou de calamidade pública, quando caracterizada urgência de atendimento de situação que possa ocasionar prejuízo ou comprometer a continuidade dos serviços públicos ou a segurança de pessoas [...] e somente para os bens necessários ao atendimento da situação emergencial."_
]

A presente Justificativa fundamenta-se no art. 75, VIII, da Lei Federal n.º 14.133/2021. Os elementos fáticos demonstram o preenchimento *cumulativo* dos quatro requisitos:

+ *Situação emergencial concreta e documentada,* não provocada por omissão da Administração;
+ *Risco direto à segurança de pacientes e profissionais de saúde;*
+ *Comprometimento da continuidade de serviço público essencial de saúde;* e
+ *Objeto delimitado ao estritamente necessário.*

= 2. Caracterização do Município e Vulnerabilidade Geográfica

O Município de Borba, situado na calha do Rio Madeira, possui *34.869 habitantes* no perímetro urbano (IBGE 2025), estendendo sua responsabilidade assistencial a aproximadamente *44 mil pessoas*, incluindo comunidades ribeirinhas e aldeias dispersas ao longo do médio Madeira. A realidade amazônica impõe ao *Hospital Municipal Vó Mundoca* o papel de *unidade de referência isolada.* Remoções aeromédicas ou fluviais até Manaus frequentemente superam 24 horas — tornando a autossuficiência tecnológica da unidade não apenas uma meta administrativa, mas um *imperativo de Segurança Pública e Sanitária.*

#info("Isolamento e Irreversibilidade do Dano")[
  Em Borba, uma infecção cirúrgica grave não pode ser resolvida por transferência rápida. O translado fluvial até Manaus varia de *15 a 40 horas.* Uma sepse pós-operatória sem tratamento especializado imediato representa *risco de óbito evitável* — risco inexistente em municípios com rede hospitalar plural.
]

= 3. Histórico Operacional e Dimensionamento da Demanda (2025)

A necessidade de capacidade mínima de *100 litros* é ratificada pela expressiva atividade assistencial de 2025. O Hospital Vó Mundoca realizou:

- *4 (quatro) grandes mutirões de cirurgias,* incluindo procedimentos de média complexidade e *cirurgias oftalmológicas especializadas;*
- *Fluxo ininterrupto de partos* — único serviço de obstetrícia de toda a área de influência;
- *Urgências traumáticas e clínicas* 24 horas por dia.

A CME opera em *regime de saturação operacional.* O parque tecnológico atingiu seu *limite de fadiga material*, conforme documenta o Relatório Técnico de Inoperância/Insuficiência de 05/03/2026. A especificação de 100 litros não é restritiva — é requisito funcional demonstrado pela demanda real.

= 4. Fato Gerador — Diagnóstico Técnico do Equipamento

== 4.1 Identificação do Equipamento Inoperante

#v(0.4em)
#ficha(
  ("Nº de patrimônio",   "6897"),
  ("Fabricante",         "Phoenix Luferco"),
  ("Ano de fabricação",  "2019 (~6 anos de uso em CME de alta demanda)"),
  ("Tipo",               "Autoclave hospitalar a vapor — câmara única"),
  ("Status atual",       [#text(weight: "semibold", fill: c-red)[INOPERANTE — falha sistêmica múltipla]]),
  ("Relatório técnico",  "Relatório de Inoperância/Insuficiência — 05/03/2026 — Daniel Gomes Vinhote, Decreto n.º 0630/2026 — Anexo II"),
)

== 4.2 Falhas Técnicas Identificadas

#v(0.4em)
#falha-card("F1", "Salto de etapas do ciclo de esterilização")[
  O equipamento transita diretamente da fase de esterilização para a secagem sem concluir o tempo de _plateau._ Essa falha *invalida a garantia de esterilidade* de todos os artigos processados, impedindo o alcance do SAL de $10^(-6)$ exigido pela RDC ANVISA 15/2012.
]

#falha-card("F2", "Não atingimento da temperatura mínima de esterilização")[
  O equipamento falha em alcançar *134 °C ± 1 °C.* O Valor F₀ fica abaixo do mínimo de *15 minutos:*
  #v(5pt)
  #align(center)[
    #block(fill: c-ibg, stroke: (paint: c-ibdr, thickness: 0.4pt), radius: 3pt, inset: (x: 16pt, y: 8pt))[
      $F_0 = integral_0^t 10^((T - 121.1) / z) thin dif t$
      #h(1.5em)
      #text(size: 8.5pt, fill: c-muted)[_T_ = temperatura (°C) #h(0.5em) _z_ = 10 °C #h(0.5em) (_G. stearothermophilus_)]
    ]
  ]
  #v(4pt)
  Com temperatura insuficiente, os artigos são microbiologicamente inseguros mesmo após ciclo completo.
]

#falha-card("F3", "Falha no sistema hidráulico de abastecimento automático")[
  Entrada de água inoperante — intervenção manual obrigatória a cada ciclo, comprometendo: (i) a *padronização* dos ciclos; (ii) a *rastreabilidade* (RDC 15/2012, art. 34); e (iii) a *segurança do operador.*
]

#falha-card("F4", "Instabilidade geral — falha sistêmica múltipla")[
  Comportamento errático com parâmetros de pressão e temperatura inconsistentes. A coexistência de F1–F3 confirma *degradação estrutural simultânea* em múltiplos subsistemas, irrecuperável por manutenção pontual.
]

= 5. Biossegurança, CCIH e Controle de Infecções

A aquisição é condição obrigatória para o cumprimento dos protocolos da *CCIH* e do *NSP* do Hospital Vó Mundoca. A inoperância do equipamento inviabiliza os indicadores biológicos e químicos exigidos pela RDC ANVISA 15/2012, elevando o risco de contaminação cruzada, surtos pós-operatórios e IRAS por *microrganismos multirresistentes* (MRSA, KPC, Acinetobacter).

#aviso("Ônus Fiscal Indireto da Não Aquisição")[
  O custo de uma única internação prolongada por ISC multirresistente pode superar *R\$ 50.000,00.* Além do dano humano irreparável, a omissão expõe o Município à *judicialização por dano ao paciente* — responsabilidade solidária do ente público (CF/88, art. 37, § 6.º).
]

= 6. Caracterização da Situação de Emergência

== 6.1 Impactos Operacionais e Risco de Desassistência

- *Redução crítica da capacidade de esterilização* de instrumentais médico-cirúrgicos;
- *Risco de desabastecimento* para o centro cirúrgico, *centro obstétrico,* pronto-socorro e internação;
- *Violação direta da RDC ANVISA 15/2012,* arts. 5.º, 6.º e 34;
- Em caso de falha definitiva: *paralisação compulsória do centro cirúrgico e obstétrico* — colapso em cidade sem hospital alternativo.

== 6.2 Risco Sanitário e Responsabilidade Institucional

#aviso("Cadeia Causal — Falha de Esterilização → Dano ao Paciente")[
  Falha sistêmica → SAL > 10⁻⁶ → *artigo crítico inseguro* → contato com sítio cirúrgico ou obstétrico → *ISC ou infecção puerperal* → sepse, *óbito evitável* — em Borba, a mais de 24h fluviais de UTI de referência.
]

A operação com equipamento inoperante sujeita o Município a *interdição sanitária,* sanções administrativas ao gestor e *responsabilidade civil solidária* por danos. O *Princípio da Continuidade* é violado: esterilização é atividade-meio essencial para preservação da vida (CF/88, art. 196).

== 6.3 Impossibilidade de Aguardar o Rito Licitatório Regular

#tabela(
  (1fr, 2cm, 3cm),
  ("Etapa do Pregão Eletrônico", "Prazo mín.", "Observação"),
  ("ETP + TR + pesquisa de preços", "15 dias", "Já concluídos"),
  ("Elaboração do edital (CPL + PGM)", "10 dias", ""),
  ("Publicação PNCP até abertura (art. 55, § 2.º)", "8 dias", ""),
  ("Propostas + sessão + habilitação", "15 dias", ""),
  ("Recursos + homologação + assinatura", "10 dias", ""),
  ("Entrega Técnica — período de seca", "90 dias", "Ago–Nov: balsas de menor calado"),
)
#block(
  fill: c-rbg, stroke: (left: (paint: c-red, thickness: 4pt)),
  radius: (right: 3pt), inset: (left: 14pt, right: 12pt, top: 9pt, bottom: 9pt),
)[
  #grid(columns: (1fr, auto), column-gutter: 12pt, align: horizon,
    text(size: 10pt)[*Total estimado até Entrega Técnica: ≈ 148 dias (≈ 5 meses)*],
    text(size: 9.5pt, fill: c-red)[CME sem esterilização segura],
  )
]

= 7. Inviabilidade da Manutenção Corretiva

+ *Falha em quatro subsistemas simultâneos* — degradação estrutural, não pane pontual;
+ *Paralisação adicional durante o reparo:* imobiliza o único equipamento, agravando o risco durante todo o período;
+ *Custo estimado em 60–75% do valor de substituição,* sem garantia de desempenho nem recomposição da garantia;
+ *Ausência de qualificação pós-reparo:* sem nova QI/QO/QD, o SAL permanece incerto;
+ *Fadiga material acelerada:* 6 anos de operação intensiva em UR ≥ 80%.

#info("Por que esta emergência não decorre de omissão administrativa")[
  O TCU e o TCE-AM exigem que a emergência não seja fruto de negligência. No presente caso: (i) equipamento adquirido regularmente em 2019; (ii) falha sistêmica progressiva, abaixo do horizonte de vida útil esperado; (iii) Emenda Parlamentar ativada; e (iv) falha *documentada tempestivamente* em Relatório Técnico formal em 05/03/2026.
]

= 8. Eficiência e Economicidade (Art. 37, CF/88)

A aquisição de equipamento novo é a solução mais econômica em perspectiva sistêmica:

- *Custo acumulado de manutenções paliativas* sem resolução definitiva;
- *Desperdício de insumos* por ciclos com SAL > 10⁻⁶ — descarte de IB e IC;
- *Passivo de responsabilização civil:* uma ISC multirresistente pode superar R\$ 50.000,00;
- *Previsibilidade orçamentária:* 24 meses de garantia + QI/QO/QD documentada.

= 9. Planejamento Estratégico e Metas para 2026

Para 2026, a Secretaria planejou a *expansão do acesso cirúrgico* e redução das *filas reprimidas.* A manutenção desse cronograma depende da modernização da CME — incluindo mutirões em comunidades ribeirinhas (saúde itinerante) e expansão da *resolutividade cirúrgica local.*

= 10. Especificação Técnica Justificada

Baseada na RDC ANVISA 15/2012, ISO 17665-1:2006 e EN 285:2015. Todos os requisitos são necessários e suficientes — sem especificação restritiva à concorrência.

#v(0.4em)
#tabela(
  (3.4cm, 1fr),
  ("Especificação", "Requisito Mínimo e Justificativa"),
  ("Tipo", "Autoclave a vapor saturado, *Tipo B (pré-vácuo)*, horizontal — obrigatório para artigos porosos e com lúmens (RDC 15/2012, art. 15)"),
  ("Câmara", "Capacidade útil *≥ 100 litros;* aço inoxidável *AISI 316L* — justificada por 4 mutirões + partos + urgências em 2025; resistência a cloretos e UR ≥ 80%"),
  ("Sistema de vácuo", "Bomba de anel líquido; pressão absoluta *≤ 30 mbar; mínimo 3 pulsos* — único método eficaz para materiais porosos e lúmens (EN 285:2015, item 8)"),
  ("Temperatura", "105 °C a 135 °C com precisão *± 1 °C* — F₀ ≥ 15 min e SAL 10⁻⁶ (ISO 17665-1:2006)"),
  ("Programas", "Mínimo *13 programas:* poroso 134 °C, sólido 134 °C, líquido 121 °C, Bowie-Dick e Leak Test integrados"),
  ("Interface e rastreabilidade", "Tela colorida *touchscreen;* impressora integrada de ciclos — art. 34 da RDC ANVISA 15/2012"),
  ("Abastecimento d'água", "*Automático* — elimina a falha F3; garante padronização e rastreabilidade"),
  ("Proteção e segurança", "Gabinete elétrico *IP 54;* mínimo *10 sistemas de segurança* incluindo antiesmagamento de porta"),
  ("Periféricos incluídos", "Osmose reversa 60 L/h (≤ 1,3 µS/cm); compressor ar médico isento de óleo ≥ 50 L (ABNT NBR ISO 7396-1:2011); racks AISI 316L ≥ 3 un.; carro inox; IB G. stearothermophilus (cx 50 un.); IC Cl. 5 (cx 200 un.); peças de desgaste 12 meses"),
  ("Qualificações", "*QI + QO + QD* (ISO 17665-1:2006) no CME; ΔT ≤ 2 °C; IB negativos; F₀ ≥ 15 min — condição inafastável do TRD"),
  ("Logística", "*CIF Borba/AM + Entrega Técnica* — frete fluvial Manaus–Borba, seguro Ad Valorem, embalagem antivibração"),
  ("Treinamento", "Mínimo *8 horas* presenciais no CME; certificados nominais — operação, manutenção preventiva, monitoramento e rastreabilidade"),
  ("Garantia e AT", "Mínimo *24 meses* a contar do TRD; atendimento no AM ≤ *72 horas;* solução definitiva ≤ *15 dias corridos*"),
  ("Registro ANVISA", "Obrigatório — registro ativo para o equipamento ofertado"),
  ("RENEM / CATMAT", "Equipamento na RENEM com código CATMAT — Portarias GM/MS 6.870 e 6.904/2025"),
)

= 11. Dotação Orçamentária e Fonte de Recursos

Custeado com *Emenda Parlamentar Estadual* (ALEAM), execução via *Transferegov* (Portarias GM/MS 6.870 e 6.904/2025). Recursos de aplicação vinculada à saúde — sem desvio de objeto.

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
A reserva de *R\$ 20.000,00* para adequação da infraestrutura do CME (rede elétrica trifásica, ponto hidráulico e exaustão) é *recurso municipal próprio, adicional e segregado* da Emenda Parlamentar.

= 12. Prazo da Contratação

Fornecimento de *bem permanente* — contrato limitado a *1 (um) ano* (art. 75, VIII). Prazo de entrega conforme período hidrológico do Rio Madeira:

#tabela(
  (2.4cm, 1.8cm, 1fr, 2.4cm),
  ("Período", "Meses", "Condição Hidrológica", "Prazo Máximo"),
  ("Cheia plena",  "Jan–Mai", "Navegação plena; balsas de grande calado",        "60 dias corridos"),
  ("Vazante",      "Jun–Jul", "Restrições incipientes; monitoramento necessário", "75 dias corridos"),
  ("Seca extrema", "Ago–Nov", "Balsas de menor calado obrigatórias (ANA)",        "90 dias corridos"),
  ("Enchente",     "Dez",     "Normalização progressiva",                         "75 dias corridos"),
)

#v(0.4em)
É *vedada a prorrogação* do contrato emergencial e a recontratação do mesmo fornecedor (_in fine_ do art. 75, VIII).

= 13. Requisitos Formais da Dispensa (Art. 72, Lei 14.133/2021)

#tabela(
  (0.7cm, 1fr, 1.8cm, 3.2cm),
  ("", "Documento", "Artigo", "Status"),
  ("①", "Esta Justificativa de Situação Emergencial",              "Art. 72, I",    "Elaborada — Anexo I"),
  ("②", "Relatório Técnico de Inoperância — Diretor Hospitalar",   "Art. 72, I",    "Elaborado — Anexo II (05/03/2026)"),
  ("③", "Termo de Referência com especificações técnicas",         "Art. 72, III",  "Elaborado — Anexo III"),
  ("④", "Pesquisa de preços — mínimo 3 cotações formalizadas",     "Art. 72, IV",   "A realizar — modelo Anexo IV"),
  ("⑤", "Planilha comparativa e seleção fundamentada",             "Art. 72, VII",  "A elaborar após cotações"),
  ("⑥", "Confirmação de disponibilidade orçamentária da emenda",   "Art. 72, VI",   "A juntar — confirmação ALEAM"),
  ("⑦", "Contrato de Fornecimento",                                "Art. 72, VIII", "Minuta — Anexo V"),
  ("⑧", "Publicação no PNCP em até 10 dias úteis",                 "Art. 174",      "Após assinatura"),
)

#v(0.5em)
#alerta[
  *Dispensas por emergência são alvo prioritário de auditoria pelo TCE-AM.* Riscos mais comuns de glosa: (i) pesquisa de preços com menos de 3 cotações válidas; (ii) urgência fundada apenas em declarações genéricas, sem Relatório Técnico objetivo; (iii) equipamento não consta da RENEM; (iv) ausência de publicação no PNCP em 10 dias úteis.
]

= 14. Conclusão e Recomendação

A urgência aqui caracterizada é *objetiva, concreta e atual.* A aquisição da autoclave é o instrumento jurídico e técnico que permitirá ao Hospital Vó Mundoca honrar o pacto do SUS com a população borbense.

#v(0.4em)
#block(
  width: 100%, fill: c-gbg,
  stroke: (left: (paint: c-green, thickness: 4pt)),
  radius: (right: 3pt), inset: (left: 14pt, right: 12pt, top: 12pt, bottom: 12pt),
  spacing: 0.9em,
)[
  #check[*Situação emergencial concreta, documentada e não provocada por omissão:* autoclave nº 6897 (Phoenix Luferco, 2019) em falha sistêmica múltipla — Relatório de 05/03/2026, Daniel Gomes Vinhote (Decreto n.º 0630/2026).]
  #v(6pt)
  #check[*Risco direto à segurança de pacientes e profissionais,* com potencial para ISC, infecção puerperal, IRAS e óbito evitável — amplificado pelo translado de 15 a 40 horas até UTI de referência.]
  #v(6pt)
  #check[*Comprometimento da continuidade do serviço público,* com risco de paralisação do centro cirúrgico e obstétrico em município sem hospital alternativo.]
  #v(6pt)
  #check[*Inviabilidade da manutenção corretiva,* inclusive pela paralisação adicional do único equipamento durante o reparo.]
  #v(6pt)
  #check[*Eficiência e economicidade:* manutenções paliativas + desperdício por ciclos falhos + passivo de judicialização superam o investimento em ativo novo com 24 meses de garantia.]
  #v(6pt)
  #check[*Objeto delimitado ao estritamente necessário* — capacidade de 100 L ratificada por 4 mutirões + partos + urgências em 2025.]
]

#v(0.8em)
Recomenda-se a *imediata abertura do procedimento de contratação direta,* com publicação do aviso de dispensa no PNCP (art. 72, III) e instrução com os documentos da Seção 13.

// ══════════════════════════════════════════════════════════════════════
//  ASSINATURAS + BASE NORMATIVA — bloco indivisível
// ══════════════════════════════════════════════════════════════════════
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
    RDC ANVISA n.º 15/2012 •
    ISO 17665-1:2006 (validação calor úmido) •
    EN 285:2015 (esterilizadores a vapor) •
    ABNT NBR ISO 7396-1:2011 (ar médico) •
    IN SEGES/MGI n.º 65/2021 •
    Portarias GM/MS n.º 6.870 e 6.904/2025 •
    CF/88, arts. 37, § 6.º, e 196.
  ]
]
