import { MailComposerBccPopover } from "@mail/core/web/mail_composer_bcc_list_popover";
import { usePopover } from "@web/core/popover/popover_hook";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { escape } from "@web/core/utils/strings";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { markup, Component } from "@odoo/owl";

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
            elements.push(`
                <span class="text-muted" title="${escape(
                    partner.email_normalized || _t("no email address")
                )}"> ${escape(partner.name)}</span>
            `);
        }
        return markup(elements);
    }

    getRecipientCount() {
        const records = this.getRecords();
        if (records.length > this.limit) {
            return escape(
                _t(" out of %(recipientCount)s", {
                    recipientCount: records.length,
                })
            );
        }
        return "";
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
    relatedFields: (fieldInfo) => {
        return [
            { name: "name", type: "char" },
            { name: "email_normalized", type: "char" },
        ];
    },
};

registry.category("fields").add("mail_composer_bcc_list", mailComposerBccList);
