import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { _t } from "@web/core/l10n/translation";
import { formatFloat, floatIsZero } from "@web/core/utils/numbers";
import { lt } from "@point_of_sale/utils";
import {
    PrintRecMessage,
    PrintRecItem,
    PrintRecTotal,
    PrintRecRefund,
    PrintRecItemAdjustment,
    PrintRecSubtotalAdjustment,
    PrintNormal,
} from "@l10n_it_pos/app/fiscal_printer/commands";

export class Body extends Component {
    static template = "l10n_it_pos.FiscalDocumentBody";

    static components = {
        PrintRecMessage,
        PrintRecItem,
        PrintRecTotal,
        PrintRecRefund,
        PrintRecItemAdjustment,
        PrintRecSubtotalAdjustment,
        PrintNormal,
    };

    static props = {
        order: {
            type: Object,
            optional: true, // To keep backward compatibility
        },
        isBasicPrint: {
            type: Boolean,
            optional: true,
        },
        isEarlyPrint: {
            type: Boolean,
            optional: true,
        },
    };
    static defaultProps = {
        isBasicPrint: false,
        isEarlyPrint: false,
    };

    setup() {
        this.pos = usePos();
        this.order = this.props.order || this.pos.get_order();
        this.adjustment = this.order.get_rounding_applied() && {
            description: _t("Rounding"),
            amount: this._itFormatCurrency(Math.abs(this.order.get_rounding_applied())),
            adjustmentType: this.order.get_rounding_applied() > 0 ? 6 : 1,
        };
    }

    _itFormatCurrency(amount) {
        const currency = this.order.currency_id || this.pos.config.currency_id;
        const decPlaces = currency.decimal_places;
        return formatFloat(amount, {
            thousandsSep: "",
            digits: [0, decPlaces],
        });
    }
    _itFormatQty(qty) {
        const uom_decimal_places = this.pos.models["decimal.precision"].find(
            (dp) => dp.name === "Product Unit of Measure"
        ).digits;
        const decimal_places = Math.min(3, uom_decimal_places);
        return formatFloat(qty, {
            thousandsSep: "",
            digits: [0, decimal_places],
        });
    }
    get isFullDiscounted() {
        return this.order.lines.length > 0 && floatIsZero(this.order.get_total_with_tax());
    }
    get lines() {
        const calculateDiscountAmount = (line) => {
            const { priceWithTaxBeforeDiscount, priceWithTax: priceWithTaxAfterDiscount } =
                line.get_all_prices();
            return priceWithTaxBeforeDiscount - priceWithTaxAfterDiscount;
        };

        const currency = this.order.currency_id || this.pos.config.currency_id;

        return this.order.lines.map((line, index) => {
            const productName = line.get_full_product_name();
            const department = line.tax_ids.map((tax) => tax.tax_group_id.pos_receipt_label)[0];
            const isRefund = line.qty < 0;
            const isReward = line.is_reward_line;
            const unitPrice = isRefund
                ? line.get_all_prices(1).priceWithTax
                : line.get_all_prices(1).priceWithTaxBeforeDiscount;
            const isGlobalDiscount = lt(unitPrice, 0, {
                decimals: currency.decimal_places,
            });
            const unitPriceFormatted = this._itFormatCurrency(
                isGlobalDiscount ? -unitPrice : unitPrice
            );
            const quantity = Math.abs(line.qty);
            const description = isRefund ? _t("%s (refund)", productName) : productName;
            const totalPriceFormatted = this._itFormatCurrency(quantity * unitPrice);

            return {
                isRefund,
                isReward,
                isGlobalDiscount,
                description,
                customer_note: line.get_customer_note(),
                quantity: this._itFormatQty(quantity),
                // DISCOUNT: Use price before discount because the discounted amount is specified in the printRecItemAdjustment.
                // REFUND: Use the price with tax because there is no adjustment for printRecRefund.
                unitPrice: unitPriceFormatted,
                department,
                index,
                discount: (!floatIsZero(line.discount) || isReward) && {
                    description: isReward
                        ? productName
                        : _t("%s discount (%s)", productName, `${line.discount}%`),
                    amount: this._itFormatCurrency(
                        isReward
                            ? Math.abs(line.price_subtotal_incl)
                            : calculateDiscountAmount(line)
                    ),
                },
                message: this._itFormatQty(quantity) + " x " + description,
                priceTotal: totalPriceFormatted,
            };
        });
    }

    get payments() {
        return this.order.payment_ids
            .filter((payment) => !payment.is_change && payment.amount > 0)
            .map((payment) => ({
                description: _t("Payment in %s", payment.payment_method_id.name),
                payment: this._itFormatCurrency(payment.amount),
                paymentType: payment.payment_method_id.it_payment_code,
                index: payment.payment_method_id.it_payment_index,
                id: payment.id,
            }));
    }

    get subtotal() {
        return _t("Subtotal: ") + this._itFormatCurrency(this.order.amount_total);
    }
}
