import { Component, props, proxy, t } from '@odoo/owl';
import { registry } from '@web/core/registry';
import { useBus } from '@web/core/utils/hooks';


export class DeliveryAvailability extends Component {
    static template = 'website_sale.DeliveryAvailability';

    setup() {
        super.setup();
        this.state = proxy({});
        Object.assign(this.state, props({
            uomName: t.string().optional(),
            deliveryStockData: t.object().optional(),
        }));
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
        this.state.uomName = combinationInfo.uom_name;
        this.state.deliveryStockData = combinationInfo.delivery_stock_data;
    }
}

registry.category('public_components').add(
    'website_sale.DeliveryAvailability', DeliveryAvailability
);
