import { Component } from "@odoo/owl";
import { ResizablePanel } from "@web/core/resizable_panel/resizable_panel";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @prop {string} title
 * @prop {Object} [slots]
 * @extends {Component<Props, Env>}
 */
export class ActionPanel extends Component {
    static template = "mail.ActionPanel";
    static components = { ResizablePanel };
    static props = ["icon?", "title?", "resizable?", "slots?", "initialWidth?", "minWidth?"];
    static defaultProps = { resizable: true };

    setup() {
        super.setup();
        this.store = useService("mail.store");
    }

    get classNames() {
        const attClass = {
            "o-mail-ActionPanel overflow-auto o-scrollbar-thin d-flex flex-column flex-shrink-0 position-relative py-2 pt-0 h-100 bg-inherit": true,
            "o-mail-ActionPanel-chatter": this.env.inChatter,
            "o-chatWindow": this.env.inChatWindow,
            "px-2": !this.env.inChatter,
            "rounded-4": !this.props.resizable,
            "rounded-4 shadow-sm": this.env.inDiscussApp,
        };
        return Object.entries(attClass)
            .filter(([classNames, value]) => value)
            .map(([classNames]) => classNames)
            .join(" ");
    }
}
