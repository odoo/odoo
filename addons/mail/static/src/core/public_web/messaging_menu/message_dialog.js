import { Message } from "@mail/core/common/message";

import { propComputed } from "@mail/utils/common/hooks";

import { Component, props, t } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class MessageDialog extends Component {
    static components = { Dialog, Message };
    static template = "mail.MessageDialog";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.message = propComputed("message", t.instanceOf(this.store["mail.message"].Class));
        this.close = props.static("close", t.function([]));
    }

    get title() {
        return this.message().thread?.displayName ?? _t("Message");
    }
}
