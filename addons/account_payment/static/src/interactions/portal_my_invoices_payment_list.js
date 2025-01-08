import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";

const { DateTime } = luxon;

export class PortalMyInvoicesPaymentList extends Interaction {
    static selector = ".o_portal_my_doc_table";

    start() {
        const today = DateTime.now().startOf("day");
        const dueDateEls = this.el.querySelectorAll(".o_portal_invoice_due_date");
        for (const dueDateEl of dueDateEls) {
            const dateTime = deserializeDateTime(dueDateEl.getAttribute("datetime")).startOf('day');
            const diff = dateTime.diff(today).as("days");

            const dueDateLabel =
                (diff === 0) ? _t("due today") :
                    (diff > 0)
                        ? _t("due in %s day(s)", Math.abs(diff).toFixed())
                        : _t("%s day(s) overdue", Math.abs(diff).toFixed());

            // We use `.createTextNode()` to escape possible HTML in translations (XSS)
            dueDateEl.replaceChildren(document.createTextNode(dueDateLabel));
        }
    }
}

registry
    .category("public.interactions")
    .add("account_payment.portal_my_invoices_payment_list", PortalMyInvoicesPaymentList);
