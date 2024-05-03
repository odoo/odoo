import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState } from "@odoo/owl";
import { usePos } from "../pos_hook";
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { floatIsZero } from "@web/core/utils/numbers";

export class ComboConfiguratorPopup extends Component {
    static template = "point_of_sale.ComboConfiguratorPopup";
    static components = { ProductCard, Dialog };
    static props = {
        product: Object,
        getPayload: Function,
        close: Function,
    };

    setup() {
        this.pos = usePos();
        this.state = useState({
            combo: Object.fromEntries(this.props.product.combo_ids.map((elem) => [elem.id, 0])),
            // configuration: id of combo_line -> ProductConfiguratorPopup payload
            configuration: {},
        });
    }

    areAllCombosSelected() {
        return Object.values(this.state.combo).every((x) => Boolean(x));
    }

    formattedComboPrice(comboLine) {
        const combo_price = comboLine.combo_price;
        if (floatIsZero(combo_price)) {
            return "";
        } else {
            const product = comboLine.product_id;
            const price = this.pos.getProductPrice(product, combo_price);
            return this.env.utils.formatCurrency(price);
        }
    }

    getSelectedComboLines() {
        return Object.values(this.state.combo)
            .filter((x) => x) // we only keep the non-zero values
            .map((x) => {
                const combo_line_id = this.pos.models["pos.combo.line"].get(x);
                return {
                    combo_line_id: combo_line_id,
                    configuration: this.state.configuration[combo_line_id.id],
                };
            });
    }

    async onClickProduct({ product, combo_line }, ev) {
        if (product.isConfigurable()) {
            const payload = await this.pos.openConfigurator(product);
            if (payload) {
                this.state.configuration[combo_line.id] = payload;
            } else {
                // Do not select the product if configuration popup is cancelled.
                this.state.combo[combo_line.id] = 0;
            }
        }
    }

    confirm() {
        this.props.getPayload(this.getSelectedComboLines());
        this.props.close();
    }
}
