import { LocationList } from '@delivery/js/location_selector/location_list/location_list';
import { MapContainer } from '@delivery/js/location_selector/map_container/map_container';
import {
    Component,
    onMounted,
    onWillStart,
    onWillUnmount,
    useEffect,
    useState,
} from '@odoo/owl';
import { browser } from '@web/core/browser/browser';
import { Dialog } from '@web/core/dialog/dialog';
import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import { SelectMenu } from '@web/core/select_menu/select_menu';
import { useDebounced } from '@web/core/utils/timing';

export class LocationSelectorDialog extends Component {
    static components = { Dialog, LocationList, MapContainer, SelectMenu };
    static template = 'delivery.locationSelector.dialog';
    static props = {
        zipCode: { type: String, optional: true},
        countryCode: { type: String, optional: true},
        selectedLocationId: { type: String, optional: true},
        carrierId: Number,
        save: Function,
        close: Function, // This is the close from the env of the Dialog Component
    };
    static defaultProps = {
        selectedLocationId: false,
    };

    setup() {
        this.state = useState({
            locations: [],
            countries: [],
            savedZipCodes: {},
            selectedCountry: {},
            error: false,
            viewMode: 'list',
            zipCode: this.props.zipCode,
            // Some APIs like FedEx use strings to identify locations.
            selectedLocationId: String(this.props.selectedLocationId),
            isSmall: this.env.isSmall,
        });

        this.getLocationUrl = '/delivery/get_pickup_locations';

        this.debouncedOnResize = useDebounced(this.updateSize, 300);
        this.debouncedSearchButton = useDebounced(() => {
            this.state.locations = [];
            this._updateLocations();
        }, 10);

        onMounted(() => {
            browser.addEventListener('resize', this.debouncedOnResize);
            this.updateSize();
        });
        onWillUnmount(() => browser.removeEventListener('resize', this.debouncedOnResize));

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

        // Fetch new locations when the zip code is updated.
        useEffect(
            (zipCode) => {
                this._updateLocations();
                this.state.savedZipCodes[this.state.selectedCountry.code] = zipCode;
                return () => {
                    this.state.locations = [];
                };
            },
            () => [this.state.zipCode]
        );
    }

    //--------------------------------------------------------------------------
    // Data Exchanges
    //--------------------------------------------------------------------------

    /**
     * Fetch the closest pickup locations based on the zip code & country.
     *
     * @private
     * @return {Object} The result values.
     */
    async _getLocations() {
        return rpc(this.getLocationUrl, this._getLocationsParams());
    }

    /**
     * Fetch the information needed to get the closest pickup locations
     *
     * @private
     * @return {Object} The result values.
     */
    _getLocationsParams() {
        return {
            zip_code: this.state.zipCode,
            country_code: this.state.selectedCountry.code,
        };
    }

    /**
     * Fetch the available countries for the delivery method.
     *
     * @private
     * @return {Object} The result values.
     */
    async _getCountries() {
        return rpc('/delivery/get_delivery_method_countries',{
            carrier_id: this.props.carrierId,
        });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Get the locations based on the zip code.
     *
     * Select the first location available if no location is currently selected or if the currently
     * selected location is not on the list anymore.
     *
     * @private
     * @return {void}
     */
    async _updateLocations() {
        this.state.error = false;
        if (this.state.zipCode){
            const { pickup_locations, error } = await this._getLocations();

            if (error) {
                this.state.error = error;
                console.error(error);
            } else {
                this.state.locations = pickup_locations;
                if (!this.state.locations.find(l => String(l.id) === this.state.selectedLocationId)) {
                    this.state.selectedLocationId = this.state.locations[0]
                        ? String(this.state.locations[0].id)
                        : false;
                }
            }
        }
        else {
            this.state.locations = []
        }

    }

    /**
     * Check if list view is needed to navigating between warehouses, if there's multiple warehouses
     * or multiple countries.
     *
     * @return {Boolean} Whether we need to show list view.
     */
    get showListView() {
        return this.state.locations.length !== 1 || this.state.countries.length > 1;
    }

    /**
     * Check if country was changed.
     *
     * @return {Boolean} Whether we need to show tax recomputation warning.
     */
    get showTaxRecomputationWarning() {
        return (
            this.props.countryCode !== '' &&
            this.props.countryCode !== this.state.selectedCountry.code
        );
    }

    /**
     * Find the selected location based on its id.
     *
     * @return {Object} The selected location.
     */
    get selectedLocation() {
        return this.state.locations.find(l => String(l.id) === this.state.selectedLocationId);
    }

    /**
     * Set the selectedLocationId in the state.
     *
     * @param {String} locationId
     * @return {void}
     */
    setSelectedLocation(locationId) {
        this.state.selectedLocationId = String(locationId);
    }

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
    }

    /**
     * Confirm the current selected location.
     *
     * @return {void}
     */
    async validateSelection() {
        if (!this.state.selectedLocationId) return;
        const selectedLocation = this.state.locations.find(
            l => String(l.id) === this.state.selectedLocationId
        );
        await this.props.save(selectedLocation);
        this.props.close();
    }

    //--------------------------------------------------------------------------
    // User Interface
    //--------------------------------------------------------------------------

    /**
     * Determines the component to show in mobile view based on the current state.
     *
     * Returns the MapContainer component if `viewMode` is strictly equal to `map`, else return the
     * List component.
     *
     * @return {Component} The component to show in mobile view.
     */
    get mobileComponent() {
        if (this.state.viewMode === 'map') return MapContainer;
        return LocationList;
    }

    get title() {
        if (this.state.locations.length === 1) {
            return _t("Pickup Location")
        }
        return _t("Choose a pick-up point");
    }

    get validationButtonLabel() {
        return _t("Choose this location");
    }

    get postalCodePlaceholder() {
        return _t("Your postal code");
    }

    get listViewButtonLabel() {
        return _t("List view");
    }

    get mapViewButtonLabel() {
        return _t("Map view");
    }

    get errorMessage() {
        return _t("No result");
    }

    get missingZipcodeMessage() {
        return _t("Please enter your postal code to search for locations in your area");
    }

    get loadingMessage() {
        return _t("Loading...");
    }

    get taxRecomputationWarning() {
        return _t("This address may require to recompute taxes.");
    }

    /**
     *
     * @return {void}
     */
    updateSize() {
        this.state.isSmall = this.env.isSmall;
    }
}
