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
    }

    onSelectionChange(selection) {
        let selectionNode = selection.editableSelection.commonAncestorContainer;
        if (selectionNode.nodeType === Node.TEXT_NODE) {
            selectionNode = selectionNode.parentElement;
        }

        for (const selector of this.selectors) {
            const snippetElement = selectionNode.closest(selector);
            if (snippetElement) {
                this.openBuilderOverlay(snippetElement);
                for (const handler of this.resources.onSnippetChange || []) {
                    handler(snippetElement);
                }
                return;
            }
        }
    }

    openBuilderOverlay(target) {
        this.removeCurrentOverlay?.();
        this.removeCurrentOverlay = this.services.overlay.add(BuilderOverlay, {
            target,
            container: this.document.documentElement,
        });
    }
}
