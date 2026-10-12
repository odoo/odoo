import { ask, makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { EcpayInfoPopup } from "@l10n_tw_edi_ecpay_pos/app/components/popups/ecpay_info_popup";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.company.account_fiscal_country_id?.code === "TW" && this.config.is_ecpay_enabled) {
            if (!this.partner_id && this.config._tw_walk_in_customer) {
                this.update({ partner_id: this.config._tw_walk_in_customer });
            }
            if (this.partner_id) {
                this.l10n_tw_edi_is_b2b = this.partner_id.commercial_partner_id.is_company;
            }
        }
    },

    setPartner(partner) {
        super.setPartner(partner);
        if (this.company.account_fiscal_country_id?.code === "TW" && this.config.is_ecpay_enabled) {
            if (partner) {
                this.setToInvoice(true);
                this.setEcpayInvoiceInfo({ l10n_tw_edi_is_print: true });
                this.l10n_tw_edi_is_b2b = partner.commercial_partner_id.is_company;
            } else {
                this.setToInvoice(false);
                this.setEcpayInvoiceInfo({});
                this.l10n_tw_edi_is_b2b = false;
            }
        }
    },

    setEcpayInvoiceInfo({
        l10n_tw_edi_is_print = false,
        l10n_tw_edi_love_code = false,
        l10n_tw_edi_carrier_type = false,
        l10n_tw_edi_carrier_number = false,
        l10n_tw_edi_carrier_number_2 = false,
    } = {}) {
        this.l10n_tw_edi_is_print = l10n_tw_edi_is_print;
        this.l10n_tw_edi_love_code = l10n_tw_edi_love_code;
        this.l10n_tw_edi_carrier_type = l10n_tw_edi_carrier_type;
        this.l10n_tw_edi_carrier_number = l10n_tw_edi_carrier_number;
        this.l10n_tw_edi_carrier_number_2 = l10n_tw_edi_carrier_number_2;
    },

    get isPrintEcpayInvoice() {
        return (
            this.config.is_ecpay_enabled &&
            this.company.account_fiscal_country_id?.code === "TW" &&
            this.isToInvoice() &&
            this.l10n_tw_edi_is_print &&
            !this.l10n_tw_edi_is_b2b &&
            !this.getOrderlines().some((line) => line.refunded_orderline_id)
        );
    },

    async askAndSetEcpayInvoiceInfo(dialog, { partner = null, isFromPaymentScreen = false } = {}) {
        const orderPartner = partner || this.getPartner();

        const isTwEcpay =
            this.company.account_fiscal_country_id?.code === "TW" &&
            this.config.is_ecpay_enabled &&
            orderPartner &&
            !this.isToInvoice() &&
            !this.getOrderlines().some((line) => line.refunded_orderline_id) &&
            !this.l10n_tw_edi_is_b2b;

        if (!isTwEcpay) {
            this.setEcpayInvoiceInfo({});
            return true;
        }

        let dismiss = false;
        const extraEcpayInfo = await ask(dialog, {
            title: _t("Ecpay Invoicing Confirmation"),
            body: _t("Store in Carrier or Donate?"),
            confirmLabel: _t("Yes"),
            cancelLabel: _t("No"),
            dismiss: () => {
                dismiss = true;
            },
        });

        if (dismiss) {
            return false;
        }

        if (extraEcpayInfo) {
            const payload = await makeAwaitable(dialog, EcpayInfoPopup);

            if (!payload) {
                return false;
            }

            const info = {
                l10n_tw_edi_love_code: payload.loveCode,
                l10n_tw_edi_carrier_type: payload.carrierType,
                l10n_tw_edi_carrier_number: payload.carrierNumber,
                l10n_tw_edi_carrier_number_2: payload.carrierNumber2,
            };

            if (isFromPaymentScreen) {
                this.setEcpayInvoiceInfo(info);
            } else {
                Object.assign(this, info);
            }
        } else {
            if (isFromPaymentScreen) {
                this.setEcpayInvoiceInfo({ l10n_tw_edi_is_print: true });
            } else {
                Object.assign(this, { l10n_tw_edi_is_print: true });
            }
        }
        return true;
    },
});
