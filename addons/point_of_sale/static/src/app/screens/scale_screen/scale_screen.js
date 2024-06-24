import { roundPrecision as round_pr } from "@web/core/utils/numbers";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class ScaleScreen extends Component {
    static template = "point_of_sale.ScaleScreen";
    static components = { Dialog };
    static props = {
        getPayload: Function,
        product: Object,
        close: Function,
    };
    setup() {
        this.pos = usePos();
        this.hardwareProxy = useService("hardware_proxy");
        this.state = useState({ weight: 0, tare: 0, tareLoading: false });
        this.pricePerUom = this.props.product.get_price(this._activePricelist, 1);
        onMounted(this.onMounted);
        onWillUnmount(this.onWillUnmount);
    }
    onMounted() {
        // start the scale reading
        this._readScale();
    }
    onWillUnmount() {
        // stop the scale reading
        this.shouldRead = false;
    }
    confirm() {
        this.props.getPayload(this.netWeight);
        this.props.close();
    }
    _readScale() {
        this.shouldRead = true;
        this._setWeight();
    }
    async _setWeight() {
        if (!this.shouldRead) {
            return;
        }
        this.state.weight = await this.hardwareProxy.readScale();
        setTimeout(() => this._setWeight(), 500);
    }
    get netWeight() {
        const weight = round_pr(this.state.weight || 0, this.productUnit.rounding);
        const weightRound = weight.toFixed(
            Math.ceil(Math.log(1.0 / this.productUnit.rounding) / Math.log(10))
        );
        return weightRound - parseFloat(this.state.tare);
    }
    get _activePricelist() {
        const current_order = this.pos.get_order();
        let current_pricelist = this.pos.config.pricelist_id;
        if (current_order) {
            current_pricelist = current_order.pricelist_id;
        }
        return current_pricelist;
    }
    get productWeightString() {
        const defaultstr = (this.state.weight || 0).toFixed(3) + " Kg";
        if (!this.props.product) {
            return defaultstr;
        }
        const unit = this.productUnit;
        if (!unit) {
            return defaultstr;
        }
        const weight = round_pr(this.state.weight || 0, unit.rounding);
        let weightstr = weight.toFixed(Math.ceil(Math.log(1.0 / unit.rounding) / Math.log(10)));
        weightstr += " " + unit.name;
        return weightstr;
    }
    get productUnit() {
        const unit = this.props.product.uom_id;
        return unit;
    }
    get computedPriceString() {
        return this.env.utils.formatCurrency(this.netWeight * this.pricePerUom);
    }
    get productPrice() {
        const product = this.props.product;
        return (product ? product.get_price(this._activePricelist, this.state.weight) : 0) || 0;
    }
    get productUom() {
        return this.props.product?.uom_id?.name;
    }
    async handleTareButtonClick() {
        this.state.tareLoading = true;
        const tareWeight = await this.hardwareProxy.readScale();
        this.state.tare = tareWeight;
        setTimeout(() => {
            this.state.tareLoading = false;
        }, 3000);
    }
}
