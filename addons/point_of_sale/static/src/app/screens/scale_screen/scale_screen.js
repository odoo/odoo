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
        productName: String,
        uomName: String,
        uomRounding: Number,
        productPrice: Number,
        close: Function,
    };
    setup() {
        this.pos = usePos();
        this.hardwareProxy = useService("hardware_proxy");
        this.state = useState({ weight: 0, tare: 0, tareLoading: false });
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
        this.pos.setScaleWeight(this.state.weight);
        setTimeout(() => this._setWeight(), 500);
    }
    get netWeight() {
        const weight = round_pr(this.state.weight || 0, this.props.uomRounding);
        const weightRound = weight.toFixed(
            Math.ceil(Math.log(1.0 / this.props.uomRounding) / Math.log(10))
        );
        return weightRound - parseFloat(this.state.tare);
    }

    get productWeightString() {
        const defaultstr = (this.state.weight || 0).toFixed(3) + " Kg";
        const uom = this.props.uomName;
        if (!uom) {
            return defaultstr;
        }
        const weight = round_pr(this.state.weight || 0, this.props.uomRounding);
        let weightstr = weight.toFixed(
            Math.ceil(Math.log(1.0 / this.props.uomRounding) / Math.log(10))
        );
        weightstr += " " + this.props.uomName;
        return weightstr;
    }
    get computedPriceString() {
        const priceString = this.env.utils.formatCurrency(this.netWeight * this.props.productPrice);
        this.pos.totalPriceOnScale = priceString;
        return priceString;
    }
    async handleTareButtonClick() {
        this.state.tareLoading = true;
        const tareWeight = await this.hardwareProxy.readScale();
        this.state.tare = tareWeight;
        this.pos.setScaleTare(this.state.tare);
        setTimeout(() => {
            this.state.tareLoading = false;
        }, 3000);
    }
    handleInputChange(ev) {
        this.pos.setScaleTare(ev.target.value);
    }
}
