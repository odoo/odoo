import re


class GovTypstSerializer:
    """Serializa estruturas Python para bindings Typst."""

    _ESCAPE = str.maketrans(
        {
            "\\": "\\\\",
            '"': '\\"',
            "\n": "\\n",
            "\r": "\\r",
            "\t": "\\t",
        }
    )

    def dumps_all(self, bindings):
        header = (
            "// Gerado automaticamente por GovTypstSerializer\n"
            "// Snapshot reprodutivel do render estruturado\n\n"
        )
        parts = [self.dumps(name, value) for name, value in bindings.items()]
        return header + "\n".join(parts).rstrip() + "\n"

    def dumps(self, name, value):
        return f"#let {self._key(name)} = {self._value(value, indent=0)}"

    def _value(self, value, indent=0):
        pad = "  " * indent
        child_pad = "  " * (indent + 1)

        if value is None:
            return "none"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            if value.is_integer():
                return str(int(value))
            return repr(value)
        if isinstance(value, str):
            return f'"{value.translate(self._ESCAPE)}"'
        if isinstance(value, (list, tuple)):
            if not value:
                return "()"
            rows = ",\n".join(f"{child_pad}{self._value(item, indent + 1)}" for item in value)
            return f"(\n{rows},\n{pad})"
        if isinstance(value, dict):
            if not value:
                return "()"
            rows = ",\n".join(
                f"{child_pad}{self._key(key)}: {self._value(item, indent + 1)}"
                for key, item in value.items()
            )
            return f"(\n{rows},\n{pad})"
        return f'"{str(value).translate(self._ESCAPE)}"'

    @staticmethod
    def _key(name):
        key = re.sub(r"[^a-zA-Z0-9_]", "_", str(name))
        if key and key[0].isdigit():
            key = f"_{key}"
        return key or "valor"
