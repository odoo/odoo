import { _t } from "@web/core/l10n/translation";
import { InvoiceButton } from "@point_of_sale/app/screens/ticket_screen/invoice_button/invoice_button";
import { patch } from "@web/core/utils/patch";

patch(InvoiceButton.prototype, {
    async _downloadInvoice(orderId) {
        const orderWithInvoice = await this.pos.data.read("pos.order", [orderId], [], {
            load: false,
        });
        const order = orderWithInvoice[0];
        if (
            this.pos.isVietnamCompany() &&
            order.l10n_vn_sinvoice_state == "sent" &&
            !order.l10n_vn_has_sinvoice_pdf &&
            order.raw.account_move
        ) {
            await this.pos.data.call("account.move", "l10n_vn_edi_fetch_invoice_files", [
                order.raw.account_move,
            ]);
        }
        return await super._downloadInvoice(...arguments);
    },
    get commandName() {
        if (this.pos.isVietnamCompany() && this.pos.config.l10n_vn_auto_send_to_sinvoice) {
            const name = super.commandName;
            return name == _t("Reprint Invoice") ? _t("Print Tax Invoice") : name;
        }
        return super.commandName;
    },
});
