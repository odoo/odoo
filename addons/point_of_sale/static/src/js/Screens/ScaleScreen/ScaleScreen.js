/** @odoo-module */

import { LegacyComponent } from "@web/legacy/legacy_component";
import { round_precision as round_pr } from "web.utils";
import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/pos_hook";

const { onMounted, onWillUnmount, useExternalListener, useState } = owl;

export class ScaleScreen extends LegacyComponent {
    static template = "ScaleScreen";

    /**
     * @param {Object} props
     * @param {Object} props.product The product to weight.
     */
    setup() {
        super.setup();
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
        this.env.proxy_queue.clear();
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
        this.env.proxy_queue.schedule(this._setWeight.bind(this), {
            duration: 500,
            repeat: true,
        });
    }
    async _setWeight() {
        const reading = await this.env.proxy.scale_read();
        this.state.weight = reading.weight;
    }
    get _activePricelist() {
        const current_order = this.env.pos.get_order();
        let current_pricelist = this.env.pos.default_pricelist;
        if (current_order) {
            current_pricelist = current_order.pricelist;
        }
        return current_pricelist;
    }
    get productWeightString() {
        const defaultstr = (this.state.weight || 0).toFixed(3) + " Kg";
        if (!this.props.product || !this.env.pos) {
            return defaultstr;
        }
        const unit_id = this.props.product.uom_id;
        if (!unit_id) {
            return defaultstr;
        }
        const unit = this.env.pos.units_by_id[unit_id[0]];
        const weight = round_pr(this.state.weight || 0, unit.rounding);
        let weightstr = weight.toFixed(Math.ceil(Math.log(1.0 / unit.rounding) / Math.log(10)));
        weightstr += " " + unit.name;
        return weightstr;
    }
    get computedPriceString() {
        return this.env.pos.format_currency(this.productPrice * this.state.weight);
    }
    get productPrice() {
        const product = this.props.product;
        return (product ? product.get_price(this._activePricelist, this.state.weight) : 0) || 0;
    }
    get productName() {
        return (
            (this.props.product ? this.props.product.display_name : undefined) || "Unnamed Product"
        );
    }
    get productUom() {
        return this.props.product
            ? this.env.pos.units_by_id[this.props.product.uom_id[0]].name
            : "";
    }
}

registry.category("pos_screens").add("ScaleScreen", ScaleScreen);
