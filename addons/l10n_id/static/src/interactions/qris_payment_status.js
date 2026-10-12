import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class QrisPaymentStatus extends Interaction {
    static selector = "#invoice_content[data-l10n-id-qris-invoice-id]";

    setup() {
        // QRIS codes are valid for 30 minutes
        this.deadline = Date.now() + 30 * 60 * 1000;
        this.schedulePoll();
    }

    destroy() {
        clearTimeout(this.pollTimeout);
    }

    schedulePoll() {
        if (Date.now() < this.deadline) {
            this.pollTimeout = this.waitForTimeout(() => this.poll(), 5000);
        }
    }

    async poll() {
        const { l10nIdQrisInvoiceId, accessToken } = this.el.dataset;
        const paid = await this.waitFor(
            rpc(`/l10n_id/qris/status/${l10nIdQrisInvoiceId}`, { access_token: accessToken }, { silent: true })
        ).catch(() => false);
        if (paid) {
            // The payment is registered, reload to display the paid status
            window.location.reload();
        } else {
            this.schedulePoll();
        }
    }
}

registry.category("public.interactions").add("l10n_id.qris_payment_status", QrisPaymentStatus);
