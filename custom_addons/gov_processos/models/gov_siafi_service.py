import logging
from datetime import date

_logger = logging.getLogger(__name__)


class GovSiafiService:
    """
    Gerador de TXT posicional para exportacao SIAFI/SIGEF.
    Cada linha tem 300 posicoes e termina com CRLF.
    """

    TAMANHO = 300

    @classmethod
    def exportar(cls, dados):
        linhas = []
        linhas.append(cls._header(dados))

        total_ne = 0
        total_nl = 0
        total_op = 0
        valor_ne = 0.0
        valor_nl = 0.0
        valor_op = 0.0

        for ne in dados.get("nes", []):
            linhas.append(cls._registro_ne(ne, dados))
            total_ne += 1
            valor_ne += float(ne.valor_empenho or 0.0)

        for nl in dados.get("nls", []):
            linhas.append(cls._registro_nl(nl, dados))
            total_nl += 1
            valor_nl += float(nl.valor_liquidado or 0.0)

        for op in dados.get("ops", []):
            linhas.append(cls._registro_op(op, dados))
            total_op += 1
            valor_op += float(op.valor or 0.0)

        linhas.append(
            cls._trailer(
                total_ne,
                valor_ne,
                total_nl,
                valor_nl,
                total_op,
                valor_op,
            )
        )

        conteudo = "\r\n".join(linhas) + "\r\n"
        return conteudo.encode("latin-1", errors="replace")

    @classmethod
    def _a(cls, val, size):
        s = str(val or "").upper()[:size]
        return s.ljust(size)

    @classmethod
    def _n(cls, val, size):
        try:
            v = int(val or 0)
        except (ValueError, TypeError):
            v = 0
        return str(v).zfill(size)[:size]

    @classmethod
    def _v(cls, val, size, dec=2):
        try:
            centavos = round(float(val or 0.0) * (10 ** dec))
        except (ValueError, TypeError):
            centavos = 0
        return str(int(centavos)).zfill(size)[:size]

    @classmethod
    def _d(cls, val):
        if hasattr(val, "strftime"):
            return val.strftime("%d%m%Y")
        return "00000000"

    @classmethod
    def _pad(cls, linha):
        return linha.ljust(cls.TAMANHO)[: cls.TAMANHO]

    @classmethod
    def _header(cls, d):
        l = ""
        l += "H "
        l += cls._a(d.get("ug_codigo", ""), 6)
        l += cls._a(d.get("ug_nome", ""), 40)
        l += cls._n(d.get("exercicio", date.today().year), 4)
        l += cls._d(d.get("data_geracao", date.today()))
        l += cls._a(d.get("operador", ""), 30)
        l += cls._a("GRP-ODOO-19", 20)
        l += cls._a("1.0", 10)
        return cls._pad(l)

    @classmethod
    def _registro_ne(cls, ne, d):
        l = ""
        l += "NE"
        l += cls._a(d.get("ug_codigo", ""), 6)
        l += cls._n(ne.exercicio, 4)
        l += cls._a(ne.name or "", 20)
        l += cls._d(ne.create_date)
        l += cls._a(ne.natureza_despesa or "", 17)
        l += cls._a(ne.tipo_empenho or "", 15)
        credor = ne.credor_id
        l += cls._a(credor.name if credor else "", 40)
        l += cls._a((credor.vat or "") if credor else "", 18)
        l += cls._v(ne.valor_empenho, 15)
        l += cls._a(ne.state or "", 10)
        l += cls._a(ne.objeto or "", 80)
        return cls._pad(l)

    @classmethod
    def _registro_nl(cls, nl, d):
        l = ""
        l += "NL"
        l += cls._a(d.get("ug_codigo", ""), 6)
        l += cls._n(nl.exercicio, 4)
        l += cls._a(nl.name or "", 20)
        l += cls._a(nl.empenho_name or "", 20)
        l += cls._d(nl.data_liquidacao)
        l += cls._d(nl.data_ateste)
        credor = nl.credor_id
        l += cls._a(credor.name if credor else "", 40)
        l += cls._v(nl.valor_liquidado, 15)
        l += cls._a(nl.state or "", 10)
        l += cls._a(nl.nf_numero or "", 20)
        l += cls._a(nl.objeto_liquidacao or "", 80)
        return cls._pad(l)

    @classmethod
    def _registro_op(cls, op, d):
        l = ""
        l += "OP"
        l += cls._a(d.get("ug_codigo", ""), 6)
        l += cls._n(op.exercicio, 4)
        l += cls._a(op.name or "", 20)
        pd = op.pd_id
        l += cls._a(pd.name if pd else "", 20)
        nl_name = pd.liquidacao_id.name if pd and pd.liquidacao_id else ""
        l += cls._a(nl_name, 20)
        l += cls._d(op.data_pagamento)
        dest = op.destinatario_id
        l += cls._a(dest.name if dest else "", 40)
        l += cls._a((dest.vat or "") if dest else "", 18)
        l += cls._v(op.valor, 15)
        l += cls._a(op.state or "", 10)
        l += cls._a(op.tipo_pagamento or "", 15)
        return cls._pad(l)

    @classmethod
    def _trailer(cls, cnt_ne, val_ne, cnt_nl, val_nl, cnt_op, val_op):
        l = ""
        l += "T "
        l += cls._n(cnt_ne, 8)
        l += cls._v(val_ne, 18)
        l += cls._n(cnt_nl, 8)
        l += cls._v(val_nl, 18)
        l += cls._n(cnt_op, 8)
        l += cls._v(val_op, 18)
        l += cls._d(date.today())
        return cls._pad(l)
