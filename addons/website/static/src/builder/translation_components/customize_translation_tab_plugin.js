import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { TranslateWebpageOption } from "./translate_webpage_option";
import { rpc } from "@web/core/network/rpc";
import { BuilderAction } from "@html_builder/core/builder_action";
import { reactive } from "@odoo/owl";

export class CustomizeTranslationTabPlugin extends Plugin {
    static id = "customizeTranslationTab";
    static shared = ["getTranslationState"];
    resources = {
        builder_actions: {
            TranslateToAction,
        },
        translate_options: [
            withSequence(
                1,
                this.getTranslationOptionBlock("translate-webpage", _t("Translation"), {
                    OptionComponent: TranslateWebpageOption,
                    props: {
                        getTranslationState: () => this.translationState,
                    },
                })
            ),
        ],
    };

    setup() {
        this.translationState = reactive({
            isLoading: undefined,
        });
    }

    getTranslationState() {
        return this.translationState;
    }

    getTranslationOptionBlock(id, name, options) {
        options.selector = "*";
        return {
            id: id,
            snippetModel: {},
            element: this.document.body,
            options: [options],
            isRemovable: false,
            isClonable: false,
            containerTopButtons: [],
        };
    }
}

class TranslateToAction extends BuilderAction {
    static id = "translateWebpageAI";
    static dependencies = ["customizeTranslationTab"];

    async apply({ editingElement: bodyEl }) {
        const translationState = this.dependencies.customizeTranslationTab.getTranslationState();
        translationState.isLoading = true;
        const language = this.services.website.currentWebsite.metadata.lang;
        const translationChunks = this.generateTranslationChunks(bodyEl);
        if (translationChunks.length == 0) {
            this.showNotification(
                _t("No translatable content found in the current webpage."),
                "Translation Info",
                "info"
            );
            translationState.isLoading = false;
            return;
        }
        const responses = await this.runTranslationChunks(translationChunks, language);
        const isSuccess = this.applyTranslationsToDOM(translationChunks, responses);
        this.cleanEmptyInlineElements(bodyEl);
        translationState.isLoading = false;
        if (!isSuccess) {
            this.showNotification(
                _t("Translation aborted due to a failure in processing."),
                "Translation Error",
                "danger"
            );
        }
    }

    getTranslatableElements(bodyEl) {
        return Array.from(
            bodyEl.querySelectorAll("[data-oe-translation-state='to_translate']")
        ).filter((el) => !el.closest(".o_not_editable, .o_frontend_to_backend_buttons"));
    }

    isSkippableText(text) {
        const trimmed = text.trim();
        const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        const PHONE_REGEX = /^[+\d][\d\s\-().]{6,}$/;
        const URL_REGEX = /^(https?:\/\/)?([\w-]+\.)+[\w-]+(:\d+)?(\/[\w\-./?%&=]*)?(#\S*)?$/i;
        const LETTER_OR_NUMBER_REGEX = /\p{L}|\p{N}/u;
        return (
            !LETTER_OR_NUMBER_REGEX.test(trimmed) ||
            EMAIL_REGEX.test(trimmed) ||
            PHONE_REGEX.test(trimmed) ||
            URL_REGEX.test(trimmed)
        );
    }

    generateTranslationChunks(container, limit = 2000) {
        const elements = this.getTranslatableElements(container);
        const translationChunks = [];
        let currentChunk = [];
        let currentLength = 0;
        const WRAPPER_LENGTH = '<generatedtext id=""></generatedtext>\n'.length;
        let id = 1;
        for (const el of elements) {
            const originalText = el.textContent.replace(/[\u200B-\u200D\uFEFF]/g, "").trim();
            if (!originalText || this.isSkippableText(originalText)) {
                continue;
            }
            const idLength = String(id).length;
            const estimatedLength = idLength + originalText.length + WRAPPER_LENGTH;
            if (currentLength + estimatedLength > limit && currentChunk.length) {
                translationChunks.push(currentChunk);
                currentChunk = [];
                currentLength = 0;
            }
            currentChunk.push({ el, id: id++, originalText });
            currentLength += estimatedLength;
        }
        if (currentChunk.length) {
            translationChunks.push(currentChunk);
        }
        return translationChunks;
    }

    async runTranslationChunks(translationChunks, language) {
        const allResults = [];
        const systemMessage = {
            role: "system",
            content:
                "You are a translation assistant. Your goal is to translate multiple blocks of text.\n" +
                "Instructions:\n" +
                '- Each block is wrapped with <generatedtext id="X">...</generatedtext>\n' +
                "- Return all blocks translated using the same format.\n" +
                "- Do not add HTML or comments.",
        };
        for (const translationChunk of translationChunks) {
            const prompt = translationChunk
                .map((t) => `<generatedtext id="${t.id}">${t.originalText}</generatedtext>`)
                .join("\n");
            const conversation = [
                systemMessage,
                { role: "user", content: `Translate the following to ${language}:\n\n${prompt}` },
            ];
            const response = await rpc(
                "/html_editor/generate_text",
                {
                    prompt,
                    conversation_history: conversation,
                },
                { shadow: true }
            );
            allResults.push(response);
        }
        return allResults;
    }

    applyTranslationsToDOM(translationChunks, responses) {
        const translationChunkMap = new Map();
        for (const translationChunk of translationChunks) {
            for (const task of translationChunk) {
                translationChunkMap.set(task.id.toString(), task.el);
            }
        }
        const regex = /<generatedtext id="(\d+)">([\s\S]*?)<\/generatedtext>/g;
        for (const response of responses) {
            let match;
            while ((match = regex.exec(response)) !== null) {
                const [, id, translated] = match;
                const el = translationChunkMap.get(id);
                if (el && translated.trim()) {
                    this.insertTranslatedTextIntoNode(el, translated.trim());
                } else {
                    this.showNotification(_t("Translation failed"), "Translation Error", "danger");
                    return false;
                }
            }
        }
        return true;
    }

    insertTranslatedTextIntoNode(el, translatedText) {
        const textNodes = [];
        const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null, false);
        while (walker.nextNode()) {
            const node = walker.currentNode;
            if (node.textContent.trim()) {
                textNodes.push(node);
            }
        }
        if (!textNodes.length) {
            el.textContent = translatedText;
            return;
        }
        const targetNode =
            textNodes.find((node) => !/^[\s\u200B]*$/.test(node.textContent)) ||
            textNodes[textNodes.length - 1];
        targetNode.textContent = translatedText;
        textNodes.forEach((node) => {
            if (node !== targetNode) {
                node.textContent = "";
            }
        });
        let parentEl = targetNode.parentNode;
        while (parentEl && parentEl.dataset.oeTranslationState !== "to_translate") {
            parentEl = parentEl.parentNode;
        }
        if (parentEl) {
            parentEl.dataset.oeTranslationState = "translated";
        }
    }

    cleanEmptyInlineElements(root) {
        const inlineTags = ["STRONG", "EM", "U", "SPAN", "I", "B", "SMALL"];
        const mediaTags = ["IMG", "SVG", "PICTURE", "VIDEO"];
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
        const elementsToRemove = [];
        while (walker.nextNode()) {
            const el = walker.currentNode;
            const isInline = inlineTags.includes(el.tagName);
            const isEmptyText = el.textContent.trim() === "";
            const hasNoAttributes = el.attributes.length === 0;
            // Case 1: Element is empty and has no useful attributes
            const isFullyEmpty = isInline && isEmptyText && hasNoAttributes;
            // Case 2: Element has only one child that is also empty
            const hasOneEmptyChild =
                isInline &&
                el.childNodes.length === 1 &&
                el.firstChild.nodeType === Node.ELEMENT_NODE &&
                el.firstChild.textContent.trim() === "" &&
                !mediaTags.includes(el.firstChild.tagName);
            if (isFullyEmpty || hasOneEmptyChild) {
                elementsToRemove.push(el);
            }
        }
        for (const el of elementsToRemove) {
            el.remove();
        }
    }

    showNotification(message, title, type) {
        this.services.notification.add(message, {
            title: title,
            type,
            sticky: true,
        });
    }
}

registry
    .category("translation-plugins")
    .add(CustomizeTranslationTabPlugin.id, CustomizeTranslationTabPlugin);
