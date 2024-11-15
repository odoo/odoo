import { Plugin } from "@html_editor/plugin";
import { BuilderOverlay } from "./builder_overlay";

export class BuilderOverlayPlugin extends Plugin {
    static id = "builder_overlay";
    static dependencies = ["selection", "overlay"];
    static resources = (p) => ({
        change_selected_toolboxes_listeners: p.openBuilderOverlay.bind(p),
    });

    setup() {
        this.overlay = this.dependencies.overlay.createOverlay(BuilderOverlay, {
            positionOptions: {
                position: "center",
            },
        });
    }

    destroy() {
        this.removeCurrentOverlay?.();
    }

    openBuilderOverlay(toolboxes) {
        const toolbox = toolboxes[0];
        this.removeCurrentOverlay?.();
        if (!toolbox) {
            return;
        }
        this.removeCurrentOverlay = this.services.overlay.add(BuilderOverlay, {
            target: toolbox.element,
            container: this.document.documentElement,
        });
    }
}
