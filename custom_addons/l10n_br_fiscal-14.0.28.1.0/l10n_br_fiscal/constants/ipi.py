# Copyright (C) 2019  Renato Lima - Akretion <renato.lima@akretion.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

CST_IPI_IN = ["00", "01", "02", "03", "04", "05", "49"]

CST_IPI_OUT = ["50", "51", "52", "53", "54", "55", "99"]

CST_IPI_IN_OUT = {
    "00": "50",
    "01": "51",
    "02": "52",
    "03": "53",
    "04": "54",
    "05": "55",
    "49": "99",
}

CST_IPI_OUT_IN = {
    "50": "00",
    "51": "01",
    "52": "02",
    "53": "03",
    "54": "04",
    "55": "05",
    "99": "49",
}


IPI_GUIDELINE_GROUP = [
    ("imunidade", "Imunidade"),
    ("suspensao", "Suspensão"),
    ("isencao", "Isenção"),
    ("reducao", "Redução"),
    ("outros", "Outros"),
]
