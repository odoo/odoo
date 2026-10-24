import { Dialog } from '@web/core/dialog/dialog';
import { t, useProps } from '@odoo/owl';
import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import {
    LocationSelectorComponent
} from '@website/components/location_selector/location_selector_component/location_selector_component';

// Props specific to the location selector dialog (never used by
// `LocationSelectorComponent` in `website`).
export const locationSelectorDialogProps = {
    isFrontend: t.boolean().optional(),
    deliveryMethodId: t.number().optional(),
    countryId: t.number().optional(),
    selectedLocationId: t.string().optional(),
    save: t.function(),
    close: t.function(), // This is the close from the env of the Dialog Component
};

export class LocationSelectorDialog extends LocationSelectorComponent {
    static components = { ...LocationSelectorComponent.components, Dialog };
    static template = 'website_sale_stock.locationSelector.dialog';
    dialogProps = useProps(locationSelectorDialogProps);

    setup() {
        super.setup();
        this.getLocationUrl = '/website_sale_stock/get_pickup_locations';
        // Some APIs like FedEx use strings to identify locations.
        this.state.selectedLocationId = String(this.dialogProps.selectedLocationId);
    }

    // The following getters override `LocationSelectorComponent` defaults
    get showSidebar() {
        return true;
    }

    get showSearchbar() {
        return true;
    }

    get mapZoom() {
        return "13";
    }

    get sidebarLocation() {
        return "left";
    }

    get showDetailsTooltip() {
        return false;
    }

    get showDetailsTextArea() {
        return true;
    }

    get showIndexes() {
        return true;
    }

    get showPinIndicator() {
        return true;
    }

    get showLocationNameOnMarkerHover() {
        return false;
    }

    get pressControlToZoom() {
        return false;
    }

    get validateSelection() {
        return this._validateSelection.bind(this);
    }

    /**
     * Fetch the information needed to get the closest pickup locations
     *
     * @private
     * @return {Object} The result values.
     */
    _getLocationsParams(searchQuery) {
        const params = { zip_code: searchQuery };
        if (!this.dialogProps.isFrontend) { // The delivery method is fetched from the order for frontend
            params.delivery_method_id = this.dialogProps.deliveryMethodId;
            params.country_id = this.dialogProps.countryId;
        }
        return params;
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
     * Overrides `LocationSelectorComponent`'s local, static search to fetch
     * the locations from the server instead.
     *
     * @return {void}
     */
    async updateLocations(searchQuery) {
        this.state.error = false;
        const { pickup_locations, error } = await rpc(
            this.getLocationUrl, this._getLocationsParams(searchQuery)
        );
        if (error) {
            this.state.error = error;
            console.error(error);
            return;
        }
        this._updateLocations(pickup_locations);
        this._selectLocation();
    }

    _updateLocations(locations) {
        this.state.locations = locations;
    }

    _selectLocation() {
        if (!this.locations.some((l) => String(l.id) === this.state.selectedLocationId)) {
            this.setSelectedLocation(this.locations[0] ? this.locations[0].id : false);
        }
    }

    /**
     * Confirm the current selected location.
     *
     * @return {void}
     */
    async _validateSelection() {
        if (!this.state.selectedLocationId) {
            return;
        }
        const selectedLocation = this.locations.find(
            (l) => String(l.id) === this.state.selectedLocationId
        );
        await this.dialogProps.save(selectedLocation);
        this.dialogProps.close();
    }

    //--------------------------------------------------------------------------
    // User Interface
    //--------------------------------------------------------------------------

    get title() {
        if (this.locations.length === 1) {
            return _t("Pickup Location")
        }
        return _t("Choose a pick-up point");
    }
}
