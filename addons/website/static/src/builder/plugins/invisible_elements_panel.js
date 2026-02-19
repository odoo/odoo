import { Component, useState } from "@odoo/owl";
import { getSnippetName } from "@html_builder/utils/utils";

export class InvisibleElementsPanel extends Component {
    static template = "html_builder.InvisibleElementsPanel";
    static props = {
        /** entry: { el, toggleInvisibleEntry, visible, children } */
        state: { type: Object, shape: { invisibleEntries: { type: Array } } },
    };

    setup() {
        this.state = useState(this.props.state);
        this.getSnippetName = getSnippetName;
    }

    getEntries() {
        return this.state.invisibleEntries;
    }
}
