import { Component, markup, onMounted, useProps, proxy, t } from '@odoo/owl';
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
        inStoreStockData: t.object().optional(),
        deliveryStockData: t.object().optional(),
        showSelectStoreButton: t.boolean().optional(),
        countryCode: t.string().optional(),
        deliveryMethodId: t.number(),
        deliveryMethodType: t.string(),
        deliveryMethodName: t.string(),
        hasOutOfStockMessage: t.boolean().optional(),
        outOfStockMessage: t.string().optional(),
    });
    setup() {
        super.setup();
        this.dialog = useService('dialog');
        this.state = proxy({
            productId: this.props.productId,
            selectedLocationData: this.props.selectedLocationData,
            inStoreStockData: this.props.inStoreStockData,
            deliveryStockData: this.props.deliveryStockData,
            active: this.props.active,
            hasOutOfStockMessage: this.props.hasOutOfStockMessage,
            outOfStockMessage: markup(this.props.outOfStockMessage || ''),
        });

        onMounted(
            () => document.querySelector('[name="click_and_collect_placeholder"]')?.remove()
        );
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
        this.state.inStoreStockData = combinationInfo.in_store_stock_data;
        this.state.deliveryStockData = combinationInfo.delivery_stock_data;
        this.state.active = combinationInfo.is_combination_possible;
        this.state.uomId = combinationInfo.uom_id;
        this.state.hasOutOfStockMessage = combinationInfo.has_out_of_stock_message;
        this.state.outOfStockMessage = combinationInfo.out_of_stock_message;
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
            deliveryMethodId: this.props.deliveryMethodId,
            deliveryMethodType: this.props.deliveryMethodType,
            save: this._saveSelectedLocation.bind(this),
        }
    }

    /**
     * Saves the selected pickup location and updates the current order.
     *
     * @param {Object} location - The location selected by the user.
     */
    async _saveSelectedLocation(location) {
        this.state.selectedLocationData = location;
        this.state.inStoreStockData = location.additional_data.in_store_stock_data;
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
