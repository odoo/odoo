import { SNIPPET_SPECIFIC, SNIPPET_SPECIFIC_NEXT } from "@html_builder/utils/option_sequence";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { renderToElement } from "@web/core/utils/render";

class CountdownInlineOptionPlugin extends Plugin {
    static id = "countdownInlineOption";
    static dependencies = ["builderActions", "CountdownOption"];
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
        builder_actions: this.getActions(),
    };

    getActions() {
        const getAction = this.dependencies.builderActions.getAction;
        return {
            // TODO AGAU: update after merging generalized restart interactions
            //  remove this and xml BuilderContext
            reloadCountdownInline: {
                apply: ({ editingElement }) => {
                    this.dispatchTo("update_interactions", editingElement);
                },
            },
            selectCountdownInlineTemplate: {
                prepare: async ({ actionParam }) => {
                    await getAction("selectTemplate").prepare({ actionParam: actionParam });
                },
                isApplied: ({editingElement, params: { templateClass } }) => {
                    if (templateClass) {
                        return !!editingElement.querySelector(`.${templateClass}`);
                    }
                    return true;
                },
                apply: (action) => {
                    getAction("selectTemplate").apply(action);

                    // Reset the monospace font option if we select a template that doesn't provide it.
                    const isDefaultOrTextTemplate = ["o_template_default", "o_template_text"].includes(action.params.templateClass);
                    const hasMonospaceFont = action.editingElement.parentElement.classList.contains("o_count_monospace");
                    if (hasMonospaceFont && isDefaultOrTextTemplate) {
                        action.editingElement.parentElement.classList.remove('o_count_monospace');
                    }
                },
                clean: (action) => getAction("selectTemplate").clean(action),
            },
            countdownInlineSetEndAction: {
                apply: ({ editingElement, value }) => {
                    editingElement.dataset.endAction = value;
                    const endMessageEl = editingElement.querySelector(".s_countdown_inline_end_message");

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
                                existingEndMessage ||
                                    renderToElement("website.s_countdown_inline.end_message")
                            );
                        }
                    } else {
                        endMessageEl?.remove();
                        this.editingElEndMessages.set(editingElement, endMessageEl);
                        // Reset end message preview to avoid countdown staying hidden
                        this.dependencies.CountdownOption.toggleEndMessagePreview(editingElement, false);
                    }
                },
                isApplied: ({ editingElement, value }) => {
                    return editingElement.dataset.endAction === value;
                }
            },
            countdownInlinePreviewEndMessage: {
                apply: ({ editingElement }) => this.dependencies.CountdownOption.toggleEndMessagePreview(editingElement, true),
                clean: ({ editingElement }) => this.dependencies.CountdownOption.toggleEndMessagePreview(editingElement, false),
                isApplied: this.dependencies.CountdownOption.isEndMessagePreviewed.bind(this),
            },
        };
    }

    /**
     * Used to preserve modified end messages through end action changes. This
     * allows the user to test options without losing their progress while in
     * between saves.
     *
     * @type {WeakMap<Element, Element>}
     */
    editingElEndMessages = new WeakMap();

    cleanForSave(editingEl) {
        editingEl?.classList.remove("s_countdown_none");
        editingEl?.classList.remove("s_countdown_enable_preview");
    }
}
registry.category("website-plugins").add(CountdownInlineOptionPlugin.id, CountdownInlineOptionPlugin);
