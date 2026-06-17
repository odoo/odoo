import { useSubEnv } from "@web/owl2/utils";
import { attClassObjectToString } from "@mail/utils/common/format";
import { Component, props, signal, t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { ResizablePanel } from "@web/core/resizable_panel/resizable_panel";
import { useBackButton, useService } from "@web/core/utils/hooks";

export class ActionPanel extends Component {
    static template = "mail.ActionPanel";
    static components = { ResizablePanel };
    setup() {
        super.setup();
        this.props = props({
            close: t.function([]).optional(),
            contentPadding: t.boolean().optional(true),
            contentRef: t.signal(t.instanceOf(HTMLDivElement)).optional(() => signal.ref()),
            icon: t.string().optional(),
            initialWidth: t.number().optional(),
            minWidth: t.number().optional(),
            resizable: t.boolean().optional(true),
            slots: t.object().optional(),
            title: t.string().optional(),
        });
        this.store = useService("mail.store");
        this.ui = useService("ui");
        useSubEnv({ inDiscussActionPanel: true });
        useBackButton(
            () => this.props.close(),
            () => this.props.close
        );
    }

    get backButtonTitle() {
        return this.env.hasPreviousActionPanel?.()
            ? _t("Back to previous panel")
            : _t("Close panel");
    }

    get classNames() {
        return attClassObjectToString({
            "o-mail-ActionPanel overflow-auto o-scrollbar-thin d-flex flex-column flex-shrink-0 position-relative py-2 pt-0 h-100 bg-inherit": true,
            "o-mail-ActionPanel-chatter": this.env.inChatter,
            "o-chatWindow": this.env.inChatWindow,
            "px-2": !this.env.inChatter && !this.env.inMeetingChat,
            rounded: !this.props.resizable,
        });
    }

    get minWidth() {
        return this.props.minWidth;
    }

    get initialWidth() {
        return this.props.initialWidth;
    }
}
