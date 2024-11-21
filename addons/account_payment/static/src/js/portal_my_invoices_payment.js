/** @odoo-module **/

import {_t} from "@web/core/l10n/translation";
import {deserializeDateTime} from "@web/core/l10n/dates";
import publicWidget from "@web/legacy/js/public/public_widget";

const {DateTime} = luxon;

publicWidget.registry.PortalMyInvoicesPaymentList = publicWidget.Widget.extend({
    selector: ".o_portal_my_doc_table",

    start() {
        this._setDueDateLabel();
        return this._super(...arguments);
    },

    _setDueDateLabel() {
        const dueDateLabels = this.el.querySelectorAll(".o_portal_invoice_due_date");
        const today = DateTime.now().startOf("day");
        dueDateLabels.forEach((label) => {
            const dateTime = deserializeDateTime(label.getAttribute("datetime")).startOf('day');
            const diff = dateTime.diff(today).as("days");

            let dueDateLabel = "";

            if (diff === 0) {
                dueDateLabel = _t("due today");
            } else if (diff > 0) {
                dueDateLabel = _t("due in %s day(s)", Math.abs(diff).toFixed());
            } else {
                dueDateLabel = _t("%s day(s) overdue", Math.abs(diff).toFixed());
            }
            // We use `.createTextNode()` to escape possible HTML in translations (XSS)
            label.replaceChildren(document.createTextNode(dueDateLabel));
        });
    },
});
