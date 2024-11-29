import { Plugin } from "@html_editor/plugin";
import { BuilderOverlay } from "./builder_overlay";

export class BuilderOverlayPlugin extends Plugin {
    static id = "builder_overlay";
    static dependencies = ["selection", "overlay"];
    resources = {
        change_current_options_containers_listeners: this.openBuilderOverlay.bind(this),
    };

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

    openBuilderOverlay(optionsContainers) {
        const optionContainer = optionsContainers[0];
        this.removeCurrentOverlay?.();
        if (!optionContainer) {
            return;
        }
        this.removeCurrentOverlay = this.services.overlay.add(BuilderOverlay, {
            target: optionContainer.element,
            container: this.document.documentElement,
        });
    }
}
