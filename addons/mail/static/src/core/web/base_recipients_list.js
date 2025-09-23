import { _t } from "@web/core/l10n/translation";
import { escape } from "@web/core/utils/strings";
import { formatList } from "@web/core/l10n/utils";
import { markup, Component } from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";

import { RecipientList } from "@mail/core/web/recipient_list";
import { SuggestedRecipientsList } from "@mail/core/web/suggested_recipient_list";
import { Thread } from "@mail/core/common/thread_model";


export class BaseRecipientsList extends Component {
    static template = "mail.BaseRecipientsList";
    static components = { SuggestedRecipientsList };
    static props = { thread: { type: Thread } };

    setup() {
        this.recipientsPopover = usePopover(RecipientList);
    }

    /** @returns {Markup} */
    getRecipientListToHTML() {
        const recipients = this.props.thread.recipients.slice(0, 5).map((
            { partner, displayName }) => {
                const text = (partner.email && partner.emailWithoutDomain) || displayName;
                return `<span class="text-muted" title="${escape(
                    partner.email || _t("no email address")
                )}">${escape(text)}</span>`;
            });
        if (this.props.thread.recipients.length > 5) {
            recipients.push(escape(
                _t("%(recipientCount)s more", {
                    recipientCount: this.props.thread.recipients.length - 5}))
            );
        }
        return markup(formatList(recipients));
    }

    /** @param {Event} ev */
    onClickRecipientList(ev) {
        if (this.recipientsPopover.isOpen) {
            return this.recipientsPopover.close();
        }
        this.recipientsPopover.open(ev.target, {
            thread: this.props.thread
        });
    }
};
