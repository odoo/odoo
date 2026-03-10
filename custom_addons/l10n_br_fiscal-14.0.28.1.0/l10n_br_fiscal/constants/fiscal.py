# Copyright (C) 2019  Renato Lima - Akretion <renato.lima@akretion.com.br>
# Copyright (C) 2019  Luis Felipe Mileo - KMEE <mileo@kmee.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import _

OPERATION_STATE = [
    ("draft", "Draft"),
    ("review", "Review"),
    ("approved", "Approved"),
    ("expired", "Expired"),
]


OPERATION_STATE_DEFAULT = "draft"


OPERATION_FISCAL_TYPE = [
    ("purchase", "Purchase"),
    ("purchase_refund", "Purchase Return"),
    ("return_in", "Return in"),
    ("sale", "Sale"),
    ("sale_refund", "Sale Return"),
    ("return_out", "Return Out"),
    ("other", "Other"),
]


OPERATION_FISCAL_TYPE_DEFAULT = "other"


COMMENT_TYPE = [
    ("fiscal", "Fiscal"),
    ("commercial", "Commercial"),
]


COMMENT_TYPE_FISCAL = "fiscal"


COMMENT_TYPE_COMMERCIAL = "commercial"


PRODUCT_FISCAL_TYPE = [
    ("00", "Mercadoria para Revenda"),
    ("01", "Matéria-prima"),
    ("02", "Embalagem"),
    ("03", "Produto em Processo"),
    ("04", "Produto Acabado"),
    ("05", "Subproduto"),
    ("06", "Produto Intermediário"),
    ("07", "Material de Uso e Consumo"),
    ("08", "Ativo Imobilizado"),
    ("09", "Serviços"),
    ("10", "Outros insumos"),
    ("99", "Outras"),
]


PRODUCT_FISCAL_TYPE_SERVICE = "09"

NCM_FOR_SERVICE = "0000.00.00"
NCM_FOR_SERVICE_REF = "l10n_br_fiscal.ncm_00000000"


TAX_BASE_TYPE = [
    ("percent", _("Percent")),
    ("quantity", _("Quantity")),
    ("fixed", _("Fixed")),
]


TAX_BASE_TYPE_PERCENT = "percent"
TAX_BASE_TYPE_VALUE = "fixed"


TAX_DOMAIN_IPI = "ipi"
TAX_DOMAIN_II = "ii"
TAX_DOMAIN_ICMS = "icms"
TAX_DOMAIN_ICMS_SN = "icmssn"
TAX_DOMAIN_ICMS_ST = "icmsst"
TAX_DOMAIN_ICMS_FCP = "icmsfcp"
TAX_DOMAIN_ICMS_FCP_ST = "icmsfcpst"
TAX_DOMAIN_PIS = "pis"
TAX_DOMAIN_PIS_ST = "pisst"
TAX_DOMAIN_PIS_WH = "pis_wh"
TAX_DOMAIN_COFINS = "cofins"
TAX_DOMAIN_COFINS_ST = "cofinsst"
TAX_DOMAIN_COFINS_WH = "cofins_wh"
TAX_DOMAIN_ISSQN = "issqn"
TAX_DOMAIN_ISSQN_WH = "issqn_wh"
TAX_DOMAIN_IBS = "ibs"
TAX_DOMAIN_CBS = "cbs"
TAX_DOMAIN_IS = "is"
TAX_DOMAIN_CSLL = "csll"
TAX_DOMAIN_CSLL_WH = "csll_wh"
TAX_DOMAIN_IR = "ir"
TAX_DOMAIN_IRPJ = "irpj"
TAX_DOMAIN_IRPJ_WH = "irpj_wh"
TAX_DOMAIN_INSS = "inss"
TAX_DOMAIN_INSS_WH = "inss_wh"
TAX_DOMAIN_SIMPLES = "simples"
TAX_DOMAIN_OTHERS = "others"


TAX_DOMAIN_PCC = (TAX_DOMAIN_PIS, TAX_DOMAIN_COFINS, TAX_DOMAIN_CSLL)


TAX_DOMAIN_PCC_RET = (TAX_DOMAIN_PIS_WH, TAX_DOMAIN_COFINS_WH, TAX_DOMAIN_CSLL_WH)


TAX_DOMAIN = [
    (TAX_DOMAIN_IPI, "IPI"),
    (TAX_DOMAIN_ICMS, "ICMS - Próprio"),
    (TAX_DOMAIN_ICMS_SN, "ICMS - Simples Nacional"),
    (TAX_DOMAIN_ICMS_FCP, "ICMS FCP - Fundo de Combate a Pobreza"),
    (TAX_DOMAIN_ICMS_ST, "ICMS - Subistituição Tributária"),
    (TAX_DOMAIN_ICMS_FCP_ST, "ICMS FCP ST- Fundo de Combate a Pobreza ST"),
    (TAX_DOMAIN_PIS, "PIS"),
    (TAX_DOMAIN_PIS_ST, "PIS ST"),
    (TAX_DOMAIN_PIS_WH, "pis_wh"),
    (TAX_DOMAIN_COFINS, "COFINS"),
    (TAX_DOMAIN_COFINS_ST, "COFINS ST"),
    (TAX_DOMAIN_COFINS_WH, "COFINS WH"),
    (TAX_DOMAIN_ISSQN, "ISSQN"),
    (TAX_DOMAIN_ISSQN_WH, "ISSQN WH"),
    (TAX_DOMAIN_IBS, "IBS"),
    (TAX_DOMAIN_CBS, "CBS"),
    (TAX_DOMAIN_IS, "IS"),
    (TAX_DOMAIN_IR, "IR"),
    (TAX_DOMAIN_IRPJ, "IRPJ"),
    (TAX_DOMAIN_IRPJ_WH, "IRPJ WH"),
    (TAX_DOMAIN_CSLL, "CSLL"),
    (TAX_DOMAIN_CSLL_WH, "CSLL WH"),
    (TAX_DOMAIN_II, "II"),
    (TAX_DOMAIN_INSS, "INSS"),
    (TAX_DOMAIN_INSS_WH, "INSS WH"),
    (TAX_DOMAIN_SIMPLES, "Simples Nacional"),
    (TAX_DOMAIN_OTHERS, "Outros"),
]


TAX_ICMS_OR_ISSQN = [
    (TAX_DOMAIN_ICMS, "ICMS"),
    (TAX_DOMAIN_ISSQN, "ISSQN"),
]


TAX_FRAMEWORK = [
    ("1", "1 - Simples Nacional"),
    ("2", "2 - Simples Nacional – excesso de sublimite da receita bruta"),
    ("3", "3 - Regime Normal"),
]


TAX_FRAMEWORK_SIMPLES = "1"
TAX_FRAMEWORK_SIMPLES_EX = "2"
TAX_FRAMEWORK_NORMAL = "3"
TAX_FRAMEWORK_SIMPLES_ALL = ("1", "2")


PROFIT_CALCULATION = [
    ("real", "Real"),
    ("presumed", "Presumed"),
    ("arbitrary", "Arbitrary"),
]


PROFIT_CALCULATION_PRESUMED = "presumed"

COEFFICIENT_R = 0.28

INDUSTRY_TYPE = [
    ("00", "00 - Industrial - Transformação"),
    ("01", "01 - Industrial - Beneficiamento"),
    ("02", "02 - Industrial - Montagem"),
    ("03", "03 - Industrial - Acondicionamento ou Reacondicionamento"),
    ("04", "04 - Industrial - Renovação ou Recondicionamento"),
    ("05", "05 - Equiparado a industrial - Por opção"),
    ("06", "06 - Equiparado a industrial - Importação Direta"),
    ("07", "07 - Equiparado a industrial - Por lei específica"),
    ("08", "08 - Equiparado a industrial - Não enquadrado nos" " códigos 05, 06 ou 07"),
    ("09", "09 - Outros"),
]


INDUSTRY_TYPE_TRANSFORMATION = "00"

CERTIFICATE_TYPE_NFE = "nf-e"
CERTIFICATE_TYPE_ECPF = "e-cpf"
CERTIFICATE_TYPE_ECNPJ = "e-cnpj"

CERTIFICATE_TYPE = [
    (CERTIFICATE_TYPE_ECPF, "E-CPF"),
    (CERTIFICATE_TYPE_ECNPJ, "E-CNPJ"),
    (CERTIFICATE_TYPE_NFE, "NF-e"),
]


CERTIFICATE_TYPE_DEFAULT = CERTIFICATE_TYPE_NFE


CERTIFICATE_SUBTYPE = [("a1", "A1"), ("a3", "A3")]


CERTIFICATE_SUBTYPE_DEFAULT = "a1"


FISCAL_IN_OUT = [("in", _("In")), ("out", _("Out"))]

FISCAL_IN_OUT_DICT = dict(FISCAL_IN_OUT)

FISCAL_IN_OUT_ALL = [("in", "In"), ("out", "Out"), ("all", "All")]


FISCAL_IN = "in"


FISCAL_OUT = "out"


FISCAL_IN_OUT_DEFAULT = "in"


# TODO - REMOVE???
DOCUMENT_TYPE = [("icms", "ICMS"), ("service", "Serviço Municipal")]


DOCUMENT_ISSUER = [("company", _("Company")), ("partner", _("Partner"))]

DOCUMENT_ISSUER_DICT = dict(DOCUMENT_ISSUER)

DOCUMENT_ISSUER_COMPANY = "company"
DOCUMENT_ISSUER_PARTNER = "partner"


CFOP_DESTINATION = [
    ("1", "Operação Interna"),
    ("2", "Operação Interestadual"),
    ("3", "Operação com Exterior"),
]


CFOP_DESTINATION_INTERNAL = "1"
CFOP_DESTINATION_EXTERNAL = "2"
CFOP_DESTINATION_EXPORT = "3"


CEST_SEGMENT = [
    ("01", "Autopeças"),
    ("02", "Bebidas alcoólicas, exceto cerveja e chope"),
    ("03", "Cervejas, chopes, refrigerantes, águas e outras bebidas"),
    ("04", "Cigarros e outros produtos derivados do fumo"),
    ("05", "Cimentos"),
    ("06", "Combustíveis e lubrificantes"),
    ("07", "Energia elétrica"),
    ("08", "Ferramentas"),
    ("09", "Lâmpadas, reatores e “starter”"),
    ("10", "Materiais de construção e congêneres"),
    ("11", "Materiais de limpeza"),
    ("12", "Materiais elétricos"),
    (
        "13",
        "Medicamentos de uso humano e outros produtos"
        " farmacêuticos para uso humano ou veterinário",
    ),
    ("14", "Papéis, plásticos, produtos cerâmicos e vidros"),
    ("15", "Pneumáticos, câmaras de ar e protetores de borracha"),
    ("16", "Produtos alimentícios"),
    ("17", "Produtos de papelaria"),
    ("18", "Produtos de perfumaria e de higiene pessoal e cosméticos"),
    ("19", "Produtos eletrônicos, eletroeletrônicos e eletrodomésticos"),
    ("20", "Rações para animais domésticos"),
    ("21", "Sorvetes e preparados para fabricação de sorvetes em máquinas"),
    ("22", "Tintas e vernizes"),
    ("23", "Veículos automotores"),
    ("24", "Veículos de duas e três rodas motorizados"),
    ("25", "Venda de mercadorias pelo sistema porta a porta"),
]


NFE_IND_IE_DEST = [
    ("1", "1 - Contribuinte do ICMS"),
    ("2", "2 - Contribuinte Isento do ICMS"),
    ("9", "9 - Não Contribuinte"),
]

NFE_IND_IE_DEST_DEFAULT = NFE_IND_IE_DEST[0][0]

NFE_IND_IE_DEST_1 = "1"
NFE_IND_IE_DEST_2 = "2"
NFE_IND_IE_DEST_9 = "9"


NFE_IND_PRES = [
    ("0", "Não se aplica"),
    ("1", "Operação presencial"),
    ("2", "Não presencial, internet"),
    ("3", "Não presencial, teleatendimento"),
    ("4", "NFC-e entrega em domicílio"),
    ("5", "Operação presencial, fora do estabelecimento"),
    ("9", "Não presencial, outros"),
]


NFE_IND_PRES_DEFAULT = "0"
NFCE_IND_PRES_DEFAULT = "1"

FINAL_CUSTOMER = [("0", "Não"), ("1", "Sim")]


FINAL_CUSTOMER_NO = "0"
FINAL_CUSTOMER_YES = "1"


PUBLIC_ENTIRY_TYPE = [
    ("1", "União"),
    ("2", "Estado"),
    ("3", "Distrito Federal"),
    ("4", "Município"),
]


CFOP_TYPE_MOVE = [
    ("purchase_industry", "Purchase Industry"),
    ("purchase_commerce", "Purchase Commerce"),
    ("purchase_asset", "Purchase Asset"),
    ("purchase_ownuse", "Purchase Own Use"),
    ("purchase_service", "Purchase Service"),
    ("purchase_refund", "Purchase Refund"),
    ("return_in", "Return in"),
    ("sale_industry", "Sale Industry"),
    ("sale_commerce", "Sale Commerce"),
    ("sale_asset", "Sale Asset"),
    ("sale_ownuse", "Sale Own Use"),
    ("sale_service", "Sale Service"),
    ("sale_refund", "Sale Refund"),
    ("return_out", "Return Out"),
    ("other", "Other"),
]

CFOP_TYPE_MOVE_DEFAULT = "other"

MODELO_FISCAL_NFE = "55"
MODELO_FISCAL_NFCE = "65"
MODELO_FISCAL_NFSE = "SE"
MODELO_FISCAL_CFE = "59"
MODELO_FISCAL_CUPOM_FISCAL_ECF = "2D"
MODELO_FISCAL_CTE = "57"
MODELO_FISCAL_MDFE = "58"
MODELO_FISCAL_RL = "04"  # Produto Rural
MODELO_FISCAL_01 = "01"
MODELO_FISCAL_04 = "04"


MODELO_FISCAL_EMISSAO_PRODUTO = [
    MODELO_FISCAL_NFE,
    MODELO_FISCAL_NFCE,
    MODELO_FISCAL_CFE,
    MODELO_FISCAL_CUPOM_FISCAL_ECF,
]
MODELO_FISCAL_EMISSAO_SERVICO = [
    MODELO_FISCAL_NFE,
    MODELO_FISCAL_NFCE,
    MODELO_FISCAL_NFSE,
    MODELO_FISCAL_RL,
]

AUTORIZADO = ("100", "150")
DENEGADO = ("110", "301", "302", "303")
LOTE_RECEBIDO = ["103"]
LOTE_PROCESSADO = ["104"]
LOTE_EM_PROCESSAMENTO = ["105"]
SERVICO_PARALIZADO = ("108", "109")
ENCERRADO = ["132", "135"]

CANCELAMENTO_HOMOLOGADO = ["101", "151"]

CANCELADO_DENTRO_PRAZO = ["135"]
CANCELADO_FORA_PRAZO = ["155"]

CANCELADO = CANCELADO_DENTRO_PRAZO + CANCELADO_FORA_PRAZO + CANCELAMENTO_HOMOLOGADO

AUTORIZADO_OU_DENEGADO = AUTORIZADO + DENEGADO

EVENTO_REGISTRADO_E_VINCULADO = "135"
EVENTO_REGISTRADO_NAO_VINCULADO = "136"

EVENTO_RECEBIDO = ["135", "136"]

SITUACAO_EDOC_EM_DIGITACAO = "em_digitacao"
SITUACAO_EDOC_A_ENVIAR = "a_enviar"
SITUACAO_EDOC_ENVIADA = "enviada"
SITUACAO_EDOC_REJEITADA = "rejeitada"
SITUACAO_EDOC_AUTORIZADA = "autorizada"
SITUACAO_EDOC_CANCELADA = "cancelada"
SITUACAO_EDOC_DENEGADA = "denegada"
SITUACAO_EDOC_INUTILIZADA = "inutilizada"
SITUACAO_EDOC_ENCERRADA = "encerrada"


SITUACAO_EDOC = [
    (SITUACAO_EDOC_EM_DIGITACAO, "Em digitação"),
    (SITUACAO_EDOC_A_ENVIAR, "Aguardando envio"),
    (SITUACAO_EDOC_ENVIADA, "Aguardando processamento"),
    (SITUACAO_EDOC_REJEITADA, "Rejeitada"),
    (SITUACAO_EDOC_AUTORIZADA, "Autorizada"),
    (SITUACAO_EDOC_CANCELADA, "Cancelada"),
    (SITUACAO_EDOC_DENEGADA, "Denegada"),
    (SITUACAO_EDOC_INUTILIZADA, "Inutilizada"),
    (SITUACAO_EDOC_ENCERRADA, "Encerrada"),
]
SITUACAO_EDOC_DICT = dict(SITUACAO_EDOC)

SITUACAO_FISCAL_REGULAR = "00"
SITUACAO_FISCAL_REGULAR_EXTEMPORANEO = "01"
SITUACAO_FISCAL_CANCELADO = "02"
SITUACAO_FISCAL_CANCELADO_EXTEMPORANEO = "03"
SITUACAO_FISCAL_DENEGADO = "04"
SITUACAO_FISCAL_INUTILIZADO = "05"
SITUACAO_FISCAL_COMPLEMENTAR = "06"
SITUACAO_FISCAL_COMPLEMENTAR_EXTEMPORANEO = "07"
SITUACAO_FISCAL_REGIME_ESPECIAL = "08"
SITUACAO_FISCAL_MERCADORIA_NAO_CIRCULOU = "NC"
SITUACAO_FISCAL_MERCADORIA_NAO_RECEBIDA = "MR"

SITUACAO_FISCAL = [
    (SITUACAO_FISCAL_REGULAR, "Regular"),
    (SITUACAO_FISCAL_REGULAR_EXTEMPORANEO, "Regular extemporâneo"),
    (SITUACAO_FISCAL_CANCELADO, "Cancelado"),
    (SITUACAO_FISCAL_CANCELADO_EXTEMPORANEO, "Cancelado extemporâneo"),
    (SITUACAO_FISCAL_DENEGADO, "Denegado"),
    (SITUACAO_FISCAL_INUTILIZADO, "Numeração inutilizada"),
    (SITUACAO_FISCAL_COMPLEMENTAR, "Complementar"),
    (SITUACAO_FISCAL_COMPLEMENTAR_EXTEMPORANEO, "Complementar extemporâneo"),
    (SITUACAO_FISCAL_REGIME_ESPECIAL, "Regime especial ou norma específica"),
    (SITUACAO_FISCAL_MERCADORIA_NAO_CIRCULOU, "Mercadoria não circulou"),
    (SITUACAO_FISCAL_MERCADORIA_NAO_RECEBIDA, "Mercadoria não recebida"),
]
SITUACAO_FISCAL_DICT = dict(SITUACAO_FISCAL)


SITUACAO_FISCAL_SPED_CONSIDERA_CANCELADO = [
    SITUACAO_FISCAL_CANCELADO,
    SITUACAO_FISCAL_CANCELADO_EXTEMPORANEO,
    SITUACAO_FISCAL_DENEGADO,
    SITUACAO_FISCAL_INUTILIZADO,
]

SITUACAO_FISCAL_SPED_CONSIDERA_ATIVO = [
    SITUACAO_FISCAL_REGULAR,
    SITUACAO_FISCAL_REGULAR_EXTEMPORANEO,
    SITUACAO_FISCAL_COMPLEMENTAR,
    SITUACAO_FISCAL_COMPLEMENTAR_EXTEMPORANEO,
    SITUACAO_FISCAL_REGIME_ESPECIAL,
]

SITUACAO_FISCAL_EXTEMPORANEO = [
    SITUACAO_FISCAL_REGULAR_EXTEMPORANEO,
    SITUACAO_FISCAL_CANCELADO_EXTEMPORANEO,
    SITUACAO_FISCAL_COMPLEMENTAR_EXTEMPORANEO,
]

WORKFLOW_DOCUMENTO_NAO_ELETRONICO = [
    (SITUACAO_EDOC_EM_DIGITACAO, SITUACAO_EDOC_A_ENVIAR),
    (SITUACAO_EDOC_EM_DIGITACAO, SITUACAO_EDOC_AUTORIZADA),
    (SITUACAO_EDOC_A_ENVIAR, SITUACAO_EDOC_AUTORIZADA),
    (SITUACAO_EDOC_A_ENVIAR, SITUACAO_EDOC_EM_DIGITACAO),
    (SITUACAO_EDOC_EM_DIGITACAO, SITUACAO_EDOC_CANCELADA),
    (SITUACAO_EDOC_AUTORIZADA, SITUACAO_EDOC_CANCELADA),
    (SITUACAO_EDOC_CANCELADA, SITUACAO_EDOC_EM_DIGITACAO),
]

WORKFLOW_EDOC = WORKFLOW_DOCUMENTO_NAO_ELETRONICO + [
    (SITUACAO_EDOC_EM_DIGITACAO, SITUACAO_EDOC_ENVIADA),
    (SITUACAO_EDOC_EM_DIGITACAO, SITUACAO_EDOC_REJEITADA),
    (SITUACAO_EDOC_EM_DIGITACAO, SITUACAO_EDOC_DENEGADA),
    (SITUACAO_EDOC_A_ENVIAR, SITUACAO_EDOC_ENVIADA),
    (SITUACAO_EDOC_A_ENVIAR, SITUACAO_EDOC_REJEITADA),
    (SITUACAO_EDOC_A_ENVIAR, SITUACAO_EDOC_AUTORIZADA),
    (SITUACAO_EDOC_A_ENVIAR, SITUACAO_EDOC_DENEGADA),
    (SITUACAO_EDOC_A_ENVIAR, SITUACAO_EDOC_CANCELADA),
    (SITUACAO_EDOC_A_ENVIAR, SITUACAO_EDOC_EM_DIGITACAO),
    (SITUACAO_EDOC_ENVIADA, SITUACAO_EDOC_REJEITADA),
    (SITUACAO_EDOC_ENVIADA, SITUACAO_EDOC_AUTORIZADA),
    (SITUACAO_EDOC_ENVIADA, SITUACAO_EDOC_DENEGADA),
    (SITUACAO_EDOC_REJEITADA, SITUACAO_EDOC_AUTORIZADA),
    (SITUACAO_EDOC_REJEITADA, SITUACAO_EDOC_EM_DIGITACAO),
    (SITUACAO_EDOC_REJEITADA, SITUACAO_EDOC_REJEITADA),
]

EDOC_PURPOSE = [
    ("1", "Normal"),
    ("2", "Complementar"),
    ("3", "Ajuste"),
    ("4", "Devolução de mercadoria"),
    ("5", "Nota de Crédito"),
    ("6", "Nota de Débito"),
]

EDOC_PURPOSE_NORMAL = "1"
EDOC_PURPOSE_COMPLEMENTAR = "2"
EDOC_PURPOSE_AJUSTE = "3"
EDOC_PURPOSE_DEVOLUCAO = "4"

EDOC_REFUND_DEBIT_TYPE = [
    ("01", "Transferência de créditos para Cooperativas"),
    ("02", "Anulação de Crédito por Saídas Imunes/Isentas"),
    ("03", "Débitos de notas fiscais não processadas na apuração"),
    ("04", "Multa e juros"),
    ("05", "Transferência de crédito de sucessão"),
]

# TODO - Implementar nas proximas versões da NT da Reforma tributária
EDOC_REFUND_CREDIT_TYPE = [
    ("00", "Não Implementado"),
]

PROCESSADOR_NENHUM = "nenhum"
PROCESSADOR_OCA = "oca"

PROCESSADOR = [
    (PROCESSADOR_NENHUM, "Sem Integração"),
    (PROCESSADOR_OCA, "Odoo Community"),
]

FISCAL_COMMENT_OBJECTS = [
    ("l10n_br_fiscal.document.mixin", "Fiscal Document"),
    ("l10n_br_fiscal.document.line.mixin", "Fiscal Document Line"),
]

FISCAL_COMMENT_DOCUMENT = "l10n_br_fiscal.document.mixin"

FISCAL_COMMENT_LINE = "l10n_br_fiscal.document.line.mixin"

EVENT_ENV_PROD = "prod"
EVENT_ENV_HML = "hml"

EVENT_ENVIRONMENT = [
    (EVENT_ENV_PROD, "Production"),
    (EVENT_ENV_HML, "Homologation"),
]

FISCAL_PAYMENT_MODE = [
    ("01", "01 - Dinheiro"),
    ("02", "02 - Cheque"),
    ("03", "03 - Cartão de Crédito"),
    ("04", "04 - Cartão de Débito"),
    ("05", "05 - Crédito de Loja"),
    ("10", "10 - Vale Alimentação"),
    ("11", "11 - Vale Refeição"),
    ("12", "12 - Vale Presente"),
    ("13", "13 - Vale Combustível"),
    ("14", "14 - Duplicata Mercanti"),
    ("15", "15 - Boleto Bancário"),
    ("16", "16 - Depósito Bancário"),
    ("17", "17 - Pagamento Instantâneo (PIX)"),
    ("18", "18 - Transferência bancária, Carteira Digital"),
    ("19", "19 - Programa de fidelidade, Cashback, Crédito Virtual"),
    ("90", "90 - Sem Pagamento"),
    ("99", "99 - Outros"),
]

TAX_RATE_TYPE = [
    ("1", "1 - Fixa"),
    ("2", "2 - Padrão"),
    ("3", "3 - Sem Alíquota"),
    ("4", "4 - Uniforme Nacional"),
    ("5", "5 - Uniforme Setorial"),
]

TAX_RATE_TYPE_DEFAULT = "2"
