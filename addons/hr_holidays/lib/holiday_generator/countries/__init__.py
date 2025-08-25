import importlib

BASE_PKG = __name__

_COUNTRY_PATHS = {
    "AE": "unitedarabemirates.UnitedArabEmirates",
    "AU": "australia.Australia",
    "BD": "bangladesh.Bangladesh",
    "BE": "belgium.Belgium",
    "CH": "switzerland.Switzerland",
    "EG": "egypt.Egypt",
    "HK": "hongkong.HongKong",
    "ID": "indonesia.Indonesia",
    "IN": "india.India",
    "JO": "jordan.Jordan",
    "KE": "kenya.Kenya",
    "LT": "lithuania.Lithuania",
    "LU": "luxembourg.Luxembourg",
    "MA": "morocco.Morocco",
    "MX": "mexico.Mexico",
    "MY": "malaysia.Malaysia",
    "NL": "netherlands.Netherlands",
    "PK": "pakistan.Pakistan",
    "PL": "poland.Poland",
    "RO": "romania.Romania",
    "SA": "saudiarabia.SaudiArabia",
    "SK": "slovakia.Slovakia",
    "TR": "turkey.Turkey",
    "US": "unitedstates.UnitedStates",
}

COUNTRY_CLASS_MAP = dict(_COUNTRY_PATHS)

def __getattr__(name: str):
    """
    Lazy-load a country class when accessed as an attribute of this package.
    Example:
        from odoo.addons.hr_holidays.lib.holiday_generator import countries
        India = getattr(countries, "IN")   # returns India class
    """
    if name in _COUNTRY_PATHS:
        subpath = _COUNTRY_PATHS[name]
        module_path, class_name = subpath.rsplit(".", 1)
        # Import relative to this package, not top-level
        mod = importlib.import_module(f"{BASE_PKG}.{module_path}")
        cls = getattr(mod, class_name)
        globals()[name] = cls  # cache
        return cls
    raise AttributeError(f"module {__name__} has no attribute {name}")
