import { useSubEnv } from "@web/owl2/utils";
import { attClassObjectToString } from "@mail/utils/common/format";
import { Component, signal, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { ResizablePanel } from "@web/core/resizable_panel/resizable_panel";
import { useBackButton, useService } from "@web/core/utils/hooks";

export class ActionPanel extends Component {
    static template = "mail.ActionPanel";
    static components = { ResizablePanel };
    setup() {
        super.setup();
        this.props = useProps({
            close: t.function([]).optional(),
            contentPadding: t.boolean().optional(true),
            icon: t.string().optional(),
            iconClass: t.string().optional(),
            initialWidth: t.number().optional(),
            minWidth: t.number().optional(),
            resizable: t.boolean().optional(true),
            title: t.string().optional(),
        });
        /** Content element, either owned by the parent (`contentRef` prop) or local. */
        this.contentRef = useProps.static(
            "contentRef",
            t.signal(t.instanceOf(HTMLDivElement)).optional(() => signal.ref())
        );
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
            "o-mail-ActionPanel overflow-auto scrollbar-width-thin d-flex flex-column flex-shrink-0 position-relative py-2 pt-0 h-100 bg-inherit": true,
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
