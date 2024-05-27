/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";
import { parseFloat } from "@web/views/fields/parsers";
import { floatIsZero } from "@web/core/utils/numbers";
import { useBus, useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { ControlButtonsMixin } from "@point_of_sale/app/utils/control_buttons_mixin";
import { Orderline } from "@point_of_sale/app/store/models";

import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";

import { SaleOrderList } from "@pos_sale/app/order_management_screen/sale_order_list/sale_order_list";
import { SaleOrderManagementControlPanel } from "@pos_sale/app/order_management_screen/sale_order_management_control_panel/sale_order_management_control_panel";
import { Component, onMounted, useRef } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

/**
 * ID getter to take into account falsy many2one value.
 * @param {[id: number, display_name: string] | false} fieldVal many2one field value
 * @returns {number | false}
 */
function getId(fieldVal) {
    return fieldVal && fieldVal[0];
}

export class SaleOrderManagementScreen extends ControlButtonsMixin(Component) {
    static storeOnOrder = false;
    static components = { SaleOrderList, SaleOrderManagementControlPanel };
    static template = "pos_sale.SaleOrderManagementScreen";

    setup() {
        super.setup();
        this.pos = usePos();
        this.popup = useService("popup");
        this.orm = useService("orm");
        this.root = useRef("root");
        this.numberBuffer = useService("number_buffer");
        this.saleOrderFetcher = useService("sale_order_fetcher");
        this.notification = useService("pos_notification");

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
    async _setNumpadMode(event) {
        const { mode } = event.detail;
        this.numpadMode = mode;
        this.numberBuffer.reset();
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
        const { confirmed, payload: selectedOption } = await this.popup.add(SelectionPopup, {
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

        if (confirmed) {
            let currentPOSOrder = this.pos.get_order();
            const sale_order = await this._getSaleOrder(clickedOrder.id);
            clickedOrder.shipping_date = this.pos.config.ship_later && sale_order.shipping_date;

            const currentSaleOrigin = this._getSaleOrderOrigin(currentPOSOrder);
            const currentSaleOriginId = currentSaleOrigin && currentSaleOrigin.id;

            if (currentSaleOriginId) {
                const linkedSO = await this._getSaleOrder(currentSaleOriginId);
                if (
                    getId(linkedSO.partner_id) !== getId(sale_order.partner_id) ||
                    getId(linkedSO.partner_invoice_id) !== getId(sale_order.partner_invoice_id) ||
                    getId(linkedSO.partner_shipping_id) !== getId(sale_order.partner_shipping_id)
                ) {
                    currentPOSOrder = this.pos.add_new_order();
                    this.notification.add(_t("A new order has been created."), 4000);
                }
            }

            const order_partner = this.pos.db.get_partner_by_id(sale_order.partner_id[0]);
            if (order_partner) {
                currentPOSOrder.set_partner(order_partner);
            } else {
                try {
                    await this.pos._loadPartners([sale_order.partner_id[0]]);
                } catch {
                    const title = _t("Customer loading error");
                    const body = _t(
                        "There was a problem in loading the %s customer.",
                        sale_order.partner_id[1]
                    );
                    await this.popup.add(ErrorPopup, { title, body });
                }
                currentPOSOrder.set_partner(
                    this.pos.db.get_partner_by_id(sale_order.partner_id[0])
                );
            }
            const orderFiscalPos = sale_order.fiscal_position_id
                ? this.pos.fiscal_positions.find(
                      (position) => position.id === sale_order.fiscal_position_id[0]
                  )
                : false;
            if (orderFiscalPos) {
                currentPOSOrder.fiscal_position = orderFiscalPos;
            }
            const orderPricelist = sale_order.pricelist_id
                ? this.pos.pricelists.find(
                      (pricelist) => pricelist.id === sale_order.pricelist_id[0]
                  )
                : false;
            if (orderPricelist) {
                currentPOSOrder.set_pricelist(orderPricelist);
            }

            if (selectedOption == "settle") {
                // settle the order
                const lines = sale_order.order_line;
                const product_to_add_in_pos = lines
                    .filter((line) => !this.pos.db.get_product_by_id(line.product_id[0]))
                    .map((line) => line.product_id[0]);
                if (product_to_add_in_pos.length) {
                    const { confirmed } = await this.popup.add(ConfirmPopup, {
                        title: _t("Products not available in POS"),
                        body: _t(
                            "Some of the products in your Sale Order are not available in POS, do you want to import them?"
                        ),
                        confirmText: _t("Yes"),
                        cancelText: _t("No"),
                    });
                    if (confirmed) {
                        await this.pos._addProducts(product_to_add_in_pos);
                    }
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
                    if (!this.pos.db.get_product_by_id(line.product_id[0])) {
                        continue;
                    }

                    const line_values = {
                        pos: this.pos,
                        order: this.pos.get_order(),
                        product: this.pos.db.get_product_by_id(line.product_id[0]),
                        description: line.name,
                        price: line.price_unit,
                        tax_ids: orderFiscalPos ? undefined : line.tax_id,
                        price_manually_set: false,
                        sale_order_origin_id: clickedOrder,
                        sale_order_line_id: line,
                        customer_note: line.customer_note,
                    };
                    const new_line = new Orderline({ env: this.env }, line_values);

                    if (
                        new_line.get_product().tracking !== "none" &&
                        (this.pos.picking_type.use_create_lots ||
                            this.pos.picking_type.use_existing_lots) &&
                        line.lot_names.length > 0
                    ) {
                        // Ask once when `useLoadedLots` is undefined, then reuse it's value on the succeeding lines.
                        const { confirmed } =
                            useLoadedLots === undefined
                                ? await this.popup.add(ConfirmPopup, {
                                      title: _t("SN/Lots Loading"),
                                      body: _t(
                                          "Do you want to load the SN/Lots linked to the Sales Order?"
                                      ),
                                      confirmText: _t("Yes"),
                                      cancelText: _t("No"),
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
                    const product = this.pos.db.get_product_by_id(line.product_id[0]);
                    const product_unit = product.get_unit();
                    if (product_unit && !product.get_unit().is_pos_groupable) {
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
                    const lines = sale_order.order_line.filter((line) => {
                        return line.product_id[0] !== this.pos.config.down_payment_product_id[0];
                    });
                    const tab = lines.map((line) => ({
                        product_name: line.product_id[1],
                        product_uom_qty: line.product_uom_qty,
                        price_unit: line.price_unit,
                        total: line.price_total,
                    }));
                    let down_payment_product = this.pos.db.get_product_by_id(
                        this.pos.config.down_payment_product_id[0]
                    );
                    if (!down_payment_product) {
                        await this.pos._addProducts([this.pos.config.down_payment_product_id[0]]);
                        down_payment_product = this.pos.db.get_product_by_id(
                            this.pos.config.down_payment_product_id[0]
                        );
                    }
                    const down_payment_tax =
                        this.pos.taxes_by_id[down_payment_product.taxes_id] || false;
                    let down_payment;
                    if (down_payment_tax) {
                        down_payment = down_payment_tax.price_include
                            ? sale_order.amount_total
                            : sale_order.amount_untaxed;
                    } else {
                        down_payment = sale_order.amount_total;
                    }

                    let popupTitle = "";
                    let popupInputSuffix = "";
                    const popupTotalDue = sale_order.amount_total;
                    let getInputBufferReminder = () => false;
                    const popupSubtitle = _t("Due balance: %s");
                    if (selectedOption == "dpAmount") {
                        popupTitle = _t("Down Payment");
                        popupInputSuffix = this.pos.currency.symbol;
                    } else {
                        popupTitle = _t("Down Payment");
                        popupInputSuffix = "%";
                        getInputBufferReminder = (buffer) => {
                            if (buffer && buffer.length > 0) {
                                const percentage = parseFloat(buffer);
                                if (isNaN(percentage)) {
                                    return false;
                                }
                                return this.env.utils.formatCurrency(
                                    (popupTotalDue * percentage) / 100
                                );
                            } else {
                                return false;
                            }
                        };
                    }
                    const { confirmed, payload } = await this.popup.add(NumberPopup, {
                        title: popupTitle,
                        subtitle: sprintf(
                            popupSubtitle,
                            this.env.utils.formatCurrency(sale_order.amount_total)
                        ),
                        inputSuffix: popupInputSuffix,
                        startingValue: 0,
                        getInputBufferReminder,
                    });

                    if (!confirmed) {
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
                        await this.popup.add(ErrorPopup, {
                            title: _t("Error amount too high"),
                            body: errorBody,
                        });
                        down_payment = sale_order.amount_unpaid > 0 ? sale_order.amount_unpaid : 0;
                    }

                    const new_line = new Orderline(
                        { env: this.env },
                        {
                            pos: this.pos,
                            order: this.pos.get_order(),
                            product: down_payment_product,
                            price: down_payment,
                            price_type: "automatic",
                            sale_order_origin_id: clickedOrder,
                            down_payment_details: tab,
                        }
                    );
                    new_line.set_unit_price(down_payment);
                    this.pos.get_order().add_orderline(new_line);
                } else {
                    const title = _t("No down payment product");
                    const body = _t(
                        "It seems that you didn't configure a down payment product in your point of sale. You can go to your point of sale configuration to choose one."
                    );
                    await this.popup.add(ErrorPopup, { title, body });
                }
            }

            this.pos.closeScreen();
        }
    }

    async _getSaleOrder(id) {
        const [sale_order] = await this.orm.read(
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

        const sale_lines = await this._getSOLines(sale_order.order_line);
        sale_order.order_line = sale_lines;

        if (sale_order.picking_ids[0]) {
            const [picking] = await this.orm.read(
                "stock.picking",
                [sale_order.picking_ids[0]],
                ["scheduled_date"]
            );
            sale_order.shipping_date = picking.scheduled_date;
        }

        return sale_order;
    }

    async _getSOLines(ids) {
        const so_lines = await this.orm.call("sale.order.line", "read_converted", [ids]);
        return so_lines;
    }
}

registry.category("pos_screens").add("SaleOrderManagementScreen", SaleOrderManagementScreen);
