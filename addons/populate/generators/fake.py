"""
Faker-based generators for the populate module.
"""
import functools
import inspect

from faker import Faker

from .generator import Generator

# Stable Policy: Only adding new entries is allowed in 'stable'.
PROVIDERS_WHITELIST = {
    'address',
    'automotive',
    'bank',
    'barcode',
    'color',
    'company',
    'credit_card',
    'currency',
    'emoji',
    'file',
    'geo',
    'internet',
    'isbn',
    'job',
    'lorem',
    'misc',
    'passport',
    'person',
    'phone_number',
    'profile',
    'sbn',
    'ssn',
    'user_agent',
}

# Stable Policy: Only removing entries is allowed in 'stable', unless urgent
METHODS_BLACKLIST = {
    'boolean',  # from misc: Use scalar.boolean instead
    'image',    # from misc: Use binary.image instead
}

KNOWN_METHODS = set()
"""
Contains the exhaustive list of 'allowed' Faker methods from the providers.
This list is set during the loading of the module.
"""


def is_allowed(faker: Faker, method_name: str) -> bool:
    """Check if a Faker method is allowed based on whitelist/blacklist.

    :param faker: Faker proxy used to inspect providers and methods.
    :param method_name: Faker method name being considered for registration.
    :return: Whether the method can be exposed as a ``fake.*`` generator.
    """

    if method_name.startswith('_'):
        return False

    if method_name in METHODS_BLACKLIST:
        return False

    try:
        method = getattr(faker, method_name, None)
    except (AttributeError, NotImplementedError, TypeError):
        return False

    if not callable(method):
        return False

    # Faker object is a proxy to mapping of generators
    if not faker._factories:
        return False

    factory = faker._factories[0]

    try:
        factory_method = getattr(factory, method_name, None)
        if factory_method is None:
            return False
    except (AttributeError, NotImplementedError):
        return False

    for provider_class in factory.providers:
        if hasattr(provider_class, method_name):
            # Extract provider name from module's path
            # e.g., 'faker.providers.person' -> 'person'
            # note: module sometimes can be 'faker.providers.person.<locale>'
            # hence we always take the third entry.
            provider_module = provider_class.__module__
            provider_name = provider_module.split('.')[2]

            return provider_name in PROVIDERS_WHITELIST

    return False


def create(method_name: str):
    """Create and register a ``Generator`` subclass for a Faker method.

    :param method_name: Allowed Faker method name to expose as ``fake.<method>``.
    """

    if method_name not in KNOWN_METHODS:
        raise ValueError(
            f"Cannot create a fake generator for unknown method '{method_name}'. "
            f"It must be in KNOWN_METHODS (i.e., from an allowed Faker provider).",
        )

    class Fake(Generator):
        """
        Dynamically created generator wrapping a single Faker method.

        Accepts ``locale`` and any of the underlying Faker method's keyword arguments.
        """
        name = f'fake.{method_name}'
        # Disable type-checking, as inferring the correct Odoo field type from
        # either the return type of the typed method or from calling it
        # can be error-prone and/or inaccurate, leading to false-positives.
        allowed_field_types = None

        def __init__(self, locale='en_US', **kwargs):
            """Split populate kwargs from Faker method kwargs.

            :param locale: Faker locale used by the wrapped method.
            :param kwargs: Populate generator kwargs plus keyword arguments for
                the wrapped Faker method.
            """
            generator_signature = inspect.signature(Generator.__init__)
            generator_params = set(generator_signature.parameters.keys()) - {'self'}
            faker_kwargs = {
                k: v
                for k, v in kwargs.items()
                if k not in generator_params
            }

            allowed_params = {'field', 'env', 'random', 'job', 'session', 'valid_fields', 'unique', 'null_ratio', 'locale'}
            invalid_params = set(kwargs.keys()) - set(faker_kwargs.keys()) - allowed_params
            if invalid_params:
                env = kwargs['env']
                raise ValueError(env._(
                    "Invalid parameters: %(invalid_params)s. "
                    "Only these parameters are allowed (besides method's arguments): %(allowed_params)s",
                    invalid_params=', '.join(sorted(invalid_params)),
                    allowed_params=', '.join(sorted(allowed_params)),
                ))

            super().__init__(**{k: v for k, v in kwargs.items() if k in allowed_params})

            faker_method = getattr(Faker(locale), method_name)
            self.method = functools.partial(faker_method, **faker_kwargs)

        def _next(self, known_vals):
            return self.method()

        @classmethod
        def convert_to_kwargs(cls, attrs):
            kwargs = super().convert_to_kwargs(attrs)

            if 'locale' in attrs:
                kwargs['locale'] = attrs['locale']

            def convert(val: str):
                match val.strip().lower():
                    case 'true' | '1':
                        return True
                    case 'false' | '0':
                        return False
                    case 'none' | 'null' | 'nil' | '':
                        return None
                    case str(v) if v.lstrip('-').isdigit():
                        return int(v)
                    case str(v) if (
                        v.replace('.', '', 1)
                         .replace('-', '', 1)
                         .replace('e', '', 1)
                         .replace('E', '', 1)
                         .isdigit()
                    ):
                        return float(v)
                    case str(_):
                        # Forward the rest as is, as `str`
                        return val.strip()
                    case _:
                        msg = "Unreachable! All attribute values should be `str` at the source."
                        raise RuntimeError(msg)

            # Best effort convertion of Faker's method arguments
            for key, value in attrs.items():
                if key not in kwargs and key not in ('generator', 'name'):
                    if ',' in value:  # Collection/Sequence
                        items = value.strip()[1:-1]  # remove any `(), {}, []`
                        kwargs[key] = [convert(item) for item in items.split(',')]
                    else:
                        kwargs[key] = convert(value)

            return kwargs

    Fake.__name__ = f'Fake{method_name.title().replace("_", "")}'
    Fake.__qualname__ = Fake.__name__
