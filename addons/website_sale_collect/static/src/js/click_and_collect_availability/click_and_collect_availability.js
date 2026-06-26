import { props, t } from '@odoo/owl';
import { rpc } from '@web/core/network/rpc';
import { useService } from '@web/core/utils/hooks';
import { patch } from '@web/core/utils/patch';
import { DeliveryAvailability } from '@website_sale/js/delivery_availability/delivery_availability';
import {
    LocationSelectorDialog
} from '@website_sale_stock/js/location_selector/location_selector_dialog/location_selector_dialog';

patch(DeliveryAvailability.prototype, {
    /** @override */
    setup() {
        super.setup();
        this.dialog = useService('dialog');
        Object.assign(this.state, props({
            productId: t.number(),
            active: t.boolean().optional(true),
            zipCode: t.or([t.string(), t.literal(null)]),
            selectedLocationData: t.object(),
            inStoreStockData: t.object(),
            showSelectStoreButton: t.or([t.boolean(), t.literal(null)]),
            countryCode: t.or([t.string(), t.literal(null)]),
            deliveryMethodId: t.or([t.number(), t.literal(null)]),
            deliveryMethodType: t.or([t.string(), t.literal(null)]),
            deliveryMethodName: t.or([t.string(), t.literal(null)]),
        }));
    },

    /** @override */
    _updateStateWithCombinationInfo(combinationInfo) {
        super._updateStateWithCombinationInfo(combinationInfo);
        this.state.productId = combinationInfo.product_id;
        this.state.inStoreStockData = combinationInfo.in_store_stock_data;
        this.state.active = combinationInfo.is_combination_possible;
        this.state.uomId = combinationInfo.uom_id;
    },

    /**
     * Configure and open the location selector.
     */
    async openLocationSelector() {
        if (
            !this.state.active // Combination is not possible.
            || !this.state.inStoreStockData?.in_stock
        ) {
            return; // Do not open the location selector.
        }
        this.dialog.add(LocationSelectorDialog, this.locationSelectorProps);
    },

    get locationSelectorProps() {
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
            save: this.onSaveLocation.bind(this),
        };
    },

    /**
     * Set the in-store delivery method and the selected pickup location on the order.
     *
     * @param {Object} location
     */
    async onSaveLocation(location) {
        this.state.selectedLocationData = location;
        this.state.inStoreStockData = location.additional_data.in_store_stock_data;
        const jsonLocation = JSON.stringify(location);
        await rpc('/shop/set_click_and_collect_location', { pickup_location_data: jsonLocation });
    },
});
