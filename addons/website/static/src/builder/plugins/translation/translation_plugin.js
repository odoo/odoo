import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { AttributeTranslateDialog } from "../../translation_components/attributeTranslateDialog";
import { withSequence } from "@html_editor/utils/resource";
import { makeContentsInline, unwrapContents } from "@html_editor/utils/dom";
import { DISABLED_NAMESPACE } from "@html_editor/main/toolbar/toolbar_plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { groupBy } from "@web/core/utils/arrays";
import { rpc } from "@web/core/network/rpc";

/**
 * @typedef {((editableEls: HTMLElement[]) => void)[]} mark_translatable_nodes
 */

const TRANSLATED_ATTRS = ["placeholder", "title", "alt", "value"];
const TRANSLATION_ATTRIBUTES_SELECTOR = TRANSLATED_ATTRS.map(
    (att) => `[${att}*="data-oe-translation-source-sha="]`
).join(", ");

export function getTranslationAttributeEls(rootEl) {
    const translationSavableEls = rootEl.querySelectorAll(TRANSLATION_ATTRIBUTES_SELECTOR);
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
        // nodes hence the o_savable_attribute hack.
        if (
            node.isContentEditable ||
            (node.classList.contains("o_savable_attribute") &&
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
    static dependencies = ["history", "savePlugin", "dirtMark"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        clean_for_save_handlers: this.cleanForSave.bind(this),
        after_setup_editor_handlers: () => {
            const translationSavableEls = getTranslationAttributeEls(
                this.services.website.pageDocument
            );
            for (const translationSavableEl of translationSavableEls) {
                translationSavableEl.classList.add("o_savable_attribute");
            }
            // Apply data-oe-readonly on wrapping editor
            const editableElSelector = ".o_savable, .o_savable_attribute";
            const editableEls = [
                ...this.services.website.pageDocument.querySelectorAll(".o_savable"),
            ];
            for (const editableEl of editableEls) {
                if (editableEl.querySelector(editableElSelector)) {
                    editableEl.setAttribute("data-oe-readonly", "true");
                    editableEl.classList.remove("o_savable");
                }
            }
            return true;
        },
        start_edition_handlers: withSequence(5, () => {
            this.prepareTranslation();
        }),
        system_classes: ["o_savable_attribute"],
        before_insert_processors: withSequence(20, (container) => {
            makeContentsInline(container);
            for (const el of container.querySelectorAll(this.nonTranslatedSelector)) {
                unwrapContents(el);
            }
            return container;
        }),
        toolbar_namespace_providers: [
            (targetedNodes, editableSelection) =>
                closestElement(editableSelection.anchorNode, ".o_translation_select") &&
                DISABLED_NAMESPACE,
        ],
        save_view_context_processors: (context) => delete context.delay_translations,
        dirt_marks: {
            id: "translation",
            setDirtyOnMutation: (record) =>
                closestElement(record.target, ".o_savable[data-oe-translation-source-sha]"),
        },
        has_unsaved_data_predicates: () =>
            this.elToTranslationInfoMap
                .entries()
                .some(([translateEl, translationInfo]) =>
                    Object.entries(translationInfo).some(
                        ([attr, data]) =>
                            this.originalElToTranslationInfoMap.get(translateEl)[attr]
                                .translation !== data.translation
                    )
                ),
        save_handlers: this.saveHandler.bind(this),
    };

    setup() {
        this.websiteService = this.services.website;
        this.notificationService = this.services.notification;
        this.dialogService = this.services.dialog;
        this.nonTranslatedSelector =
            `:not(${this.config.translatedElements.join(", ")})` + `:not(.o_translate_inline)`;
    }

    prepareTranslation() {
        this.editableEls = findOEditable(this.editable);
        this.buildTranslationInfoMap(this.editableEls);
        this.handleSelectTranslation(this.editable);
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
                const editableEl = ev.target.closest(".o_savable");
                if (editableEl && menuEl.contains(editableEl)) {
                    ev.stopPropagation();
                    ev.preventDefault();
                }
            });
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
            ".o_not_editable .o_savable, .o_not_editable .o_savable_attribute"
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

    /**
     * Hack: we add a temporary element to handle <option> translations directly
     * inside the page.
     *
     * @param {HTMLElement} containerEl
     */
    handleSelectTranslation(containerEl) {
        const selectEls = containerEl.querySelectorAll(
            "select:has(> option[data-oe-translation-span-wrapper])"
        );
        for (const selectEl of selectEls) {
            const selectTranslationEl = document.createElement("div");
            selectTranslationEl.className = "o_translation_select form-control";
            for (const optionEl of selectEl.options) {
                if (!optionEl.dataset.oeTranslationSpanWrapper) {
                    continue;
                }
                const optionTranslationEl = document.createElement("div");
                const translationSpanEl = this.parseTranslationEl(
                    optionEl.dataset.oeTranslationSpanWrapper
                );
                translationSpanEl.classList.add("o_savable");
                translationSpanEl.setAttribute("contenteditable", "true");
                optionTranslationEl.appendChild(translationSpanEl);
                selectTranslationEl.appendChild(optionTranslationEl);
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
        this.dispatchTo("mark_translatable_nodes", this.editableEls);
    }

    parseTranslationEl(translationHtml) {
        return new DOMParser()
            .parseFromString(translationHtml, "text/html")
            .querySelector("[data-oe-translation-source-sha]");
    }

    updateTranslationMap(translateEl, translation, attrName) {
        const translationEl = this.parseTranslationEl(translation);
        if (!this.elToTranslationInfoMap.get(translateEl)) {
            this.elToTranslationInfoMap.set(translateEl, {});
        }
        this.elToTranslationInfoMap.get(translateEl)[attrName] = translationEl.dataset;
        this.elToTranslationInfoMap.get(translateEl)[attrName].translation =
            translationEl.innerHTML;
    }

    cleanForSave({ root }) {
        root.querySelectorAll(".o_savable_attribute").forEach((el) => {
            el.classList.remove("o_savable_attribute");
        });
        if (root.dataset.oeTranslationSaveSha) {
            root.dataset.oeTranslationSourceSha = root.dataset.oeTranslationSaveSha;
            delete root.dataset.oeTranslationSaveSha;
        }
    }

    async saveHandler() {
        const delayedTranslation = [...this.editable.querySelectorAll(".o_delay_translation")].map(
            (el) => ({
                group: JSON.stringify([el.dataset.oeModel, el.dataset.oeId, el.dataset.oeField]),
                content: {},
                afterSave: () => {},
            })
        );
        const dirtys = [...this.dependencies.dirtMark.queryDirtys("translation")];
        const elTranslation = dirtys.map(({ el, setClean }) => {
            const cleanedEl = this.dependencies.savePlugin.prepareElementForSave(el);
            return {
                group: JSON.stringify([el.dataset.oeModel, el.dataset.oeId, el.dataset.oeField]),
                content: { [cleanedEl.dataset.oeTranslationSourceSha]: cleanedEl.innerHTML },
                afterSave: setClean,
            };
        });

        const attrTranslation = this.elToTranslationInfoMap
            .entries()
            .flatMap(([translateEl, translationInfo]) =>
                Object.entries(translationInfo)
                    .filter(
                        ([attr, data]) =>
                            this.originalElToTranslationInfoMap.get(translateEl)[attr]
                                .translation !== data.translation
                    )
                    .map(([attr, data]) => ({
                        group: JSON.stringify([data.oeModel, data.oeId, data.oeField]),
                        content: { [data.oeTranslationSourceSha]: data.translation },
                        afterSave: () => {
                            this.originalElToTranslationInfoMap.get(translateEl)[attr].translation =
                                data.translation;
                        },
                    }))
            );

        const lang = this.services.website.currentWebsite.metadata.lang;
        const allTranslations = [...elTranslation, ...attrTranslation, ...delayedTranslation];
        await Promise.all(
            Object.entries(groupBy(allTranslations, (e) => e.group)).map(
                async ([group, toSave]) => {
                    const [oeModel, oeId, oeField] = JSON.parse(group);
                    const contents = toSave.map((t) => t.content);
                    await rpc("/website/field/translation/update", {
                        model: oeModel,
                        record_id: [Number(oeId)],
                        field_name: oeField,
                        translations: { [lang]: Object.assign({}, ...contents) },
                    });
                    toSave.forEach((t) => t.afterSave());
                }
            )
        );
    }
}

registry.category("translation-plugins").add(TranslationPlugin.id, TranslationPlugin);
