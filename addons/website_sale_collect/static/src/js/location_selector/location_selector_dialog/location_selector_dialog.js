import { useState } from "@web/owl2/utils";
import { patch } from '@web/core/utils/patch';
import { SelectMenu } from '@web/core/select_menu/select_menu';
import { _t } from '@web/core/l10n/translation';

import {
    LocationSelectorDialog
} from '@delivery/js/location_selector/location_selector_dialog/location_selector_dialog';

patch(LocationSelectorDialog, {
    components: {
        ...LocationSelectorDialog.components,
        SelectMenu,
    },
    props: {
        ...LocationSelectorDialog.props,
        productId: { type: Number, optional: true },
        isProductPage: { type: Boolean, optional: true },
        uomId: { type: Number, optional: true },
        countryCode: { type: String, optional: true},
        deliveryMethodId: Number,
        deliveryMethodType: String,
    },
});

patch(LocationSelectorDialog.prototype, {
    setup() {
        super.setup();
        if (this.isClickAndCollect) {
            this.state = useState({
                ...this.state,
                countries: [],
                selectedCountryData: {},
            });
        }
    },


    /**
     * Returns whether the list view should be hidden.
     * The list view is hidden when there is only one location available for Click & Collect.
     *
     * @return {Boolean} Whether we need to show list view.
     */
    get hideListView() {
        return this.isClickAndCollect && this.state.locations.length === 1;
    },

    /**
     * Check if the location selector is on the Click & Collect delivery method.
     *
     */
    get isClickAndCollect() {
        return this.props.deliveryMethodType === 'in_store';
    },

    /**
     * @override of `delivery` to add the request params specific for Click & Collect.
     *
     * @returns {Object} - The request params for the location selector's endpoint.
     * @private
     */
    _getLocationsParams() {
        let params = super._getLocationsParams(...arguments);
        if (this.props.isProductPage) {
            params.product_id = this.props.productId;
            params.uom_id = this.props.uomId;
        }
        if (this.isClickAndCollect) {
            params.country_code = this.state.selectedCountryData.code ?? this.props.countryCode;
        }
        return params;
    },

    /**
     * Returns the warning if the country was changed for Click & Collect in checkout page.
     *
     * @return {String} Tax recomputation warning if a country was changed, empty string otherwise.
     */
    get taxRecomputationWarning() {
        if (
            this.isClickAndCollect &&
            !this.props.isProductPage &&
            this.props.countryCode !== this.state.selectedCountryData.code
        )
            return _t("This address may require to recompute taxes.");
        return "";
    },

    /**
     * Save the selectedCountry in the state.
     *
     * @param {Object} countryData - The data (image_url, code, name) of the selected country.
     *
     * @returns {void}
     */
    setSelectedCountry(countryData) {
        this.state.selectedCountryData = countryData;
        this._selectLocation();  // Reset the location if the country was changed.
    },

    /**
     * Filter locations by selected country for Click & Collect.
     *
     * @override method from `@delivery/static/src/js/location_selector_dialog`
     */
    get locations() {
        if (this.isClickAndCollect && this.state.selectedCountryData.code) {
            return this.state.locations.filter(
                (l) => l.country_code === this.state.selectedCountryData.code
            );
        }
        return super.locations;
    },

    /**
     * Set the countries on the location selector and set the first one as the selected country if
     * no country was selected previously for Click & Collect in checkout page.
     *
     * @override method from `@delivery/static/src/js/location_selector_dialog`
     */
    _updateLocations(locations) {
        if (!this.isClickAndCollect) {
            return super._updateLocations(...arguments);
        }
        this.state.locations = locations.pickup_location_data;
        this.state.countries = locations.country_data;
        if (this.state.countries.length && !this.state.selectedCountryData.code) {
            this.state.selectedCountryData = this.props.countryCode ? this.state.countries.find(
                (country) => country.value.code === this.props.countryCode
            ).value : this.state.countries[0].value;
        }
    },
});
