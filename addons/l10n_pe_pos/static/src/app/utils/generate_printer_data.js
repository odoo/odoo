import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";

patch(GeneratePrinterData.prototype, {
    generateTaxData() {
        if (this.company.country_id.code !== "PE") {
            return super.generateTaxData(...arguments);
        }
        const data = this.order._constructPriceData();
        const discount = this.order.getTotalDiscount();
        const rounding = this.order.appliedRounding;
        const sign = this.order.orderSign; // Invert values for refund (reverse sign)

        return {
            same_tax_base: data.taxDetails.same_tax_base,
            discount_amount: discount ? this.formatCurrency(discount * sign) : false,
            rounding_amount: rounding ? this.formatCurrency(rounding * sign) : false,
            tax_amount: this.formatCurrency(data.taxDetails.tax_amount * sign),
            total_amount: this.formatCurrency(data.taxDetails.total_amount * sign),
            subtotal_amount: this.formatCurrency(data.taxDetails.base_amount_currency * sign),
            taxes: data.taxDetails.subtotals[0]?.tax_groups?.map((tax) => ({
                name: tax.group_name,
                amount: this.formatCurrency(tax.tax_amount * sign),
                amount_base: this.formatCurrency(tax.base_amount_currency * sign),
            })),
        };
    },

    generateLineData() {
        const lines = super.generateLineData(...arguments);
        if (this.company.country_id.code !== "PE") {
            return lines;
        }
        const sign = this.order.orderSign;
        return lines.map((line) => ({
            ...line,
            qty: line.qty * sign,
        }));
    },

    generatePaymentData() {
        const data = super.generatePaymentData(...arguments);
        if (this.company.country_id.code !== "PE") {
            return data;
        }
        const sign = this.order.orderSign;
        return this.order.payment_ids.map((line, index) => ({
            ...data[index],
            amount: this.formatCurrency(line.amount * sign),
        }));
    },
});
