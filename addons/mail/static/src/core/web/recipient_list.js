import { useVisible } from "@mail/utils/common/hooks";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {Object} Props
 * @property {import('@mail/core/common/thread_model').Thread} thread
 * @property {function} [close]
 * @extends {Component<Props, Env>}
 * @deprecated Will be removed in master
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
        return recipient.partner.email
            ? _t("%(name)s <%(email)s>", {
                  name: recipient.partner.name,
                  email: recipient.partner.email,
              })
            : recipient.partner.name;
    }
}
