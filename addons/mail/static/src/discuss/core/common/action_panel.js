import { attClassObjectToString } from "@mail/utils/common/format";
import { Component, useSubEnv } from "@odoo/owl";
import { ResizablePanel } from "@web/core/resizable_panel/resizable_panel";
import { useForwardRefToParent, useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @prop {string} title
 * @prop {Object} [slots]
 * @extends {Component<Props, Env>}
 */
export class ActionPanel extends Component {
    static template = "mail.ActionPanel";
    static components = { ResizablePanel };
    static props = [
        "contentRef?",
        "icon?",
        "title?",
        "resizable?",
        "slots?",
        "initialWidth?",
        "minWidth?",
    ];
    static defaultProps = { contentPadding: true, resizable: true };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.ui = useService("ui");
        useForwardRefToParent("contentRef");
        useSubEnv({ inDiscussActionPanel: true });
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
