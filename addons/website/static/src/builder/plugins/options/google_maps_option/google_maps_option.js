import { useRef, onMounted, useState, useEffect, onWillDestroy } from "@odoo/owl";
import { BaseOptionComponent } from "@html_builder/core/utils";

/** @import { Coordinates, Place } from './google_maps_option_plugin.js' */

export class GoogleMapsOption extends BaseOptionComponent {
    static template = "website.GoogleMapsOption";
    static dependencies = ["googleMapsOption"];
    static selector = ".s_google_map";

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
        useEffect(
            () => {
                this.env.getEditingElement().dataset.pinAddress = this.state.formattedAddress;
            },
            () => [this.state.formattedAddress]
        );
        onMounted(async () => {
            this.initializeAutocomplete(this.inputRef.el);
        });
        onWillDestroy(() => {
            if (this.autocompleteListener) {
                this.getMapsAPI().event.removeListener(this.autocompleteListener);
            }
            // Without this, the Google library injects elements inside the
            // DOM but does not remove them once the option is closed.
            for (const container of document.body.querySelectorAll(".pac-container")) {
                container.remove();
            }
        });
    }

    /**
     * Initialize Google Places API's autocompletion on the option's input.
     *
     * @param {Element} inputEl
     */
    initializeAutocomplete(inputEl) {
        if (!this.googleMapsAutocomplete && this.getMapsAPI()) {
            const mapsAPI = this.getMapsAPI();
            this.googleMapsAutocomplete = new mapsAPI.places.Autocomplete(inputEl, {
                types: ["geocode"],
            });
            this.autocompleteListener = mapsAPI.event.addListener(
                this.googleMapsAutocomplete,
                "place_changed",
                this.onPlaceChanged.bind(this)
            );
            if (!this.state.formattedAddress) {
                const editingElement = this.env.getEditingElement();
                /** @type {Coordinates} */
                const coordinates = editingElement.dataset.mapGps;
                this.getPlace(editingElement, coordinates).then((place) => {
                    if (place?.formatted_address) {
                        this.state.formattedAddress = place.formatted_address;
                    }
                });
            }
        }
    }

    /**
     * Retrieve the new place given by Google Places API's autocompletion
     * whenever it sends a signal that the place changed, and send it to the
     * plugin.
     */
    onPlaceChanged() {
        /** @type {Place | undefined} */
        const place = this.googleMapsAutocomplete.getPlace();
        this.commitPlace(this.env.getEditingElement(), place);
        this.state.formattedAddress = place?.formatted_address || "";
    }
}
