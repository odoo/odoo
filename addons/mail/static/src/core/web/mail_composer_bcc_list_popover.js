import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";


export class MailComposerBccPopover extends Component {
    static template = "mail.MailComposerBccPopover";
    static props = ["records", "close?"];

    /**
     * @param {Record} record
     * @returns {string}
     **/
    getRecipientText(record) {
        return _t("%(name)s <%(email)s>", {
            name: record.data.name,
            email: record.data.email_normalized
        });
    }
}
