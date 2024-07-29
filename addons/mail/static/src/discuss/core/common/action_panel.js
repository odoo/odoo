import { Component } from "@odoo/owl";
import { ResizablePanel } from "@web/core/resizable_panel/resizable_panel";

/**
 * @typedef {Object} Props
 * @prop {string} title
 * @prop {Object} [slots]
 * @extends {Component<Props, Env>}
 */
export class ActionPanel extends Component {
    static template = "mail.ActionPanel";
    static components = { ResizablePanel };
    static props = {
        className: { type: String, optional: true },
        title: { type: String, optional: true },
        resizable: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        resizable: true,
    };

    get attClass() {
        return {
            "o-mail-ActionPanel overflow-auto d-flex flex-column flex-shrink-0 position-relative h-100": true,
            [this.props.className]: true,
            "o-mail-inspectorBg": !this.env.inChatter,
            "o-mail-ActionPanel-chatter": this.env.inChatter,
        };
    }

    get classNames() {
        return Object.entries(this.attClass)
            .filter(([key, val]) => val)
            .map(([key]) => key)
            .join(" ");
    }
}
