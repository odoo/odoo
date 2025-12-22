import { Component, useState, onWillDestroy } from '@odoo/owl';
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
        selectedWhLocation: { type: Object, optional: true },
        inStoreStock: { type: Object, optional: true },
    }
    static defaultProps = {
        active: true,
    }
    setup() {
        super.setup();
        this.dialog = useService('dialog');
        this.state = useState({
            productId: this.props.productId,
            selectedWhLocation: this.props.selectedWhLocation,
            inStoreStock: this.props.inStoreStock,
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
        this.state.inStoreStock = combinationInfo.in_store_stock;
        this.state.active = combinationInfo.is_combination_possible;
    }

    /**
     * Configure and open the location selector.
     *
     * @return {void}
     */
    async openLocationSelector() {
        const { zip_code, id } = this.state.selectedWhLocation;
        this.dialog.add(LocationSelectorDialog, {
            isProductPage: true,
            isFrontend: true,
            productId: this.state.productId,
            zipCode: zip_code || this.props.zipCode,
            selectedLocationId: String(id),
            save: async location => {
                this.state.selectedWhLocation = location;
                this.state.inStoreStock = location.additional_data.in_store_stock;
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
