try:
    from lxml import etree
except ImportError:  # pragma: no cover
    etree = None


class BrNfeXmlGenerator:
    def generate(self, nfe_record) -> bytes:
        if etree is None:
            raise RuntimeError("Dependencia lxml nao instalada.")
        root = etree.Element("NFe")
        inf_nfe = etree.SubElement(root, "infNFe", Id=nfe_record.chave_acesso or "TEMP")
        self._build_ide(inf_nfe, nfe_record)
        self._build_emit(inf_nfe, nfe_record)
        self._build_dest(inf_nfe, nfe_record)
        self._build_total(inf_nfe, nfe_record)
        return etree.tostring(root, encoding="utf-8", xml_declaration=True)

    def _build_ide(self, parent, nfe):
        ide = etree.SubElement(parent, "ide")
        etree.SubElement(ide, "nNF").text = str(nfe.numero or 0)
        etree.SubElement(ide, "serie").text = nfe.serie or "1"

    def _build_emit(self, parent, nfe):
        emit = etree.SubElement(parent, "emit")
        etree.SubElement(emit, "xNome").text = nfe.company_id.name or ""
        etree.SubElement(emit, "CNPJ").text = (nfe.company_id.cnpj or "").replace(".", "").replace("/", "").replace("-", "")

    def _build_dest(self, parent, nfe):
        dest = etree.SubElement(parent, "dest")
        partner = nfe.account_move_id.partner_id
        etree.SubElement(dest, "xNome").text = partner.name or ""
        etree.SubElement(dest, "CNPJ").text = (partner.cnpj_cpf or "").replace(".", "").replace("/", "").replace("-", "")

    def _build_total(self, parent, nfe):
        total = etree.SubElement(parent, "total")
        icms = etree.SubElement(total, "ICMSTot")
        etree.SubElement(icms, "vNF").text = str(getattr(nfe.account_move_id, "amount_total", 0.0))

