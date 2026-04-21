import { useLayoutEffect, useRef, useState } from "@web/owl2/utils";
import { onMounted, onWillDestroy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { PlacesAutoComplete } from "@website/components/googleplaces_autocomplete/places_autocomplete";
import utils from "@website/js/utils";

/** @import { Coordinates, Place } from './google_maps_option_plugin.js' */

export class GoogleMapsOption extends BaseOptionComponent {
    static id = "google_maps_option";
    static template = "website.GoogleMapsOption";
    static dependencies = ["googleMapsOption"];

    async setup() {
        super.setup();

        this.getMapsAPI = this.dependencies.googleMapsOption.getMapsAPI;
        /** @type {function(Element, Coordinates):Promise<Place | undefined>} */
        this.getPlace = this.dependencies.googleMapsOption.getPlace;
        /** @type {function(Element, Place):void} */
        this.commitPlace = this.dependencies.googleMapsOption.commitPlace;

        this.inputRef = useRef("inputRef");
        /** @type {{ formattedAddress: string }} */
        this.state = useState({
            formattedAddress: this.env.getEditingElement().dataset.pinAddress || "",
        });
        useLayoutEffect(
            () => {
                this.env.getEditingElement().dataset.pinAddress = this.state.formattedAddress;
            },
            () => [this.state.formattedAddress]
        );
        onMounted(async () => {
            this.initializeAutocomplete(this.inputRef.el);
        });
        onWillDestroy(() => {
            this.unmountAutocomplete?.();
        });
    }

    /**
     * Initialize Google Places API's autocompletion on the option's input.
     *
     * @param {Element} inputEl
     */
    initializeAutocomplete(inputEl) {
        const editingElement = this.env.getEditingElement();
        this.unmountAutocomplete = utils.mountAutocompleteComponent(PlacesAutoComplete, {
            targetDropdown: inputEl,
            maps: this.getMapsAPI(),
            onPlaceSelected: this.onPlaceSelected.bind(this),
            onError: () => this.dependencies.googleMapsOption.notifyGMapsError(editingElement),
        });
        if (!this.state.formattedAddress) {
            /** @type {Coordinates} */
            const coordinates = editingElement.dataset.mapGps;
            this.getPlace(editingElement, coordinates).then((place) => {
                if (place?.formatted_address) {
                    this.state.formattedAddress = place.formatted_address;
                }
            });
        }
    }

    /**
     * Retrieve the new place given by Google Places API's autocompletion
     * whenever it sends a signal that the place changed, and send it to the
     * plugin.
     *
     * @param {Place} place Place object from Google Maps API
     */
    onPlaceSelected(place) {
        this.commitPlace(this.env.getEditingElement(), place);
        this.state.formattedAddress = place?.formatted_address || "";
    }
}

registry.category("website-options").add(GoogleMapsOption.id, GoogleMapsOption);
