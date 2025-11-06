import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { before, SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { getElementsWithOption } from "@html_builder/utils/utils";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";

export class CountdownOption extends BaseOptionComponent {
    static template = "website.CountdownOption";
    static selector = ".s_countdown";
    static cleanForSave = (editingEl) => {
        editingEl.classList.remove("s_countdown_enable_preview");
    };
}

class CountdownOptionPlugin extends Plugin {
    static id = "CountdownOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [withSequence(before(SNIPPET_SPECIFIC_END), CountdownOption)],
        so_content_addition_selector: [".s_countdown"],
        builder_actions: {
            // TODO AGAU: update after merging generalized restart interactions
            //  remove this and xml BuilderContext
            ReloadCountdownAction,
            SetEndActionAction,
            PreviewEndMessageAction,
            SetLayoutAction,
        },
        on_cloned_handlers: ({ cloneEl }) => {
            const countdownEls = getElementsWithOption(cloneEl, ".s_countdown");
            for (const countdownEl of countdownEls) {
                countdownEl.classList.remove("s_countdown_enable_preview");
            }
        },
    };
}

export class BaseCountdownAction extends BuilderAction {
    static id = "baseCountdown";
    /**
     * Used to preserve modified end messages through end action changes. This
     * allows the user to test options without losing their progress while in
     * between saves.
     *
     * @type {WeakMap<Element, Element>}
     */
    editingElEndMessages = new WeakMap();

    cleanForSave(editingEl) {
        return CountdownOption.cleanForSave(editingEl);
    }

    setEndAction({ editingElement, value }) {
        editingElement.dataset.endAction = value;
        const endMessageEl = editingElement.querySelector(".s_countdown_end_message");

        // Only hide countdown in one case
        editingElement.classList.toggle("hide-countdown", value === "message_no_countdown");

        // Only have redirect url attribute in one case
        if (value === "redirect") {
            editingElement.dataset.redirectUrl = "";
        } else {
            delete editingElement.dataset.redirectUrl;
        }

        if (value === "message" || value === "message_no_countdown") {
            if (!endMessageEl) {
                const existingEndMessage = this.editingElEndMessages.get(editingElement);
                editingElement.appendChild(
                    existingEndMessage || renderToElement("website.s_countdown.end_message")
                );
            }
        } else {
            endMessageEl?.remove();
            this.editingElEndMessages.set(editingElement, endMessageEl);
            // Reset end message preview to avoid countdown staying hidden
            this.toggleEndMessagePreview(editingElement, false);
        }
    }

    isEndActionApplied({ editingElement, value }) {
        return editingElement.dataset.endAction === value;
    }

    setLayout({ editingElement, value }) {
        switch (value) {
            case "circle":
                editingElement.dataset.progressBarStyle = "disappear";
                editingElement.dataset.progressBarWeight = "thin";
                editingElement.dataset.layoutBackground = "none";
                break;
            case "boxes":
                editingElement.dataset.progressBarStyle = "none";
                editingElement.dataset.layoutBackground = "plain";
                break;
            case "clean":
                editingElement.dataset.progressBarStyle = "none";
                editingElement.dataset.layoutBackground = "none";
                break;
            case "text":
                editingElement.dataset.progressBarStyle = "none";
                editingElement.dataset.layoutBackground = "none";
                break;
        }
        editingElement.dataset.layout = value;
    }

    isLayoutApplied({ editingElement, value }) {
        return editingElement.dataset.layout === value;
    }

    isEndMessagePreviewed({ editingElement }) {
        return !!editingElement?.classList.contains("s_countdown_enable_preview");
    }

    toggleEndMessagePreview(editingElement, doShow) {
        editingElement?.classList.toggle("s_countdown_enable_preview", doShow === true);
    }
}

// TODO AGAU: update after merging generalized restart interactions
//  remove this and xml BuilderContext
export class ReloadCountdownAction extends BaseCountdownAction {
    static id = "reloadCountdown";
    apply({ editingElement }) {
        return this.dispatchTo("update_interactions", editingElement);
    }
}

export class SetEndActionAction extends BaseCountdownAction {
    static id = "setEndAction";
    apply(context) {
        return this.setEndAction(context);
    }
    isApplied(context) {
        return this.isEndActionApplied(context);
    }
}

export class PreviewEndMessageAction extends BaseCountdownAction {
    static id = "previewEndMessage";
    static dependencies = ["builderOptions"];
    apply({ editingElement }) {
        this.toggleEndMessagePreview(editingElement, true);
    }
    clean({ editingElement }) {
        this.toggleEndMessagePreview(editingElement, false);
        // Activate the countdown options, to not stay on the message preview
        // ones if they were active.
        this.dependencies.builderOptions.setNextTarget(editingElement);
    }
    isApplied(context) {
        return this.isEndMessagePreviewed(context);
    }
}

export class SetLayoutAction extends BaseCountdownAction {
    static id = "setLayout";
    apply(context) {
        return this.setLayout(context);
    }
    isApplied(context) {
        return this.isLayoutApplied(context);
    }
}
registry.category("website-plugins").add(CountdownOptionPlugin.id, CountdownOptionPlugin);
