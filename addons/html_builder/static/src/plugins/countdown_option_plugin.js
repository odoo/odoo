import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";

class CountdownOptionPlugin extends Plugin {
    static id = "CountdownOption";
    resources = {
        builder_options: [
            withSequence(50, {
                template: "html_builder.CountdownOption",
                selector: ".s_countdown",
                cleanForSave: this.cleanForSave.bind(this),
            }),
        ],
        builder_actions: {
            // TODO AGAU: update after merging generalized restart interactions
            //  remove this and xml BuilderContext
            reloadCountdown: {
                apply: ({ editingElement }) => {
                    this.dispatchTo("update_interactions", editingElement);
                },
            },
            setEndAction: {
                apply: this.setEndAction.bind(this),
                isApplied: this.isEndActionApplied.bind(this),
            },
            previewEndMessage: {
                apply: ({ editingElement }) => this.toggleEndMessagePreview(editingElement, true),
                clean: ({ editingElement }) => this.toggleEndMessagePreview(editingElement, false),
                isApplied: this.isEndMessagePreviewed.bind(this),
            },
            setLayout: {
                apply: this.setLayout.bind(this),
                isApplied: this.isLayoutApplied.bind(this),
            },
        },
    };

    /**
     * Used to preserve modified end messages through end action changes. This
     * allows the user to test options without losing their progress while in
     * between saves.
     *
     * @type {WeakMap<Element, Element>}
     */
    editingElEndMessages = new WeakMap();

    cleanForSave(editingEl) {
        editingEl.classList.remove("s_countdown_enable_preview");
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
                    existingEndMessage ||
                        renderToElement("html_builder.website.s_countdown.end_message")
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
registry.category("website-plugins").add(CountdownOptionPlugin.id, CountdownOptionPlugin);
