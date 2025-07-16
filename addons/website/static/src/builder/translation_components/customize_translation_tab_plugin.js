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
        try {
            translationState.isLoading = true;
            const language = this.services.website.currentWebsite.metadata.langName;
            const translationChunks = this.generateTranslationChunks(bodyEl);
            if (translationChunks.length === 0) {
                this.showNotification(
                    _t("No translatable content found in the current webpage."),
                    _t("Translation Info"),
                    "info"
                );
                return;
            }
            const responses = await this.runTranslationChunks(translationChunks, language);
            const success = this.applyTranslationsToDOM(translationChunks, responses);
            if (!success) {
                this.showNotification(
                    _t("Translation aborted due to processing errors."),
                    _t("Translation Error"),
                    "danger"
                );
            }
        } finally {
            translationState.isLoading = false;
        }
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
        const elements = Array.from(
            container.querySelectorAll("[data-oe-translation-state='to_translate']")
        ).filter(
            (el) =>
                !el.closest(".o_not_editable, .o_frontend_to_backend_buttons") &&
                !el.classList.contains("o_translatable_attribute")
        );
        const translationChunks = [];
        let currentChunk = [];
        let currentLength = 0;
        const WRAPPER_LENGTH = '<generatedtext id=""></generatedtext>\n'.length;
        let id = 1;
        for (const el of elements) {
            const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
            while (walker.nextNode()) {
                const node = walker.currentNode;
                const text = node.textContent.replace(/[\u200B-\u200D\uFEFF]/g, "").trim();
                if (!text || this.isSkippableText(text)) {
                    continue;
                }
                const estimatedLength = String(id).length + text.length + WRAPPER_LENGTH;
                if (currentLength + estimatedLength > limit && currentChunk.length) {
                    translationChunks.push(currentChunk);
                    currentChunk = [];
                    currentLength = 0;
                }
                currentChunk.push({ el: node, id: id++, originalText: text });
                currentLength += estimatedLength;
            }
        }
        if (currentChunk.length) {
            translationChunks.push(currentChunk);
        }
        return translationChunks;
    }

    async runTranslationChunks(translationChunks, language) {
        const systemMessage = {
            role: "system",
            content:
                "You are a translation assistant. Your goal is to translate multiple blocks of text.\n" +
                "Instructions:\n" +
                '- Each block is wrapped with <generatedtext id="X">...</generatedtext>\n' +
                "- Return all blocks translated using the same format.\n" +
                "- Do not add HTML or comments.",
        };
        const tasks = translationChunks.map((chunk) => async () => {
            const prompt = chunk
                .map((t) => `<generatedtext id="${t.id}">${t.originalText}</generatedtext>`)
                .join("\n");
            const conversation = [
                systemMessage,
                { role: "user", content: `Translate the following to ${language}:\n\n${prompt}` },
            ];
            return rpc(
                "/html_editor/generate_text",
                {
                    prompt,
                    conversation_history: conversation,
                },
                { silent: true }
            );
        });
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

    applyTranslationsToDOM(translationChunks, responses) {
        const translationMap = new Map();
        for (const chunk of translationChunks) {
            for (const task of chunk) {
                translationMap.set(task.id.toString(), task.el);
            }
        }
        const regex = /<generatedtext id="(\d+)">([\s\S]*?)<\/generatedtext>/g;
        for (const response of responses) {
            let match;
            while ((match = regex.exec(response)) !== null) {
                const [, id, translated] = match;
                const node = translationMap.get(id);
                if (node && translated.trim()) {
                    node.textContent = translated.trim();
                    const parentEl = node.parentElement?.closest("[data-oe-translation-state]");
                    if (parentEl) {
                        parentEl.dataset.oeTranslationState = "translated";
                    }
                } else {
                    this.showNotification(_t("Translation failed"), "Translation Error", "danger");
                    return false;
                }
            }
        }
        return true;
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
