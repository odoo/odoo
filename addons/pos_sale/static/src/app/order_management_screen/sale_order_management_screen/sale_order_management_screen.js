/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";
import { parseFloat } from "@web/views/fields/parsers";
import { floatIsZero } from "@web/core/utils/numbers";
import { useBus, useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { Orderline } from "@point_of_sale/app/store/models";

import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";

import { SaleOrderList } from "@pos_sale/app/order_management_screen/sale_order_list/sale_order_list";
import { SaleOrderManagementControlPanel } from "@pos_sale/app/order_management_screen/sale_order_management_control_panel/sale_order_management_control_panel";
import { Component, onMounted, useRef } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ask, makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
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
        // calculate how many can fit in the screen.
        // It is based on the height of the header element.
        // So the result is only accurate if each row is just single line.
        const flexContainer = this.root.el.querySelector(".flex-container");
        const cpEl = this.root.el.querySelector(".control-panel");
        const headerEl = this.root.el.querySelector(".header-row");
        const val = Math.trunc(
            (flexContainer.offsetHeight - cpEl.offsetHeight - headerEl.offsetHeight) /
                headerEl.offsetHeight
        );
        this.saleOrderFetcher.setNPerPage(val);
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
                linkedSO.partner_id !== sale_order.partner_id ||
                linkedSO.partner_invoice_id !== sale_order.partner_invoice_id ||
                linkedSO.partner_shipping_id !== sale_order.partner_shipping_id
            ) {
                currentPOSOrder = this.pos.add_new_order();
                this.notification.add(_t("A new order has been created."));
            }
        }

        try {
            await this.pos.load_new_partners();
        } catch {
            // FIXME Universal catch seems ill advised
        }
        const order_partner = this.pos.models["res.partner"].get(sale_order.partner_id);
        if (order_partner) {
            currentPOSOrder.set_partner(order_partner);
        } else {
            try {
                await this.pos._loadPartners([sale_order.partner_id]);
            } catch {
                const title = _t("Customer loading error");
                const body = _t("There was a problem in loading the %s customer.");
                this.dialog.add(AlertDialog, { title, body });
            }
            currentPOSOrder.set_partner(this.pos.models["res.partner"].get(sale_order.partner_id));
        }
        const orderFiscalPos = sale_order.fiscal_position_id
            ? this.pos.models["account.fiscal.position"].find(
                  (position) => position.id === sale_order.fiscal_position_id
              )
            : false;
        if (orderFiscalPos) {
            currentPOSOrder.fiscal_position = orderFiscalPos;
        }

        if (selectedOption == "settle") {
            // settle the order
            const lines = sale_order.order_line;
            const product_to_add_in_pos = lines
                .filter(
                    (line) =>
                        !this.pos.models["product.product"].get(line.product_id) && line.product_id
                )
                .map((line) => line.product_id);
            if (product_to_add_in_pos.length) {
                const confirmed = await ask(this.dialog, {
                    title: _t("Products not available in POS"),
                    body: _t(
                        "Some of the products in your Sale Order are not available in POS, do you want to import them?"
                    ),
                    confirmLabel: _t("Yes"),
                    cancelLabel: _t("No"),
                });
                if (confirmed) {
                    try {
                        await this.pos.data.ormWrite("product.product", product_to_add_in_pos, {
                            available_in_pos: true,
                        });
                    } catch (e) {
                        if (e.exceptionName !== "odoo.exceptions.AccessError") {
                            throw e;
                        }
                    }
                    await this.pos.loadProducts([...product_to_add_in_pos]);
                }
            }

            // The pricelist of the sale order is available after loading the products.
            const orderPricelist = sale_order.pricelist_id
                ? this.pos.models["product.pricelist"].find(
                      (pricelist) => pricelist.id === sale_order.pricelist_id
                  )
                : false;
            if (orderPricelist) {
                currentPOSOrder.set_pricelist(orderPricelist);
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

            for (var i = 0; i < lines.length; i++) {
                const line = lines[i];
                const productProduct = line.is_downpayment
                    ? this.pos.config.down_payment_product_id
                    : this.pos.models["product.product"].get(line.product_id);

                if (!productProduct) {
                    continue;
                }

                const line_values = {
                    pos: this.pos,
                    order: this.pos.get_order(),
                    product: productProduct,
                    description: line.name,
                    price: line.price_unit,
                    tax_ids: orderFiscalPos ? undefined : line.tax_id,
                    price_manually_set: false,
                    price_type: "automatic",
                    sale_order_origin_id: clickedOrder,
                    sale_order_line_id: line,
                    customer_note: line.customer_note,
                };
                const new_line = new Orderline({ env: this.env }, line_values);

                if (
                    new_line.get_product().tracking !== "none" &&
                    (this.pos.pickingType.use_create_lots ||
                        this.pos.pickingType.use_existing_lots) &&
                    line.lot_names.length > 0
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
                        new_line.setPackLotLines({
                            modifiedPackLotLines: [],
                            newPackLotLines: (line.lot_names || []).map((name) => ({
                                lot_name: name,
                            })),
                        });
                    }
                }
                new_line.setQuantityFromSOL(line);
                new_line.set_unit_price(line.price_unit);
                new_line.set_discount(line.discount);
                const product_unit = productProduct.uom_id;
                if (product_unit && !product_unit.is_pos_groupable) {
                    let remaining_quantity = new_line.quantity;
                    while (!floatIsZero(remaining_quantity, 6)) {
                        const splitted_line = new Orderline({ env: this.env }, line_values);
                        splitted_line.set_quantity(Math.min(remaining_quantity, 1.0), true);
                        this.pos.get_order().add_orderline(splitted_line);
                        remaining_quantity -= splitted_line.quantity;
                    }
                } else {
                    this.pos.get_order().add_orderline(new_line);
                }
            }
        } else {
            // apply a downpayment
            if (this.pos.config.down_payment_product_id) {
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
                        this.env.utils.formatCurrency(sale_order.amount_unpaid)
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
                        title: _t("Error amount too high"),
                        body: errorBody,
                    });
                    down_payment = sale_order.amount_unpaid > 0 ? sale_order.amount_unpaid : 0;
                }

                this._createDownpaymentLines(
                    sale_order,
                    down_payment,
                    clickedOrder,
                    down_payment_product
                );
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

    _createDownpaymentLines(sale_order, total_down_payment, clickedOrder, down_payment_product) {
        //This function will create all the downpaymentlines. We will create on downpayment line per unique tax combination

        const grouped = {};
        sale_order.order_line.forEach((obj) => {
            const sortedTaxes = obj.tax_id.slice().sort((a, b) => a - b);
            const key = sortedTaxes.join(",");
            if (!grouped[key]) {
                grouped[key] = [];
            }
            grouped[key].push(obj);
        });
        Object.keys(grouped).forEach((key) => {
            const group = grouped[key];
            const tab = group.map((line) => ({
                product_name: line.name,
                product_uom_qty: line.product_uom_qty,
                price_unit: line.price_unit,
                total: line.price_total,
            }));

            // Compute the part of the downpayment that should be assigned to this group
            const total_price = group.reduce((total, line) => (total += line.price_total), 0);
            const ratio = total_price / sale_order.amount_total;
            const down_payment_line_price = total_down_payment * ratio;
            // We apply the taxes and keep the same price
            const new_price = this.pos.compute_price_force_price_include(
                group[0].tax_id.map((tax_id) => this.pos.models["account.tax"].get(tax_id)),
                down_payment_line_price
            );
            this.pos.get_order().add_orderline(
                new Orderline(
                    { env: this.env },
                    {
                        pos: this.pos,
                        order: this.pos.get_order(),
                        product: down_payment_product,
                        price: new_price,
                        price_type: "automatic",
                        sale_order_origin_id: clickedOrder,
                        down_payment_details: tab,
                        tax_ids: group[0].tax_id,
                    }
                )
            );
        });
    }

    async _getSaleOrder(id) {
        const result = await this.pos.data.read(
            "sale.order",
            [id],
            [
                "order_line",
                "partner_id",
                "pricelist_id",
                "fiscal_position_id",
                "amount_total",
                "amount_untaxed",
                "amount_unpaid",
                "picking_ids",
                "partner_shipping_id",
                "partner_invoice_id",
            ]
        );

        const sale_order = result[0];
        const sale_lines = await this._getSOLines(sale_order.order_line);
        sale_order.order_line = sale_lines;

        return sale_order;
    }

    async _getSOLines(ids) {
        const so_lines = await this.pos.data.call("sale.order.line", "read_converted", [ids]);
        return so_lines;
    }
}

registry.category("pos_screens").add("SaleOrderManagementScreen", SaleOrderManagementScreen);
