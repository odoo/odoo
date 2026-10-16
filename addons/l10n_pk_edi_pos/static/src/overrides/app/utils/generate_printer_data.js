import { accountTaxHelpers } from "@account/helpers/account_tax";
import { formatCurrency } from "@web/core/currency";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";
import { patch } from "@web/core/utils/patch";
import { roundPrecision } from "@web/core/utils/numbers";

patch(GeneratePrinterData.prototype, {
    generateReceiptData() {
        const data = super.generateReceiptData(...arguments);
        if (this.company.country_id?.code !== "PK") {
            return data;
        }
        if (this.order.l10n_pk_edi_pos_qr) {
            data.extra_data.l10n_pk_edi_pos_qr = this.generateQrCode(this.order.l10n_pk_edi_pos_qr);
            data.image.l10n_pk_edi_pos_fbr_logo = "/l10n_pk_edi_pos/static/src/img/img_fbr_pos.png";
        }
        if (this.config.l10n_pk_edi_pos_enabled) {
            data.conditions.l10n_pk_edi_pos_enabled = true;
            this.addFbrReceiptData(data);
        }
        return data;
    },

    addFbrReceiptData(data) {
        let subtotal = 0;
        let serviceFee = 0;
        let hasServiceFee = false;
        const lineByUuid = Object.fromEntries(this.order.lines.map((line) => [line.uuid, line]));
        for (const lineData of data.lines) {
            const line = lineByUuid[lineData.uuid];
            const taxDetails = line.prices;
            const taxesData = taxDetails.taxes_data;
            const untaxed =
                taxDetails.total_excluded_currency + taxDetails.delta_total_excluded_currency;
            const total =
                untaxed + taxesData.reduce((sum, taxData) => sum + taxData.tax_amount_currency, 0);
            const isServiceFee = line.isFbrServiceFeeLine();
            if (isServiceFee) {
                hasServiceFee = true;
                serviceFee += total;
            } else {
                subtotal += untaxed;
            }

            // Same figures as sent to the FBR, which leaves out the fee and zero-quantity lines.
            let taxRate = "";
            let taxAmount = "";
            if (!isServiceFee && line.qty) {
                let rateBase = taxDetails.raw_total_excluded_currency;
                if (line.product_id.product_tmpl_id.l10n_pk_is_fbr_3rd_schedule) {
                    const saleLine = line.getBaseLine({
                        price_unit: line.product_id.lst_price,
                        discount: 0,
                    });
                    accountTaxHelpers.add_tax_details_in_base_line(saleLine, this.company);
                    rateBase = saleLine.tax_details.raw_total_excluded_currency;
                }
                const salesTax = taxesData
                    .filter((taxData) => !taxData.tax.l10n_pk_is_further_tax)
                    .reduce((sum, taxData) => sum + taxData.tax_amount_currency, 0);
                taxRate = `${this.getFbrTaxRate(taxesData, rateBase)}%`;
                taxAmount = formatCurrency(salesTax, this.currency.id, { noSymbol: true });
            }

            Object.assign(lineData, {
                unit_price: line.currencyDisplayPriceUnitExcl,
                l10n_pk_edi_pos_is_service_fee: isServiceFee,
                l10n_pk_edi_pos_tax_rate: taxRate,
                l10n_pk_edi_pos_tax_amount: taxAmount,
                l10n_pk_edi_pos_total: formatCurrency(total, this.currency.id, { noSymbol: true }),
            });
        }

        data.extra_data.prices.subtotal_amount = this.formatCurrency(subtotal);
        Object.assign(data.extra_data, {
            l10n_pk_edi_pos_service_fee: hasServiceFee ? this.formatCurrency(serviceFee) : false,
            l10n_pk_edi_pos_received: this.formatCurrency(this.order.amountPaid),
        });
    },

    getFbrTaxRate(taxesData, base) {
        let rate = 0;
        for (const taxData of taxesData) {
            const tax = taxData.tax;
            if (tax.l10n_pk_is_further_tax) {
                continue;
            }
            if (tax.amount_type === "percent") {
                rate += tax.amount;
            } else if (base) {
                rate += (taxData.raw_tax_amount_currency / base) * 100;
            }
        }
        return roundPrecision(rate, 0.01);
    },
});
