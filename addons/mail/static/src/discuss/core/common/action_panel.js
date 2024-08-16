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
        title: { type: String, optional: true },
        resizable: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        resizable: true,
    };

    get classNames() {
        return `o-mail-ActionPanel overflow-auto d-flex flex-column flex-shrink-0 position-relative py-3 pt-0 h-100 ${
            !this.env.inChatter ? " px-3 bg-view" : " o-mail-ActionPanel-chatter"
        }`;
    }
}
