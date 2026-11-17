import { Component, useProps, t } from "@odoo/owl";
import { getSnippetName } from "@html_builder/utils/utils";

export class InvisibleElementsPanel extends Component {
    static template = "html_builder.InvisibleElementsPanel";
    props = useProps({
        /** entry: { el, toggleInvisibleEntry, visible, children } */
        state: t.object({ invisibleEntries: t.array() }),
    });

    setup() {
        this.getSnippetName = getSnippetName;
    }

    getEntries() {
        return this.props.state.invisibleEntries;
    }
}
