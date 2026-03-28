from .gov_typst_framework import GovTypstFramework


class GovTypstDocumentBuilder:
    @classmethod
    def get_model_selection(cls):
        return GovTypstFramework.get_model_selection()

    @classmethod
    def get_defaults(cls, model_key):
        return GovTypstFramework.get_defaults(model_key)

    @classmethod
    def get_default_doc_type(cls, model_key):
        return cls.get_defaults(model_key).get("doc_type", "outro")

    @classmethod
    def get_default_title(cls, model_key):
        return cls.get_defaults(model_key).get("title", "Documento")

    @classmethod
    def build_document(cls, payload):
        return GovTypstFramework.build_document(payload)
