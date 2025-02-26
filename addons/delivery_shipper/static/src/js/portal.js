/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc, RPCError } from '@web/core/network/rpc';

publicWidget.registry.portalDetails = publicWidget.Widget.extend({
    selector: '.o_portal_details',
    events: {
        'change select[name="country_id"]': '_onCountryChange',
        'change select[name="state_id"]': '_onStateChange',
        'change select[name="city_id"]': '_onCityChange',
        'change select[name="district_id"]': '_onDistrictChange',
    },

    init() {
        this._super(...arguments);
    },

    /**
     * @override
     */
    start: function () {
        const def = this._super.apply(this, arguments);

        this.$state = this.$('select[name="state_id"]');
        this.$city = this.$('select[name="city_id"]');
        this.$district = this.$('select[name="district_id"]');
        this.$area = this.$('select[name="area_id"]');

        this.$stateOptions = this.$state.find('option:not(:first)');
        this.$cityOptions = this.$city.find('option:not(:first)');
        this.$districtOptions = this.$district.find('option:not(:first)');
        this.$areaOptions = this.$area.find('option:not(:first)');

        this._adaptAddressForm();
        this._adaptCityForm();
        this._adaptDistrictForm();
        this._adaptAreaForm();

        return def;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Filters the states dropdown based on the selected country.
     * @private
     */
    _adaptAddressForm: function () {
        const $country = this.$('select[name="country_id"]');
        const countryID = $country.val() || 0;

        this.$stateOptions.detach(); // Remove all state options
        const $displayedState = this.$stateOptions.filter(`[data-country_id="${countryID}"]`);
        $displayedState.appendTo(this.$state).show();

        const hasStates = $displayedState.length > 0;
        this.$state.parent().toggle(hasStates);

        if (!hasStates) {
            this.$state.val('');
            this.$city.val('');
            this.$district.val('');
            this.$area.val('');
            this.$city.parent().hide();
            this.$district.parent().hide();
            this.$area.parent().hide();
        } else {
            this._adaptCityForm(); // Update city options based on new state
        }
    },

    /**
     * Filters the cities dropdown based on the selected state.
     * @private
     */
    _adaptCityForm: function () {
        const stateID = this.$state.val() || 0;

        this.$cityOptions.detach(); // Remove all city options
        const $displayedCity = this.$cityOptions.filter(`[data-state_id="${stateID}"]`);
        $displayedCity.appendTo(this.$city).show();

        const hasCities = $displayedCity.length > 0;
        this.$city.parent().toggle(hasCities);

        if (!hasCities) {
            this.$city.val('');
            this.$district.val('');
            this.$area.val('');
            this.$district.parent().hide();
            this.$area.parent().hide();
        } else {
            this._adaptDistrictForm(); // Update districts based on new city
        }
    },

    /**
     * Filters the districts dropdown based on the selected city.
     * @private
     */
    _adaptDistrictForm: function () {
        const cityID = this.$city.val() || 0;

        this.$districtOptions.detach(); // Remove all district options
        const $displayedDistrict = this.$districtOptions.filter(`[data-city_id="${cityID}"]`);
        $displayedDistrict.appendTo(this.$district).show();

        const hasDistricts = $displayedDistrict.length > 0;
        this.$district.parent().toggle(hasDistricts);

        if (!hasDistricts) {
            this.$district.val('');
            this.$area.val('');
            this.$area.parent().hide();
        } else {
            this._adaptAreaForm(); // Update areas based on new district
        }
    },

    /**
     * Filters the areas dropdown based on the selected district.
     * @private
     */
    async _adaptAreaForm() {
        const districtID = this.$district.val() || 0;
        if (!districtID) {
            this.$area.empty().parent().hide();
            return;
        }
        this.$area.empty().append($('<option>', { text: 'Loading...', disabled: true }));
        const areaOptions = await rpc("/get_areas", {
            district_id: districtID,
        });
        this.$area.empty();
        if (areaOptions.length) {
            areaOptions.forEach((area) => {
                this.$area.append($('<option>', { value: area.id, text: area.name }));
            });
            this.$area.parent().show();
        } else {
            this.$area.parent().hide();
        }
    },
    

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handles country change event and updates states, cities, districts, and areas.
     * @private
     */
    _onCountryChange: function () {
        this._adaptAddressForm();
    },

    /**
     * Handles state change event and updates cities, districts, and areas.
     * @private
     */
    _onStateChange: function () {
        this._adaptCityForm();
    },

    /**
     * Handles city change event and updates districts and areas.
     * @private
     */
    _onCityChange: function () {
        this._adaptDistrictForm();
    },

    /**
     * Handles district change event and updates areas.
     * @private
     */
    _onDistrictChange: function () {
        this._adaptAreaForm();
    },
});
