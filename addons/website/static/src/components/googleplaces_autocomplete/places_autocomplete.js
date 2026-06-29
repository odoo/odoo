/** @odoo-module **/

import { Component } from "@odoo/owl";
import { AutoCompleteWithPages } from "@website/components/autocomplete_with_pages/autocomplete_with_pages";

export class PlacesAutoComplete extends Component {
    static template = "website.PlacesAutoComplete";
    static components = { AutoCompleteWithPages };
    static props = {
        targetDropdown: { type: HTMLElement, required: true },
        maps: { type: Object, required: true },
        onPlaceSelected: { type: Function, required: true },
        onError: { type: Function, required: true },
    };

    setup() {
        this.state = { sessionToken: null };
    }

    get sources() {
        return [
            {
                optionTemplate: "website.PlacesAutoComplete.Item",
                options: async (inputValue) => {
                    if (inputValue.length < 2) {
                        return [];
                    }
                    if (!this.state.sessionToken) {
                        this.state.sessionToken =
                            new this.props.maps.places.AutocompleteSessionToken();
                    }
                    try {
                        const result =
                            await this.props.maps.places.AutocompleteSuggestion.fetchAutocompleteSuggestions(
                                {
                                    input: inputValue,
                                    includedPrimaryTypes: ["geocode"],
                                    sessionToken: this.state.sessionToken,
                                }
                            );
                        return result.suggestions.map((suggestion) => ({
                            id: suggestion.placePrediction.id,
                            label: suggestion.placePrediction.text.toString(),
                            value: suggestion.placePrediction.text.toString(),
                            classList: "pac-item",
                            placePrediction: suggestion.placePrediction,
                        }));
                    } catch {
                        this.props.onError();
                        return [];
                    }
                },
            },
        ];
    }

    async onSelect(selectedSuggestion, { input }) {
        const placePrediction = selectedSuggestion.placePrediction;
        try {
            const placeResult = placePrediction.toPlace();
            await placeResult.fetchFields({
                fields: ["formattedAddress", "location"],
            });
            this.state.sessionToken = null;
            const place = {
                place_id: placeResult.id,
                formatted_address: placeResult.formattedAddress || placePrediction.text.toString(),
                geometry: {
                    location: {
                        lat: placeResult.location.lat(),
                        lng: placeResult.location.lng(),
                    },
                },
            };
            this.props.onPlaceSelected(place);
        } catch {
            this.props.onError();
        }
    }
}
