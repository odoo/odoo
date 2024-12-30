import { Plugin } from "@html_editor/plugin";

// Snippets are replaceable only if they are not within another snippet (e.g. a
// "s_countdown" is not replaceable when it is dropped as inner content).
function isReplaceable(el) {
    // TODO has snippet group ?
    return (
        el.matches("[data-snippet]:not([data-snippet] *), .oe_structure > *") &&
        !el.matches(".oe_structure_solo *")
    );
}

export class ReplacePlugin extends Plugin {
    static id = "replace";
    static dependencies = ["history"];
    resources = {
        get_overlay_buttons: this.getActiveOverlayButtons.bind(this),
    };

    setup() {
        this.target = null;
    }

    getActiveOverlayButtons(target) {
        if (!isReplaceable(target)) {
            this.target = null;
            return [];
        }

        const buttons = [];
        this.target = target;
        buttons.push({
            class: "o_snippet_replace bg-warning fa fa-exchange",
            handler: this.replaceSnippet.bind(this),
        });
        return buttons;
    }

    async replaceSnippet() {
        const newSnippet = await this.config.replaceSnippet(this.target);
        if (newSnippet) {
            this.target = null;
            // TODO find a way to wait for the images to load before updating or
            // to trigger a refresh once the images are loaded afterwards.
            // If not possible, call updateContainers with nothing.
            this.dispatchTo("update_containers", newSnippet);
            // TODO post snippet drop (onBuild,...)
            this.dependencies.history.addStep();
        }
    }
}
