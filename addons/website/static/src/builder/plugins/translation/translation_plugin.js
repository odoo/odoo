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
 * @property {TranslationPlugin["getTranslationInfo"]} getTranslationInfo
 * @property {TranslationPlugin["updateTranslationMap"]} updateTranslationMap
 * @property {TranslationPlugin["getDirtyTranslationsInfo"]} getDirtyTranslationsInfo
 */

/**
 * @typedef {((editableEls: HTMLElement[]) => void)[]} on_nodes_marked_translatable_handlers
 */

export class TranslationPlugin extends Plugin {
    static id = "translation";
    static shared = ["getTranslationInfo", "updateTranslationMap", "getDirtyTranslationsInfo"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        clean_for_save_processors: this.cleanForSave.bind(this),
        on_replicated_handlers: ({ sourceEl, targetEl }) => {
            targetEl.classList.toggle("o_dirty", sourceEl.classList.contains("o_dirty"));
        },
        after_setup_editor_overrides: () => {
            this.prepareTranslatedAttributes();
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
        // Keep the original values of elToTranslationInfoMap so that we know
        // which translations have been updated.
        /** @type {ElToTranslationInfoMap} */
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
     * And replace the translated attributes with their translated content
     * The map has the form `Map<HTMLElement, ElementTranslationInfo>`:
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
    prepareTranslatedAttributes() {
        const translatedAttrs = new Set(this.config.translatedAttributes);
        // This selector does `is_translatable_attrib_value` from `translate.py`
        const translatableValueAttrSelector =
            "input:is([type=text], :not([type])):not(.datetimepicker-input), input[type=hidden].o_translatable_input_hidden";

        this.elToTranslationInfoMap = new Map();
        const registerTranslatedAttribute = ({ el, name, infoEl }) => {
            el.classList.add("o_savable_attribute");
            if (
                (!el.hasChildNodes() ||
                    el.innerHTML.trim() === "" ||
                    el.matches("input, select, textarea, img")) &&
                (!el.closest(".o_not_editable") || el.classList.contains("o_editable_media"))
            ) {
                el.classList.add(
                    name === "textContent" ? "o_translatable_text" : "o_translatable_attribute"
                );
                if (el.matches("textarea, input")) {
                    // We want those elements to be translated by the sidebar,
                    // not by editing the input.
                    el.setAttribute("readonly", "");
                    if (el.matches("textarea")) {
                        el.classList.remove("o_text_content_invisible");
                    }
                }
                const info = this.elToTranslationInfoMap.get(el) ?? {};
                info[name] = { ...infoEl.dataset, translation: infoEl.textContent };
                this.elToTranslationInfoMap.set(el, info);
            }
        };

        const tryParseTranslationEl = (html) =>
            html.includes("data-oe-translation-source-sha=") && this.parseTranslationEl(html);

        const walker = document.createTreeWalker(this.editable, NodeFilter.SHOW_ELEMENT, (el) =>
            el.hasAttribute("data-oe-translation-source-sha")
                ? NodeFilter.FILTER_REJECT
                : NodeFilter.FILTER_ACCEPT
        );
        let el, infoEl;
        while ((el = walker.nextNode())) {
            for (const attr of [...el.attributes]) {
                if (
                    (translatedAttrs.has(attr.name) ||
                        (attr.name === "value" && el.matches(translatableValueAttrSelector))) &&
                    (infoEl = tryParseTranslationEl(attr.value))
                ) {
                    attr.value = infoEl.textContent;
                    if (attr.name === "value") {
                        el.value = infoEl.textContent;
                    }
                    if (["placeholder", "title", "alt", "value"].includes(attr.name)) {
                        registerTranslatedAttribute({ el, name: attr.name, infoEl });
                    }
                }
                if (
                    attr.name.startsWith("data-oe-translate-") &&
                    (infoEl = tryParseTranslationEl(attr.value))
                ) {
                    el.removeAttribute(attr.name);
                    const originalName = attr.name.substring("data-oe-translate-".length);
                    registerTranslatedAttribute({ el, name: originalName, infoEl });
                }
            }
            if (el.matches("textarea") && (infoEl = tryParseTranslationEl(el.textContent))) {
                el.textContent = infoEl.textContent;
                el.value = infoEl.textContent;
                registerTranslatedAttribute({ el, name: "textContent", infoEl });
            }
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
        }
        this.trigger("on_nodes_marked_translatable_handlers");
    }

    parseTranslationEl(translationHtml) {
        return new DOMParser()
            .parseFromString(translationHtml, "text/html")
            .querySelector("[data-oe-translation-source-sha]");
    }
    /**
     * @param {HTMLElement} translateEl - the element whose attribute
     * translations we want to get.
     * @returns {ElementTranslationInfo} translationInfo
     */
    getTranslationInfo(translateEl) {
        return this.elToTranslationInfoMap.get(translateEl);
    }
    /**
     * @param {HTMLElement} translateEl - element on which the translatable
     * attribute is
     * @param {string} translation - new translation
     * @param {string} attrName - attribute to translate
     */
    updateTranslationMap(translateEl, translation, attrName) {
        if (!this.elToTranslationInfoMap.get(translateEl)) {
            throw new Error(
                `Translation map was not set up: cannot update ${attrName} on ${translateEl.nodeName}`
            );
        }
        this.elToTranslationInfoMap.get(translateEl)[attrName].translation = translation;
    }

    /**
     * Gets the modified translations info
     * @returns {AttributeTranslationInfo[]}
     */
    getDirtyTranslationsInfo() {
        const dirtyInfo = [];
        for (const [translateEl, translationInfo] of this.elToTranslationInfoMap) {
            for (const [attr, data] of Object.entries(translationInfo)) {
                if (
                    this.originalElToTranslationInfoMap.get(translateEl)[attr].translation !==
                    data.translation
                ) {
                    dirtyInfo.push(data);
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
