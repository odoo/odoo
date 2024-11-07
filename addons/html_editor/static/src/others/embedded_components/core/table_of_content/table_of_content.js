import { Component, onWillStart, useState } from "@odoo/owl";
import { TableOfContentManager } from "@html_editor/others/embedded_components/core/table_of_content/table_of_content_manager";

export class EmbeddedTableOfContentComponent extends Component {
    static template = "html_editor.EmbeddedTableOfContent";
    static props = {
        manager: { type: TableOfContentManager },
        readonly: { type: Boolean, optional: true },
    };

    setup() {
        this.state = useState({ toc: this.props.manager.structure, folded: false });
        onWillStart(async () => {
            await this.props.manager.batchedUpdateStructure();
        });
    }

    displayTocHint() {
        return this.state.toc.headings.length < 2 && !this.props.readonly;
    }

    /**
     * @param {Object} heading
     */
    onTocLinkClick(heading) {
        this.props.manager.scrollIntoView(heading);
    }
}

export const tableOfContentEmbedding = {
    name: "tableOfContent",
    Component: EmbeddedTableOfContentComponent,
};

export const readonlyTableOfContentEmbedding = {
    name: "tableOfContent",
    Component: EmbeddedTableOfContentComponent,
    getProps: (host) => {
        return {
            readonly: true,
        };
    },
};
