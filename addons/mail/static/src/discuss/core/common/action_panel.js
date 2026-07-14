import { Component, useState } from "@odoo/owl";
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
        this.store = useState(useService("mail.store"));
    }

    get classNames() {
        return `o-mail-ActionPanel overflow-auto d-flex flex-column flex-shrink-0 position-relative py-2 pt-0 h-100 bg-inherit ${
            !this.env.inChatter ? " px-2" : " o-mail-ActionPanel-chatter"
        } ${this.env.inDiscussApp ? " o-mail-discussSidebarBgColor" : ""}`;
    }
}
