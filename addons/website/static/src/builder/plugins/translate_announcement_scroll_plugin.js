import { InputConfirmationDialog } from "@html_builder/snippets/input_confirmation_dialog";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";

export class TranslateAnnouncementScrollPlugin extends Plugin {
    static id = "translateAnnouncementScroll";
    static dependencies = ["history"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        mark_translatable_nodes: this.listenToAnnouncementScrollClick.bind(this),
    };

    /**
     * On click, opens a dialog to translate the interaction's text.
     */
    listenToAnnouncementScrollClick() {
        const announcementScrollEls = this.document.querySelectorAll(".s_announcement_scroll");

        for (const announcementScrollEl of announcementScrollEls) {
            this.addDomListener(announcementScrollEl, "click", () => {
                this.rollbackHistory = this.dependencies.history.makeSavePoint();

                const translatableEl = announcementScrollEl.querySelector(
                    ".s_announcement_scroll_marquee_item:first-child > [data-oe-translation-source-sha]"
                );

                this.services.dialog.add(InputConfirmationDialog, {
                    defaultValue: translatableEl.textContent,
                    title: _t("Translate Text"),
                    confirmLabel: _t("Save"),
                    cancelLabel: _t("Apply"),
                    inputLabel: _t("Translation"),
                    confirm: this.updateText.bind(this, translatableEl),
                    // Override "cancel" to have an "apply" button.
                    cancel: (inputValue) => {
                        this.updateText.apply(this, [translatableEl, inputValue]);
                        return false;
                    },
                    dismiss: this.rollbackHistory,
                });
            });
        }
    }
    /**
     * Update the translated text.
     *
     * @param {HTMLElement} translatableEl
     * @param {String} inputValue
     */
    updateText(translatableEl, inputValue) {
        if (inputValue !== translatableEl.textContent) {
            translatableEl.textContent = inputValue;
            translatableEl.dataset.oeTranslationState = "translated";
            this.dependencies.history.addStep();
        }
    }
}
