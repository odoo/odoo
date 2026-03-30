// ╔══════════════════════════════════════════════════════════════════╗
// ║  DADOS DO CASO — único arquivo que muda entre processos         ║
// ║  Alimentado automaticamente pelo sistema de geração de modelos  ║
// ╚══════════════════════════════════════════════════════════════════╝

// ── IDENTIFICAÇÃO DO ENTE ────────────────────────────────────────────
#let ente = (
  municipio:     "Borba",
  estado:        "AM",
  sigla_estado:  "Amazonas",
  prefeitura:    "Prefeitura Municipal de Borba",
  secretaria:    "Secretaria Municipal de Saúde",
  sigla_sec:     "SEMSA",
  endereco:      "Avenida Cônego Bento, S/N — Centro",
  cep:           "69200-000",
  telefone:      "(92) 0000-0000",
)

// ── IDENTIFICAÇÃO DO PROCESSO ────────────────────────────────────────
#let processo = (
  numero:        "2026.00003",
  tipo:          "Dispensa de Licitação",
  amparo_legal:  "Art. 75, VIII, Lei n.º 14.133/2021",
  fonte:         "Emenda Parlamentar Estadual — ALEAM",
  valor_total:   "R$ 200.000,00",
  valor_extenso: "duzentos mil reais",
  data_laudo:    "05 de março de 2026",
  data_doc:      "15 de março de 2026",
  data_local:    "Borba/AM, 15 de março de 2026",
)

// ── UNIDADE ASSISTENCIAL ─────────────────────────────────────────────
#let hospital = (
  nome:           "Hospital Central de Borba",
  setor:          "Central de Material e Esterilização (CME)",
  leitos:         "40",
  pop_abrangencia: "44 mil",        // área de abrangência total
  pop_ibge:       "34.869",         // IBGE 2025, população urbana
  pop_ibge_ano:   "2025",
  acesso:         "predominantemente fluvial",
  tempo_capital:  "mais de 24 horas por via fluvial até Manaus",
  referencia:     "único hospital de referência regional",
)

// ── OBJETO DA CONTRATAÇÃO ────────────────────────────────────────────
#let objeto = (
  descricao_curta: "Autoclave Hospitalar a Vapor",
  descricao_completa: "Aquisição de autoclave hospitalar a vapor, Tipo B (pré-vácuo), câmara ≥ 100 L, com periféricos, logística CIF " + ente.municipio + "/" + ente.estado + ", qualificações QI/QO/QD e treinamento",
  justificativa_capacidade: "100 litros",
  normas: ("RDC ANVISA 15/2012", "ISO 17665-1:2006", "EN 285:2015", "Lei 14.133/2021"),
)

// ── EQUIPAMENTO SUBSTITUÍDO ──────────────────────────────────────────
#let equip_substituido = (
  patrimonio:  "6897",
  fabricante:  "Phoenix Luferco",
  ano_fab:     "2019",
  anos_uso:    "≈ 6",
  tipo:        "Autoclave hospitalar a vapor — câmara única",
  localizacao: "CME — " + hospital.nome,
  status:      "INOPERANTE — falha sistêmica múltipla",
)

// ── RESPONSÁVEIS E SIGNATÁRIOS ───────────────────────────────────────
#let responsaveis = (
  cme: (
    nome:  "Cíntia Felipe Roque",
    cargo: "Responsável — CME",
    org:   ente.secretaria,
  ),
  diretor: (
    nome:    "Daniel Gomes Vinhote",
    cargo:   "Diretor Hospitalar",
    org:     hospital.nome,
    decreto: "Decreto n.º 0630/2026",
  ),
  secretaria: (
    nome:    "Cíntia Roque da Silva Felipe",
    cargo:   "Secretária Municipal de Saúde",
    decreto: "Decreto nº 0004/2025-GPMB",
  ),
)

// ── FALHAS TÉCNICAS ──────────────────────────────────────────────────
#let falhas = (
  (
    cod:    "F1",
    titulo: "Salto de etapas do ciclo",
    desc:   "O equipamento avança da fase de esterilização diretamente para a secagem sem concluir o plateau de exposição, inviabilizando o SAL de 10⁻⁶ exigido pela RDC ANVISA 15/2012.",
    norma:  "RDC ANVISA 15/2012",
  ),
  (
    cod:    "F2",
    titulo: "Temperatura mínima não atingida",
    desc:   "Falha em alcançar 134 °C ± 1 °C nos ciclos de pré-vácuo. O valor F₀ calculado fica abaixo do mínimo de 15 min, tornando os artigos microbiologicamente inseguros.",
    norma:  "ISO 17665-1:2006",
  ),
  (
    cod:    "F3",
    titulo: "Falha no sistema hidráulico automático",
    desc:   "Entrada de água inoperante, exigindo intervenção manual a cada ciclo — comprometendo padronização, rastreabilidade (RDC 15/2012, art. 34) e segurança do operador.",
    norma:  "RDC 15/2012, art. 34",
  ),
  (
    cod:    "F4",
    titulo: "Instabilidade sistêmica geral",
    desc:   "Pressão e temperatura com parâmetros inconsistentes — falha simultânea em controle eletrônico, sensores e válvulas. Confirma degradação estrutural irreversível, descartando pane isolada.",
    norma:  "Laudo técnico formal",
  ),
)

// ── ESPECIFICAÇÕES TÉCNICAS ──────────────────────────────────────────
#let especificacoes = (
  (k: "Tipo",                  v: "Autoclave a vapor saturado, Tipo B (pré-vácuo), horizontal — obrigatório para artigos porosos e com lúmens (RDC 15/2012, art. 15)"),
  (k: "Câmara",                v: "Capacidade útil ≥ 100 L; aço inox AISI 316L polido — resistência a cloretos e UR ≥ 80% (clima amazônico)"),
  (k: "Sistema de vácuo",      v: "Bomba de anel líquido; pressão absoluta ≤ 30 mbar; mínimo 3 pulsos vácuo/vapor (EN 285:2015, item 8)"),
  (k: "Temperatura",           v: "105–135 °C com precisão ± 1 °C — necessária para F₀ ≥ 15 min e SAL 10⁻⁶ (ISO 17665-1:2006)"),
  (k: "Programas",             v: "Mínimo 13: poroso 134 °C, sólido 134 °C, líquido 121 °C, Bowie-Dick e Leak Test"),
  (k: "Interface",             v: "Touchscreen colorida, gestão de usuários com senha, impressora integrada de etiquetas de ciclo (RDC 15/2012, art. 34)"),
  (k: "Registro eletrônico",   v: "Memória interna de ciclos + saída USB para relatórios auditáveis pelo TCE-AM e Transferegov"),
  (k: "Proteção elétrica",     v: "Gabinete IP 54 mínimo — essencial dado UR ≥ 80% em " + ente.municipio + "/" + ente.estado),
  (k: "Segurança",             v: "Mínimo 10 sistemas: antiesmagamento de porta, bloqueio sob pressão, alarmes sonoros e visuais"),
  (k: "Periféricos",           v: "Osmose reversa 60 L/h (≤ 1,3 µS/cm); compressor ar médico ≥ 50 L (NBR ISO 7396-1); racks AISI 316L (≥ 3); carro inox; IB G. stearothermophilus (cx 50); IC Cl. 5 (cx 200); peças desgaste 12 meses"),
  (k: "Qualificações",         v: "QI + QO + QD (ISO 17665-1:2006) realizadas no CME, com Relatório em 2 vias + PDF assinado como condição do TRD"),
  (k: "Logística",             v: "CIF " + ente.municipio + "/" + ente.estado + " — frete fluvial Manaus–" + ente.municipio + ", seguro Ad Valorem, embalagem antivibração/antihumidade"),
  (k: "Treinamento",           v: "Mínimo 8 h presenciais no CME, com certificados nominais — operação, manutenção preventiva, monitoramento biológico/químico"),
  (k: "Garantia",              v: "Mínimo 24 meses a contar do TRD; atendimento técnico no Amazonas em ≤ 72 h; solução definitiva em ≤ 15 dias corridos"),
  (k: "Registro ANVISA",       v: "Obrigatório — fabricante ou importador com registro ativo para o equipamento ofertado"),
  (k: "RENEM / CATMAT",        v: "Equipamento deve constar da RENEM com código CATMAT — Portarias GM/MS 6.870 e 6.904/2025"),
)

// ── ORÇAMENTO ────────────────────────────────────────────────────────
#let orcamento = (
  itens: (
    ("Autoclave hospitalar ≥ 100 L com barreira sanitária", "R$ 120.000,00", "60,0%"),
    ("Periféricos (osmose, compressor, racks, carro, IB, IC)", "R$ 35.000,00",  "17,5%"),
    ("Logística CIF " + ente.municipio + "/" + ente.estado + " + seguro Ad Valorem", "R$ 15.000,00",  "7,5%"),
    ("Entrega Técnica (QI/QO/QD) + Treinamento (8 h)", "R$ 10.000,00",  "5,0%"),
    ("Peças de desgaste e consumíveis — 12 meses", "R$ 15.000,00",  "7,5%"),
    ("Contingência logística (sazonalidade Rio Madeira)", "R$ 5.000,00",   "2,5%"),
  ),
  total: "R$ 200.000,00",
  total_pct: "100%",
  obs: "A reserva de R$ 20.000,00 para adequação da infraestrutura do CME (rede elétrica trifásica, ponto hidráulico e exaustão de vapor) é recurso municipal próprio, segregado da Emenda Parlamentar — executado em processo distinto.",
)

// ── PRAZO HIDROLÓGICO ────────────────────────────────────────────────
#let prazos_hidro = (
  (periodo: "Jan–Mai", fase: "Cheia plena",   cond: "Navegação plena; balsas de grande calado",          prazo: "60 dias"),
  (periodo: "Jun–Jul", fase: "Vazante",        cond: "Restrições incipientes; monitoramento necessário",  prazo: "75 dias"),
  (periodo: "Ago–Nov", fase: "Seca extrema",   cond: "Balsas de menor calado obrigatórias (ANA)",         prazo: "90 dias"),
  (periodo: "Dez",     fase: "Enchente",       cond: "Normalização progressiva da navegabilidade",        prazo: "75 dias"),
)

// ── PRAZO LICITATÓRIO (comparativo) ─────────────────────────────────
#let prazo_licit = (
  etapas: (
    ("ETP + TR + pesquisa de preços",                "15 dias",  "Já concluídos"),
    ("Elaboração e revisão do edital (CPL + PGM)",   "10 dias",  ""),
    ("Publicação no PNCP até abertura",              "8 dias",   "Art. 55, § 2.º"),
    ("Prazo de propostas + sessão + habilitação",    "15 dias",  ""),
    ("Recursos + homologação + assinatura",          "10 dias",  ""),
    ("Entrega Técnica — período de seca",            "90 dias",  "Ago–Nov: balsas de menor calado"),
  ),
  total_dias: "≈ 148 dias",
  total_obs:  "Quase 5 meses sem esterilização segura",
)

// ── CHECKLIST DE REQUISITOS FORMAIS ─────────────────────────────────
#let requisitos_formais = (
  ("①", "Justificativa de Situação Emergencial (este documento)",  "Art. 72, I",    "Elaborada — Anexo I"),
  ("②", "Laudo Técnico do CME — Diretor Hospitalar",               "Art. 72, I",    "Elaborado — Anexo II"),
  ("③", "Termo de Referência com especificações técnicas",          "Art. 72, III",  "Elaborado — Anexo III"),
  ("④", "Pesquisa de preços — mínimo 3 cotações",                   "Art. 72, IV",   "A realizar — Anexo IV"),
  ("⑤", "Planilha comparativa e seleção do fornecedor",             "Art. 72, VII",  "A elaborar após cotações"),
  ("⑥", "Contrato de Fornecimento",                                 "Art. 72, VIII", "Minuta — Anexo V"),
  ("⑦", "Publicação no PNCP em até 10 dias úteis",                  "Art. 174",      "Após assinatura"),
)

// ── CONCLUSÃO — itens verificados ───────────────────────────────────
#let conclusao_checks = (
  "Situação emergencial concreta e documentada, não provocada por omissão: autoclave nº " + equip_substituido.patrimonio + " (" + equip_substituido.fabricante + ", " + equip_substituido.ano_fab + ") com falha sistêmica múltipla, formalmente documentada pelo Diretor Hospitalar " + responsaveis.diretor.nome + " (" + responsaveis.diretor.decreto + ").",
  "Risco direto e imediato à segurança de pacientes e profissionais de saúde, com potencial para ISC, IRAS sistêmica e óbito evitável, em " + hospital.referencia + " para " + hospital.pop_ibge + " habitantes com acesso " + hospital.acesso + ".",
  "Comprometimento da continuidade de serviço público essencial de saúde, com risco iminente de desabastecimento de materiais esterilizados para todos os setores assistenciais.",
  "Inviabilidade técnica e econômica da manutenção corretiva — custo de reparo estimado em 60–75% do valor de substituição, sem garantia de desempenho equivalente, sem nova qualificação QI/QO/QD.",
  "Objeto delimitado ao estritamente necessário, sem excesso ou superdimensionamento, nos termos do art. 75, VIII, in fine.",
)

// ── BASE NORMATIVA ───────────────────────────────────────────────────
#let base_normativa = (
  "Lei n.º 14.133/2021, arts. 72 e 75, VIII",
  "RDC ANVISA n.º 15/2012",
  "ISO 17665-1:2006 (validação calor úmido)",
  "EN 285:2015 (esterilizadores a vapor)",
  "ABNT NBR ISO 7396-1:2011 (ar médico)",
  "IN SEGES/MGI n.º 65/2021 (pesquisa de preços)",
  "Portarias GM/MS n.º 6.870 e 6.904/2025",
  "CF/88, arts. 37 e 196",
)
