import { Thread } from "@mail/core/common/thread_model";
import { RecipientList } from "@mail/core/web/recipient_list";

import { Component, markup } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { htmlFormatList } from "@web/core/utils/html";

export class BaseRecipientsList extends Component {
    static template = "mail.BaseRecipientsList";
    static components = {};
    static props = { thread: { type: Thread } };

    setup() {
        this.recipientsPopover = usePopover(RecipientList);
    }

    /** @returns {Markup} */
    getRecipientListToHTML() {
        const recipients = this.props.thread.recipients
            .slice(0, 5)
            .map(
                ({ partner }) =>
                    markup`<span class="text-muted" title="${
                        partner.email || _t("no email address")
                    }">${partner.name}</span>`
            );
        if (this.props.thread.recipients.length > 5) {
            recipients.push(
                _t("%(recipientCount)s more", {
                    recipientCount: this.props.thread.recipients.length - 5,
                })
            );
        }
        return htmlFormatList(recipients);
    }

    /** @param {Event} ev */
    onClickRecipientList(ev) {
        if (this.recipientsPopover.isOpen) {
            return this.recipientsPopover.close();
        }
        this.recipientsPopover.open(ev.target, {
            thread: this.props.thread,
        });
    }
}
