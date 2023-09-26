/* @odoo-module */

import { PosModel, PosCollection } from "@point_of_sale/app/base_models/base";
import { formatDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { uuidv4 } from "@point_of_sale/utils";
import { roundPrecision } from "@web/core/utils/numbers";

const { DateTime } = luxon;

export class BaseOrder extends PosModel {
    setup() {
        super.setup(...arguments);
        const pos_session = this.env.cache.pos_session;
        this.orderlines = new PosCollection();
        this.paymentlines = new PosCollection();
        this.partner = null;
        this.state = null;
        this.date_order = DateTime.now();
        this.pricelist = this.env.cache.default_pricelist;
        this.sequence_number = pos_session.sequence_number++;
        this.access_token = uuidv4(); // unique uuid used to identify the authenticity of the request from the QR code.
        this.ticketCode = this._generateTicketCode(); // 5-digits alphanum code shown on the receipt
        this.uid = this.generate_unique_id();
        this.name = _t("Order %s", this.uid);
        this.fiscal_position = this.env.cache.fiscal_positions.find((fp) => {
            return fp.id === this.env.cache.config.default_fiscal_position_id[0];
        });
    }

    generate_unique_id() {
        // Generates a public identification number for the order.
        // The generated number must be unique and sequential. They are made 12 digit long
        // to fit into EAN-13 barcodes, should it be needed
        function zero_pad(num, size) {
            var s = "" + num;
            while (s.length < size) {
                s = "0" + s;
            }
            return s;
        }
        return (
            zero_pad(this.env.cache.pos_session.id, 5) +
            "-" +
            zero_pad(this.env.cache.pos_session.login_number, 3) +
            "-" +
            zero_pad(this.sequence_number, 4)
        );
    }

    get_orderlines() {
        return this.orderlines;
    }

    get_paymentlines() {
        return this.paymentlines;
    }

    get_name() {
        return this.name;
    }

    get_subtotal() {
        return roundPrecision(
            this.orderlines.reduce((sum, orderLine) => {
                return sum + orderLine.get_display_price();
            }, 0),
            this.env.cache.currency.rounding
        );
    }

    get_total_tax() {
        if (this.env.cache.company.tax_calculation_rounding_method === "round_globally") {
            // As always, we need:
            // 1. For each tax, sum their amount across all order lines
            // 2. Round that result
            // 3. Sum all those rounded amounts
            const groupTaxes = {};
            this.orderlines.forEach((line) => {
                const taxDetails = line.get_tax_details();
                const taxIds = Object.keys(taxDetails);
                for (let t = 0; t < taxIds.length; t++) {
                    const taxId = taxIds[t];
                    if (!(taxId in groupTaxes)) {
                        groupTaxes[taxId] = 0;
                    }
                    groupTaxes[taxId] += taxDetails[taxId].amount;
                }
            });

            let sum = 0;
            const taxIds = Object.keys(groupTaxes);
            for (let j = 0; j < taxIds.length; j++) {
                const taxAmount = groupTaxes[taxIds[j]];
                sum += roundPrecision(taxAmount, this.env.cache.currency.rounding);
            }
            return sum;
        } else {
            return roundPrecision(
                this.orderlines.reduce((sum, orderLine) => {
                    return sum + orderLine.get_tax();
                }, 0),
                this.env.cache.currency.rounding
            );
        }
    }

    get_total_without_tax() {
        return roundPrecision(
            this.orderlines.reduce((sum, line) => {
                return sum + line.get_price_without_tax();
            }, 0),
            this.env.cache.currency.rounding
        );
    }

    get_total_with_tax() {
        return this.get_total_without_tax() + this.get_total_tax();
    }

    get_tax_details() {
        const details = {};
        const fulldetails = [];

        this.orderlines.forEach((line) => {
            const ldetails = line.get_tax_details();
            for (const id in ldetails) {
                if (Object.hasOwnProperty.call(ldetails, id)) {
                    details[id] = {
                        amount: (details[id]?.amount || 0) + ldetails[id].amount,
                        base: (details[id]?.base || 0) + ldetails[id].base,
                    };
                }
            }
        });

        for (const id in details) {
            if (Object.hasOwnProperty.call(details, id)) {
                fulldetails.push({
                    amount: details[id].amount,
                    base: details[id].base,
                    tax: this.env.cache.taxes_by_id[id],
                    name: this.env.cache.taxes_by_id[id].name,
                });
            }
        }

        return fulldetails;
    }

    _make_qr_code_data(url) {
        const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
        const qr_code_svg = new XMLSerializer().serializeToString(codeWriter.write(url, 150, 150));
        return "data:image/svg+xml;base64," + window.btoa(qr_code_svg);
    }

    _get_qr_code_data() {
        if (this.env.cache.company.point_of_sale_use_ticket_qr_code) {
            // Use the unique access token to ensure the authenticity of the request. Use the order reference as a second check just in case.
            return this._make_qr_code_data(
                `${this.env.cache.base_url}/pos/ticket/validate?access_token=${this.access_token}`
            );
        } else {
            return false;
        }
    }

    /**
     * Returns a random 5 digits alphanumeric code
     * @returns {string}
     */
    _generateTicketCode() {
        let code = "";
        while (code.length != 5) {
            code = Math.random().toString(36).slice(2, 7);
        }
        return code;
    }

    export_for_printing(
        { rounding_applied, total_discount, total_paid, change, logo } = {
            rounding_applied: 0,
            total_discount: 0,
            total_paid: 0,
            change: 0,
        }
    ) {
        const company = this.env.cache.company;

        const receipt = {
            orderlines: this.orderlines.map((line) => line.export_for_printing()),
            // If order is locked (paid), the 'change' is saved as negative payment,
            // and is flagged with is_change = true. A receipt that is printed first
            // time doesn't show this negative payment so we filter it out.
            paymentlines: this.paymentlines
                .filter((payment) => {
                    return !payment.is_change;
                })
                .map((payment) => {
                    return payment.export_for_printing();
                }),
            subtotal: this.get_subtotal(),
            total_with_tax: this.get_total_with_tax(),
            total_rounded: this.get_total_with_tax() + rounding_applied,
            total_without_tax: this.get_total_without_tax(),
            total_tax: this.get_total_tax(),
            total_paid,
            total_discount,
            rounding_applied,
            tax_details: this.get_tax_details(),
            change,
            name: this.get_name(),
            partner: this.partner,
            cashier: this.cashier ? this.cashier.name : null,
            date: {
                localestring: formatDateTime(luxon.DateTime.now()),
                date_order: this.date_order,
            },
            company: {
                email: company.email,
                website: company.website,
                company_registry: company.company_registry,
                contact_address: company.partner_id[1],
                vat: company.vat,
                vat_label: (company.country && company.country.vat_label) || _t("Tax ID"),
                name: company.name,
                phone: company.phone,
                logo,
            },
            currency: this.env.cache.currency,
            pos_qr_code: this._get_qr_code_data(),
            ticket_code: this.ticketCode,
            base_url: this.env.cache.base_url,
        };

        const isHeaderOrFooter = this.env.cache.config.is_header_or_footer;
        receipt.header = (isHeaderOrFooter && this.env.cache.config.receipt_header) || "";
        receipt.footer = (isHeaderOrFooter && this.env.cache.config.receipt_footer) || "";

        if (!receipt.date.localestring && (!this.state || this.state == "draft")) {
            receipt.date.localestring = formatDateTime(DateTime.local());
        }

        return receipt;
    }
}
