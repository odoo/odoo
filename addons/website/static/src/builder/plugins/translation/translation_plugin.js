import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { shouldEditableMediaBeEditable } from "@html_builder/utils/utils_css";
import { withSequence } from "@html_editor/utils/resource";
import { makeContentsInline, unwrapContents } from "@html_editor/utils/dom";
import { DISABLED_NAMESPACE } from "@html_editor/main/toolbar/toolbar_plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";

/**
 * @typedef {Map<HTMLElement, ElementTranslationInfo} ElToTranslationInfoMap
 *
 * @typedef {{[attributeName: string]: AttributeTranslationInfo}} ElementTranslationInfo
 *
 * @typedef {Object} AttributeTranslationInfo
 * @property {string} oeModel
 * @property {string} oeId
 * @property {string} oeField
 * @property {string} oeTranslationState
 * @property {string} oeTranslationSourceSha
 * @property {string} translation
 */

/**
 * @typedef {Object} TranslationShared
 * @property {TranslationPlugin["getDirtyTranslationsInfo"]} getDirtyTranslationsInfo
 * @property {TranslationPlugin["getTranslatableAttributes"]} getTranslatableAttributes
 */

const TRANSLATED_ATTRS = [
    "placeholder",
    "title",
    "alt",
    "value",
    "data-oe-translate-src",
    "data-oe-translate-srcset",
];

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
    static shared = ["getDirtyTranslationsInfo", "getTranslatableAttributes"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        clean_for_save_processors: this.cleanForSave.bind(this),
        on_replicated_handlers: ({ sourceEl, targetEl }) => {
            targetEl.classList.toggle("o_dirty", sourceEl.classList.contains("o_dirty"));
        },
        after_setup_editor_overrides: () => {
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
        on_editor_started_handlers: withSequence(5, () => {
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
    };

    setup() {
        this.websiteService = this.services.website;
        this.notificationService = this.services.notification;
        this.dialogService = this.services.dialog;
        this.nonTranslatedSelector =
            `:not(${this.config.translatedElements.join(", ")})` + `:not(.o_translate_inline)`;
    }

    prepareTranslation() {
        const editableEls = findOEditable(this.editable);
        const elWithTranslatedAttributes = this.buildTranslationInfoMap(editableEls);
        this.handleSelectTranslation(this.editable);
        this.setTranslationStateOfNodesWithTranslatedAttributes(elWithTranslatedAttributes);
        for (const translatedEl of elWithTranslatedAttributes) {
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
            if (ev.target.closest(".o_carousel_controllers")) {
                return;
            }
            this.notificationService.add(message, {
                type: "info",
                sticky: false,
            });
        };
        const savableInsideNotEditableEls = this.editable.querySelectorAll(
            ".o_not_editable .o_savable, .o_not_editable .o_savable_attribute"
        );
        for (const savableInsideNotEditableEl of savableInsideNotEditableEls) {
            if (
                savableInsideNotEditableEl.matches(".o_editable_media") &&
                shouldEditableMediaBeEditable(savableInsideNotEditableEl)
            ) {
                continue;
            }
            this.addDomListener(savableInsideNotEditableEl, "click", showNotification);
        }
    }
    /**
     * Creates a map that links html elements to their attributes to translate.
     * It has the form `Map<HTMLElement, ElementTranslationInfo>`:
     *
     *     Map(
     *         translateEl1 => {
     *             attribute1: {
     *                 oeModel: "ir.ui.view",
     *                 oeId: "5",
     *                 oeField: "arch_db",
     *                 oeTranslationState: "translated",
     *                 oeTranslationSourceSha: "123",
     *                 translation: "traduction",
     *             },
     *         }
     *     );
     *
     * @param {HTMLElement[]} editableEls
     */
    buildTranslationInfoMap(editableEls) {
        const elWithTranslatedAttributes = new Set();
        const translationRegex =
            /<span [^>]*data-oe-translation-source-sha="([^"]+)"[^>]*>([\s\S]*?)<\/span>/;
        const isEmpty = (el) => !el.hasChildNodes() || el.innerHTML.trim() === "";
        const matchTag = (el) => el.matches("input, select, textarea, img");

        // Placeholder attributes on non-form elements (i.e. not input, select,
        // textarea) are intended for content editors, not visible text
        // for end-users. For example, blog post title is such a placeholder.
        const placeholderEls = editableEls.filter(
            (el) =>
                el.getAttribute("placeholder")?.includes("data-oe-translation-source-sha=") &&
                !matchTag(el)
        );
        for (const el of placeholderEls) {
            const translation = el.getAttribute("placeholder");
            const match = translation.match(translationRegex);
            el.setAttribute("placeholder", match[2]);
        }

        for (const translatedAttr of TRANSLATED_ATTRS) {
            const filteredEditableEls = editableEls.filter(
                (editableEl) =>
                    editableEl.hasAttribute(translatedAttr) &&
                    editableEl
                        .getAttribute(translatedAttr)
                        .includes("data-oe-translation-source-sha=") &&
                    (isEmpty(editableEl) || matchTag(editableEl))
            );
            for (const filteredEditableEl of filteredEditableEls) {
                elWithTranslatedAttributes.add(filteredEditableEl);
                const translation = filteredEditableEl.getAttribute(translatedAttr);
                const match = translation.match(translationRegex);
                if (translatedAttr.startsWith("data-oe-translate-")) {
                    filteredEditableEl.removeAttribute(translatedAttr);
                    const originalAttr = translatedAttr.split("data-oe-translate-")[1];
                    // Use the original attribute in the translation map to make
                    // it easier to update later.
                    this.setupTranslationInfo(filteredEditableEl, translation, originalAttr);
                } else {
                    this.setupTranslationInfo(filteredEditableEl, translation, translatedAttr);
                    filteredEditableEl.setAttribute(translatedAttr, match[2]);
                }
                if (translatedAttr === "value") {
                    filteredEditableEl.value = match[2];
                }
                filteredEditableEl.classList.add("o_translatable_attribute");
                if (filteredEditableEl.matches("textarea, input")) {
                    // We want those elements to be translated by the sidebar,
                    // not by editing the input.
                    filteredEditableEl.setAttribute("readonly", "");
                }
            }
        }
        const textEditEls = editableEls.filter(
            (editableEl) =>
                editableEl.matches("textarea") &&
                editableEl.textContent.includes("data-oe-translation-source-sha")
        );
        for (const textEditEl of textEditEls) {
            elWithTranslatedAttributes.add(textEditEl);
            const translation = textEditEl.textContent;
            this.setupTranslationInfo(textEditEl, translation, "textContent");
            const match = translation.match(translationRegex);
            textEditEl.value = match[2];
            // Update the text content of textarea too
            textEditEl.innerText = match[2];
            textEditEl.classList.add("o_translatable_text");
            // We want those elements to be translated by the sidebar,
            // not by editing the input.
            textEditEl.setAttribute("readonly", "");
            textEditEl.classList.remove("o_text_content_invisible");
        }
        return elWithTranslatedAttributes;
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

    setTranslationStateOfNodesWithTranslatedAttributes(elWithTranslatedAttributes) {
        for (const translateEl of elWithTranslatedAttributes) {
            for (const attrName of this.getTranslatableAttributes(translateEl)) {
                const translationData = JSON.parse(
                    translateEl.getAttribute(`data-translated-attribute-info-${attrName}`)
                );
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
        }
    }

    parseTranslationEl(translationHtml) {
        return new DOMParser()
            .parseFromString(translationHtml, "text/html")
            .querySelector("[data-oe-translation-source-sha]");
    }
    /**
     * @param {HTMLElement} translateEl - the element whose translatable
     * attributes we want to get.
     * @returns {[string]} the attributes names of the translatable attributes,
     * including the fake attribute `textContent`
     */
    getTranslatableAttributes(translateEl) {
        const translatableAttrNames = [];
        for (const attrName of [...translateEl.getAttributeNames(), "textContent"]) {
            if (translateEl.hasAttribute(`data-translated-attribute-info-${attrName}`)) {
                translatableAttrNames.push(attrName);
            }
        }
        return translatableAttrNames;
    }
    /**
     * @param {HTMLElement} translateEl - element on which the translatable
     * attribute is
     * @param {string} translation - current translation
     * @param {string} attrName - attribute to translate
     */
    setupTranslationInfo(translateEl, translation, attrName) {
        const translationEl = this.parseTranslationEl(translation);
        translateEl.setAttribute(
            `data-translated-attribute-info-${attrName}`,
            JSON.stringify({ ...translationEl.dataset, translation: translationEl.innerHTML })
        );
    }

    /**
     * Gets the modified translations info
     * @returns {AttributeTranslationInfo[]}
     */
    getDirtyTranslationsInfo() {
        const dirtyInfo = [];
        for (const translateEl of this.editable.querySelectorAll(".o_savable_attribute")) {
            for (const attr of this.getTranslatableAttributes(translateEl)) {
                const data = JSON.parse(
                    translateEl.getAttribute(`data-translated-attribute-info-${attr}`)
                );
                const newTranslation =
                    attr === "textContent"
                        ? translateEl.textContent
                        : translateEl.getAttribute(attr);
                if (newTranslation !== data.translation) {
                    dirtyInfo.push({ ...data, translation: newTranslation });
                }
            }
        }
        return dirtyInfo;
    }

    cleanForSave(root) {
        root.querySelectorAll(".o_savable_attribute").forEach((el) => {
            el.classList.remove("o_savable_attribute");
        });
        return root;
    }
}

registry.category("translation-plugins").add(TranslationPlugin.id, TranslationPlugin);
