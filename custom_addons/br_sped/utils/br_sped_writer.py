import hashlib


class BrSpedWriter:
    def __init__(self, company, period_from, period_to):
        self.company = company
        self.period_from = period_from
        self.period_to = period_to
        self._blocks = []

    def write_line(self, registro: str, fields: list) -> str:
        serialized = ["" if value is None else str(value) for value in fields]
        return f"|{registro}|{'|'.join(serialized)}|\n"

    def write_block(self, bloco: str, registros: list[str]) -> str:
        content = "".join(registros)
        self._blocks.append((bloco, content))
        return content

    def build_file(self) -> bytes:
        return "".join(block for _bloco, block in self._blocks).encode()

    def get_hash_md5(self, content: bytes) -> str:
        return hashlib.md5(content).hexdigest()

    def validate_version(self, obrigacao: str, version: str) -> bool:
        return bool(obrigacao and version)

