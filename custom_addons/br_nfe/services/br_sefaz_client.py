class BrSefazClient:
    def __init__(self, certificado, ambiente: str):
        self.certificado = certificado
        self.ambiente = ambiente

    def autorizar_lote(self, xml_signed: bytes, uf: str) -> dict:
        return {"uf": uf, "status": "queued", "xml_size": len(xml_signed)}

    def consultar_retorno(self, rec_ibo: str, uf: str) -> dict:
        return {"recibo": rec_ibo, "uf": uf, "status": "pending"}

    def cancelar(self, chave: str, protocolo: str, motivo: str, uf: str) -> dict:
        return {"chave": chave, "protocolo": protocolo, "motivo": motivo, "uf": uf}

    def inutilizar(self, cnpj, ano, serie, ini, fim, justificativa, uf) -> dict:
        return {"cnpj": cnpj, "ano": ano, "serie": serie, "ini": ini, "fim": fim, "uf": uf}

    def status_servico(self, uf: str) -> dict:
        return {"uf": uf, "status": "unknown"}

