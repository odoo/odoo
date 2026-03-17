// ╔══════════════════════════════════════════════════════════════════╗
// ║  TEMPLATE REUTILIZÁVEL — Justificativa de Emergência           ║
// ║  Lógica visual e argumentativa independente do caso            ║
// ║  Importa variáveis de dados.typ                                ║
// ╚══════════════════════════════════════════════════════════════════╝

#import "dados.typ": *

// ═══════════════════════════════════════════════════════════════════
// PALETA E TIPOGRAFIA
// ═══════════════════════════════════════════════════════════════════

#let cor = (
  primaria:    rgb("#00703C"),   // verde institucional
  secundaria:  rgb("#F7941D"),   // laranja institucional
  legal:       rgb("#1A3E6C"),   // azul jurídico
  alerta:      rgb("#C0392B"),   // vermelho de risco
  texto:       rgb("#1A1A1A"),
  subtexto:    rgb("#555555"),
  fundo_sec:   rgb("#EAF4EC"),   // verde muito claro
  fundo_alt:   rgb("#F2F9F4"),   // alternância de linha
  fundo_aviso: rgb("#FFF8EE"),   // laranja muito claro
  fundo_risco: rgb("#FFF0EE"),   // vermelho muito claro
  borda:       rgb("#C0D6C5"),
  branco:      white,
)

// ═══════════════════════════════════════════════════════════════════
// CONFIGURAÇÃO DE PÁGINA
// ═══════════════════════════════════════════════════════════════════

#set page(
  paper: "a4",
  margin: (top: 2.2cm, bottom: 2.4cm, left: 2.4cm, right: 2.2cm),
  footer: context [
    #set text(size: 7.5pt, fill: cor.subtexto, font: "Liberation Sans")
    #line(length: 100%, stroke: 0.5pt + cor.borda)
    #v(3pt)
    #grid(
      columns: (1fr, auto),
      align(left)[
        #ente.secretaria — #ente.prefeitura #sym.bar.v
        #ente.endereco — CEP #ente.cep — #ente.telefone
      ],
      align(right)[
        Processo #processo.numero #sym.bar.v
        Pág. #counter(page).display("1 de 1", both: true)
      ]
    )
  ]
)

#set text(
  font:   "Liberation Sans",
  size:   10pt,
  fill:   cor.texto,
  lang:   "pt",
)

#set par(
  justify:     true,
  leading:     0.72em,
  spacing:     0.85em,
)

#show heading: it => it  // headings controlados manualmente

// ═══════════════════════════════════════════════════════════════════
// COMPONENTES REUTILIZÁVEIS
// ═══════════════════════════════════════════════════════════════════

// ── Linha divisória com cor ──────────────────────────────────────
#let divider(c: cor.borda, espessura: 0.5pt) = {
  line(length: 100%, stroke: espessura + c)
}

// ── Cabeçalho institucional ──────────────────────────────────────
#let cabecalho() = {
  grid(
    columns: (1fr),
    align(center)[
      #text(weight: "bold", size: 15pt, fill: cor.primaria,
        upper(ente.prefeitura)
      )
      #v(2pt)
      #text(size: 9pt, fill: cor.subtexto)[
        #ente.secretaria — Gabinete #ente.sigla_sec
      ]
      #v(1pt)
      #text(size: 7.5pt, fill: rgb("#888888"))[
        #ente.endereco #sym.bar.v CEP #ente.cep — #ente.municipio/#ente.estado
        #sym.bar.v Tel.: #ente.telefone
      ]
    ]
  )
  v(4pt)
  // barra laranja
  rect(width: 100%, height: 3pt, fill: cor.secundaria, radius: 1pt)
  v(4pt)
  // barra verde fina
  rect(width: 100%, height: 1pt, fill: cor.primaria)
  v(14pt)
}

// ── Bloco de título do documento ─────────────────────────────────
#let titulo_doc() = {
  align(center)[
    #block(
      fill: cor.primaria,
      radius: 6pt,
      inset: (x: 20pt, y: 10pt),
      width: 100%,
    )[
      #text(weight: "bold", size: 13pt, fill: white, tracking: 1.5pt,
        upper("Justificativa de Situação Emergencial")
      )
    ]
    #v(6pt)
    #text(size: 10pt, fill: cor.legal)[
      *#objeto.descricao_curta — #hospital.setor*
    ]
    #v(3pt)
    #text(size: 9pt, fill: cor.subtexto)[
      #processo.tipo — #processo.amparo_legal
    ]
    #v(2pt)
    #text(size: 8pt, fill: cor.subtexto)[
      Processo Administrativo n.º #processo.numero
    ]
    #v(4pt)
    #text(size: 7.5pt, fill: rgb("#999999"))[
      #objeto.normas.join("  ·  ")
    ]
  ]
  v(14pt)
}

// ── Heading de seção principal ───────────────────────────────────
#let h1(num, titulo) = {
  v(12pt)
  grid(
    columns: (auto, 1fr),
    column-gutter: 8pt,
    align(horizon)[
      #box(
        fill: cor.primaria,
        radius: 3pt,
        inset: (x: 7pt, y: 4pt),
      )[
        #text(weight: "bold", size: 9pt, fill: white)[#num]
      ]
    ],
    align(horizon)[
      #text(weight: "bold", size: 11pt, fill: cor.primaria, upper(titulo))
    ]
  )
  v(2pt)
  line(length: 100%, stroke: 1.5pt + cor.primaria)
  v(6pt)
}

// ── Heading de subseção ──────────────────────────────────────────
#let h2(titulo) = {
  v(8pt)
  text(weight: "bold", size: 10pt, fill: cor.legal)[#titulo]
  v(1pt)
  line(length: 100%, stroke: 0.5pt + cor.borda)
  v(5pt)
}

// ── Item de bullet estilizado ─────────────────────────────────────
#let item(body) = {
  grid(
    columns: (8pt, 1fr),
    column-gutter: 6pt,
    align(top)[
      #box(
        fill: cor.secundaria,
        radius: 50%,
        width: 5pt, height: 5pt,
        inset: 0pt,
      )
      #v(3pt)  // alinhamento vertical
    ],
    par(justify: true)[#body]
  )
  v(2pt)
}

// ── Item check (conclusão) ────────────────────────────────────────
#let check_item(body) = {
  grid(
    columns: (14pt, 1fr),
    column-gutter: 4pt,
    align(top)[
      #text(size: 11pt, fill: cor.primaria, weight: "bold")[✓]
    ],
    par(justify: true, leading: 0.72em)[#body]
  )
  v(4pt)
}

// ── Caixa de destaque legal ───────────────────────────────────────
#let caixa_legal(body) = {
  block(
    width: 100%,
    fill: rgb("#EEF3FA"),
    stroke: (left: 4pt + cor.legal),
    radius: (right: 4pt),
    inset: (left: 14pt, right: 12pt, top: 10pt, bottom: 10pt),
  )[
    #text(size: 9pt, fill: cor.legal)[#body]
  ]
  v(6pt)
}

// ── Caixa de alerta/atenção ───────────────────────────────────────
#let caixa_alerta(titulo: "ATENÇÃO", body) = {
  block(
    width: 100%,
    fill: cor.fundo_aviso,
    stroke: (left: 4pt + cor.secundaria, rest: 0.5pt + rgb("#F0C080")),
    radius: 4pt,
    inset: (x: 14pt, y: 10pt),
  )[
    #text(weight: "bold", size: 8.5pt, fill: rgb("#7D4000"))[⚠ #titulo — ]
    #text(size: 8.5pt, fill: rgb("#5A3000"))[#body]
  ]
  v(6pt)
}

// ── Caixa de risco crítico ────────────────────────────────────────
#let caixa_risco(titulo, body) = {
  block(
    width: 100%,
    fill: cor.fundo_risco,
    stroke: (left: 4pt + cor.alerta, rest: 0.5pt + rgb("#F0B0A0")),
    radius: 4pt,
    inset: (x: 14pt, y: 10pt),
  )[
    #text(weight: "bold", size: 8.5pt, fill: cor.alerta)[🔴 #titulo]
    #v(3pt)
    #text(size: 9pt, fill: rgb("#5C0000"))[#body]
  ]
  v(6pt)
}

// ── Tabela de identificação (2 colunas chave-valor) ───────────────
#let tabela_id(dados) = {
  let n = dados.len()
  table(
    columns: (28%, 72%),
    stroke: 0.5pt + cor.borda,
    fill: (col, row) => {
      if col == 0 { if calc.rem(row, 2) == 0 { cor.fundo_sec } else { white } }
      else        { if calc.rem(row, 2) == 0 { cor.fundo_sec } else { white } }
    },
    inset: (x: 8pt, y: 6pt),
    ..dados.map(par => (
      text(weight: "bold", size: 8.5pt, fill: cor.primaria)[#par.at(0)],
      text(size: 8.5pt)[#par.at(1)],
    )).flatten()
  )
  v(6pt)
}

// ── Tabela de falhas técnicas ─────────────────────────────────────
#let tabela_falhas(lista) = {
  table(
    columns: (5%, 22%, 73%),
    stroke: 0.5pt + cor.borda,
    fill: (col, row) => {
      if row == 0 { cor.primaria }
      else if col == 0 { cor.alerta }
      else if calc.rem(row, 2) == 0 { white }
      else { cor.fundo_alt }
    },
    inset: (x: 7pt, y: 6pt),
    // Header
    text(weight: "bold", size: 8.5pt, fill: white)[Cód.],
    text(weight: "bold", size: 8.5pt, fill: white)[Falha],
    text(weight: "bold", size: 8.5pt, fill: white)[Descrição e Impacto Normativo],
    // Dados
    ..lista.map(f => (
      align(center)[#text(weight: "bold", size: 9pt, fill: white)[#f.cod]],
      text(weight: "bold", size: 8.5pt, fill: cor.legal)[#f.titulo],
      text(size: 8.5pt)[#f.desc #h(4pt) #text(size: 7.5pt, fill: cor.subtexto, style: "italic")[(#f.norma)]],
    )).flatten()
  )
  v(6pt)
}

// ── Tabela de especificações ──────────────────────────────────────
#let tabela_especificacoes(lista) = {
  table(
    columns: (22%, 78%),
    stroke: 0.5pt + cor.borda,
    fill: (col, row) => {
      if calc.rem(row, 2) == 0 { cor.fundo_sec } else { white }
    },
    inset: (x: 8pt, y: 6pt),
    ..lista.map(e => (
      text(weight: "bold", size: 8.5pt, fill: cor.primaria)[#e.k],
      text(size: 8.5pt)[#e.v],
    )).flatten()
  )
  v(6pt)
}

// ── Tabela de orçamento ───────────────────────────────────────────
#let tabela_orcamento(orc) = {
  let n_itens = orc.itens.len()
  table(
    columns: (1fr, auto, auto),
    stroke: 0.5pt + cor.borda,
    fill: (col, row) => {
      if row == 0 { cor.primaria }
      else if row == n_itens + 1 { cor.legal }
      else if calc.rem(row, 2) == 0 { white }
      else { cor.fundo_alt }
    },
    inset: (x: 8pt, y: 6pt),
    // Header
    text(weight: "bold", size: 8.5pt, fill: white)[Componente],
    text(weight: "bold", size: 8.5pt, fill: white)[Valor (R$)],
    text(weight: "bold", size: 8.5pt, fill: white)[%],
    // Itens
    ..orc.itens.map(it => (
      text(size: 8.5pt)[#it.at(0)],
      align(right)[#text(size: 8.5pt)[#it.at(1)]],
      align(right)[#text(size: 8.5pt)[#it.at(2)]],
    )).flatten(),
    // Total
    text(weight: "bold", size: 9pt, fill: white)[TOTAL — #processo.fonte],
    align(right)[#text(weight: "bold", size: 9pt, fill: white)[#orc.total]],
    align(right)[#text(weight: "bold", size: 9pt, fill: white)[#orc.total_pct]],
  )
  v(4pt)
  text(size: 8pt, fill: cor.subtexto, style: "italic")[#orc.obs]
  v(6pt)
}

// ── Tabela hidrológica ────────────────────────────────────────────
#let tabela_hidro(lista) = {
  table(
    columns: (12%, 17%, 1fr, 14%),
    stroke: 0.5pt + cor.borda,
    fill: (col, row) => {
      if row == 0 { cor.primaria }
      else if calc.rem(row, 2) == 0 { white }
      else { cor.fundo_alt }
    },
    inset: (x: 8pt, y: 6pt),
    text(weight: "bold", size: 8.5pt, fill: white)[Período],
    text(weight: "bold", size: 8.5pt, fill: white)[Fase],
    text(weight: "bold", size: 8.5pt, fill: white)[Condição Hidrológica],
    text(weight: "bold", size: 8.5pt, fill: white)[Prazo Máximo],
    ..lista.map(r => (
      text(weight: "bold", size: 8.5pt)[#r.periodo],
      text(size: 8.5pt, fill: cor.legal)[#r.fase],
      text(size: 8.5pt)[#r.cond],
      align(center)[#text(weight: "bold", size: 8.5pt, fill: cor.primaria)[#r.prazo]],
    )).flatten()
  )
  v(6pt)
}

// ── Tabela de prazo licitatório ───────────────────────────────────
#let tabela_prazo_licit(pl) = {
  let n = pl.etapas.len()
  table(
    columns: (1fr, 14%, 28%),
    stroke: 0.5pt + cor.borda,
    fill: (col, row) => {
      if row == 0 { cor.legal }
      else if row == n + 1 { cor.alerta }
      else if calc.rem(row, 2) == 0 { white }
      else { cor.fundo_alt }
    },
    inset: (x: 8pt, y: 6pt),
    text(weight: "bold", size: 8.5pt, fill: white)[Etapa do Pregão Eletrônico],
    text(weight: "bold", size: 8.5pt, fill: white)[Prazo Mín.],
    text(weight: "bold", size: 8.5pt, fill: white)[Observação],
    ..pl.etapas.map(e => (
      text(size: 8.5pt)[#e.at(0)],
      align(center)[#text(size: 8.5pt)[#e.at(1)]],
      text(size: 8pt, fill: cor.subtexto)[#e.at(2)],
    )).flatten(),
    // Linha total em vermelho
    text(weight: "bold", size: 8.5pt, fill: white)[Total estimado até Entrega Técnica],
    align(center)[#text(weight: "bold", size: 9pt, fill: white)[#pl.total_dias]],
    text(weight: "bold", size: 8.5pt, fill: white)[#pl.total_obs],
  )
  v(6pt)
}

// ── Tabela de requisitos formais ──────────────────────────────────
#let tabela_requisitos(lista) = {
  let status_cor(s) = {
    if s.contains("Elaborad") or s.contains("Elaborad") { cor.primaria }
    else if s.contains("realizar") or s.contains("elaborar") { cor.secundaria }
    else { cor.subtexto }
  }
  table(
    columns: (4%, 1fr, 13%, 25%),
    stroke: 0.5pt + cor.borda,
    fill: (col, row) => {
      if row == 0 { cor.primaria }
      else if col == 3 and row > 0 { rgb("#F8FBF8") }
      else if calc.rem(row, 2) == 0 { white }
      else { cor.fundo_alt }
    },
    inset: (x: 7pt, y: 6pt),
    text(weight: "bold", size: 8.5pt, fill: white)[Nº],
    text(weight: "bold", size: 8.5pt, fill: white)[Documento],
    text(weight: "bold", size: 8.5pt, fill: white)[Artigo],
    text(weight: "bold", size: 8.5pt, fill: white)[Status],
    ..lista.map(r => (
      align(center)[#text(weight: "bold", size: 9pt)[#r.at(0)]],
      text(size: 8.5pt)[#r.at(1)],
      align(center)[#text(size: 8pt, fill: cor.legal, style: "italic")[#r.at(2)]],
      text(weight: "bold", size: 8pt, fill: status_cor(r.at(3)))[#r.at(3)],
    )).flatten()
  )
  v(6pt)
}

// ── Bloco de assinaturas ──────────────────────────────────────────
#let bloco_assinaturas(r) = {
  v(20pt)
  align(center)[#text(size: 9pt, fill: cor.subtexto)[#processo.data_local]]
  v(20pt)
  grid(
    columns: (1fr, 1fr, 1fr),
    column-gutter: 16pt,
    ..( r.cme, r.diretor, r.secretaria ).map(sig => {
      block(
        stroke: (top: 1.5pt + cor.primaria),
        inset: (top: 10pt, bottom: 0pt),
        width: 100%,
      )[
        #text(weight: "bold", size: 9pt)[#sig.nome]
        #linebreak()
        #text(size: 8pt, fill: cor.subtexto)[#sig.cargo]
        #linebreak()
        #text(size: 7.5pt, fill: cor.subtexto)[#sig.org]
        #if "decreto" in sig.keys() [
          #linebreak()
          #text(size: 7.5pt, fill: cor.subtexto, style: "italic")[#sig.decreto]
        ]
      ]
    })
  )
}

// ── Rodapé normativo ─────────────────────────────────────────────
#let nota_normativa(normas) = {
  v(10pt)
  divider(c: cor.borda)
  v(4pt)
  text(size: 7.5pt, fill: cor.subtexto)[
    *Base normativa:* #normas.join("  ·  ")
  ]
}

// ═══════════════════════════════════════════════════════════════════
// DOCUMENTO
// ═══════════════════════════════════════════════════════════════════

// ── CAPA / CABEÇALHO ────────────────────────────────────────────
#cabecalho()
#titulo_doc()

// ── TABELA DE IDENTIFICAÇÃO ──────────────────────────────────────
#tabela_id((
  ("Processo Administrativo",  processo.numero),
  ("Unidade Solicitante",       ente.secretaria + " — " + ente.municipio + "/" + ente.estado),
  ("Setor / Local",             hospital.setor + " — " + hospital.nome),
  ("Responsável (CME)",         responsaveis.cme.nome),
  ("Objeto",                    objeto.descricao_completa),
  ("Equipamento Substituído",   equip_substituido.fabricante + " nº " + equip_substituido.patrimonio + " — fab. " + equip_substituido.ano_fab + " (" + equip_substituido.anos_uso + " anos de uso)"),
  ("Fundamentação Legal",       processo.amparo_legal + " — Dispensa por Emergência Administrativa"),
  ("Fonte de Recursos",         processo.fonte),
  ("Valor Estimado",            processo.valor_total + " (" + processo.valor_extenso + ")"),
  ("Data do Rel. Técnico",      processo.data_laudo),
  ("Data desta Justificativa",  processo.data_doc),
))

// ═══════════════════════════════════════════════════════════
#h1("1", "Fundamento Legal")

O presente processo fundamenta-se no *art. 75, inciso VIII, da Lei Federal n.º 14.133/2021*, que autoriza a dispensa de licitação nas situações de emergência ou calamidade pública que comprometam a continuidade de serviços públicos essenciais ou a segurança de pessoas. Os elementos fáticos expostos nas seções seguintes demonstram o preenchimento *cumulativo* dos três requisitos legais:

#grid(
  columns: (1fr, 1fr, 1fr),
  column-gutter: 10pt,
  ..( 
    ("①", "Situação emergencial\nconcreta e documentada,\nnão provocada por omissão"),
    ("②", "Risco direto à segurança\nde pacientes e\nprofissionais de saúde"),
    ("③", "Objeto delimitado ao\nestritamente necessário\nao atendimento"),
  ).map(card => {
    block(
      fill: cor.fundo_sec,
      stroke: 1pt + cor.primaria,
      radius: 6pt,
      inset: (x: 10pt, y: 10pt),
      width: 100%,
    )[
      #align(center)[
        #text(weight: "bold", size: 16pt, fill: cor.primaria)[#card.at(0)]
        #v(3pt)
        #text(size: 8.5pt, fill: cor.legal)[#card.at(1)]
      ]
    ]
  })
)

#v(8pt)
#caixa_legal[
  *Art. 75, VIII* — _"É dispensável a licitação \[...\] nos casos de emergência ou de calamidade pública, quando caracterizada urgência de atendimento de situação que possa ocasionar prejuízo ou comprometer a continuidade dos serviços públicos ou a segurança de pessoas \[...\] e somente para os bens necessários ao atendimento da situação emergencial."_
]

// ═══════════════════════════════════════════════════════════
#h1("2", "Fato Gerador — Diagnóstico do Equipamento")

#h2("2.1  Caracterização do Município e da Vulnerabilidade Geográfica")

O Município de #ente.municipio, situado na calha do Rio Madeira, atende uma população estimada em *#hospital.pop_abrangencia habitantes* em sua área de abrangência, incluindo vastas comunidades ribeirinhas. A população urbana, conforme o IBGE #hospital.pop_ibge_ano, é de *#hospital.pop_ibge habitantes* — todos dependentes de *#hospital.referencia*. O acesso à capital Manaus pode superar *#hospital.tempo_capital*, tornando a autossuficiência tecnológica da unidade um imperativo de Segurança Pública e Sanitária.

#h2("2.2  Equipamento Inoperante")

O #hospital.nome dispõe de uma única autoclave instalada na CME. O equipamento encontra-se *#upper(equip_substituido.status)*, conforme relatório técnico formal lavrado pelo Diretor Hospitalar.

#tabela_id((
  ("Nº de Patrimônio",    equip_substituido.patrimonio),
  ("Fabricante",          equip_substituido.fabricante),
  ("Ano de Fabricação",   equip_substituido.ano_fab + " (" + equip_substituido.anos_uso + " anos de uso)"),
  ("Tipo",                equip_substituido.tipo),
  ("Localização",         equip_substituido.localizacao),
  ("Status Atual",        equip_substituido.status),
  ("Laudo Técnico",       "Relatório formal — " + responsaveis.diretor.nome + " (" + responsaveis.diretor.decreto + ") — Anexo II"),
))

#h2("2.3  Falhas Técnicas Identificadas (diagnóstico de " + processo.data_laudo + ")")

#tabela_falhas(falhas)

// ═══════════════════════════════════════════════════════════
#h1("3", "Histórico de Alta Produtividade e Dimensão da Emergência")

A necessidade de uma autoclave com capacidade de *#objeto.justificativa_capacidade* é ratificada pela intensa atividade cirúrgica de 2025. O #hospital.nome realizou *04 (quatro) grandes mutirões de cirurgias*, abrangendo procedimentos de média complexidade, intervenções eletivas e cirurgias oftalmológicas especializadas, além do fluxo ininterrupto de partos e urgências traumáticas. A CME opera habitualmente em regime de saturação.

A inoperância do único equipamento disponível não representa mera redução de capacidade — representa *colapso total do sistema de esterilização* do único hospital de referência regional, afetando diretamente todos os procedimentos invasivos realizados na unidade.

// ═══════════════════════════════════════════════════════════
#h1("4", "Caracterização da Situação de Emergência")

#h2("4.1  Impactos Operacionais Imediatos")

#item[Redução crítica da capacidade de esterilização de instrumentais médico-cirúrgicos utilizados em cirurgias, curativos e procedimentos invasivos;]
#item[Risco de desabastecimento de materiais esterilizados para o centro cirúrgico, pronto-socorro e unidades de internação;]
#item[Impossibilidade de garantir a eficácia da esterilização — violação direta dos arts. 5.º, 6.º e 34 da RDC ANVISA 15/2012;]
#item[Exposição dos profissionais de saúde a materiais potencialmente contaminados durante o reprocessamento manual emergencial.]

#h2("4.2  Biossegurança e Controle de Infecções (CCIH/NSP)")

A aquisição pleiteada é condição técnica obrigatória para o cumprimento dos protocolos estabelecidos pela Comissão de Controle de Infecção Hospitalar (CCIH) e pelo Núcleo de Segurança do Paciente (NSP). A esterilização por vapor saturado sob pressão com monitoramento microprocessado é a barreira primária contra a proliferação de microrganismos multirresistentes no ambiente hospitalar.

A utilização de equipamentos obsoletos compromete a eficácia dos indicadores biológicos e químicos, inviabilizando o monitoramento rigoroso exigido pela RDC 15/2012, elevando o risco de contaminação cruzada e surtos infecciosos pós-operatórios — com o consequente ônus financeiro ao município com o prolongamento de internações e o uso de antibióticos de alto custo.

#h2("4.3  Risco Sanitário Direto ao Paciente")

#caixa_risco("Cadeia Causal — Falha de Esterilização → Dano ao Paciente")[
  Falha sistêmica do equipamento *→* SAL > 10⁻⁶ *→* artigo crítico inseguro *→* contato com sítio cirúrgico *→* Infecção de Sítio Cirúrgico (ISC) ou IRAS sistêmica *→* morbidade, internação prolongada, sepse, *óbito evitável*.

  No interior do Amazonas, onde o tempo de acesso a Manaus pode superar 24 horas por via fluvial, a evolução de uma ISC grave sem tratamento imediato configura risco de morte *diretamente atribuível* à falha de esterilização.
]

O uso de equipamentos obsoletos eleva o risco de IRAS, sujeitando o município a sanções sanitárias, à judicialização por danos aos pacientes e à violação do dever constitucional de continuidade do serviço de saúde (CF/88, art. 196).

#h2("4.4  Inviabilidade de Aguardar o Rito Licitatório Regular")

Um Pregão Eletrônico para aquisição deste bem demandaria, em condições normais:

#tabela_prazo_licit(prazo_licit)

Cinco meses de operação hospitalar sem autoclave funcional — em hospital de referência regional realizando cirurgias e atendimentos de urgência — configura risco inaceitável à vida humana.

// ═══════════════════════════════════════════════════════════
#h1("5", "Inviabilidade da Manutenção Corretiva")

A natureza múltipla e sistêmica das falhas F1 a F4 torna a manutenção corretiva *economicamente inviável* e tecnicamente insuficiente:

#item[*Degradação estrutural:* falha simultânea em quatro subsistemas críticos (controle de ciclos, sistema térmico, hidráulico e estabilidade operacional geral) — não pane pontual reparável;]
#item[*Obsolescência acelerada:* #equip_substituido.anos_uso anos de uso em CME de alta rotatividade; umidade relativa ≥ 80% e temperatura 26–34 °C no Amazonas aceleram a degradação de componentes eletrônicos e guarnições;]
#item[*Custo inviável:* restauração dos quatro subsistemas no interior do Amazonas representa custo estimado de *60–75% do valor de substituição*, sem garantia de desempenho e sem recomposição do período de garantia;]
#item[*Ausência de qualificação pós-reparo:* mesmo reparado, o equipamento não seria submetido a nova qualificação documentada (QI/QO/QD), mantendo incerteza permanente sobre o SAL efetivamente alcançado.]

#caixa_alerta(titulo: "Jurisprudência TCU/TCE-AM")[
  A emergência não decorre de omissão administrativa: (i) o equipamento foi adquirido regularmente em #equip_substituido.ano_fab; (ii) a falha sistêmica ocorreu de forma progressiva e imprevisível, abaixo do horizonte de vida útil esperado (10–15 anos); (iii) a Emenda Parlamentar estava disponível; (iv) a falha foi documentada tempestivamente pelo Diretor Hospitalar. O gestor agiu com diligência ao identificar, formalizar e imediatamente encaminhar a solução.
]

// ═══════════════════════════════════════════════════════════
#h1("6", "Especificação Técnica Justificada")

Especificação elaborada com base em *RDC ANVISA 15/2012*, *ISO 17665-1:2006* e *EN 285:2015*, nas características operacionais do CME (#hospital.leitos leitos, cirurgias de urgência e eletivas) e nas condições climáticas da Amazônia.

#tabela_especificacoes(especificacoes)

// ═══════════════════════════════════════════════════════════
#h1("7", "Planejamento Estratégico e Metas para 2026")

Para o exercício de 2026, a #ente.secretaria planejou a expansão do acesso cirúrgico, com novas ações programadas e o aumento da oferta de procedimentos para reduzir as filas reprimidas. A manutenção do cronograma é *diretamente dependente da modernização da CME*. A aquisição deste equipamento visa garantir que o hospital não apenas reponha um item depreciado, mas possua a infraestrutura necessária para suportar o incremento de demanda planejado, assegurando a continuidade das políticas de saúde itinerante e hospitalar.

// ═══════════════════════════════════════════════════════════
#h1("8", "Eficiência e Economicidade")

Embora expressivo, o valor de mercado para equipamentos de #objeto.justificativa_capacidade com tecnologia microprocessada e rastreabilidade representa a *solução mais econômica* sob o prisma da Eficiência (CF/88, art. 37). O custo acumulado de manutenções paliativas, somado ao risco de desperdício de insumos por ciclos falhos e ao potencial de prolongamento de internações por IRAS, justifica o investimento em ativo novo com garantia técnica plena — otimizando o gasto público em longo prazo e evitando passivos sanitários e judiciais ao Município.

// ═══════════════════════════════════════════════════════════
#h1("9", "Dotação Orçamentária e Fonte de Recursos")

A aquisição é custeada com *#processo.fonte*, destinada à #ente.secretaria para equipamentos hospitalares. A execução financeira ocorrerá via Transferegov (Ministério da Saúde), observadas as Portarias GM/MS n.º 6.870 e 6.904/2025.

#tabela_orcamento(orcamento)

// ═══════════════════════════════════════════════════════════
#h1("10", "Prazo da Contratação")

Nos termos do art. 75, VIII, da Lei n.º 14.133/2021, a contratação emergencial é limitada ao prazo de 1 (um) ano. O prazo de entrega será estipulado conforme o período hidrológico do Rio Madeira vigente na data de assinatura do contrato:

#tabela_hidro(prazos_hidro)

Atraso comprovadamente causado por seca extrema declarada pela ANA não configurará mora do fornecedor, desde que comunicado ao Gestor com antecedência mínima de 15 dias e comprovado com declaração da empresa de navegação e boletim da ANA. É *vedada* a prorrogação do contrato emergencial e a recontratação do mesmo fornecedor sob esta hipótese (_art. 75, VIII, in fine_).

// ═══════════════════════════════════════════════════════════
#h1("11", "Requisitos Formais da Dispensa")

Em cumprimento ao art. 72 da Lei n.º 14.133/2021, o processo deve ser instruído com:

#tabela_requisitos(requisitos_formais)

#caixa_alerta(titulo: "Riscos de Glosa — TCE-AM")[
  Dispensas por emergência de alto valor são alvo prioritário de auditoria. Os riscos mais comuns: (i) ausência ou insuficiência da pesquisa de preços; (ii) urgência documentada apenas com declarações genéricas, sem laudo técnico; (iii) contratação de empresa sem capacidade técnica comprovada; (iv) ausência de publicação no PNCP no prazo legal. Esta Justificativa, o Laudo do Diretor Hospitalar e as 3 cotações de mercado formam o conjunto mínimo para defesa sólida em eventual tomada de contas especial.
]

// ═══════════════════════════════════════════════════════════
#h1("12", "Conclusão e Recomendação")

Ante o exposto, a urgência aqui caracterizada é *objetiva, concreta e atual*. Estão configurados cumulativamente todos os pressupostos legais para a contratação direta por emergência:

#v(4pt)
#for chk in conclusao_checks {
  check_item(chk)
}

#v(6pt)
A aquisição da autoclave é o instrumento jurídico e técnico que permitirá ao *#hospital.nome* continuar honrando o pacto do SUS com a população de #ente.municipio, preservando a vida e a dignidade assistencial no interior do #ente.sigla_estado.

#v(6pt)
*Recomenda-se a imediata abertura do procedimento de contratação direta, com as seguintes providências:*

#item[Publicação do aviso de dispensa no PNCP, nos termos do art. 72, III;]
#item[Instrução do processo com esta Justificativa, o Laudo Técnico (Anexo II), o Termo de Referência (Anexo III) e pesquisa de preços com mínimo de 3 cotações (Anexo IV);]
#item[Seleção do fornecedor com proposta mais vantajosa, compatível com as especificações técnicas e com o registro do equipamento na RENEM;]
#item[Assinatura do Contrato de Fornecimento com cláusula de Entrega Técnica (QI/QO/QD) e garantia mínima de 24 meses;]
#item[Publicação da contratação no PNCP em até 10 dias úteis da assinatura (art. 174).]

// ── ASSINATURAS ─────────────────────────────────────────────────
#bloco_assinaturas(responsaveis)

// ── NOTA NORMATIVA ───────────────────────────────────────────────
#nota_normativa(base_normativa)
