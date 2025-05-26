import { useRef, onMounted, useState, useEffect, onWillDestroy } from "@odoo/owl";
import { BaseOptionComponent } from "@html_builder/core/utils";

/** @import { Coordinates, Place } from './google_maps_option_plugin.js' */
/**
 * @typedef {Object} Props
 * @property {function():object} getMapsAPI
 * @property {function(Element, Coordinates):Promise<Place | undefined>} getPlace
 * @property {function(Element, Place):void} onPlaceChanged
 */

export class GoogleMapsOption extends BaseOptionComponent {
    static template = "website.GoogleMapsOption";
    /** @type {Props} */
    static props = {
        getMapsAPI: { type: Function },
        getPlace: { type: Function },
        onPlaceChanged: { type: Function },
    };

    async setup() {
        super.setup();
        /** @type {Props} */
        this.props;
        /** @type {{ getEditingElement: function():Element }} */
        this.env;
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
                this.props.getMapsAPI().event.removeListener(this.autocompleteListener);
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
        if (!this.googleMapsAutocomplete && this.props.getMapsAPI()) {
            const mapsAPI = this.props.getMapsAPI();
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
                this.props.getPlace(editingElement, coordinates).then((place) => {
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
        this.props.onPlaceChanged(this.env.getEditingElement(), place);
        this.state.formattedAddress = place?.formatted_address || "";
    }
}
