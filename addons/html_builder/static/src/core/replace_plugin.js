import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";

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
    static dependencies = ["history", "builder-options"];
    resources = {
        get_overlay_buttons: withSequence(3, {
            getButtons: this.getActiveOverlayButtons.bind(this),
        }),
    };

    setup() {
        this.overlayTarget = null;
    }

    getActiveOverlayButtons(target) {
        if (!isReplaceable(target)) {
            this.overlayTarget = null;
            return [];
        }

        const buttons = [];
        this.overlayTarget = target;
        buttons.push({
            class: "o_snippet_replace bg-warning fa fa-exchange",
            title: _t("Replace"),
            handler: this.replaceSnippet.bind(this),
        });
        return buttons;
    }

    async replaceSnippet() {
        const newSnippet = await this.config.replaceSnippet(this.overlayTarget);
        if (newSnippet) {
            this.overlayTarget = null;
            newSnippet.querySelectorAll(".s_dialog_preview").forEach((el) => el.remove());
            // TODO find a way to wait for the images to load before updating or
            // to trigger a refresh once the images are loaded afterwards.
            // If not possible, call updateContainers with nothing.
            this.dependencies.history.addStep();
            this.dependencies["builder-options"].updateContainers(newSnippet);
            // TODO post snippet drop (onBuild,...)
        }
    }
}
