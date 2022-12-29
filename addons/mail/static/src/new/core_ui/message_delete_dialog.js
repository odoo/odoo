/* @odoo-module */

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class MessageDeleteDialog extends Component {
    static components = { Dialog };
    static props = ["close", "message", "messageComponent"];
    static template = "mail.MessageDeleteDialog";

    setup() {
        /** @type {import("@mail/new/core/message_service").MessageService} */
        this.messageService = useState(useService("mail.message"));
        this.title = _t("Confirmation");
    }

    onClickDelete() {
        this.messageService.delete(this.props.message);
        this.props.close();
    }
}
