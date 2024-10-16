import { Plugin } from "@html_editor/plugin";
import { BuilderOverlay } from "./builder_overlay";

export class BuilderOverlayPlugin extends Plugin {
    static name = "builder_overlay";
    static resources = (p) => ({
        onSelectionChange: p.onSelectionChange.bind(p),
    });
    static dependencies = ["selection", "overlay"];

    setup() {
        this.selectors = [".row > div", "div[data-name]", "section"];
        this.overlay = this.shared.createOverlay(BuilderOverlay, {
            positionOptions: {
                position: "center",
            },
        });
        this.addDomListener(this.editable, "pointerup", (e) => {
            if (!this.shared.getEditableSelection().isCollapsed) {
                return;
            }
            this.changeSnippet(e.target);
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
        this.changeSnippet(selectionNode);
    }

    findSnippetElementFromTarget(target) {
        for (const selector of this.selectors) {
            const snippetElement = target.closest(selector);
            if (snippetElement) {
                return snippetElement;
            }
        }
    }

    changeSnippet(selectedElement) {
        const snippetElement = this.findSnippetElementFromTarget(selectedElement);
        this.openBuilderOverlay(snippetElement);
        for (const handler of this.resources.onSnippetChange || []) {
            handler(snippetElement);
        }
        return;
    }

    openBuilderOverlay(target) {
        this.removeCurrentOverlay?.();
        this.removeCurrentOverlay = this.services.overlay.add(BuilderOverlay, {
            target,
            container: this.document.documentElement,
        });
    }
}
