class BrNfeContingencia:
    FALLBACK_ORDER = ["svc_an", "svc_rs"]

    def detect_sefaz_down(self, uf: str) -> bool:
        return bool(uf)

    def activate(self, nfe_record):
        nfe_record.write({"estado": "contingencia", "contingencia_tipo": self.FALLBACK_ORDER[0]})

    def try_transmission(self, nfe_record) -> bool:
        if not self.detect_sefaz_down(nfe_record.company_id.state_id.code):
            return False
        self.activate(nfe_record)
        return True

