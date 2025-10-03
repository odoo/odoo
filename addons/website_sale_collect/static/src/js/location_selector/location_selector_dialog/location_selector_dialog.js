import {
    onWillStart,
    useEffect,
    useState,
} from '@odoo/owl';
import { patch } from '@web/core/utils/patch';
import { rpc } from '@web/core/network/rpc';
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
        countryCode: { type: String, optional: true},
        carrierId: Number,
        carrierType: String,
    },
});

patch(LocationSelectorDialog.prototype, {
    setup() {
        super.setup();
        if (this.isClickAndCollect) {
            this.state = useState({
                ...this.state,
                countries: [],
                savedZipCodes: {},
                selectedCountry: {},
            });
            onWillStart(async () => {
                this.state.countries = await this._getCountries();
                if (this.state.countries) {
                    if (this.props.countryCode) {
                        this.state.selectedCountry = this.state.countries.find(
                            (country) => country.value.code == this.props.countryCode
                        ).value;
                    }
                    else {
                        this.state.selectedCountry = this.state.countries[0].value;
                    }
                }
            });

            // Save zipcode to current country.
            useEffect(
                (zipCode) => {
                    this.state.savedZipCodes[this.state.selectedCountry.code] = zipCode;
                },
                () => [this.state.zipCode]
            );
        }
    },

    /**
     * Check if delivery type is click & collect
     *
     */
    get isClickAndCollect() {
        return this.props.carrierType == 'in_store';
    },

    _getLocationsParams() {
        let params = super._getLocationsParams(...arguments);
        if (this.props.isProductPage) {
            params.product_id = this.props.productId;
        }
        if (this.isClickAndCollect){
            params.country_code = this.state.selectedCountry.code
        }
        return params;
    },

    /**
     * Override
     * Check if country was changed for click and collect in checkout page.
     *
     * @return {Boolean} Whether we need to show tax recomputation warning.
     */
    get taxRecomputationWarning() {
        if (
            !this.props.isProductPage &&
            this.isClickAndCollect &&
            this.props.countryCode !== '' &&
            this.props.countryCode !== this.state.selectedCountry.code
        )
            return _t("This address may require to recompute taxes.");
        return ""
    },

    /**
     * Set the selectedCountry in the state, and save the zipcode to be displayed,
     * if a previously selected country is reselected.
     *
     * @param {String} country_code - The selected country code.
     *
     * @returns {void}
     */
    setSelectedCountry(value) {
        this.state.selectedCountry = value;
        this.state.zipCode = this.state.savedZipCodes[value.code];
        this._updateLocations();
    },

    /**
     * Fetch the available countries for the delivery method.
     *
     * @private
     * @return {Object} The result values.
     */
    async _getCountries() {
        return rpc('/shop/get_click_and_collect_countries',{
            carrier_id: this.props.carrierId,
        });
    },

    /**
     * Override
     * Check if list view is needed if there's  multiple countries.
     *
     * @return {Boolean} Whether we need to show list view.
     */
    get showListView() {
        return super.showListView || this.state.countries.length > 1;
    },
});
