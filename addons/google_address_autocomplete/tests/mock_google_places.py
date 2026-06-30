def make_mock_google_route(on_call=None):
    def _call_google_route(self, route, params):
        res = None
        if on_call:
            res = on_call(route, params)
        if res is not None:
            return res
        if route == "/autocomplete/json":
            return {
                "predictions": [
                    {
                        "description": "Paris, France",
                        "matched_substrings": [{"length": 5, "offset": 0}],
                        "place_id": "ChIJD7fiBh9u5kcRYJSMaMOCCwQ",
                        "reference": "ChIJD7fiBh9u5kcRYJSMaMOCCwQ",
                        "structured_formatting": {
                            "main_text": "Paris",
                            "main_text_matched_substrings": [
                                {"length": 5, "offset": 0}
                            ],
                            "secondary_text": "France",
                        },
                        "terms": [
                            {"offset": 0, "value": "Paris"},
                            {"offset": 7, "value": "France"},
                        ],
                        "types": ["locality", "political", "geocode"],
                    },
                    {
                        "description": "Paris, TX, USA",
                        "matched_substrings": [{"length": 5, "offset": 0}],
                        "place_id": "ChIJmysnFgZYSoYRSfPTL2YJuck",
                        "reference": "ChIJmysnFgZYSoYRSfPTL2YJuck",
                        "structured_formatting": {
                            "main_text": "Paris",
                            "main_text_matched_substrings": [
                                {"length": 5, "offset": 0}
                            ],
                            "secondary_text": "TX, USA",
                        },
                        "terms": [
                            {"offset": 0, "value": "Paris"},
                            {"offset": 7, "value": "TX"},
                            {"offset": 11, "value": "USA"},
                        ],
                        "types": ["locality", "political", "geocode"],
                    },
                    {
                        "description": "Paris, TN, USA",
                        "matched_substrings": [{"length": 5, "offset": 0}],
                        "place_id": "ChIJ4zHP-Sije4gRBDEsVxunOWg",
                        "reference": "ChIJ4zHP-Sije4gRBDEsVxunOWg",
                        "structured_formatting": {
                            "main_text": "Paris",
                            "main_text_matched_substrings": [
                                {"length": 5, "offset": 0}
                            ],
                            "secondary_text": "TN, USA",
                        },
                        "terms": [
                            {"offset": 0, "value": "Paris"},
                            {"offset": 7, "value": "TN"},
                            {"offset": 11, "value": "USA"},
                        ],
                        "types": ["locality", "political", "geocode"],
                    },
                    {
                        "description": "Paris, Brant, ON, Canada",
                        "matched_substrings": [{"length": 5, "offset": 0}],
                        "place_id": "ChIJsamfQbVtLIgR-X18G75Hyi0",
                        "reference": "ChIJsamfQbVtLIgR-X18G75Hyi0",
                        "structured_formatting": {
                            "main_text": "Paris",
                            "main_text_matched_substrings": [
                                {"length": 5, "offset": 0}
                            ],
                            "secondary_text": "Brant, ON, Canada",
                        },
                        "terms": [
                            {"offset": 0, "value": "Paris"},
                            {"offset": 7, "value": "Brant"},
                            {"offset": 14, "value": "ON"},
                            {"offset": 18, "value": "Canada"},
                        ],
                        "types": ["neighborhood", "political", "geocode"],
                    },
                    {
                        "description": "Paris, KY, USA",
                        "matched_substrings": [{"length": 5, "offset": 0}],
                        "place_id": "ChIJsU7_xMfKQ4gReI89RJn0-RQ",
                        "reference": "ChIJsU7_xMfKQ4gReI89RJn0-RQ",
                        "structured_formatting": {
                            "main_text": "Paris",
                            "main_text_matched_substrings": [
                                {"length": 5, "offset": 0}
                            ],
                            "secondary_text": "KY, USA",
                        },
                        "terms": [
                            {"offset": 0, "value": "Paris"},
                            {"offset": 7, "value": "KY"},
                            {"offset": 11, "value": "USA"},
                        ],
                        "types": ["locality", "political", "geocode"],
                    },
                ],
                "status": "OK",
            }
        if route == "/details/json":
            return {
                "result": {
                    "address_components": [
                        {
                            "long_name": "48",
                            "short_name": "48",
                            "types": ["street_number"],
                        },
                        {
                            "long_name": "Pirrama Road",
                            "short_name": "Pirrama Rd",
                            "types": ["route"],
                        },
                        {
                            "long_name": "Pyrmont",
                            "short_name": "Pyrmont",
                            "types": ["locality", "political"],
                        },
                        {
                            "long_name": "City of Sydney",
                            "short_name": "City of Sydney",
                            "types": ["administrative_area_level_2", "political"],
                        },
                        {
                            "long_name": "New South Wales",
                            "short_name": "NSW",
                            "types": ["administrative_area_level_1", "political"],
                        },
                        {
                            "long_name": "Australia",
                            "short_name": "AU",
                            "types": ["political", "country"],  # should work w/ "unordered" types
                        },
                        {
                            "long_name": "2009",
                            "short_name": "2009",
                            "types": ["postal_code"],
                        },
                    ],
                    "adr_address": '<span class="street-address">48 Pirrama Rd</span>, <span class="locality">Pyrmont</span> <span class="region">NSW</span> <span class="postal-code">2009</span>, <span class="country-name">Australia</span>',
                },
                "status": "OK",
            }

    return _call_google_route
