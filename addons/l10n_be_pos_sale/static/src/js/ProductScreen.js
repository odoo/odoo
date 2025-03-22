/** @odoo-module **/

import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';

export const PoSSaleBeProductScreen = (ProductScreen) =>
    class extends ProductScreen {
        async _onClickPay() {
            const orderLines = this.currentOrder.get_orderlines();
            const has_origin_order = orderLines.some(line => line.sale_order_origin_id);
            const has_intracom_taxes = orderLines.some(
                (line) =>
                    line.tax_ids &&
                    this.env.pos.intracom_tax_ids &&
                    line.tax_ids.some((tax) => this.env.pos.intracom_tax_ids.includes(tax))
            );
            if (
                this.env.pos.company.country &&
                this.env.pos.company.country.code === "BE" &&
                has_origin_order &&
                has_intracom_taxes
            ) {
                this.currentOrder.to_invoice = true;
            }
            return super._onClickPay(...arguments);
        }
    };

Registries.Component.extend(ProductScreen, PoSSaleBeProductScreen);
