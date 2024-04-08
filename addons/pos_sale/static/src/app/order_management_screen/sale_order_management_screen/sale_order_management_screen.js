/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";
import { parseFloat } from "@web/views/fields/parsers";
import { floatIsZero } from "@web/core/utils/numbers";
import { useBus, useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";

import { SaleOrderList } from "@pos_sale/app/order_management_screen/sale_order_list/sale_order_list";
import { SaleOrderManagementControlPanel } from "@pos_sale/app/order_management_screen/sale_order_management_control_panel/sale_order_management_control_panel";
import { Component, onMounted, useRef } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { enhancedButtons } from "@point_of_sale/app/generic_components/numpad/numpad";

/**
 * ID getter to take into account falsy many2one value.
 * @param {[id: number, display_name: string] | false} fieldVal many2one field value
 * @returns {number | false}
 */

export class SaleOrderManagementScreen extends Component {
    static storeOnOrder = false;
    static components = { SaleOrderList, SaleOrderManagementControlPanel };
    static template = "pos_sale.SaleOrderManagementScreen";
    static props = {};

    setup() {
        super.setup();
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.root = useRef("root");
        this.numberBuffer = useService("number_buffer");
        this.saleOrderFetcher = useService("sale_order_fetcher");
        this.notification = useService("notification");

        useBus(this.saleOrderFetcher, "update", this.render);

        onMounted(this.onMounted);
    }
    onMounted() {
        this.saleOrderFetcher.setNPerPage(35);
        this.saleOrderFetcher.fetch();
    }
    _getSaleOrderOrigin(order) {
        for (const line of order.get_orderlines()) {
            if (line.sale_order_origin_id) {
                return line.sale_order_origin_id;
            }
        }
        return false;
    }
    get selectedPartner() {
        const order = this.pos.orderManagement.selectedOrder;
        return order ? order.get_partner() : null;
    }
    get orders() {
        return this.saleOrderFetcher.get();
    }
    onNextPage() {
        this.saleOrderFetcher.nextPage();
    }
    onPrevPage() {
        this.saleOrderFetcher.prevPage();
    }
    onSearch(domain) {
        this.saleOrderFetcher.setSearchDomain(domain);
        this.saleOrderFetcher.setPage(1);
        this.saleOrderFetcher.fetch();
    }
    async onClickSaleOrder(clickedOrder) {
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
        let currentPOSOrder = this.pos.get_order();
        const sale_order = await this._getSaleOrder(clickedOrder.id);
        clickedOrder.shipping_date = this.pos.config.ship_later && sale_order.shipping_date;

        const currentSaleOrigin = this._getSaleOrderOrigin(currentPOSOrder);
        const currentSaleOriginId = currentSaleOrigin && currentSaleOrigin.id;

        if (currentSaleOriginId) {
            const linkedSO = await this._getSaleOrder(currentSaleOriginId);
            if (
                linkedSO.partner_id?.id !== sale_order.partner_id?.id ||
                linkedSO.partner_invoice_id?.id !== sale_order.partner_invoice_id?.id ||
                linkedSO.partner_shipping_id?.id !== sale_order.partner_shipping_id?.id
            ) {
                currentPOSOrder = this.pos.add_new_order({
                    partner_id: sale_order.partner_id,
                });
                this.notification.add(_t("A new order has been created."));
            }
        }

        const orderFiscalPos = sale_order.fiscal_position_id
            ? this.pos.models["account.fiscal.position"].find(
                  (position) => position.id === sale_order.fiscal_position_id
              )
            : false;
        if (orderFiscalPos) {
            currentPOSOrder.update({
                fiscal_position_id: orderFiscalPos,
            });
        }

        if (sale_order.partner_id) {
            currentPOSOrder.set_partner(sale_order.partner_id);
        }

        if (selectedOption == "settle") {
            // settle the order
            const lines = sale_order.order_line;

            if (sale_order.pricelist_id) {
                currentPOSOrder.set_pricelist(sale_order.pricelist_id);
            }

            /**
             * This variable will have 3 values, `undefined | false | true`.
             * Initially, it is `undefined`. When looping thru each sale.order.line,
             * when a line comes with lots (`.lot_names`), we use these lot names
             * as the pack lot of the generated pos.order.line. We ask the user
             * if he wants to use the lots that come with the sale.order.lines to
             * be used on the corresponding pos.order.line only once. So, once the
             * `useLoadedLots` becomes true, it will be true for the succeeding lines,
             * and vice versa.
             */
            let useLoadedLots;
            let previousProductLine = null;
            for (const line of lines) {
                const newLineValues = {
                    product_id: line.product_id,
                    qty: line.product_uom_qty,
                    price_unit: line.price_unit,
                    tax_ids:
                        orderFiscalPos || !line.tax_id
                            ? undefined
                            : line.tax_id.map((t) => ["link", t]),
                    sale_order_origin_id: clickedOrder,
                    sale_order_line_id: line,
                    customer_note: line.customer_note,
                    description: line.name,
                    order_id: currentPOSOrder,
                };

                if (line.display_type === "line_note") {
                    if (previousProductLine) {
                        const previousNote = previousProductLine.customer_note;
                        previousProductLine.customer_note = previousNote
                            ? previousNote + "--" + line.name
                            : line.name;
                    }

                    continue;
                }

                if (line.display_type === "line_section") {
                    continue;
                }

                const newLine = await this.pos.addLineToCurrentOrder(newLineValues, {}, false);
                previousProductLine = newLine;

                if (
                    newLine.get_product().tracking !== "none" &&
                    (this.pos.pickingType.use_create_lots ||
                        this.pos.pickingType.use_existing_lots) &&
                    line.pack_lot_ids?.length > 0
                ) {
                    // Ask once when `useLoadedLots` is undefined, then reuse it's value on the succeeding lines.
                    const { confirmed } =
                        useLoadedLots === undefined
                            ? this.dialog.add(ConfirmationDialog, {
                                  title: _t("SN/Lots Loading"),
                                  body: _t(
                                      "Do you want to load the SN/Lots linked to the Sales Order?"
                                  ),
                                  confirmLabel: _t("Yes"),
                                  cancelLabel: _t("No"),
                              })
                            : { confirmed: useLoadedLots };
                    useLoadedLots = confirmed;
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
                    while (!floatIsZero(remaining_quantity, 6)) {
                        const splitted_line =
                            this.pos.models["pos.order.line"].create(newLineValues);
                        splitted_line.set_quantity(Math.min(remaining_quantity, 1.0), true);
                        remaining_quantity -= splitted_line.qty;
                    }
                    newLine.delete();
                }
            }
        } else {
            // apply a downpayment
            if (this.pos.config.down_payment_product_id) {
                const lines = sale_order.order_line.filter((line) => {
                    return (
                        line.product_id &&
                        line.product_id.id !== this.pos.config.down_payment_product_id.id
                    );
                });
                const tab = lines.map((line) => ({
                    product_name: line.product_id.display_name,
                    product_uom_qty: line.product_uom_qty,
                    price_unit: line.price_unit,
                    total: line.price_total,
                }));
                let down_payment_product = this.pos.config.down_payment_product_id;

                if (!down_payment_product) {
                    const dpId = this.pos.config.raw.down_payment_product_id;
                    await this.pos.data.read("product.product", [dpId]);
                    down_payment_product = this.pos.config.down_payment_product_id;
                }

                const down_payment_tax =
                    this.pos.models["account.tax"].get(down_payment_product.taxes_id) || false;
                let down_payment;
                if (down_payment_tax) {
                    down_payment = down_payment_tax.price_include
                        ? sale_order.amount_total
                        : sale_order.amount_untaxed;
                } else {
                    down_payment = sale_order.amount_total;
                }

                let popupInputSuffix = "";
                const popupTotalDue = sale_order.amount_total;
                let feedback = () => false;
                const popupSubtitle = _t("Due balance: %s");
                if (selectedOption == "dpAmount") {
                    popupInputSuffix = this.pos.currency.symbol;
                } else {
                    popupInputSuffix = "%";
                    feedback = (buffer) => {
                        if (buffer && buffer.length > 0) {
                            const percentage = parseFloat(buffer);
                            if (isNaN(percentage)) {
                                return false;
                            }
                            return `(${this.env.utils.formatCurrency(
                                (popupTotalDue * percentage) / 100
                            )})`;
                        } else {
                            return false;
                        }
                    };
                }
                const payload = await makeAwaitable(this.dialog, NumberPopup, {
                    title: _t("Down Payment"),
                    subtitle: sprintf(
                        popupSubtitle,
                        this.env.utils.formatCurrency(sale_order.amount_total)
                    ),
                    buttons: enhancedButtons(this.env),
                    formatDisplayedValue: (x) => `${popupInputSuffix} ${x}`,
                    feedback,
                });

                if (!payload) {
                    return;
                }
                if (selectedOption == "dpAmount") {
                    down_payment = parseFloat(payload);
                } else {
                    down_payment = (down_payment * parseFloat(payload)) / 100;
                }

                if (down_payment > sale_order.amount_unpaid) {
                    const errorBody = _t(
                        "You have tried to charge a down payment of %s but only %s remains to be paid, %s will be applied to the purchase order line.",
                        this.env.utils.formatCurrency(down_payment),
                        this.env.utils.formatCurrency(sale_order.amount_unpaid),
                        sale_order.amount_unpaid > 0
                            ? this.env.utils.formatCurrency(sale_order.amount_unpaid)
                            : this.env.utils.formatCurrency(0)
                    );
                    this.dialog.add(AlertDialog, {
                        title: "Error amount too high",
                        body: errorBody,
                    });
                    down_payment = sale_order.amount_unpaid > 0 ? sale_order.amount_unpaid : 0;
                }

                const new_line = await this.pos.addLineToCurrentOrder({
                    order_id: this.pos.get_order(),
                    product_id: down_payment_product,
                    price_unit: down_payment,
                    sale_order_origin_id: clickedOrder,
                    down_payment_details: tab,
                });
                new_line.uiState.price_type = "automatic";
                new_line.set_unit_price(down_payment);
            } else {
                const title = _t("No down payment product");
                const body = _t(
                    "It seems that you didn't configure a down payment product in your point of sale. You can go to your point of sale configuration to choose one."
                );
                this.dialog.add(AlertDialog, { title, body });
            }
        }

        this.pos.closeScreen();
    }

    async _getSaleOrder(id) {
        const result = await this.pos.data.read("sale.order", [id]);
        const sale_order = result[0];

        if (sale_order.picking_ids[0]) {
            const result = await this.pos.data.read(
                "stock.picking",
                [sale_order.picking_ids[0]],
                ["scheduled_date"]
            );
            const picking = result[0];
            sale_order.shipping_date = picking.scheduled_date;
        }

        return sale_order;
    }
}

registry.category("pos_screens").add("SaleOrderManagementScreen", SaleOrderManagementScreen);
