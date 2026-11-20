/** @odoo-module */

import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, onMounted, onWillUnmount, useExternalListener, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ScaleScreen extends Component {
    static template = "point_of_sale.ScaleScreen";

    /**
     * @param {Object} props
     * @param {Object} props.product The product to weight.
     */
    setup() {
        this.pos = usePos();
        this.hardwareProxy = useService("hardware_proxy");
        useExternalListener(document, "keyup", this._onHotkeys);
        this.state = useState({ weight: 0 });
        onMounted(this.onMounted);
        onWillUnmount(this.onWillUnmount);
        this.pos = usePos();
    }
    onMounted() {
        // start the scale reading
        this._readScale();
    }
    onWillUnmount() {
        // stop the scale reading
        this.shouldRead = false;
    }
    back() {
        this.props.resolve({ confirmed: false, payload: null });
        this.pos.closeTempScreen();
    }
    confirm() {
        this.props.resolve({
            confirmed: true,
            payload: { weight: this.state.weight },
        });
        this.pos.closeTempScreen();
    }
    _onHotkeys(event) {
        if (event.key === "Escape") {
            this.back();
        } else if (event.key === "Enter") {
            this.confirm();
        }
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
    get _activePricelist() {
        const current_order = this.pos.get_order();
        let current_pricelist = this.pos.default_pricelist;
        if (current_order) {
            current_pricelist = current_order.pricelist;
        }
        return current_pricelist;
    }
    get productWeightString() {
        return (this.state.weight || 0).toFixed(3);
    }
    get computedPriceString() {
        return this.env.utils.formatCurrency(this.productPrice * this.state.weight);
    }
    get productPrice() {
        const product = this.props.product;
        return (product ? product.get_price(this._activePricelist, this.state.weight) : 0) || 0;
    }
    get productName() {
        return this.props.product?.display_name || "Unnamed Product";
    }
    get productUom() {
        if (!this.props.product) {
            return "";
        }
        return this.pos.units_by_id[this.props.product.uom_id[0]].name;
    }
}

registry.category("pos_screens").add("ScaleScreen", ScaleScreen);
