from __future__ import annotations

import typing

from odoo.libs.collections.mappings import ReadonlyDict

if typing.TYPE_CHECKING:
    from .environment import Environment


class LangData(ReadonlyDict[str, typing.Any]):
    # the shape res.lang caches per language, for a registry without the
    # language table; attribute access like the model's own LangData
    __slots__ = ()

    def __bool__(self) -> bool:
        return bool(self["id"])

    def __getattr__(self, name: str) -> typing.Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None


# base's res.lang.csv row for en_US, the language every registry speaks
_EN_US = {
    "id": 1,
    "name": "English (US)",
    "code": "en_US",
    "iso_code": "en",
    "url_code": "en",
    "active": True,
    "direction": "ltr",
    "date_format": "%m/%d/%Y",
    "time_format": "%I:%M:%S %p",
    "week_start": "7",
    "grouping": "[3,0]",
    "decimal_point": ".",
    "thousands_sep": ",",
    "flag_image_url": "/base/static/img/country_flags/us.png",
}


class Locale:
    __slots__ = ()

    def lang_data(self, env: Environment, code: str) -> typing.Any:
        if "res.lang" not in env.registry:
            # every installed language answers en_US's formats: the DB-free
            # tier has no language table to read them from
            if not self.is_lang_installed(env, code):
                return LangData({**_EN_US, "id": False, "code": code, "active": False})
            return LangData({**_EN_US, "code": code})
        return env["res.lang"]._get_data(code=code)

    def installed_langs(self, env: Environment) -> list[str]:
        if "res.lang" not in env.registry:
            return ["en_US"]
        return [code for code, _name in env["res.lang"].get_installed()]

    def is_lang_installed(self, env: Environment, code: str) -> bool:
        if "res.lang" not in env.registry:
            # a registry without the language table (the DB-free tier) speaks the
            # base language and nothing else
            return code == "en_US"
        return bool(env["res.lang"]._get_data(code=code))

    def decimal_precision(self, env: Environment, application: str) -> int:
        if "decimal.precision" not in env.registry:
            # the model's own default for an application nobody defined
            return 2
        return env["decimal.precision"].get_precision(application)

    def currency_rates(
        self, env: Environment, company: typing.Any, date: typing.Any
    ) -> dict[int, float]:
        # the rate of every currency for a company's root, as the sum_currency
        # aggregate's subquery picks it: the root's own rates before the shared
        # ones, and in that bucket the latest rate dated up to the day, else
        # the earliest later one; a currency without a rate is absent
        if "res.currency.rate" not in env.registry:
            return {}
        root_id = company.root_id.id
        rates = (
            env["res.currency.rate"]
            .sudo()
            .search([("company_id", "in", [root_id, False])])
        )
        rate_by_currency: dict[int, float] = {}
        for currency, currency_rates in rates.grouped("currency_id").items():
            own = currency_rates.filtered(lambda r: r["company_id"].id == root_id)
            bucket = own or currency_rates
            past = bucket.filtered(lambda r: r["name"] <= date)
            chosen = (
                max(past, key=lambda r: r["name"])
                if past
                else min(bucket, key=lambda r: r["name"])
            )
            rate_by_currency[currency.id] = chosen["rate"]
        return rate_by_currency


LOCALE = Locale()
