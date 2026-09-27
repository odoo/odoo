import { Component, useProps, proxy, t } from '@odoo/owl';
import { deserializeDate, toLocaleDateString } from '@web/core/l10n/dates';
import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
import { useBus, useService } from '@web/core/utils/hooks';

import {
    LocationSelectorDialog
} from '@website_sale_stock/js/location_selector/location_selector_dialog/location_selector_dialog';

export class ClickAndCollectAvailability extends Component {
    static template = 'website_sale_collect.ClickAndCollectAvailability';
    props = useProps({
        productId: t.number(),
        active: t.boolean().optional(true),
        zipCode: t.string().optional(),
        selectedLocationData: t.object().optional(),
        inStoreData: t.object().optional(),
        deliveryData: t.object().optional(),
        isInStoreSelected: t.boolean().optional(false),
        showSelectStoreButton: t.boolean().optional(),
        countryCode: t.string().optional(),
    });
    setup() {
        super.setup();
        this.dialog = useService('dialog');
        this.state = proxy({
            productId: this.props.productId,
            selectedLocationData: this.props.selectedLocationData,
            inStoreData: this.props.inStoreData,
            deliveryData: this.props.deliveryData,
            isInStoreSelected: this.props.isInStoreSelected,
            active: this.props.active,
        });
        useBus(
            this.env.bus,
            'updateCombinationInfo',
            (ev) => this._updateStateWithCombinationInfo(ev.detail),
        );
    }

    /**
     * Update the state with the product combination info.
     *
     * @private
     * @param {Object} combinationInfo - The information on the current product variant.
     * @return {void}
     */
    _updateStateWithCombinationInfo(combinationInfo) {
        this.state.productId = combinationInfo.product_id;
        this.state.inStoreData = combinationInfo.in_store_data;
        this.state.deliveryData = combinationInfo.delivery_data;
        this.state.active = combinationInfo.is_combination_possible;
        this.state.uomId = combinationInfo.uom_id;
        this.state.hasOutOfStockMessage = combinationInfo.has_out_of_stock_message;
        this.state.outOfStockMessage = combinationInfo.out_of_stock_message;
    }

    /**
     * Return the label indicating from when the in-store pickup is available, based on the
     * delivery method's estimated delivery, or else on the selected store's opening hours.
     *
     * @return {String} The availability label, or an empty string if it cannot be determined.
     */
    get availabilityFromLabel() {
        if (this.state.selectedLocationData.next_open_date) {
            return _t(
                "from %(date)s",
                {
                    date: toLocaleDateString(
                        deserializeDate(this.state.selectedLocationData.next_open_date)
                    ),
                },
            );
        }
        return "";
    }

    /**
     * Return the label indicating from when the standard delivery is available, based on the
     * delivery method's estimated delivery.
     *
     * @return {String} The availability label, or an empty string if it cannot be determined.
     */
    get deliveryAvailabilityFromLabel() {
        if (this.state.deliveryData.estimated_date) {
            return _t(
                'from %(date)s',
                {
                    date: toLocaleDateString(
                        deserializeDate(this.state.deliveryData.estimated_date)
                    ),
                },
            );
        }
        return '';
    }

    /**
     * Configure and open the location selector.
     *
     * @return {void}
     */
    async openLocationSelector() {
        if (!this.state.active) { // Combination is not possible.
            return; // Do not open the location selector.
        }
        this.dialog.add(LocationSelectorDialog, this._getLocationSelectorDialogProps());
    }

    /**
     * Select the in-store pickup delivery mode.
     *
     * If the pickup mode is already selected, clicking again opens the location selector
     *
     * @return {void}
     */
    async selectPickup() {
        if (this.state.isInStoreSelected || !this.state.selectedLocationData.id) {
            await this.openLocationSelector();
            return;
        }
        await this._saveSelectedLocation(this.state.selectedLocationData);
    }

    /**
     * Select the standard shipping delivery mode and set it on the current order.
     *
     * @return {void}
     */
    async selectStandardDelivery() {
        this.state.isInStoreSelected = false;
        await rpc("/shop/set_delivery_method", { dm_id: this.state.deliveryData.dm_id });
    }

    /**
     * Build the props to pass to the LocationSelectorDialog.
     *
     * @return {Object} Props for LocationSelectorDialog.
     */
    _getLocationSelectorDialogProps() {
        const { zip_code, country_code, id } = this.state.selectedLocationData;
        return {
            isProductPage: true,
            isFrontend: true,
            productId: this.state.productId,
            uomId: this.state.uomId,
            zipCode: zip_code || this.props.zipCode,
            selectedLocationId: String(id),
            countryCode: country_code || this.props.countryCode,
            deliveryMethodId: this.state.inStoreData.dm_id,
            deliveryMethodType: this.state.inStoreData.dm_type,
            save: this._saveSelectedLocation.bind(this),
        }
    }

    /**
     * Saves the selected pickup location and updates the current order.
     *
     * @param {Object} location - The location selected by the user.
     */
    async _saveSelectedLocation(location) {
        this.state.isInStoreSelected = true;
        this.state.selectedLocationData = location;
        this.state.inStoreData.stock_data =
            location.additional_data?.in_store_stock_data ?? this.state.inStoreData.stock_data;
        const jsonLocation = JSON.stringify(location);
        // Set the in-store delivery method and the selected pickup location on the order.
        await rpc(
            '/shop/set_click_and_collect_location', { pickup_location_data: jsonLocation }
        );
    }

}

registry.category('public_components').add(
    'website_sale_collect.ClickAndCollectAvailability', ClickAndCollectAvailability
);
