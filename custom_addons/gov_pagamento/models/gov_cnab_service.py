import logging
from datetime import date, datetime

_logger = logging.getLogger(__name__)

BANCO_BB = "001"
BANCO_CEF = "104"


class GovCnabService:
    """
    Gerador de remessa CNAB240 para OPs.
    """

    TAMANHO_LINHA = 240

    @classmethod
    def gerar_arquivo(cls, ops, empresa):
        linhas = []
        data_hoje = date.today()
        hora_agora = datetime.now()

        lote_num = 1
        total_registros = 0

        linhas.append(cls._header_arquivo(empresa, data_hoje, hora_agora))
        total_registros += 1

        from itertools import groupby

        ops_sorted = sorted(ops, key=lambda op: op.get("tipo_pagamento", "outros"))
        for tipo, grupo in groupby(ops_sorted, key=lambda op: op.get("tipo_pagamento", "outros")):
            grupo_list = list(grupo)
            seq_reg = 1
            lote_linhas = []

            for op in grupo_list:
                segmentos = cls._segmentos_op(op, lote_num, seq_reg)
                lote_linhas.extend(segmentos)
                seq_reg += len(segmentos)

            qtd_lote = len(lote_linhas) + 2
            valor_lote = sum(op.get("valor", 0.0) or 0.0 for op in grupo_list)

            linhas.append(cls._header_lote(empresa, lote_num, tipo, data_hoje, qtd_lote))
            total_registros += 1
            linhas.extend(lote_linhas)
            total_registros += len(lote_linhas)
            linhas.append(cls._trailer_lote(lote_num, qtd_lote, valor_lote))
            total_registros += 1

            lote_num += 1

        total_registros += 1
        linhas.append(cls._trailer_arquivo(lote_num - 1, total_registros))

        conteudo = "\r\n".join(linhas) + "\r\n"
        return conteudo.encode("latin-1", errors="replace")

    @classmethod
    def _pad(cls, valor, tamanho, tipo="A", fill=" "):
        s = str(valor or "")
        if tipo == "N":
            s = "".join(ch for ch in s if ch.isdigit())
            s = s.zfill(tamanho)
        else:
            s = s.upper().ljust(tamanho, fill)
        return s[:tamanho]

    @classmethod
    def _valor_cnab(cls, valor, tamanho):
        centavos = round((valor or 0.0) * 100)
        return str(int(centavos)).zfill(tamanho)

    @classmethod
    def _finalizar(cls, linha):
        return linha.ljust(cls.TAMANHO_LINHA)[: cls.TAMANHO_LINHA]

    @classmethod
    def _header_arquivo(cls, emp, data_ref, hora_ref):
        l = ""
        l += cls._pad(emp.get("banco", BANCO_BB), 3, "N")
        l += cls._pad("0000", 4, "N")
        l += "0"
        l += cls._pad("", 9)
        l += "2"
        l += cls._pad(emp.get("cnpj", ""), 14, "N")
        l += cls._pad(emp.get("convenio", ""), 20)
        l += cls._pad(emp.get("agencia", ""), 5, "N")
        l += cls._pad(emp.get("agencia_dv", ""), 1)
        l += cls._pad(emp.get("conta", ""), 12, "N")
        l += cls._pad(emp.get("conta_dv", ""), 1)
        l += cls._pad("", 1)
        l += cls._pad(emp.get("nome", ""), 30)
        l += cls._pad("GRP ODOO", 30)
        l += cls._pad("", 10)
        l += "1"
        l += data_ref.strftime("%d%m%Y")
        l += hora_ref.strftime("%H%M%S")
        l += cls._pad("000001", 6, "N")
        l += cls._pad("103", 3, "N")
        l += cls._pad("01600", 5, "N")
        l += cls._pad("", 20)
        l += cls._pad("", 20)
        l += cls._pad("", 29)
        return cls._finalizar(l)

    @classmethod
    def _header_lote(cls, emp, lote, tipo, data_ref, qtd):
        l = ""
        l += cls._pad(emp.get("banco", BANCO_BB), 3, "N")
        l += cls._pad(lote, 4, "N")
        l += "1"
        l += "C"
        l += cls._pad("98", 2, "N")
        l += cls._pad("00", 2, "N")
        l += cls._pad("045", 3, "N")
        l += cls._pad("", 1)
        l += "2"
        l += cls._pad(emp.get("cnpj", ""), 14, "N")
        l += cls._pad(emp.get("convenio", ""), 20)
        l += cls._pad(emp.get("agencia", ""), 5, "N")
        l += cls._pad(emp.get("agencia_dv", ""), 1)
        l += cls._pad(emp.get("conta", ""), 12, "N")
        l += cls._pad(emp.get("conta_dv", ""), 1)
        l += cls._pad("", 1)
        l += cls._pad(emp.get("nome", ""), 30)
        l += cls._pad("", 40)
        l += cls._pad("", 30)
        l += cls._pad(emp.get("logradouro", ""), 30)
        l += cls._pad(emp.get("numero", ""), 5, "N")
        l += cls._pad(emp.get("complemento", ""), 15)
        l += cls._pad(emp.get("cidade", ""), 20)
        l += cls._pad(emp.get("cep", ""), 8, "N")
        l += cls._pad(emp.get("estado", "AM"), 2)
        l += cls._pad("", 8)
        return cls._finalizar(l)

    @classmethod
    def _segmentos_op(cls, op, lote, seq):
        tipo = op.get("tipo_pagamento", "transferencia")
        if tipo in ("transferencia",):
            return [cls._segmento_a(op, lote, seq)]
        if tipo in ("darf", "gps", "guia_iss"):
            return [cls._segmento_j52(op, lote, seq)]
        return [cls._segmento_a(op, lote, seq)]

    @classmethod
    def _segmento_a(cls, op, lote, seq):
        l = ""
        l += cls._pad(op.get("banco_pagador", BANCO_BB), 3, "N")
        l += cls._pad(lote, 4, "N")
        l += "3"
        l += cls._pad(seq, 5, "N")
        l += "A"
        l += cls._pad("", 1)
        l += cls._pad("01", 2, "N")
        l += cls._pad(op.get("banco_dest", ""), 3, "N")
        l += cls._pad(op.get("agencia_dest", ""), 5, "N")
        l += cls._pad(op.get("agencia_dest_dv", ""), 1)
        l += cls._pad(op.get("conta_dest", ""), 12, "N")
        l += cls._pad(op.get("conta_dest_dv", ""), 1)
        l += cls._pad("", 1)
        l += cls._pad(op.get("nome_dest", ""), 30)
        l += cls._pad(op.get("numero_doc", ""), 20)
        data_pag = op.get("data_pagamento", date.today())
        if hasattr(data_pag, "strftime"):
            l += data_pag.strftime("%d%m%Y")
        else:
            l += date.today().strftime("%d%m%Y")
        l += cls._pad("BRL", 3)
        l += cls._pad("0", 15, "N")
        l += cls._valor_cnab(op.get("valor", 0.0), 15)
        l += cls._pad(op.get("numero_op", ""), 20)
        l += cls._pad("", 8)
        l += cls._pad("BRL", 3)
        l += cls._pad("0", 15, "N")
        l += cls._valor_cnab(op.get("valor", 0.0), 15)
        l += cls._pad(op.get("historico", ""), 40)
        l += cls._pad("01", 2, "N")
        l += cls._pad("", 5)
        l += cls._pad("0", 1, "N")
        return cls._finalizar(l)

    @classmethod
    def _segmento_j52(cls, op, lote, seq):
        l = ""
        l += cls._pad(op.get("banco_pagador", BANCO_BB), 3, "N")
        l += cls._pad(lote, 4, "N")
        l += "3"
        l += cls._pad(seq, 5, "N")
        l += "J"
        l += cls._pad("", 1)
        l += cls._pad("01", 2, "N")
        l += cls._pad(op.get("codigo_barras", ""), 48)
        l += cls._pad(op.get("nome_dest", ""), 30)
        data_pag = op.get("data_pagamento", date.today())
        if hasattr(data_pag, "strftime"):
            l += data_pag.strftime("%d%m%Y")
        else:
            l += date.today().strftime("%d%m%Y")
        l += cls._pad("", 8)
        l += cls._valor_cnab(op.get("valor", 0.0), 15)
        l += cls._valor_cnab(op.get("valor", 0.0), 15)
        l += cls._pad(op.get("numero_op", ""), 20)
        l += cls._pad("52", 2, "N")
        l += "2"
        l += cls._pad(op.get("cnpj_dest", ""), 14, "N")
        l += cls._pad(op.get("numero_doc", ""), 15)
        l += cls._pad(op.get("competencia", ""), 6, "N")
        l += cls._pad(op.get("darf_codigo", ""), 6, "N")
        l += cls._pad("0", 15, "N")
        l += cls._pad("0", 15, "N")
        l += cls._pad("0", 15, "N")
        return cls._finalizar(l)

    @classmethod
    def _trailer_lote(cls, lote, qtd, valor):
        l = ""
        l += cls._pad(BANCO_BB, 3, "N")
        l += cls._pad(lote, 4, "N")
        l += "5"
        l += cls._pad("", 9)
        l += cls._pad(qtd, 6, "N")
        l += cls._valor_cnab(valor, 18)
        l += cls._pad("0", 18, "N")
        l += cls._pad("0", 6, "N")
        l += cls._pad("", 165)
        return cls._finalizar(l)

    @classmethod
    def _trailer_arquivo(cls, qtd_lotes, qtd_registros):
        l = ""
        l += cls._pad(BANCO_BB, 3, "N")
        l += cls._pad("9999", 4, "N")
        l += "9"
        l += cls._pad("", 9)
        l += cls._pad(qtd_lotes, 6, "N")
        l += cls._pad(qtd_registros, 6, "N")
        l += cls._pad("0", 6, "N")
        l += cls._pad("", 205)
        return cls._finalizar(l)
