# Copyright (C) 2019  Renato Lima - Akretion <renato.lima@akretion.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

ICMS_ORIGIN = [
    ("0", "0 - Nacional, exceto as indicadas nos códigos 3, 4, 5 e 8"),
    ("1", "1 - Estrangeira – importação direta, exceto a indicada no " "código 6"),
    (
        "2",
        "2 – Estrangeira – adquirida no mercado interno, exceto a indicada "
        "no código 7",
    ),
    (
        "3",
        "3 – Nacional – mercadoria ou bem com Conteúdo de Importação "
        "superior a 40% (quarenta por cento) e inferior ou igual a "
        "70% (setenta por cento)",
    ),
    (
        "4",
        "4 – Nacional – cuja produção tenha sido feita em conformidade com "
        "os processos produtivos básicos de que tratam o Decreto-lei "
        "n° 288/67 e as Leis (federais) nos 8.428/91, 8.397/91, "
        "10.176/2001 e 11.484/2007",
    ),
    (
        "5",
        "5 – Nacional – mercadoria ou bem com Conteúdo de Importação "
        "inferior ou igual a 40% (quarenta por cento)",
    ),
    (
        "6",
        "6 – Estrangeira – importação direta, sem similar nacional, "
        "constante em lista de Resolução CAMEX e gás natural",
    ),
    (
        "7",
        "7 – Estrangeira – adquirida no mercado interno, sem similar "
        "nacional, constante em lista de Resolução CAMEX e gás natural",
    ),
    (
        "8",
        "8 – Nacional – mercadoria ou bem com Conteúdo de Importação "
        "superior a 70% (setenta por cento). (cf. Ajuste SINIEF 15/2013)",
    ),
]


ICMS_ORIGIN_DEFAULT = "0"


ICMS_ORIGIN_TAX_IMPORTED = ["1", "2", "3", "8"]


ICMS_CST = ["00", "10", "20", "30", "40", "41", "50", "51", "60", "70", "90"]


ICMS_BASE_TYPE = [
    ("0", "Margem Valor Agregado (%)"),
    ("1", "Pauta (valor)"),
    ("2", "Preço Tabelado Máximo (valor)"),
    ("3", "Valor da Operação"),
]


ICMS_BASE_TYPE_DEFAULT = "0"


ICMS_ST_BASE_TYPE = [
    ("0", "Preço tabelado ou máximo  sugerido"),
    ("1", "Lista Negativa (valor)"),
    ("2", "Lista Positiva (valor)"),
    ("3", "Lista Neutra (valor)"),
    ("4", "Margem Valor Agregado (%)"),
    ("5", "Pauta (valor)"),
]


ICMS_ST_BASE_TYPE_DEFAULT = "4"


ICMS_TAX_BENEFIT_TYPE = [
    ("0", "0 - imunidade ou não incidência"),
    ("1", "1 - isenção"),
    ("2", "2 - redução de base de cálculo"),
    ("3", "3 - diferimento"),
    ("4", "4 - suspensão"),
    ("5", "5 - Crédito Presumido"),
]


ICMS_SN_CST = ["101", "102", "103", "201", "202", "203", "300", "400", "500", "900"]


ICMS_SN_CST_WITH_CREDIT = ["101", "201"]


ICMS_SN_CST_WITHOUT_CREDIT = ["102", "103", "202", "203", "300", "400", "500", "900"]


ICMS_DIFAL_PARTITION = {
    2016: {"difal_origin_perc": 60.00, "difal_dest_perc": 40.00},
    2017: {"difal_origin_perc": 40.00, "difal_dest_perc": 60.00},
    2018: {"difal_origin_perc": 20.00, "difal_dest_perc": 80.00},
    2019: {"difal_origin_perc": 0.00, "difal_dest_perc": 100.00},
}


ICMS_DIFAL_UNIQUE_BASE = [
    "DF",
    "ES",
    "MA",
    "MS",
    "PE",
    "RJ",
    "RN",
    "RR",
]


ICMS_DIFAL_DOUBLE_BASE = [
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "GO",
    "MG",
    "MT",
    "PA",
    "PB",
    "PI",
    "PR",
    "RO",
    "RS",
    "SC",
    "SE",
    "SP",
    "TO",
]


ICSM_CST_CSOSN_ST_BASE = ["10", "30", "70", "90", "201", "202", "203", "900"]

ICMS_CST_RELIEF = ["20", "30", "40", "41", "50", "70", "90"]
