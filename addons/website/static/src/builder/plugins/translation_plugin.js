import { Plugin } from "@html_editor/plugin";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { AttributeTranslateDialog } from "../translation_components/attributeTranslateDialog";
import { SelectTranslateDialog } from "../translation_components/selectTranslateDialog";
import {
    localStorageNoDialogKey,
    TranslatorInfoDialog,
} from "../translation_components/translatorInfoDialog";
import { withSequence } from "@html_editor/utils/resource";

export const translationAttributeSelector =
    '[placeholder*="data-oe-translation-source-sha="], ' +
    '[title*="data-oe-translation-source-sha="], ' +
    '[value*="data-oe-translation-source-sha="], ' +
    '[alt*="data-oe-translation-source-sha="]';

export function getTranslationAttributeEls(rootEl) {
    const translationSavableEls = rootEl.querySelectorAll(translationAttributeSelector);
    const textAreaEls = Array.from(rootEl.querySelectorAll("textarea")).find((el) =>
        el.textContent.includes("data-oe-translation-source-sha")
    );
    return Array.from(translationSavableEls).concat(textAreaEls || []);
}

/**
 *
 * @param {HTMLElement} containerEl
 * @returns {HTMLElement[]}
 */
function findOEditable(containerEl) {
    const isOEditable = (node) => {
        // Ideally, we should entirely rely on the contenteditable mechanism.
        // The problem is that the translatable attributes are not branded DOM
        // nodes hence the o_editable_attribute hack.
        if (
            node.isContentEditable ||
            (node.classList.contains("o_editable_attribute") &&
                (!node.closest(".o_not_editable") || node.classList.contains("o_editable_media")))
        ) {
            return true;
        }
        return false;
    };
    const allDescendantEls = containerEl.querySelectorAll("*");
    return Array.from(allDescendantEls).filter(isOEditable);
}

export class TranslationPlugin extends Plugin {
    static id = "translation";
    static dependencies = ["history"];

    resources = {
        clean_for_save_handlers: this.cleanForSave.bind(this),
        get_dirty_els: this.getDirtyTranslations.bind(this),
        after_setup_editor_handlers: () => {
            const translationSavableEls = getTranslationAttributeEls(
                this.services.website.pageDocument
            );
            for (const translationSavableEl of translationSavableEls) {
                translationSavableEl.classList.add("o_editable_attribute");
            }
            // Apply data-oe-readonly on wrapping editor
            const editableElSelector = ".o_editable, .o_editable_attribute";
            const editableEls = [
                ...translationSavableEls,
                ...this.services.website.pageDocument.querySelectorAll(".o_editable"),
            ];
            for (const editableEl of editableEls) {
                if (editableEl.querySelectorAll(editableElSelector).length) {
                    editableEl.setAttribute("data-oe-readonly", "true");
                }
            }
            return true;
        },
        start_edition_handlers: withSequence(5, () => {
            this.prepareTranslation();
        }),
        system_classes: ["o_editable_attribute"],
    };

    setup() {
        this.websiteService = this.services.website;
        this.notificationService = this.services.notification;
        this.dialogService = this.services.dialog;
    }

    prepareTranslation() {
        this.editableEls = findOEditable(this.editable);
        this.buildTranslationInfoMap(this.editableEls);
        this.handleSelectTranslation(this.editableEls);
        this.markTranslatableNodes();
        for (const [translatedEl] of this.elToTranslationInfoMap) {
            if (translatedEl.matches("input[type=hidden].o_translatable_input_hidden")) {
                translatedEl.setAttribute("type", "text");
            }
        }

        // We don't want the BS dropdown to close when clicking in a element to
        // translate.
        const menuEls = this.websiteService.pageDocument.querySelectorAll(".dropdown-menu");
        for (const menuEl of menuEls) {
            this.addDomListener(menuEl, "click", (ev) => {
                const editableEl = ev.target.closest(".o_editable");
                if (editableEl && menuEl.contains(editableEl)) {
                    ev.stopPropagation();
                    ev.preventDefault();
                }
            });
        }

        if (!browser.localStorage.getItem(localStorageNoDialogKey)) {
            this.dialogService.add(TranslatorInfoDialog);
        }

        const showNotification = (ev) => {
            // Prevent duplicate notifications for the same click but allow the
            // event to bubble (i.e. for carousel sliding)
            if (ev.__shownNotification) {
                return;
            }
            ev.__shownNotification = true;
            let message = _t("This translation is not editable.");
            if (ev.target.closest(".s_table_of_content_navbar_wrap")) {
                message = _t("Translate header in the text. Menu is generated automatically.");
            }
            this.notificationService.add(message, {
                type: "info",
                sticky: false,
            });
        };
        for (const translateEl of this.editableEls) {
            this.handleToC(translateEl);
        }
        const savableInsideNotEditableEls = this.editable.querySelectorAll(
            ".o_not_editable .o_editable, .o_not_editable .o_editable_attribute"
        );
        for (const savableInsideNotEditableEl of savableInsideNotEditableEls) {
            this.addDomListener(savableInsideNotEditableEl, "click", showNotification);
        }
        // Keep the original values of elToTranslationInfoMap so that we know
        // which translations have been updated.
        this.originalElToTranslationInfoMap = new Map();
        for (const [translateEl, translationInfo] of this.elToTranslationInfoMap) {
            this.originalElToTranslationInfoMap.set(
                translateEl,
                JSON.parse(JSON.stringify(translationInfo))
            );
        }
    }

    /**
     * Creates a map that links html elements to their attributes to translate.
     * It has the form:
     * {translateEl1: {
     *     attribute1: {
     *         oeModel: "ir.ui.view",
     *         oeId: "5",
     *         oeField: "arch_db",
     *         oeTranslationState: "translated",
     *         oeTranslationSourceSha: "123",
     *         translation: "traduction",
     *     },
     * }};
     *
     * @param {HTMLElement[]} editableEls
     */
    buildTranslationInfoMap(editableEls) {
        this.elToTranslationInfoMap = new Map();
        const translatedAttrs = ["placeholder", "title", "alt", "value"];
        const translationRegex =
            /<span [^>]*data-oe-translation-source-sha="([^"]+)"[^>]*>(.*)<\/span>/;
        const isEmpty = (el) => !el.hasChildNodes() || el.innerHTML.trim() === "";
        const matchTag = (el) => el.matches("input, select, textarea, img");
        for (const translatedAttr of translatedAttrs) {
            const filteredEditableEls = editableEls.filter(
                (editableEl) =>
                    editableEl.hasAttribute(translatedAttr) &&
                    editableEl
                        .getAttribute(translatedAttr)
                        .includes("data-oe-translation-source-sha=") &&
                    (isEmpty(editableEl) || matchTag(editableEl))
            );
            for (const filteredEditableEl of filteredEditableEls) {
                const translation = filteredEditableEl.getAttribute(translatedAttr);
                this.updateTranslationMap(filteredEditableEl, translation, translatedAttr);
                const match = translation.match(translationRegex);
                filteredEditableEl.setAttribute(translatedAttr, match[2]);
                if (translatedAttr === "value") {
                    filteredEditableEl.value = match[2];
                }
                filteredEditableEl.classList.add("o_translatable_attribute");
            }
        }
        const textEditEls = editableEls.filter(
            (editableEl) =>
                editableEl.matches("textarea") &&
                editableEl.textContent.includes("data-oe-translation-source-sha")
        );
        for (const textEditEl of textEditEls) {
            const translation = textEditEl.textContent;
            this.updateTranslationMap(textEditEl, translation, "textContent");
            const match = translation.match(translationRegex);
            textEditEl.value = match[2];
            // Update the text content of textarea too
            textEditEl.innerText = match[2];
            textEditEl.classList.add("o_translatable_text");
            textEditEl.classList.remove("o_text_content_invisible");
        }
    }

    handleSelectTranslation(editableEls) {
        // Hack: we add a temporary element to handle option's text translations
        // from the linked <select/>. The final values are copied to the
        // original element right before save.
        const selectEls = editableEls.filter((editableEl) =>
            editableEl.matches("[data-oe-translation-source-sha] > select")
        );
        this.translateSelectEls = [];
        for (const selectEl of selectEls) {
            const selectTranslationEl = document.createElement("div");
            selectTranslationEl.className = "o_translation_select";
            const optionNames = [...selectEl.options].map((option) => option.text);
            for (const optionName of optionNames) {
                const optionEl = document.createElement("div");
                optionEl.textContent = optionName;
                optionEl.dataset.initialTranslationValue = optionName;
                optionEl.className = "o_translation_select_option";
                selectTranslationEl.appendChild(optionEl);
                this.translateSelectEls.push(optionEl);
            }
            selectEl.before(selectTranslationEl);
        }
    }

    handleToC(translateEl) {
        if (translateEl.closest(".s_table_of_content_navbar_wrap")) {
            // Make sure the same translation ids are used
            const href = translateEl.closest("a").getAttribute("href");
            const headerEl = translateEl
                .closest(".s_table_of_content")
                .querySelector(`${href} [data-oe-translation-source-sha]`);
            if (headerEl) {
                if (
                    translateEl.dataset.oeTranslationSourceSha !==
                    headerEl.dataset.oeTranslationSourceSha
                ) {
                    // Use the same identifier for the generated navigation
                    // label and its associated header so that the general
                    // synchronization mechanism kicks in.
                    // The initial value is kept to be restored before save in
                    // order to keep the translation of the unstyled label
                    // distinct from the one of the header.
                    translateEl.dataset.oeTranslationSaveSha =
                        translateEl.dataset.oeTranslationSourceSha;
                    translateEl.dataset.oeTranslationSourceSha =
                        headerEl.dataset.oeTranslationSourceSha;
                }
                // TODO: handle o_translation_without_style
                translateEl.classList.add("o_translation_without_style");
            }
        }
    }

    markTranslatableNodes() {
        // attributes
        for (const [translateEl, translationInfo] of this.elToTranslationInfoMap) {
            for (const translationData of Object.values(translationInfo)) {
                // If a node has an already translated attribute, we don't need
                // to update its state, since it can be set again as
                // "to_translate" by other attributes...
                if (translateEl.dataset.oeTranslationState !== "translated") {
                    translateEl.setAttribute(
                        "data-oe-translation-state",
                        translationData.oeTranslationState || "to_translate"
                    );
                }
            }
            this.addDomListener(translateEl, "click", (ev) => {
                const translateEl = ev.target;
                const elToTranslationInfoMap = this.elToTranslationInfoMap;
                this.dialogService.add(AttributeTranslateDialog, {
                    node: translateEl,
                    elToTranslationInfoMap: elToTranslationInfoMap,
                    addStep: this.dependencies.history.addStep,
                    applyCustomMutation: this.dependencies.history.applyCustomMutation,
                });
            });
        }
        for (const translateSelectEl of this.translateSelectEls) {
            this.addDomListener(translateSelectEl, "click", (ev) => {
                const translateSelectEl = ev.target;
                this.dialogService.add(SelectTranslateDialog, {
                    node: translateSelectEl,
                    addStep: this.dependencies.history.addStep,
                });
            });
        }
        this.dispatchTo("mark_translatable_nodes", this.editableEls);
    }

    updateTranslationMap(translateEl, translation, attrName) {
        const parser = new DOMParser();
        const dummyDoc = parser.parseFromString(translation, "text/html");
        const translationEl = dummyDoc.querySelector("[data-oe-translation-source-sha]");
        if (!this.elToTranslationInfoMap.get(translateEl)) {
            this.elToTranslationInfoMap.set(translateEl, {});
        }
        this.elToTranslationInfoMap.get(translateEl)[attrName] = translationEl.dataset;
        this.elToTranslationInfoMap.get(translateEl)[attrName].translation =
            translationEl.innerHTML;
    }

    /**
     * Gets the modified translations
     * @returns {HTMLElement[]}
     */
    getDirtyTranslations() {
        const dirtyEls = [];
        for (const [translateEl, translationInfo] of this.elToTranslationInfoMap) {
            for (const [attr, data] of Object.entries(translationInfo)) {
                if (
                    this.originalElToTranslationInfoMap.get(translateEl)[attr].translation !==
                    data.translation
                ) {
                    const spanEl = document.createElement("span");
                    for (const [name, value] of Object.entries(data)) {
                        spanEl.dataset[name] = value;
                    }
                    const translation = spanEl.dataset.translation;
                    delete spanEl.dataset.translation;
                    spanEl.innerHTML = translation;
                    dirtyEls.push(spanEl);
                }
            }
        }
        return dirtyEls;
    }

    cleanForSave({ root }) {
        root.querySelectorAll(".o_editable_attribute").forEach((el) => {
            el.classList.remove("o_editable_attribute");
        });
        // Remove the `.o_translation_select` temporary element
        const optionsEl = root.querySelector(".o_translation_select");
        if (optionsEl) {
            const selectEl = optionsEl.nextElementSibling;
            const translatedOptions = optionsEl.children;
            const selectOptions = selectEl.tagName === "SELECT" ? [...selectEl.options] : [];
            if (selectOptions.length === translatedOptions.length) {
                selectOptions.map((option, i) => {
                    option.text = translatedOptions[i].textContent;
                });
            }
            optionsEl.remove();
        }
        if (root.dataset.oeTranslationSaveSha) {
            root.dataset.oeTranslationSourceSha = root.dataset.oeTranslationSaveSha;
            delete root.dataset.oeTranslationSaveSha;
        }
    }
}
