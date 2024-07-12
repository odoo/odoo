import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";
import { parseFloat } from "@web/views/fields/parsers";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { ask, makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { enhancedButtons } from "@point_of_sale/app/generic_components/numpad/numpad";
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async onClickSaleOrder(clickedOrderId) {
        const selectedOption = await makeAwaitable(this.dialog, SelectionPopup, {
            title: _t("What do you want to do?"),
            list: [
                { id: "0", label: _t("Settle the order"), item: "settle" },
                {
                    id: "1",
                    label: _t("Apply a down payment (percentage)"),
                    item: "dpPercentage",
                },
                {
                    id: "2",
                    label: _t("Apply a down payment (fixed amount)"),
                    item: "dpAmount",
                },
            ],
        });
        if (!selectedOption) {
            return;
        }
        const sale_order = await this._getSaleOrder(clickedOrderId);
        sale_order.shipping_date = this.config.ship_later && sale_order.shipping_date;

        const currentSaleOrigin = this.get_order()
            .get_orderlines()
            .find((line) => line.sale_order_origin_id)?.sale_order_origin_id;
        if (currentSaleOrigin?.id) {
            const linkedSO = await this._getSaleOrder(currentSaleOrigin.id);
            if (
                linkedSO.partner_id?.id !== sale_order.partner_id?.id ||
                linkedSO.partner_invoice_id?.id !== sale_order.partner_invoice_id?.id ||
                linkedSO.partner_shipping_id?.id !== sale_order.partner_shipping_id?.id
            ) {
                this.add_new_order({
                    partner_id: sale_order.partner_id,
                });
                this.notification.add(_t("A new order has been created."));
            }
        }
        const orderFiscalPos =
            sale_order.fiscal_position_id &&
            this.models["account.fiscal.position"].find(
                (position) => position.id === sale_order.fiscal_position_id
            );
        if (orderFiscalPos) {
            this.get_order().update({
                fiscal_position_id: orderFiscalPos,
            });
        }
        if (sale_order.partner_id) {
            this.get_order().set_partner(sale_order.partner_id);
        }
        selectedOption == "settle"
            ? this.settleSO(sale_order, orderFiscalPos)
            : this.downPaymentSO(sale_order, selectedOption == "dpPercentage");
    },
    async _getSaleOrder(id) {
        const sale_order = (await this.data.read("sale.order", [id]))[0];
        if (sale_order.picking_ids[0]) {
            const result = await this.data.read(
                "stock.picking",
                [sale_order.picking_ids[0]],
                ["scheduled_date"]
            );
            const picking = result[0];
            sale_order.shipping_date = picking.scheduled_date;
        }
        return sale_order;
    },
    async settleSO(sale_order, orderFiscalPos) {
        if (sale_order.pricelist_id) {
            this.get_order().set_pricelist(sale_order.pricelist_id);
        }
        let useLoadedLots = false;
        let userWasAskedAboutLoadedLots = false;
        let previousProductLine = null;
        for (const line of sale_order.order_line) {
            if (line.display_type === "line_note") {
                if (previousProductLine) {
                    const previousNote = previousProductLine.customer_note;
                    previousProductLine.customer_note = previousNote
                        ? previousNote + "--" + line.name
                        : line.name;
                }
                continue;
            }
            const newLineValues = {
                product_id: line.product_id,
                qty: line.product_uom_qty,
                price_unit: line.price_unit,
                tax_ids:
                    orderFiscalPos || !line.tax_id
                        ? undefined
                        : line.tax_id.map((t) => ["link", t]),
                sale_order_origin_id: sale_order,
                sale_order_line_id: line,
                customer_note: line.customer_note,
                description: line.name,
                order_id: this.get_order(),
            };
            if (line.display_type === "line_section") {
                continue;
            }
            const newLine = await this.addLineToCurrentOrder(newLineValues, {}, false);
            previousProductLine = newLine;
            if (
                newLine.get_product().tracking !== "none" &&
                (this.pickingType.use_create_lots || this.pickingType.use_existing_lots) &&
                line.pack_lot_ids?.length > 0
            ) {
                if (!useLoadedLots && !userWasAskedAboutLoadedLots) {
                    useLoadedLots = await ask(this.dialog, {
                        title: _t("SN/Lots Loading"),
                        body: _t("Do you want to load the SN/Lots linked to the Sales Order?"),
                    });
                    userWasAskedAboutLoadedLots = true;
                }
                if (useLoadedLots) {
                    newLine.setPackLotLines({
                        modifiedPackLotLines: [],
                        newPackLotLines: (line.lot_names || []).map((name) => ({
                            lot_name: name,
                        })),
                    });
                }
            }
            newLine.setQuantityFromSOL(line);
            newLine.set_unit_price(line.price_unit);
            newLine.set_discount(line.discount);

            const product_unit = line.product_id.uom_id;
            if (product_unit && !product_unit.is_pos_groupable) {
                let remaining_quantity = newLine.qty;
                while (!this.env.utils.floatIsZero(remaining_quantity)) {
                    const splitted_line = this.models["pos.order.line"].create(newLineValues);
                    splitted_line.set_quantity(Math.min(remaining_quantity, 1.0), true);
                    remaining_quantity -= splitted_line.qty;
                }
                newLine.delete();
            }
        }
    },
    async downPaymentSO(sale_order, isPercentage) {
        if (!this.config.down_payment_product_id && this.config.raw.down_payment_product_id) {
            await this.data.read("product.product", [this.config.raw.down_payment_product_id]);
        }
        if (!this.config.down_payment_product_id) {
            this.dialog.add(AlertDialog, {
                title: _t("No down payment product"),
                body: _t(
                    "It seems that you didn't configure a down payment product in your point of sale. You can go to your point of sale configuration to choose one."
                ),
            });
            return;
        }
        const payload = await makeAwaitable(this.dialog, NumberPopup, {
            title: _t("Down Payment"),
            subtitle: sprintf(
                _t("Due balance: %s"),
                this.env.utils.formatCurrency(sale_order.amount_total)
            ),
            buttons: enhancedButtons(),
            formatDisplayedValue: (x) => (isPercentage ? `% ${x}` : x),
            feedback: (buffer) =>
                isPercentage
                    ? `(${this.env.utils.formatCurrency(
                          (sale_order.amount_total * parseFloat(buffer)) / 100
                      )})`
                    : "",
        });
        if (!payload) {
            return;
        }
        const userValue = parseFloat(payload);
        let proposed_down_payment = userValue;
        if (isPercentage) {
            const down_payment_tax = this.models["account.tax"].get(
                this.config.down_payment_product_id.taxes_id
            );
            const percentageBase =
                !down_payment_tax || down_payment_tax.price_include
                    ? sale_order.amount_total
                    : sale_order.amount_untaxed;
            proposed_down_payment = (percentageBase * userValue) / 100;
        }
        if (proposed_down_payment > sale_order.amount_unpaid) {
            this.dialog.add(AlertDialog, {
                title: _t("Error amount too high"),
                body: _t(
                    "You have tried to charge a down payment of %s but only %s remains to be paid, %s will be applied to the purchase order line.",
                    this.env.utils.formatCurrency(proposed_down_payment),
                    this.env.utils.formatCurrency(sale_order.amount_unpaid),
                    this.env.utils.formatCurrency(sale_order.amount_unpaid || 0)
                ),
            });
            proposed_down_payment = sale_order.amount_unpaid || 0;
        }
        const new_line = await this.addLineToCurrentOrder({
            order_id: this.get_order(),
            product_id: this.config.down_payment_product_id,
            price_unit: proposed_down_payment,
            sale_order_origin_id: sale_order,
            down_payment_details: sale_order.order_line
                .filter(
                    (line) =>
                        line.product_id &&
                        line.product_id.id !== this.config.down_payment_product_id.id
                )
                .map((line) => ({
                    product_name: line.product_id.display_name,
                    product_uom_qty: line.product_uom_qty,
                    price_unit: line.price_unit,
                    total: line.price_total,
                })),
        });
        new_line.price_type = "automatic";
        new_line.set_unit_price(proposed_down_payment);
    },
    selectOrderLine(order, line) {
        super.selectOrderLine(...arguments);
        if (
            line &&
            this.config.down_payment_product_id &&
            line.product_id.id === this.config.down_payment_product_id.id
        ) {
            this.numpadMode = "price";
        }
    },
});
