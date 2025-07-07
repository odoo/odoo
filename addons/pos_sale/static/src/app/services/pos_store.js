import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";
import { parseFloat } from "@web/views/fields/parsers";
import { SelectionPopup } from "@point_of_sale/app/components/popups/selection_popup/selection_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { ask, makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { enhancedButtons } from "@point_of_sale/app/components/numpad/numpad";
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { accountTaxHelpers } from "@account/helpers/account_tax";
import { getTaxesAfterFiscalPosition } from "@point_of_sale/app/models/utils/tax_utils";

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

        const currentSaleOrigin = this.getOrder()
            .getOrderlines()
            .find((line) => line.sale_order_origin_id)?.sale_order_origin_id;
        if (currentSaleOrigin?.id) {
            const linkedSO = await this._getSaleOrder(currentSaleOrigin.id);
            if (
                linkedSO.partner_id?.id !== sale_order.partner_id?.id ||
                linkedSO.partner_invoice_id?.id !== sale_order.partner_invoice_id?.id ||
                linkedSO.partner_shipping_id?.id !== sale_order.partner_shipping_id?.id
            ) {
                this.addNewOrder({
                    partner_id: sale_order.partner_id,
                });
                this.notification.add(_t("A new order has been created."));
            }
        }
        if (sale_order.partner_id) {
            this.getOrder().setPartner(sale_order.partner_id);
        }

        // Fiscal position should be set after the partner is set
        // to ensure that the fiscal position is correctly computed
        // based on sale order.
        const orderFiscalPos = sale_order.fiscal_position_id;
        this.getOrder().update({
            fiscal_position_id: orderFiscalPos,
        });

        selectedOption == "settle"
            ? await this.settleSO(sale_order, orderFiscalPos)
            : await this.downPaymentSO(sale_order, selectedOption == "dpPercentage");
        this.selectOrderLine(this.getOrder(), this.getOrder().lines.at(-1));
    },
    async _getSaleOrder(id) {
        const result = await this.data.callRelated("sale.order", "load_sale_order_from_pos", [
            id,
            this.config.id,
        ]);
        return result["sale.order"][0];
    },
    async settleSO(sale_order, orderFiscalPos) {
        if (sale_order.pricelist_id) {
            this.getOrder().setPricelist(sale_order.pricelist_id);
        }
        let useLoadedLots = false;
        let userWasAskedAboutLoadedLots = false;
        let previousProductLine = null;

        const converted_lines = await this.data.call("sale.order.line", "read_converted", [
            sale_order.order_line.map((l) => l.id),
        ]);

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

            if (line.is_downpayment) {
                line.product_id = this.config.down_payment_product_id;
            }

            const taxes = getTaxesAfterFiscalPosition(line.tax_ids, orderFiscalPos, this.models);
            const newLineValues = {
                product_tmpl_id: line.product_id?.product_tmpl_id,
                product_id: line.product_id,
                qty: line.product_uom_qty,
                price_unit: line.price_unit,
                price_type: "automatic",
                tax_ids: taxes.map((tax) => ["link", tax]),
                sale_order_origin_id: sale_order,
                sale_order_line_id: line,
                customer_note: line.customer_note,
                description: line.name,
                order_id: this.getOrder(),
                custom_attribute_value_ids: Object.values(
                    line.product_custom_attribute_value_ids || {}
                ).map((value_line) => [
                    "create",
                    {
                        custom_product_template_attribute_value_id:
                            value_line.custom_product_template_attribute_value_id,
                        custom_value: value_line.custom_value,
                    },
                ]),
            };
            if (line.display_type === "line_section") {
                continue;
            }
            newLineValues.attribute_value_ids = line.product_custom_attribute_value_ids.map(
                (value_line) => {
                    if (value_line?.custom_product_template_attribute_value_id) {
                        return ["link", value_line.custom_product_template_attribute_value_id];
                    }
                }
            );
            const newLine = await this.addLineToCurrentOrder(newLineValues, {}, false);
            previousProductLine = newLine;

            const converted_line = converted_lines.find((l) => l.id === line.id);
            if (
                newLine.getProduct().tracking !== "none" &&
                (this.pickingType.use_create_lots || this.pickingType.use_existing_lots) &&
                converted_line.lot_names.length > 0
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
                        newPackLotLines: (converted_line.lot_names || []).map((name) => ({
                            lot_name: name,
                        })),
                    });
                }
            }
            newLine.setQuantityFromSOL(converted_line);
            newLine.setUnitPrice(converted_line.price_unit);
            newLine.setDiscount(line.discount);

            const product_unit = line.product_id.uom_id;
            if (product_unit && !product_unit.is_pos_groupable) {
                let remaining_quantity = newLine.qty;
                newLineValues.product_id = newLine.product_id;
                newLine.delete();
                while (!product_unit.isZero(remaining_quantity)) {
                    const splitted_line = this.models["pos.order.line"].create({
                        ...newLineValues,
                    });
                    splitted_line.setQuantity(Math.min(remaining_quantity, 1.0), true);
                    splitted_line.setDiscount(line.discount);
                    remaining_quantity -= splitted_line.qty;
                }
            }
        }
    },

    prepareSoBaseLineForTaxesComputationExtraValues(so, soLine) {
        const extraValues = { currency_id: so.currency_id || this.company.currency_id };
        return {
            ...extraValues,
            quantity: soLine.product_uom_qty,
            tax_ids: soLine.tax_ids,
            partner_id: so.partner_id,
            product_id: soLine.product_id,
            extra_tax_data: soLine.extra_tax_data,
        };
    },

    async downPaymentSO(saleOrder, isPercentage) {
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
                this.env.utils.formatCurrency(saleOrder.amount_unpaid)
            ),
            buttons: enhancedButtons(),
            formatDisplayedValue: (x) => (isPercentage ? `% ${x}` : x),
            feedback: (buffer) =>
                isPercentage && buffer
                    ? `(${this.env.utils.formatCurrency(
                          (saleOrder.amount_unpaid * parseFloat(buffer)) / 100
                      )})`
                    : "",
        });
        if (!payload) {
            return;
        }

        const saleOrderLines = saleOrder.order_line.filter((soLine) => !soLine.display_type);
        const baseLines = [];
        for (const saleOrderLine of saleOrderLines) {
            baseLines.push(
                accountTaxHelpers.prepare_base_line_for_taxes_computation(
                    saleOrderLine,
                    this.prepareSoBaseLineForTaxesComputationExtraValues(saleOrder, saleOrderLine)
                )
            );
        }
        accountTaxHelpers.add_tax_details_in_base_lines(baseLines, this.company);
        accountTaxHelpers.round_base_lines_tax_details(baseLines, this.company);

        const amount = parseFloat(payload);
        const amountType = isPercentage ? "percent" : "fixed";
        const downPaymentProduct = this.config.down_payment_product_id;
        const groupingFunction = (base_line) => ({
            grouping_key: { product_id: downPaymentProduct },
            raw_grouping_key: { product_id: downPaymentProduct.id },
        });
        const downPaymentBaseLines = accountTaxHelpers.prepare_down_payment_lines(
            baseLines,
            this.company,
            amountType,
            amount,
            {
                computation_key: "down_payment", // TODO: won't work with multiple down payment on the same order... is it a problem?
                grouping_function: groupingFunction,
            }
        );

        // Update the pos order.
        for (const baseLine of downPaymentBaseLines) {
            // Find the sale order lines that are impacted by this down payment line.
            const taxIds = new Set(baseLine.tax_ids.map((tax) => tax.id));
            const matchedSaleOrderLines = [];
            for (const saleOrderLine of saleOrderLines) {
                // TODO: use '!saleOrderLine.is_down_payment' instead?
                // TODO: 'product_id' is always set on a SO line, correct?
                if (
                    !saleOrderLine.product_id ||
                    saleOrderLine.product_id.id === downPaymentProduct.id
                ) {
                    continue;
                }

                const saleOrderLineTaxIds = saleOrderLine.tax_ids.map((tax) => tax.id);
                if (
                    saleOrderLineTaxIds.length === taxIds.size &&
                    saleOrderLineTaxIds.every((taxId) => taxIds.has(taxId))
                ) {
                    matchedSaleOrderLines.push(saleOrderLine);
                }
            }

            this.addLineToCurrentOrder({
                pos: this,
                order: saleOrder,
                product_id: baseLine.product_id,
                product_tmpl_id: baseLine.product_id.product_tmpl_id,
                price: baseLine.price_unit,
                price_unit: baseLine.price_unit,
                price_type: "automatic",
                sale_order_origin_id: saleOrder,
                down_payment_details: matchedSaleOrderLines.map((saleOrderLine) => ({
                    product_name: saleOrderLine.product_id.display_name,
                    product_uom_qty: saleOrderLine.product_uom_qty,
                    price_unit: saleOrderLine.price_unit,
                    total: saleOrderLine.price_total,
                })),
                tax_ids: [["link", ...baseLine.tax_ids]],
                extra_tax_data: accountTaxHelpers.export_base_line_extra_tax_data(baseLine),
            });
        }
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
    setPartnerToCurrentOrder(partner) {
        if (partner.sale_warn_msg) {
            this.dialog.add(AlertDialog, {
                title: _t("Warning for %s", partner.name),
                body: partner.sale_warn_msg,
            });
        }
        super.setPartnerToCurrentOrder(partner);
    },
    addLineToCurrentOrder(vals, opt = {}, configure = true) {
        if (!vals.product_tmpl_id && vals.product_id) {
            vals.product_tmpl_id = vals.product_id.product_tmpl_id;
        }

        const productTemplate = vals.product_tmpl_id;
        if (productTemplate.sale_line_warn_msg) {
            this.dialog.add(AlertDialog, {
                title: _t("Warning for %s", productTemplate.name),
                body: productTemplate.sale_line_warn_msg,
            });
        }
        return super.addLineToCurrentOrder(vals, opt, configure);
    },
});
