import { Message } from "@mail/core/common/message";

import { Component, t, useProps } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class MessageInDialog extends Component {
    static components = { Dialog, Message };
    static template = "mail.MessageInDialog";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = useProps({
            close: t.function([]).static(),
            message: t.signal(t.instanceOf(this.store["mail.message"])),
        });
    }

    get title() {
        return this.props.message().thread?.displayName ?? _t("Message");
    }
}
