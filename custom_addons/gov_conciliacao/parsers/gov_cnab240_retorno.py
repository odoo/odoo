"""
Parser de arquivo CNAB240 Retorno Bancario.
Suporta Banco do Brasil (001) e Caixa Economica Federal (104).
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


OCORRENCIAS_BB = {
    "00": "aceito",
    "01": "aceito",
    "02": "aceito",
    "BD": "aceito",
    "BE": "rejeitado",
    "BN": "rejeitado",
    "CD": "divergencia",
    "CI": "informativo",
    "DT": "devolvido",
    "ED": "rejeitado",
    "ER": "rejeitado",
    "FK": "aceito",
    "FP": "rejeitado",
    "HA": "aceito",
    "HB": "rejeitado",
    "HC": "aceito",
    "HD": "divergencia",
    "HE": "rejeitado",
    "HJ": "devolvido",
    "TA": "rejeitado",
    "TE": "rejeitado",
}

OCORRENCIAS_CAIXA = {
    "00": "aceito",
    "01": "aceito",
    "BD": "aceito",
    "BE": "rejeitado",
    "CD": "divergencia",
    "DT": "devolvido",
    "ED": "rejeitado",
    "ER": "rejeitado",
    "HA": "aceito",
    "HB": "rejeitado",
    "HC": "aceito",
    "HD": "divergencia",
    "HJ": "devolvido",
    "TE": "rejeitado",
    "OC": "aceito",
    "ND": "debito_nao_id",
    "NC": "credito_nao_id",
}


@dataclass
class LinhaRetorno:
    banco: str = ""
    lote: int = 0
    seq: int = 0
    segmento: str = ""
    ocorrencia: str = ""
    status: str = ""
    numero_doc: str = ""
    valor_pago: float = 0.0
    valor_original: float = 0.0
    data_pagamento: Optional[date] = None
    data_real: Optional[date] = None
    nome_beneficiario: str = ""
    banco_dest: str = ""
    agencia_dest: str = ""
    conta_dest: str = ""
    mensagem: str = ""
    raw: str = ""


@dataclass
class RetornoCnab240:
    banco: str = ""
    data_arquivo: Optional[date] = None
    empresa_nome: str = ""
    empresa_cnpj: str = ""
    linhas: list = field(default_factory=list)
    erros: list = field(default_factory=list)
    total_aceito: float = 0.0
    total_rejeitado: float = 0.0
    total_divergente: float = 0.0


class Cnab240RetornoParser:
    TAMANHO = 240

    def parse(self, conteudo: bytes) -> RetornoCnab240:
        try:
            texto = conteudo.decode("latin-1")
        except Exception:
            texto = conteudo.decode("utf-8", errors="replace")

        linhas_raw = [linha for linha in texto.splitlines() if len((linha or "").strip()) >= 10]
        resultado = RetornoCnab240()

        for linha in linhas_raw:
            linha = (linha or "").ljust(self.TAMANHO)
            tipo_registro = linha[7]
            if tipo_registro == "0":
                self._parse_header_arquivo(linha, resultado)
                continue
            if tipo_registro != "3":
                continue
            detalhe = self._parse_detalhe(linha, resultado.banco)
            if not detalhe:
                continue
            resultado.linhas.append(detalhe)
            if detalhe.status == "aceito":
                resultado.total_aceito += detalhe.valor_pago
            elif detalhe.status == "rejeitado":
                resultado.total_rejeitado += detalhe.valor_original
            elif detalhe.status in ("divergencia", "devolvido"):
                resultado.total_divergente += detalhe.valor_pago

        return resultado

    def _parse_header_arquivo(self, linha: str, resultado: RetornoCnab240):
        resultado.banco = (linha[0:3] or "").strip()
        resultado.empresa_nome = (linha[72:102] or "").strip()
        resultado.empresa_cnpj = (linha[18:32] or "").strip()
        resultado.data_arquivo = self._parse_data(linha[143:151])

    def _parse_detalhe(self, linha: str, banco: str) -> Optional[LinhaRetorno]:
        segmento = linha[13]
        if segmento == "A":
            return self._parse_segmento_a(linha, banco)
        if segmento == "B":
            return self._parse_segmento_b(linha, banco)
        if segmento == "J":
            return self._parse_segmento_j(linha, banco)
        return None

    def _parse_segmento_a(self, linha: str, banco: str) -> LinhaRetorno:
        ocorrencias_map = OCORRENCIAS_BB if banco == "001" else OCORRENCIAS_CAIXA
        ocorrencia = (linha[230:232] or "").strip()
        status = ocorrencias_map.get(ocorrencia, "informativo")
        return LinhaRetorno(
            banco=banco,
            lote=self._parse_int(linha[3:7]),
            seq=self._parse_int(linha[8:13]),
            segmento="A",
            ocorrencia=ocorrencia,
            status=status,
            numero_doc=(linha[73:93] or "").strip(),
            valor_pago=self._parse_valor(linha[152:167], dec=2),
            valor_original=self._parse_valor(linha[119:134], dec=2),
            data_pagamento=self._parse_data(linha[93:101]),
            data_real=self._parse_data(linha[137:145]),
            nome_beneficiario=(linha[43:73] or "").strip(),
            banco_dest=(linha[20:23] or "").strip(),
            agencia_dest=(linha[23:28] or "").strip(),
            conta_dest=(linha[29:41] or "").strip(),
            mensagem=ocorrencia,
            raw=linha,
        )

    def _parse_segmento_b(self, linha: str, banco: str) -> LinhaRetorno:
        return LinhaRetorno(
            banco=banco,
            segmento="B",
            status="informativo",
            raw=linha,
        )

    def _parse_segmento_j(self, linha: str, banco: str) -> LinhaRetorno:
        ocorrencias_map = OCORRENCIAS_BB if banco == "001" else OCORRENCIAS_CAIXA
        ocorrencia = (linha[230:232] or "").strip()
        status = ocorrencias_map.get(ocorrencia, "informativo")
        return LinhaRetorno(
            banco=banco,
            lote=self._parse_int(linha[3:7]),
            seq=self._parse_int(linha[8:13]),
            segmento="J",
            ocorrencia=ocorrencia,
            status=status,
            numero_doc=(linha[73:93] or "").strip(),
            valor_pago=self._parse_valor(linha[152:167], dec=2),
            valor_original=self._parse_valor(linha[119:134], dec=2),
            data_pagamento=self._parse_data(linha[93:101]),
            nome_beneficiario=(linha[48:78] or "").strip(),
            mensagem=ocorrencia,
            raw=linha,
        )

    @staticmethod
    def _parse_data(valor: str) -> Optional[date]:
        texto = (valor or "").strip().replace("/", "")
        if len(texto) == 8 and texto != "00000000":
            try:
                return date(int(texto[4:8]), int(texto[2:4]), int(texto[0:2]))
            except ValueError:
                return None
        return None

    @staticmethod
    def _parse_valor(valor: str, dec: int = 2) -> float:
        try:
            return int((valor or "").strip() or 0) / (10 ** dec)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _parse_int(valor: str) -> int:
        try:
            return int((valor or "").strip() or 0)
        except (ValueError, TypeError):
            return 0


PARSERS = {
    "001": Cnab240RetornoParser,
    "104": Cnab240RetornoParser,
}


def get_parser(banco_codigo: str) -> Cnab240RetornoParser:
    parser_class = PARSERS.get(banco_codigo, Cnab240RetornoParser)
    return parser_class()
