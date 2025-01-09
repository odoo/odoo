import { SNIPPET_SPECIFIC, SNIPPET_SPECIFIC_NEXT } from "@html_builder/utils/option_sequence";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { BuilderAction } from "@html_builder/core/builder_action";
import { renderToElement } from "@web/core/utils/render";

class CountdownInlineOptionPlugin extends Plugin {
    static id = "countdownInlineOption";
    static dependencies = ["builderActions", "CountdownOption"];

    constructor(...args) {
        super(...args);
        /**
         * Used to preserve modified end messages through end action changes. This
         * allows the user to test options without losing their progress while in
         * between saves.
         *
         * @type {WeakMap<Element, Element>}
        */
        this.editingElEndMessages = new WeakMap();
    }

    resources = {
        builder_options: [
            withSequence(SNIPPET_SPECIFIC, {
                template: "website.CountdownInlineOption",
                selector: ".s_countdown_inline",
                cleanForSave: this.cleanForSave.bind(this),
            }),
            withSequence(SNIPPET_SPECIFIC_NEXT, {
                template: "website.CountdownInlineOptionStyle",
                selector: ".s_countdown_inline",
                applyTo: ".s_countdown_inline_wrapper",
            }),
        ],

        so_content_addition_selector: [".s_countdown_inline"],

        // Note inherited from `CountdownOption`.
        //
        // TODO AGAU: update after merging generalized restart interactions
        //  remove this and xml BuilderContext
        builder_actions: {
            ReloadCountdownInlineAction,
            SelectCountdownInlineTemplateAction,
            SetEndActionInlineAction,
            PreviewEndMessageInlineAction,
        },
    };

    // Reuse logic from base countdown but with inline-specific selectors
    setEndAction({ editingElement, value }) {
        editingElement.dataset.endAction = value;
        const endMessageEl = editingElement.querySelector(".s_countdown_inline_end_message");

        editingElement.classList.toggle("hide-countdown", value === "message_no_countdown");

        if (value === "redirect") {
            editingElement.dataset.redirectUrl = "";
        } else {
            delete editingElement.dataset.redirectUrl;
        }

        if (value === "message" || value === "message_no_countdown") {
            if (!endMessageEl) {
                const existingEndMessage = this.editingElEndMessages.get(editingElement);
                editingElement.appendChild(
                    existingEndMessage ||
                        renderToElement("website.s_countdown_inline.end_message")
                );
            }
        } else {
            endMessageEl?.remove();
            this.editingElEndMessages.set(editingElement, endMessageEl);
            this.dependencies.CountdownOption.toggleEndMessagePreview(editingElement, false);
        }
    }

    isEndActionApplied({ editingElement, value }) {
        return editingElement.dataset.endAction === value;
    }

    cleanForSave(editingEl) {
        editingEl?.classList.remove("s_countdown_none");
        editingEl?.classList.remove("s_countdown_enable_preview");
    }
}

// Note inherited from `CountdownOption`.
//
// TODO AGAU: update after merging generalized restart interactions
//  remove this and xml BuilderContext
class ReloadCountdownInlineAction extends BuilderAction {
    static id = "reloadCountdownInline";
    apply({ editingElement }) {
        return this.dispatchTo("update_interactions", editingElement);
    }
}

class SelectCountdownInlineTemplateAction extends BuilderAction {
    static id = "selectCountdownInlineTemplate";
    static dependencies = ["builderActions"];

    async prepare({ actionParam }) {
        const getAction = this.dependencies.builderActions.getAction;
        await getAction("selectTemplate").prepare({ actionParam: actionParam });
    }

    isApplied({editingElement, params: { templateClass } }) {
        if (templateClass) {
            return !!editingElement.querySelector(`.${templateClass}`);
        }
        return true;
    }

    apply(action) {
        const getAction = this.dependencies.builderActions.getAction;
        getAction("selectTemplate").apply(action);

        // Reset the monospace font option if we select a template that doesn't provide it.
        const isDefaultOrTextTemplate = ["o_template_default", "o_template_text"].includes(action.params.templateClass);
        const hasMonospaceFont = action.editingElement.parentElement.classList.contains("o_count_monospace");
        if (hasMonospaceFont && isDefaultOrTextTemplate) {
            action.editingElement.parentElement.classList.remove('o_count_monospace');
        }
    }

    clean(action) {
        const getAction = this.dependencies.builderActions.getAction;
        return getAction("selectTemplate").clean(action);
    }
}

class SetEndActionInlineAction extends BuilderAction {
    static id = "countdownInlineSetEndAction";
    static dependencies = ["countdownInlineOption"];

    apply({ editingElement, value }) {
        const plugin = this.config.getShared().countdownInlineOption;
        return plugin.setEndAction({ editingElement, value });
    }

    isApplied({ editingElement, value }) {
        const plugin = this.config.getShared().countdownInlineOption;
        return plugin.isEndActionApplied({ editingElement, value });
    }
}

class PreviewEndMessageInlineAction extends BuilderAction {
    static id = "countdownInlinePreviewEndMessage";
    static dependencies = ["CountdownOption"];

    apply({ editingElement }) {
        return this.dependencies.CountdownOption.toggleEndMessagePreview(editingElement, true);
    }

    clean({ editingElement }) {
        return this.dependencies.CountdownOption.toggleEndMessagePreview(editingElement, false);
    }

    isApplied({ editingElement }) {
        return this.dependencies.CountdownOption.isEndMessagePreviewed({ editingElement });
    }
}

CountdownInlineOptionPlugin.shared = ["setEndAction", "isEndActionApplied"];

registry.category("website-plugins").add(CountdownInlineOptionPlugin.id, CountdownInlineOptionPlugin);
