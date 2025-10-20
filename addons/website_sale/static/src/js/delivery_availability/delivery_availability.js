import { Component, onWillDestroy, useState } from '@odoo/owl';
import { registry } from '@web/core/registry';


export class DeliveryAvailability extends Component {
    static template = 'delivery.availability';
    static props = {
        active: {type: Boolean, optional: true},
        deliveryStockData: { type: Object, optional: true},
    }
    static defaultProps = {
        active: true,
    }
    setup() {
        super.setup();
        this.state = useState(this._getState());
        const updateState = this._updateStateWithCombinationInfo.bind(this);
        this.env.bus.addEventListener('updateCombinationInfo', res => updateState(res.detail));
        onWillDestroy(() => this.env.bus.removeEventListener('updateCombinationInfo', updateState));
    }

    _getState() {
        return {
            deliveryStockData: this.props.deliveryStockData,
            active: this.props.active,
        };
    }

    /**
     * Update the state with the product combination info.
     *
     * @private
     * @param {Object} combinationInfo - The information on the current product variant.
     * @return {void}
     */
    _updateStateWithCombinationInfo (combinationInfo) {
        this.state.deliveryStockData = combinationInfo.delivery_stock_data;
        this.state.active = combinationInfo.is_combination_possible;
    }
}

registry.category('public_components').add(
    'delivery.availability', DeliveryAvailability
);
