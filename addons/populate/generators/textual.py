from string import ascii_letters, digits

from .generator import Generator


class Char(Generator):
    """Generate random strings from a character set."""
    name = 'textual.char'
    allowed_field_types = ('char', 'html', 'virtual')  # TODO: add dedicated html generator.

    def __init__(self, char_set: str = ascii_letters + digits, length: int = 12, **kwargs):
        super().__init__(**kwargs)
        self.char_set = char_set
        self.length = length

    def _next(self, known_vals):
        return ''.join(self.distribution.choices(self.char_set, k=self.length))

    @classmethod
    def convert_to_kwargs(cls, attrs):
        kwargs = super().convert_to_kwargs(attrs)

        if 'char_set' in attrs:
            kwargs['char_set'] = attrs['char_set']

        if 'length' in attrs:
            kwargs['length'] = int(attrs['length'])

        return kwargs


class Text(Char):
    """Generate random text strings."""
    name = 'textual.text'
    allowed_field_types = ('text', 'html', 'virtual')

    def __init__(self, char_set: str = ascii_letters + digits + ' \n', length: int = 50, **kwargs):
        super().__init__(char_set, length, **kwargs)
