/** @odoo-module **/

import { Component } from "@odoo/owl";
import { AutoCompleteWithPages } from "@website/components/autocomplete_with_pages/autocomplete_with_pages";

export class PlacesAutoComplete extends Component {
    static template = "website.PlacesAutoComplete";
    static components = { AutoCompleteWithPages };
    static props = {
        targetDropdown: { type: HTMLElement, required: true },
        contentWindow: { type: Object, required: true },
        onPlaceSelected: { type: Function, required: true },
        onError: { type: Function, required: true },
    };

    get sources() {
        return [
            {
                optionTemplate: "website.PlacesAutoComplete.Item",
                options: async (inputValue) => {
                    if (inputValue.length < 2) {
                        return [];
                    }
                    try {
                        const result =
                            await this.props.contentWindow.google.maps.places.AutocompleteSuggestion.fetchAutocompleteSuggestions(
                                {
                                    input: inputValue,
                                    includedPrimaryTypes: ["geocode"],
                                }
                            );
                        const suggestions = result.suggestions || [];
                        return suggestions.map((suggestion) => ({
                            id: suggestion.placePrediction.id,
                            label: suggestion.placePrediction.text.toString(),
                            value: suggestion.placePrediction.text.toString(),
                            classList: "pac-item",
                            placePrediction: suggestion.placePrediction,
                        }));
                    } catch {
                        this.props.onError();
                    }
                },
            },
        ];
    }

    async onSelect(selectedSubjection, { input }) {
        const { placePrediction } = Object.getPrototypeOf(selectedSubjection);
        try {
            const placeResult = placePrediction.toPlace();
            await placeResult.fetchFields({
                fields: ["displayName", "formattedAddress", "location"],
            });
            const place = {
                place_id: placeResult.id,
                formatted_address: placeResult.formattedAddress || placeResult.displayName,
                geometry: {
                    location: {
                        lat: placeResult.location.lat,
                        lng: placeResult.location.lng,
                    },
                },
                name: placeResult.displayName,
            };
            input.value = place.formatted_address || placePrediction.text;
            this.props.targetDropdown.value = input.value;
            this.props.onPlaceSelected(place);
        } catch {
            this.props.onError();
        }
    }
}
