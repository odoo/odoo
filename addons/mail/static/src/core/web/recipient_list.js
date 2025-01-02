import { useVisible } from "@mail/utils/common/hooks";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";

/**
 * @typedef {Object} Props
 * @property {import('@mail/core/common/thread_model').Thread} thread
 * @property {function} [close]
 * @extends {Component<Props, Env>}
 */
export class RecipientList extends Component {
    static template = "mail.RecipientList";
    static props = ["thread", "close?"];

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.loadMoreState = useVisible("load-more", () => {
            if (this.loadMoreState.isVisible) {
                this.props.thread.loadMoreRecipients();
            }
        });
    }

    getRecipientText(recipient) {
        return (
            recipient.partner.email ||
            sprintf(_t("[%(name)s] (no email address)"), { name: recipient.partner.name })
        );
    }
}
