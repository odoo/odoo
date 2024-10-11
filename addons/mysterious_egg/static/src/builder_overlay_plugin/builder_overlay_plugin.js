import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BuilderOverlay } from "./builder_overlay";

export class BuilderOverlayPlugin extends Plugin {
    static name = "builder_overlay";
    static resources = (p) => ({
        onSelectionChange: p.onSelectionChange.bind(p),
    });
    static dependencies = ["selection", "overlay"];

    setup() {
        this.selectors = ["img", "div[data-name]", "section"];
        console.log("initialized");
    }

    onSelectionChange(selection) {
        let selectionNode = selection.editableSelection.commonAncestorContainer;
        if (selectionNode.nodeType === Node.TEXT_NODE) {
            selectionNode = selectionNode.parentElement;
        }

        for (const selector of this.selectors) {
            const overlaySelector = selectionNode.closest(selector);
            if (overlaySelector) {
                this.openBuilderOverlay(overlaySelector);
                return;
            }
        }
    }

    openBuilderOverlay(target) {
        //  NOT WORKING and in WIP: use overlay service instead
        if (registry.category("main_components").contains("BuilderOverlay")) {
            registry.category("main_components").remove("BuilderOverlay");
        }
        registry.category("main_components").add("BuilderOverlay", {
            Component: BuilderOverlay,
            props: {
                target,
            },
        });
    }

    destroy() {
        registry.category("main_components").remove("BuilderOverlay");
    }
}
