import { MailComposerBccPopover } from "@mail/core/web/mail_composer_bcc_list_popover";

import { Component, markup } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { registry } from "@web/core/registry";
import { htmlFormatList } from "@web/core/utils/html";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class MailComposerBccList extends Component {
    static template = "mail.MailComposerBccList";
    static components = {};
    static props = { ...standardFieldProps };

    setup() {
        this.limit = 5;
        this.popover = usePopover(MailComposerBccPopover);
    }

    /** @returns {Markup} */
    getRecipientListToHTML() {
        const elements = [];
        const records = this.getRecords();
        for (const record of records.slice(0, this.limit)) {
            const partner = record.data;
            elements.push(
                markup`<span class="text-muted" title="${
                    partner.email_normalized || _t("no email address")
                }">${partner.name}</span>`
            );
        }
        if (records.length > this.limit) {
            elements.push(
                _t("%(recipientCount)s more", {
                    recipientCount: records.length - this.limit,
                })
            );
        }
        return htmlFormatList(elements);
    }

    /** @returns {Array[Record]} */
    getRecords() {
        return this.props.record.data[this.props.name].records;
    }

    /** @returns {boolean} */
    hasRecipients() {
        return this.getRecords().length > 0;
    }

    /** @returns {boolean} */
    hasMoreRecipients() {
        return this.getRecords().length > this.limit;
    }

    /** @param {Event} event */
    onClickRecipientList(event) {
        if (this.popover.isOpen) {
            return this.popover.close();
        }
        this.popover.open(event.target, {
            records: this.getRecords(),
        });
    }
}

export const mailComposerBccList = {
    component: MailComposerBccList,
    relatedFields: (fieldInfo) => [
        { name: "name", type: "char" },
        { name: "email_normalized", type: "char" },
    ],
};

registry.category("fields").add("mail_composer_bcc_list", mailComposerBccList);
