from __future__ import annotations
from .object_type import Organization, Place


class LocalBusiness(Organization, Place):
    __schema_properties__ = Organization.__schema_properties__ | Place.__schema_properties__ | {
        "currenciesAccepted": ['r', "Text"],
        "openingHours": ['r', "Text"],
        "paymentAccepted": ['r', "Text"],
        "priceRange": "Text"
    }


class FoodEstablishment(LocalBusiness):
    __schema_properties__ = LocalBusiness.__schema_properties__ | {
        "acceptsReservations": ["Boolean", "Text", "URL"],
        "hasMenu": ["Menu", "Text", "URL"],
        "servesCuisine": ["Text"],
        "starRating": ['r', "Rating"]
    }


class Restaurant(FoodEstablishment):
    pass
