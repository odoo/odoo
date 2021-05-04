/** @odoo-module alias=point_of_sale.ScaleScreen **/

const { useState, useExternalListener } = owl.hooks;
import PosComponent from 'point_of_sale.PosComponent';
import { round_precision as round_pr } from 'web.utils';

class ScaleScreen extends PosComponent {
    /**
     * @param {Object} props
     * @param {Object} props.product The product to weight.
     */
    constructor() {
        super(...arguments);
        useExternalListener(document, 'keyup', this._onHotkeys);
        this.state = useState({ weight: 0 });
    }
    mounted() {
        // start the scale reading
        this._readScale();
    }
    willUnmount() {
        // stop the scale reading
        this.env.model.proxy_queue.clear();
    }
    back() {
        this.props.resolve([false, null]);
        this.trigger('close-temp-screen');
    }
    confirm() {
        this.props.resolve([true, { weight: this.state.weight }]);
        this.trigger('close-temp-screen');
    }
    _onHotkeys(event) {
        if (event.key === 'Escape') {
            this.back();
        } else if (event.key === 'Enter') {
            this.confirm();
        }
    }
    _readScale() {
        this.env.model.proxy_queue.schedule(this._setWeight.bind(this), {
            duration: 500,
            repeat: true,
        });
    }
    async _setWeight() {
        const reading = await this.env.model.proxy.scale_read();
        this.state.weight = reading.weight;
    }
    get _activePricelistId() {
        const activeOrder = this.env.model.getActiveOrder();
        const orderPricelistId = activeOrder.pricelist_id;
        return orderPricelistId || this.env.model.config.pricelist_id;
    }
    get productWeightString() {
        const defaultstr = (this.state.weight || 0).toFixed(3) + ' Kg';
        if (!this.props.product || !this.env.model) {
            return defaultstr;
        }
        const unit = this.env.model.getProductUnit(this.props.product.id);
        if (!unit) {
            return defaultstr;
        }
        const weight = round_pr(this.state.weight || 0, unit.rounding);
        let weightstr = weight.toFixed(Math.ceil(Math.log(1.0 / unit.rounding) / Math.log(10)));
        weightstr += ' ' + unit.name;
        return weightstr;
    }
    get computedPriceString() {
        return this.env.model.formatCurrency(this.productPrice * this.state.weight);
    }
    get productPrice() {
        if (!this.props.product) {
            return 0;
        } else {
            return this.env.model.getProductPrice(this.props.product.id, this._activePricelistId, this.state.weight);
        }
    }
    get productName() {
        return (this.props.product ? this.props.product.display_name : undefined) || 'Unnamed Product';
    }
    get productUom() {
        if (!this.props.product) return '';
        return this.env.model.getProductUnit(this.props.product.id).name;
    }
}
ScaleScreen.template = 'point_of_sale.ScaleScreen';

export default ScaleScreen;
