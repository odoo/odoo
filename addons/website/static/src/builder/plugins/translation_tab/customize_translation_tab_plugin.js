import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { reactive } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { uniqueId } from "@web/core/utils/functions";
import { TranslateWebpageOption } from "./translate_webpage_option";

/**
 * @typedef { Object } CustomizeTranslationTabShared
 * @property { CustomizeTranslationTabPlugin['getTranslationState'] } getTranslationState
 */

/**
 * Action to translate the entire webpage using AI.
 */
class TranslateToAction extends BuilderAction {
    static id = "translateWebpageAI";
    static dependencies = ["customizeTranslationTab", "translation", "history"];

    setup() {
        this.canTimeout = false;
    }
    async apply() {
        const translationState = this.dependencies.customizeTranslationTab.getTranslationState();
        this.elToTranslationInfoMap = this.dependencies.translation.getElToTranslationInfoMap();
        try {
            translationState.isTranslating = true;
            const language = this.services.website.currentWebsite.metadata.langName;
            const { translationChunks, translationMap } = this.generateTranslationChunks(
                this.editable
            );
            if (!translationChunks.length) {
                this.showNotification(
                    _t("No translatable content found in the current webpage."),
                    _t("Translation Info"),
                    "info"
                );
                return;
            }
            const responses = await this.runTranslationChunks(translationChunks, language);
            const failedNodeCount = this.applyTranslationsToDOM(translationMap, responses);
            if (failedNodeCount > 0) {
                this.showNotification(
                    _t(
                        "%s text blocks were skipped during translation. Please try again.",
                        failedNodeCount
                    ),
                    _t("Translation Error"),
                    "danger"
                );
            }
        } finally {
            translationState.isTranslating = false;
        }
    }

    /**
     * Determines if a text node should be skipped for translation.
     * Skip if it contains no letters/numbers or is likely an email, phone
     * number or URL.
     *
     * @param {string} textValue - Text content of the node
     * @return {boolean} True if the node should be skipped
     */
    shouldSkipTranslation(textValue) {
        const text = textValue.replace(/[\u200B-\u200D\uFEFF]/g, "").trim();
        const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        const PHONE_REGEX = /^[+\d][\d\s\-().]{6,}$/;
        const URL_REGEX = /^(https?:\/\/)?([\w-]+\.)+[\w-]+(:\d+)?(\/[\w\-./?%&=]*)?(#\S*)?$/i;
        const LETTER_OR_NUMBER_REGEX = /\p{L}|\p{N}/u;
        return (
            !LETTER_OR_NUMBER_REGEX.test(text) ||
            EMAIL_REGEX.test(text) ||
            PHONE_REGEX.test(text) ||
            URL_REGEX.test(text)
        );
    }

    /**
     * Collects translatable text nodes in the DOM and group them into chunks.
     * Each chunk is limited in size to avoid overloading the translation API.
     *
     * @param {HTMLElement} containerEl - Root element
     * @param {number} limit - Max characters per chunk
     * @return {Object} { List of chunks, Map of original nodes by their IDs }
     */
    generateTranslationChunks(containerEl, limit = 2000) {
        const elements = Array.from(
            containerEl.querySelectorAll("[data-oe-translation-state='to_translate']")
        ).filter(
            (el) =>
                // TODO: fix `o_frontend_to_backend_buttons` to have no
                // attribute `data-oe-translation-state`
                !el.closest(".o_not_editable, .o_frontend_to_backend_buttons, .o_brand_promotion")
        );

        const translationChunks = [];
        const translationMap = new Map();
        let currentChunk = [];
        let currentChunkLength = 0;
        const flushChunk = () => {
            if (currentChunk.length) {
                translationChunks.push(currentChunk);
                currentChunk = [];
                currentChunkLength = 0;
            }
        };

        const enqueueTranslation = (el, id, text, attr = null) => {
            if (this.shouldSkipTranslation(text)) {
                return;
            }
            const itemSize = JSON.stringify({ id, text }).length;
            if (currentChunkLength + itemSize > limit && currentChunk.length) {
                flushChunk();
            }
            currentChunk.push({ el, id, originalText: text });
            const mapValue = attr ? { el, attribute: attr } : el;
            translationMap.set(id, mapValue);
            currentChunkLength += itemSize;
        };

        for (const el of elements) {
            // Special case: translate default values of textarea/input elements.
            // They may also have `o_translatable_text` (e.g. when using placeholders).
            if (el.classList.contains("o_translatable_text")) {
                const text = el.textContent;
                enqueueTranslation(el, uniqueId("ta_"), text, "textContent");
            }
            if (el.classList.contains("o_translatable_attribute")) {
                for (const attr of ["alt", "title", "placeholder", "value"]) {
                    if (el.hasAttribute(attr)) {
                        const attrValue = el.getAttribute(attr);
                        enqueueTranslation(el, uniqueId("ta_"), attrValue, attr);
                    }
                }
            } else {
                const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
                while (walker.nextNode()) {
                    const node = walker.currentNode;
                    const text = node.textContent;
                    enqueueTranslation(node, uniqueId("t_"), text);
                }
            }
        }
        // If any chunk left, flush it
        flushChunk();
        return { translationChunks, translationMap };
    }

    /**
     * Translates each chunk with limited concurrency.
     *
     * @param {Array} translationChunks - List of chunks to translate
     * @param {string} language - Target language code
     * @return {Promise<Array>} Server responses for each chunk
     */
    async runTranslationChunks(translationChunks, language) {
        const systemMessage = {
            role: "system",
            content:
                "You are a translation assistant. Your goal is to translate multiple text blocks.\n" +
                "Instructions:\n" +
                "- Input will be an array of objects: [{id: string, text: string}, ...]\n" +
                "- Strictly preserve the trailing and leading spaces in 'text'.\n" +
                "- Only translate the 'text' field, without changing the meaning.\n" +
                "    - Example:\n" +
                "       -' Hello ' should be translated to ' Hola ' (with spaces preserved).\n" +
                "-      -'Enhance Your' and 'Experience' should be translated separately, preserving their individual meanings.\n" +
                "- Return ONLY valid JSON in the same array format, replacing 'text' with the translated text.\n" +
                "- Do not add comments or extra fields.",
        };

        const tasks = translationChunks.map((chunk) => async () => {
            const prompt = JSON.stringify(
                chunk.map(({ id, originalText }) => ({ id, text: originalText }))
            );
            const conversation = [
                systemMessage,
                { role: "user", content: `Translate the following to ${language}:\n\n${prompt}` },
            ];
            return rpc(
                "/html_editor/generate_text",
                {
                    prompt: prompt,
                    conversation_history: conversation,
                },
                { silent: true }
            );
        });

        // Limit concurrency to avoid
        // "Oops, it looks like our AI is unreachable!" error
        // when too many requests are sent in a short time.
        const concurrencyLimit = 5;
        const allResults = [];
        const executing = new Set();
        for (const task of tasks) {
            if (executing.size >= concurrencyLimit) {
                await Promise.race(executing);
            }
            const promise = task().finally(() => executing.delete(promise));
            executing.add(promise);
            allResults.push(promise);
        }
        return Promise.all(allResults);
    }

    /**
     * Parses translation responses and update DOM nodes in-place.
     * Returns the failed translation nodes count.
     *
     * @param {Map<string, Object} translationMap - Original Nodes mapped by their IDs
     * @param {Array} responses - Translated text responses
     * @return {Number} Count of failed translation nodes
     */
    applyTranslationsToDOM(translationMap, responses) {
        let numOfFailedTranslationNodes = 0;
        const allMutations = [];

        for (const response of responses) {
            let translations;
            try {
                translations = JSON.parse(response);
            } catch {
                numOfFailedTranslationNodes += translationMap.size;
                continue;
            }

            for (const { id, text } of translations) {
                const node = translationMap.get(id);
                if (!node || !text.trim()) {
                    numOfFailedTranslationNodes++;
                    continue;
                }
                if (id.startsWith("t_")) {
                    node.textContent = text;
                    const parentEl = node.parentElement?.closest("[data-oe-translation-state]");
                    if (parentEl) {
                        parentEl.dataset.oeTranslationState = "translated";
                    }
                } else if (id.startsWith("ta_")) {
                    const { el, attribute } = node;
                    const attributeInfo = this.elToTranslationInfoMap.get(el)?.[attribute];
                    if (attributeInfo) {
                        const oldValue = attributeInfo.translation;
                        const oldTranslationState = el.dataset.oeTranslationState;
                        const applyAttributeChange = (attr, value) => {
                            attr.translation = value;
                            el.dataset.oeTranslationState =
                                value === oldValue ? oldTranslationState : "translated";
                            if (attribute === "textContent" || attribute === "value") {
                                el.value = value;
                            } else {
                                el.setAttribute(attribute, value);
                            }
                        };

                        allMutations.push({
                            apply: () => applyAttributeChange(attributeInfo, text),
                            revert: () => applyAttributeChange(attributeInfo, oldValue),
                        });
                    }
                }
            }
        }

        if (allMutations.length > 0) {
            this.dependencies.history.applyCustomMutation({
                apply: () => {
                    for (const mutation of allMutations) {
                        mutation.apply();
                    }
                },
                revert: () => {
                    for (let i = allMutations.length - 1; i >= 0; i--) {
                        allMutations[i].revert();
                    }
                },
            });
            // Single addStep for all translations, so that undo/redo is easier
            // to manage for the user.
            this.dependencies.history.addStep();
        }

        return numOfFailedTranslationNodes;
    }

    showNotification(message, title, type) {
        this.services.notification.add(message, {
            title: title,
            type,
            sticky: true,
        });
    }
}

/**
 * Plugin that adds a "Translation" tab to the sidebar and provides AI-powered
 * options to translate the entire webpage.
 */
export class CustomizeTranslationTabPlugin extends Plugin {
    static id = "customizeTranslationTab";
    static shared = ["getTranslationState"];

    translationState = reactive({
        isTranslating: false,
    });

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            TranslateToAction,
        },
        translate_options: [
            withSequence(
                1,
                this.getTranslationOptionBlock(
                    "translate-webpage",
                    _t("Translation"),
                    TranslateWebpageOption
                )
            ),
        ],
    };

    getTranslationState() {
        return this.translationState;
    }

    /**
     * Prepares and returns a translation option block for the sidebar.
     *
     * @param {string} id - Unique identifier for the block
     * @param {string} name - Display name for the block
     * @param {Object} Option - Option component
     */
    getTranslationOptionBlock(id, name, Option) {
        const el = this.document.createElement("div");
        el.dataset.name = name;
        this.document.body.appendChild(el);

        return {
            id: id,
            snippetModel: {},
            element: el,
            options: [Option],
            isRemovable: false,
            isClonable: false,
            containerTopButtons: [],
        };
    }
}

registry
    .category("translation-plugins")
    .add(CustomizeTranslationTabPlugin.id, CustomizeTranslationTabPlugin);
