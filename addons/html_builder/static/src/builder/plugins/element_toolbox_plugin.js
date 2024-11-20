import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class ElementToolboxPlugin extends Plugin {
    static id = "element-toolbox";
    static dependencies = ["selection", "overlay"];
    static resources = (p) => ({
        onSelectionChange: p.onSelectionChange.bind(p),
    });

    setup() {
        // todo: use resources instead of registry
        this.toolboxes = this.getToolboxDefinitions();
        this.addDomListener(this.editable, "pointerup", (e) => {
            if (!this.dependencies.selection.getEditableSelection().isCollapsed) {
                return;
            }
            this.changeSidebarTarget(e.target);
        });
    }

    getToolboxDefinitions() {
        return registry.category("sidebar-element-toolbox").getAll();
    }

    onSelectionChange(selection) {
        if (selection.editableSelection.isCollapsed) {
            // Some elements are not selectable in the editor but still can be
            // a snippet. The selection will be put in the closest selectable element.
            // Therefore if the selection is collapsed, let the pointerup event handle
            return;
        }
        let selectionNode = selection.editableSelection.commonAncestorContainer;
        if (selectionNode.nodeType === Node.TEXT_NODE) {
            selectionNode = selectionNode.parentElement;
        }
        this.changeSidebarTarget(selectionNode);
    }

    changeSidebarTarget(selectedElement) {
        const map = new Map();
        for (const toolbox of this.toolboxes) {
            const { selector } = toolbox;
            const element = selectedElement.closest(selector);
            if (element) {
                map.set(element, toolbox);
            }
        }
        const toolboxes = [...map]
            .sort(([a], [b]) => {
                return b.contains(a) ? 1 : -1;
            })
            .map(([element, toolbox]) => ({ element, toolbox }));
        for (const handler of this.getResource("change_selected_toolboxes_listeners")) {
            handler(toolboxes);
        }
        return;
    }
}
