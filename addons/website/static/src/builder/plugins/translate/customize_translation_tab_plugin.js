import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { TranslateWebpageOption } from "./translate_webpage_option";
import { rpc } from "@web/core/network/rpc";
import { BuilderAction } from "@html_builder/core/builder_action";

export class CustomizeTranslationTabPlugin extends Plugin {
    static id = "customizeTranslationTab";
    resources = {
        builder_actions: {
            TranslateWebpageAI,
        },
        translate_options: [
            withSequence(
                100,
                this.getTranslationOptionBlock("translate-webpage", _t("Translation"), {
                    OptionComponent: TranslateWebpageOption,
                })
            ),
        ],
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

class TranslateWebpageAI extends BuilderAction {
    static id = "translateWebpageAI";

    async apply({ editingElement: fieldEl, value: language }) {
        const elements = this.getTranslatableElements(fieldEl);
        const translationTasks = this.buildTranslationTasks(elements, language);

        const responses = await this.runTranslationTasks(translationTasks, language);
        const success = this.applyTranslatedResults(translationTasks, responses);

        if (!success) {
            this.showNotification("Translation aborted due to a failure in processing.", "Translation Error", "danger");
        }
    }

    getTranslatableElements(container) {
        return Array.from(container.querySelectorAll("[data-oe-translation-state='to_translate']"));
    }

    isSkippableText(text) {
        const trimmed = text.trim();
        return trimmed === "" || /^[|·\-–—•]+$/.test(trimmed);
    }

    buildTranslationTasks(elements, language) {
        const tasks = [];
        let id = 1;
        for (const el of elements) {
            const text = el.textContent.replace(/[\u200B-\u200D\uFEFF]/g, "").trim();
            if (!text || this.isSkippableText(text)) continue;
            tasks.push({ el, id: id++, text });
        }
        return tasks;
    }


    async runTranslationTasks(tasks, language) {
        const chunks = this.chunkTranslationTasksByLength(tasks, 2000);
        const allResults = [];

        const systemMessage = {
            role: "system",
            content:
                "You are a translation assistant. Your goal is to translate multiple blocks of text.\n" +
                "Instructions:\n" +
                "- Each block is wrapped with <generatedtext id=\"X\">...</generatedtext>\n" +
                "- Return all blocks translated using the same format.\n" +
                "- Do not add HTML or comments.",
        };

        for (const chunk of chunks) {
            const prompt = chunk.map(t => `<generatedtext id="${t.id}">${t.text}</generatedtext>`).join("\n");
            const conversation = [
                systemMessage,
                { role: "user", content: `Translate the following to ${language}:\n\n${prompt}` },
            ];
            const response = await rpc("/web_editor/generate_text", {
                prompt,
                conversation_history: conversation,
            }, { shadow: true });
            allResults.push(response);
        }
        return allResults;
    }

    chunkTranslationTasksByLength(tasks, limit) {
        const chunks = [];
        let currentChunk = [];
        let currentLength = 0;
        for (const task of tasks) {
            const promptLine = `<generatedtext id="${task.id}">${task.text}</generatedtext>\n`;
            if (currentLength + promptLine.length > limit) {
                chunks.push(currentChunk);
                currentChunk = [];
                currentLength = 0;
            }
            currentChunk.push(task);
            currentLength += promptLine.length;
        }
        if (currentChunk.length) {
            chunks.push(currentChunk);
        }
        return chunks;
    }

    applyTranslatedResults(tasks, responses) {
        const map = new Map(tasks.map(t => [t.id.toString(), t.el]));
        const regex = /<generatedtext id="(\d+)">([\s\S]*?)<\/generatedtext>/g;

        for (const response of responses) {
            let match;
            while ((match = regex.exec(response)) !== null) {
                const [, id, translated] = match;
                const el = map.get(id);
                if (el && translated.trim()) {
                    this.applyTextNodeTranslation(el, translated.trim());
                    el.dataset.oeTranslationState = "translated";
                } else {
                    this.showNotification(`Translation failed for ID ${id}`, "Translation Error", "danger");
                    return false;
                }
            }
        }
        return true;
    }

    applyTextNodeTranslation(el, translatedText) {
        const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null, false);
        const textNodes = [];
        while (walker.nextNode()) {
            const node = walker.currentNode;
            if (node.textContent.trim()) {
                textNodes.push(node);
            }
        }
        if (textNodes.length === 0) return;
        textNodes[0].textContent = translatedText;
        for (let i = 1; i < textNodes.length; i++) {
            textNodes[i].textContent = "";
        }
    }

    showNotification(message, title, type, context) {
        context.services.notification.add(message, {
            title: _t(title),
            type,
            sticky: true,
        });
    }
}

registry.category("translation-plugins").add(CustomizeTranslationTabPlugin.id, CustomizeTranslationTabPlugin);
