try:
    from lxml import etree
except ImportError:  # pragma: no cover
    etree = None


class BrNfeXsdValidator:
    def validate(self, xml_bytes: bytes) -> list[str]:
        if etree is None:
            return ["Dependencia lxml nao instalada."]
        try:
            etree.fromstring(xml_bytes)
            return []
        except etree.XMLSyntaxError as exc:
            return [str(exc)]

