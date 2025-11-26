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
            isContainedInOtherSnippet: this.env
                .getEditingElement()
                .matches("[data-snippet] :not(.oe_structure) > [data-snippet]"),
        });
        useEffect(
            () => {
                this.env.getEditingElement().dataset.pinAddress = this.state.formattedAddress;
            },
            () => [this.state.formattedAddress]
        );
        onMounted(async () => {
            await this.initializeAutocomplete(this.inputRef.el);
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
    async initializeAutocomplete(inputEl) {
        if (!this.googleMapsAutocomplete && this.getMapsAPI()) {
            inputEl.addEventListener("input", this._OnInput.bind(this));
            // const mapsAPI = this.getMapsAPI();
            // const { Autocomplete } = await mapsAPI.importLibrary("places");
            // this.googleMapsAutocomplete = new Autocomplete(inputEl, {
            //     types: ["geocode", "establishment"],
            //     fields: ["geometry", "formatted_address"],
            // });
            // const { event } = await mapsAPI.importLibrary("core");
            // event.addListener(
            //     this.googleMapsAutocomplete,
            //     "place_changed",
            //     this.onPlaceChanged.bind(this)
            // );
            // if (!this.state.formattedAddress) {
            //     const editingElement = this.env.getEditingElement();
            //     /** @type {Coordinates} */
            //     const coordinates = editingElement.dataset.mapGps;
            //     this.getPlace(editingElement, coordinates).then((place) => {
            //         const formattedAddress =
            //             place?.formatted_address || place?.Eg?.formattedAddress;
            //         if (formattedAddress) {
            //             this.state.formattedAddress = formattedAddress;
            //         }
            //     });
            // }
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
        // this.props.onPlaceChanged(this.env.getEditingElement(), place);
        const formattedAddress = place?.formatted_address || place?.Eg?.formattedAddress;
        this.state.formattedAddress = formattedAddress || "";
    }
    /**
     * Creates or retrieves the suggestion box for Google Maps autocomplete.
     * If it doesn't exist yet, it is appended to the DOM.
     *
     * @private
     * @returns {HTMLElement} The suggestion box element.
     */
    _getOrCreateSuggestionBox() {
        if (!this.suggestionBoxEl) {
            this.suggestionBoxEl = document.createElement("div");
            this.suggestionBoxEl.className = "s_google_map_suggestion_box";
            this.inputRef.el.parentNode.appendChild(this.suggestionBoxEl);
            this.inputRef.el.parentNode.style.position = "relative";
        }
        this.suggestionBoxEl.classList.remove("d-none");
        return this.suggestionBoxEl;
    }
    /**
     * Clears all suggestions and hides the suggestion box.
     *
     * @private
     */
    _clearSuggestions() {
        this._suggestionItems = [];
        this._selectedIndex = -1;
        if (this.suggestionBoxEl) {
            this.suggestionBoxEl.innerHTML = "";
            this.suggestionBoxEl.classList.add("d-none");
        }
    }
    /**
     * Updates the visual highlight for the currently selected suggestion.
     *
     * @private
     */
    _updateHighlight() {
        this._suggestionItems.forEach((itemEl, index) => {
            itemEl.classList.toggle(
                "s_google_map_suggestion_item_selected",
                index === this._selectedIndex
            );
        });
    }
    /**
     * Highlights a specific suggestion item in the list.
     *
     * @private
     * @param {HTMLElement} itemEl - The DOM element to highlight.
     */
    _highlightItem(itemEl) {
        const index = this._suggestionItems.indexOf(itemEl);
        if (index >= 0) {
            this._selectedIndex = index;
            this._updateHighlight();
        }
    }
    /**
     * Creates a DOM element for a place suggestion.
     *
     * @private
     * @param {Object} placePrediction - The prediction object for the place.
     * @returns {HTMLElement} The suggestion item DOM element.
     */
    _createSuggestionItem(placePrediction) {
        const itemEl = document.createElement("div");
        itemEl.className = "s_google_map_suggestion_item";
        itemEl.style.cursor = "pointer";
        const iconSpanEl = document.createElement("span");
        iconSpanEl.className = "s_google_map_suggestion_icon s_google_map_suggestion_icon_marker";
        itemEl.appendChild(iconSpanEl);
        const text = document.createTextNode(placePrediction.text.toString());
        itemEl.appendChild(text);
        itemEl.addEventListener("mouseenter", () => this._highlightItem(itemEl));
        itemEl.addEventListener("mousedown", () => this._selectPlace(placePrediction));
        return itemEl;
    }
    /**
     * Selects a place from the suggestions and updates the input field accordingly.
     * Fetches additional fields for the selected place.
     *
     * @private
     * @param {Object} placePrediction - The selected place prediction object.
     * @returns {Promise<void>}
     */
    async _selectPlace(placePrediction) {
        const place = placePrediction.toPlace();
        await place.fetchFields({
            fields: ["displayName", "formattedAddress", "location"],
        });
        this.inputRef.el.value =
            place.formattedAddress || place.displayName || placePrediction.text;
        this._gmapAutocompletePlace = place;
        this._clearSuggestions();
        this._onPlaceChanged();
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onPlaceChanged(ev) {
        const gmapPlace = this._gmapAutocompletePlace;
        if (gmapPlace && gmapPlace.location) {
            this._gmapPlace = gmapPlace;
            const placeLocation = this._gmapPlace.location;
            const oldValue = this._value;
            this._value = `(${placeLocation.lat()},${placeLocation.lng()})`;
            this._gmapCacheGPSToPlace[this._value] = gmapPlace;
            if (oldValue !== this._value) {
                this._onUserValueChange(ev);
            }
        }
    }
    /**
     * @override
     */
    _onInputBlur() {
        this._clearSuggestions();
    }
    async _OnInput(ev) {
        const inputValue = ev.currentTarget.value.trim();
        this._clearSuggestions();
        if (inputValue.length < 1) {
            return;
        }
        const { AutocompleteSuggestion } = await this.window.google.maps.importLibrary("places");
        const result = await AutocompleteSuggestion.fetchAutocompleteSuggestions({
            input: inputValue,
        });
        this._suggestions = result.suggestions || [];
        const suggestionBoxEl = this._getOrCreateSuggestionBox();
        this._suggestions.forEach((suggestion) => {
            const item = this._createSuggestionItem(suggestion.placePrediction);
            suggestionBoxEl.appendChild(item);
            this._suggestionItems.push(item);
        });
    }
    async _OnKeyDown(ev) {
        if (!this._suggestionItems.length) {
            return;
        }
        if (ev.key === "ArrowDown") {
            ev.preventDefault();
            this._selectedIndex = (this._selectedIndex + 1) % this._suggestionItems.length;
            this._updateHighlight();
        } else if (ev.key === "ArrowUp") {
            ev.preventDefault();
            this._selectedIndex =
                (this._selectedIndex - 1 + this._suggestionItems.length) %
                this._suggestionItems.length;
            this._updateHighlight();
        } else if (ev.key === "Enter") {
            ev.preventDefault();
            if (this._selectedIndex >= 0 && this._suggestions[this._selectedIndex]) {
                const placePrediction = this._suggestions[this._selectedIndex].placePrediction;
                await this._selectPlace(placePrediction);
            }
        }
    }
}
