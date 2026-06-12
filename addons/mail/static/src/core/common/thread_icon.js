import { useService } from "@web/core/utils/hooks";

import { Component, props, t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { ImStatus } from "./im_status";
import { attClassObjectToString } from "@mail/utils/common/format";

export class ThreadIcon extends Component {
    static template = "mail.ThreadIcon";
    static components = { ImStatus };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = props({
            className: t.string().optional(""),
            size: t.selection(["small", "medium", "large"]).optional("medium"),
            thread: t.instanceOf(this.store["mail.thread"].Class),
            title: t.boolean().optional(true),
            typing: t.boolean().optional(),
        });
        this.attClassObjectToString = attClassObjectToString;
    }

    get channel() {
        return this.props.thread.channel;
    }

    get correspondent() {
        return this.channel?.correspondent;
    }

    get defaultChatIcon() {
        return {
            class: "fa fa-question-circle opacity-75",
            title: _t("No IM status available"),
        };
    }
}
