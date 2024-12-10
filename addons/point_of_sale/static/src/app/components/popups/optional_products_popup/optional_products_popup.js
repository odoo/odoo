import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { useService } from "@web/core/utils/hooks";
import { ComboConfiguratorPopup } from "@point_of_sale/app/components/popups/combo_configurator_popup/combo_configurator_popup";

export class OptionalProductPopup extends Component {
    static template = "point_of_sale.OptionalProductPopup";
    static components = { Dialog };
    static props = ["close", "productTemplate"];

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.state = useState({
            product_lines:
                this.props.productTemplate?.pos_optional_product_ids.map((product) => ({
                    product_tmpl_id: product,
                    payload: [],
                    qty: 0,
                })) || [],
            buttonDisabled: true,
        });
    }

    changeQuantity = async (optional_product, increase) => {
        if (
            optional_product.product_tmpl_id.isConfigurable() &&
            !Object.keys(optional_product.payload).length
        ) {
            const payload = await this.pos.openConfigurator(optional_product.product_tmpl_id);
            if (!payload) {
                return;
            }
            optional_product.payload = payload;
        }

        if (
            optional_product.product_tmpl_id.isCombo() &&
            !Object.keys(optional_product.payload).length
        ) {
            const payload = await makeAwaitable(this.dialog, ComboConfiguratorPopup, {
                productTemplate: optional_product.product_tmpl_id,
            });
            if (!payload) {
                return;
            }
            optional_product.payload = payload;
        }

        optional_product.qty = Math.max(0, optional_product.qty + (increase ? 1 : -1));
        this.state.buttonDisabled = !this.state.product_lines.some((product) => product.qty > 0);
    };

    onInputChangeQuantity(optional_product, quantity) {
        optional_product.qty = Math.max(0, parseInt(quantity) || 0);
    }

    confirm() {
        this.state.product_lines.forEach(async (product) => {
            if (product.qty > 0) {
                const line = await this.pos.addLineToCurrentOrder(product, {});
                if (line.product_id.isCombo()) {
                    for (const l of line.combo_line_ids) {
                        l.setQuantity(product.qty, true);
                    }
                }
            }
        });
        this.props.close();
    }

    cancel() {
        this.props.close();
    }
}
