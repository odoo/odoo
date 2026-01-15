import { Component, onWillDestroy, useState } from '@odoo/owl';
import { rpc } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';

import {
    LocationSelectorDialog
} from '@delivery/js/location_selector/location_selector_dialog/location_selector_dialog';

export class ClickAndCollectAvailability extends Component {
    static template = 'website_sale_collect.ClickAndCollectAvailability';
    static props = {
        productId: Number,
        active: {type: Boolean, optional: true},
        zipCode: { type: String, optional: true },
        selectedLocationData: { type: Object, optional: true },
        inStoreStockData: { type: Object, optional: true },
        deliveryStockData: { type: Object, optional: true},
        showSelectStoreButton: { type: Boolean, optional: true },
    }
    static defaultProps = {
        active: true,
    }
    setup() {
        super.setup();
        this.dialog = useService('dialog');
        this.state = useState({
            productId: this.props.productId,
            selectedLocationData: this.props.selectedLocationData,
            inStoreStockData: this.props.inStoreStockData,
            deliveryStockData: this.props.deliveryStockData,
            active: this.props.active,
        });
        const updateState = this._updateStateWithCombinationInfo.bind(this);
        this.env.bus.addEventListener('updateCombinationInfo', res => updateState(res.detail));
        onWillDestroy(() => this.env.bus.removeEventListener('updateCombinationInfo', updateState));
    }

    /**
     * Update the state with the product combination info.
     *
     * @private
     * @param {Object} combinationInfo - The information on the current product variant.
     * @return {void}
     */
    _updateStateWithCombinationInfo (combinationInfo) {
        this.state.productId = combinationInfo.product_id;
        this.state.inStoreStockData = combinationInfo.in_store_stock_data;
        this.state.deliveryStockData = combinationInfo.delivery_stock_data;
        this.state.active = combinationInfo.is_combination_possible;
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

}

registry.category('public_components').add(
    'website_sale_collect.ClickAndCollectAvailability', ClickAndCollectAvailability
);
