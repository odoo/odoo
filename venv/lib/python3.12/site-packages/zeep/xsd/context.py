from zeep.settings import Settings


class XmlParserContext:
    """Parser context when parsing XML elements"""

    def __init__(self, settings=None):
        self.schemas = []
        self.settings = settings or Settings()
