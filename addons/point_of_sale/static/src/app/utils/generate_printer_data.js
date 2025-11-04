import { generateQRCodeDataUrl } from "@point_of_sale/utils";
import { formatCurrency } from "@web/core/currency";
import { renderToElement } from "@web/core/utils/render";
import { toCanvas } from "@point_of_sale/app/utils/html-to-image";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
export class GeneratePrinterData {
    constructor() {
        this.setup(...arguments);
    }

    setup(order, basicReceipt = false) {
        this.order = order;
        this.company = order.company;
        this.config = order.config;
        this.currency = order.currency;
        this.basicReceipt = basicReceipt;
    }

    formatCurrency(amount) {
        return formatCurrency(amount, this.currency.id);
    }

    generateTaxeData() {
        const data = this.order._constructPriceData();
        const discount = this.order.getTotalDiscount();
        const rounding = this.order.appliedRounding;

        return {
            same_tax_base: data.taxDetails.same_tax_base,
            discount_amount: discount ? this.formatCurrency(discount) : false,
            rounding_amount: rounding ? this.formatCurrency(rounding) : false,
            tax_amount: this.formatCurrency(data.taxDetails.tax_amount),
            total_amount: this.formatCurrency(data.taxDetails.total_amount),
            subtotal_amount: this.formatCurrency(data.taxDetails.base_amount_currency),
            taxes: data.taxDetails.subtotals[0]?.tax_groups?.map((tax) => ({
                name: tax.group_name,
                amount: this.formatCurrency(tax.tax_amount),
                amount_base: this.formatCurrency(tax.base_amount_currency),
            })),
        };
    }

    generateQrCode(value) {
        if (!value) {
            return null;
        }
        return generateQRCodeDataUrl(value);
    }

    generateLineData() {
        return this.order.lines.map((line) => {
            const productData = { ...line.product_id.raw };
            productData.display_name = line.getFullProductName();

            return {
                ...line.raw,
                product_data: productData,
                product_uom_name: line.product_id.uom_id?.name || "",
                unit_price: line.currencyDisplayPriceUnit,
                product_unit_price: line.product_id.displayPriceUnit,
                price_subtotal_incl: line.currencyDisplayPrice,
                lot_names: line.pack_lot_ids?.length
                    ? line.pack_lot_ids.map((l) => l.lot_name)
                    : false,
            };
        });
    }

    generatePaymentData() {
        return this.order.payment_ids.map((line) => ({
            ...line.raw,
            payment_method_data: { name: line.payment_method_id?.name || "" },
            amount: this.formatCurrency(line.amount),
        }));
    }

    generateData() {
        const baseUrl = this.order.config._base_url;
        const company = this.order.company;
        const url = `${baseUrl}/pos/ticket?order_uuid=${this.order.uuid}`;
        const useQrCode = company.point_of_sale_ticket_portal_url_display_mode !== "url";
        const useTips = this.config.set_tip_after_payment && this.order.displayPrice > 0;
        const tipsConfiguration = {
            15: this.formatCurrency(this.order.displayPrice * 0.15),
            20: this.formatCurrency(this.order.displayPrice * 0.2),
            25: this.formatCurrency(this.order.displayPrice * 0.25),
        };

        return {
            order: this.order.raw,
            config: this.order.config.raw,
            company: this.order.company.raw,
            partner: this.order.partner_id ? this.order.partner_id.raw : false,
            preset: this.order.preset_id ? this.order.preset_id.raw : false,
            lines: this.generateLineData(),
            payments: this.generatePaymentData(),
            image: {
                invoice_qr_code: useQrCode ? this.generateQrCode(url) : false,
                logo: this.order.config.uiState.receiptLogoDataUrl,
            },
            conditions: {
                basic_receipt: this.basicReceipt,
                display_vat: this.order.config._IS_VAT,
                display_qr_code: useQrCode,
                display_url: company.point_of_sale_ticket_portal_url_display_mode != "qr_code",
                use_self_invoicing: company.point_of_sale_use_ticket_qr_code,
                module_pos_restaurant: this.order.config.module_pos_restaurant,
            },
            extra_data: {
                tips_configuration: useTips ? tipsConfiguration : false,
                preset_datetime: this.order.presetDateTime,
                partner_vat_label: company.country_id.vat_label || "Tax ID",
                self_invoicing_url: `${baseUrl}/pos/ticket`,
                prices: this.generateTaxeData(),
                cashier_name: this.order.getCashierName(),
                company_state_name: company.state_id?.name || "",
                company_country_name: company.country_id?.name || "",
                formated_date_order: this.order.formatDateOrTime("date_order", "datetime"),
            },
        };
    }

    generateHtml() {
        const data = this.generateData();
        return renderToElement("point_of_sale.pos_order_receipt", data);
    }

    async generateImage() {
        const container = document.getElementById("receipt-iframe-container");
        const iframe = document.createElement("iframe");
        const el = this.generateHtml();
        iframe.style.width = "100%";
        iframe.style.height = "100%";
        iframe.style.border = "none";
        iframe.srcdoc = el.outerHTML;
        container.appendChild(iframe);

        // Wait for iframe to be ready
        await new Promise((resolve) => (iframe.onload = resolve));
        const doc = iframe.contentDocument || iframe.contentWindow.document;
        const iframeEl = doc.getElementById("pos-receipt");
        const sizes = iframeEl.getBoundingClientRect();
        try {
            return await toCanvas(iframeEl, {
                backgroundColor: "#ffffff",
                height: Math.ceil(sizes.height),
                width: Math.ceil(sizes.width),
                pixelRatio: 1,
            });
        } finally {
            iframe.remove();
        }
    }
}
