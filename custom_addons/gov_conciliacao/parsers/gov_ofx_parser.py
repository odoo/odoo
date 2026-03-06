"""
Parser OFX (Open Financial Exchange) para extratos bancarios.
Suporta OFX 1.x (SGML) e OFX 2.x (XML).
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional
import re


@dataclass
class TransacaoOFX:
    tipo: str = ""
    data: Optional[date] = None
    valor: float = 0.0
    fitid: str = ""
    memo: str = ""
    checknum: str = ""
    natureza: str = ""


@dataclass
class ExtratoOFX:
    banco: str = ""
    agencia: str = ""
    conta: str = ""
    moeda: str = "BRL"
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    saldo_final: float = 0.0
    saldo_data: Optional[date] = None
    transacoes: list = field(default_factory=list)
    erros: list = field(default_factory=list)


class GovOfxParser:
    def parse(self, conteudo: bytes) -> ExtratoOFX:
        try:
            texto = conteudo.decode("latin-1")
        except Exception:
            texto = conteudo.decode("utf-8", errors="replace")

        inicio = (texto or "").lower()[:200]
        if "<?ofx" in inicio or "<?xml" in inicio:
            return self._parse_xml(texto)
        return self._parse_sgml(texto)

    def _parse_sgml(self, texto: str) -> ExtratoOFX:
        extrato = ExtratoOFX()

        def tag(nome):
            match = re.search(rf"<{nome}>\s*([^\r\n<]+)", texto, re.IGNORECASE)
            return match.group(1).strip() if match else ""

        extrato.banco = tag("BANKID")
        extrato.agencia = tag("BRANCHID") or tag("AGENCIA")
        extrato.conta = tag("ACCTID")
        extrato.moeda = tag("CURSYM") or tag("CURDEF") or "BRL"
        extrato.data_inicio = self._parse_data(tag("DTSTART"))
        extrato.data_fim = self._parse_data(tag("DTEND"))
        extrato.saldo_final = self._parse_valor(tag("BALAMT"))
        extrato.saldo_data = self._parse_data(tag("DTASOF"))

        for bloco in re.finditer(r"<STMTTRN>(.*?)</STMTTRN>", texto, re.DOTALL | re.IGNORECASE):
            transacao = self._parse_transacao(bloco.group(1))
            if transacao:
                extrato.transacoes.append(transacao)

        return extrato

    def _parse_xml(self, texto: str) -> ExtratoOFX:
        extrato = ExtratoOFX()

        def xtag(nome):
            match = re.search(rf"<{nome}[^>]*>\s*([^<]+)", texto, re.IGNORECASE)
            return match.group(1).strip() if match else ""

        extrato.banco = xtag("BANKID")
        extrato.conta = xtag("ACCTID")
        extrato.moeda = xtag("CURDEF") or "BRL"
        extrato.data_inicio = self._parse_data(xtag("DTSTART"))
        extrato.data_fim = self._parse_data(xtag("DTEND"))
        extrato.saldo_final = self._parse_valor(xtag("BALAMT"))

        for bloco in re.finditer(r"<STMTTRN[^>]*>(.*?)</STMTTRN>", texto, re.DOTALL | re.IGNORECASE):
            transacao = self._parse_transacao(bloco.group(1))
            if transacao:
                extrato.transacoes.append(transacao)

        return extrato

    def _parse_transacao(self, bloco: str) -> Optional[TransacaoOFX]:
        def tag(nome):
            match = re.search(rf"<{nome}>\s*([^\r\n<]+)", bloco, re.IGNORECASE)
            return match.group(1).strip() if match else ""

        tipo = tag("TRNTYPE").upper()
        valor_raw = self._parse_valor(tag("TRNAMT"))
        if valor_raw == 0.0:
            return None

        natureza = "credito" if valor_raw > 0 else "debito"
        return TransacaoOFX(
            tipo=tipo,
            data=self._parse_data(tag("DTPOSTED")),
            valor=abs(valor_raw),
            fitid=tag("FITID"),
            memo=tag("MEMO") or tag("NAME"),
            checknum=tag("CHECKNUM"),
            natureza=natureza,
        )

    @staticmethod
    def _parse_data(valor: str) -> Optional[date]:
        texto = (valor or "").strip()[:8]
        if len(texto) == 8 and texto.isdigit():
            try:
                return date(int(texto[0:4]), int(texto[4:6]), int(texto[6:8]))
            except ValueError:
                return None
        return None

    @staticmethod
    def _parse_valor(valor: str) -> float:
        texto = (valor or "").strip().replace(",", ".")
        try:
            return float(texto)
        except (ValueError, TypeError):
            return 0.0
