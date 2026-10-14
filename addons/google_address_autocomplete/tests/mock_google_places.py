def make_mock_google_route(on_call=None):
    def _call_google_route(self, route, api_key, field_mask, params, method='GET'):
        res = None
        if on_call:
            res = on_call(route, api_key, field_mask, params, method)
        if res is not None:
            return res
        if route == "/places:autocomplete":
            return {
                "suggestions": [
                    {
                        "placePrediction": {
                            "placeId": "ChIJD7fiBh9u5kcRYJSMaMOCCwQ",
                            "text": {"text": "Paris, France"},
                        },
                    },
                    {
                        "placePrediction": {
                            "placeId": "ChIJmysnFgZYSoYRSfPTL2YJuck",
                            "text": {"text": "Paris, TX, USA"},
                        },
                    },
                    {
                        "placePrediction": {
                            "placeId": "ChIJ4zHP-Sije4gRBDEsVxunOWg",
                            "text": {"text": "Paris, TN, USA"},
                        },
                    },
                    {
                        "placePrediction": {
                            "placeId": "ChIJsamfQbVtLIgR-X18G75Hyi0",
                            "text": {"text": "Paris, Brant, ON, Canada"},
                        },
                    },
                    {
                        "placePrediction": {
                            "placeId": "ChIJsU7_xMfKQ4gReI89RJn0-RQ",
                            "text": {"text": "Paris, KY, USA"},
                        },
                    },
                ],
            }
        if route.startswith("/places/"):
            return {
                "addressComponents": [
                    {
                        "longText": "48",
                        "shortText": "48",
                        "types": ["street_number"],
                    },
                    {
                        "longText": "Pirrama Road",
                        "shortText": "Pirrama Rd",
                        "types": ["route"],
                    },
                    {
                        "longText": "Pyrmont",
                        "shortText": "Pyrmont",
                        "types": ["locality", "political"],
                    },
                    {
                        "longText": "City of Sydney",
                        "shortText": "City of Sydney",
                        "types": ["administrative_area_level_2", "political"],
                    },
                    {
                        "longText": "New South Wales",
                        "shortText": "NSW",
                        "types": ["administrative_area_level_1", "political"],
                    },
                    {
                        "longText": "Australia",
                        "shortText": "AU",
                        "types": ["political", "country"],  # should work w/ "unordered" types
                    },
                    {
                        "longText": "2009",
                        "shortText": "2009",
                        "types": ["postal_code"],
                    },
                ],
                "adrFormatAddress": '<span class="street-address">48 Pirrama Rd</span>, <span class="locality">Pyrmont</span> <span class="region">NSW</span> <span class="postal-code">2009</span>, <span class="country-name">Australia</span>',
            }

    return _call_google_route
