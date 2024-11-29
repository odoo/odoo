import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { uniqueId } from "@web/core/utils/functions";

export class BuilderOptionsPlugin extends Plugin {
    static id = "builder-options";
    static dependencies = ["selection", "overlay"];
    static resources = (p) => ({
        onSelectionChange: p.onSelectionChange.bind(p),
    });

    setup() {
        // todo: use resources instead of registry
        this.builderOptions = registry.category("sidebar-element-option").getAll();
        this.addDomListener(this.editable, "pointerup", (e) => {
            if (!this.dependencies.selection.getEditableSelection().isCollapsed) {
                return;
            }
            this.changeSidebarTarget(e.target);
        });
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
        for (const option of this.builderOptions) {
            const { selector } = option;
            const element = selectedElement.closest(selector);
            if (element) {
                if (map.has(element)) {
                    map.get(element).push(option);
                } else {
                    map.set(element, [option]);
                }
            }
        }
        const optionsContainers = [...map]
            .sort(([a], [b]) => {
                return b.contains(a) ? 1 : -1;
            })
            .map(([element, options]) => ({ element, options, id: uniqueId() }));
        for (const handler of this.getResource("change_current_options_containers_listeners")) {
            handler(optionsContainers);
        }
        return;
    }
}
