import { Message } from "@mail/core/common/message";

import { propComputed, propStatic, usePropsPlus } from "@mail/utils/common/hooks";

import { Component, t } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class MessageInDialog extends Component {
    static components = { Dialog, Message };
    static template = "mail.MessageInDialog";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = usePropsPlus({
            close: propStatic(t.function([])),
            message: propComputed(t.instanceOf(this.store["mail.message"])),
        });
    }

    get title() {
        return this.props.message().thread?.displayName ?? _t("Message");
    }
}
