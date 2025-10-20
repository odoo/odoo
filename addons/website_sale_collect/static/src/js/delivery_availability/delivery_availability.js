import {
    LocationSelectorDialog
} from '@delivery/js/location_selector/location_selector_dialog/location_selector_dialog';
import { rpc } from '@web/core/network/rpc';
import { useService } from '@web/core/utils/hooks';
import { patch } from '@web/core/utils/patch';
import { DeliveryAvailability } from '@website_sale/js/delivery_availability/click_and_collect_availability/delivery_availability';

patch(DeliveryAvailability, {
    props: {
        ...DeliveryAvailability.props,
        productId: Number,
        zipCode: { type: String, optional: true },
        selectedLocationData: { type: Object, optional: true },
        inStoreStockData: { type: Object, optional: true },
        showSelectStoreButton: { type: Boolean, optional: true },
    },
});

patch(DeliveryAvailability.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService('dialog');
    },
    _getState() {
        return {
            ...super._getState(...arguments),
            productId: this.props.productId,
            selectedLocationData: this.props.selectedLocationData,
            inStoreStockData: this.props.inStoreStockData,
        };
    },
    /**
     * Update the state with the product combination info.
     *
     * @private
     * @param {Object} combinationInfo - The information on the current product variant.
     * @return {void}
     */
    _updateStateWithCombinationInfo (combinationInfo) {
        super._updateStateWithCombinationInfo(...arguments);
        this.state.productId = combinationInfo.product_id;
        this.state.inStoreStockData = combinationInfo.in_store_stock_data;
    },
    /**
     * Configure and open the location selector.
     *
     * @return {void}
     */
    async openLocationSelector() {
        if (!this.state.active) { // Combination is not possible.
            return; // Do not open the location selector.
        }
        const { zip_code, id } = this.state.selectedLocationData;
        this.dialog.add(LocationSelectorDialog, {
            isProductPage: true,
            isFrontend: true,
            productId: this.state.productId,
            zipCode: zip_code || this.props.zipCode,
            selectedLocationId: String(id),
            save: async location => {
                this.state.selectedLocationData = location;
                this.state.inStoreStockData = location.additional_data.in_store_stock_data;
                const jsonLocation = JSON.stringify(location);
                // Set the in-store delivery method and the selected pickup location on the order.
                await rpc(
                    '/shop/set_click_and_collect_location', { pickup_location_data: jsonLocation }
                );
            },
        });
    }
});
