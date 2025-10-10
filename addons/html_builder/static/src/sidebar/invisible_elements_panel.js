import { Component, EventBus, useState } from "@odoo/owl";
import { getSnippetName } from "@html_builder/utils/utils";
import { useBus } from "@web/core/utils/hooks";

export class InvisibleElementsPanel extends Component {
    static template = "html_builder.InvisibleElementsPanel";
    static props = {
        /** entry:
         * - el
         * - toggle
         * - visible
         * - children
         */
        getEntries: Function,
        invalidateEntriesBus: EventBus,
    };

    setup() {
        this.state = useState({ invisibleEntries: null });
        useBus(
            this.props.invalidateEntriesBus,
            "INVALIDATE_INVISIBLE_ENTRIES",
            () => (this.state.invisibleEntries = null)
        );
        this.getSnippetName = getSnippetName;
    }

    getEntries() {
        if (this.state.invisibleEntries === null) {
            this.state.invisibleEntries = this.props.getEntries();
        }
        return this.state.invisibleEntries;
    }
}
