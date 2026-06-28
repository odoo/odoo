import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillDestroy, markup, props, proxy, t } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { GoogleTranslator, ChatGPTTranslator } from "./translator";

const RTL_LANGUAGES = new Set(["ar", "he", "fa", "ur", "yi", "ps", "ku", "sd", "ug", "dv", "ha"]);

const POSTPROCESS_GENERATED_CONTENT = (content, baseContainer, document) => {
    let lines = content.split("\n");
    if (baseContainer.toUpperCase() === "P") {
        // P has a margin bottom which is used as an interline, no need to
        // keep empty lines in that case.
        lines = lines.filter((line) => line.trim().length);
    }
    const fragment = document.createDocumentFragment();
    let parentUl, parentOl;
    let lineIndex = 0;
    for (const line of lines) {
        if (line.trim().startsWith("- ")) {
            // Create or continue an unordered list.
            parentUl = parentUl || document.createElement("ul");
            const li = document.createElement("li");
            li.textContent = line.trim().slice(2);
            parentUl.appendChild(li);
        } else if (
            (parentOl && line.startsWith(`${parentOl.children.length + 1}. `)) ||
            (!parentOl && line.startsWith("1. ") && lines[lineIndex + 1]?.startsWith("2. "))
        ) {
            // Create or continue an ordered list (only if the line starts
            // with the next number in the current ordered list (or 1 if no
            // ordered list was in progress and it's followed by a 2).
            parentOl = parentOl || document.createElement("ol");
            const li = document.createElement("li");
            li.textContent = line.slice(line.indexOf(".") + 2);
            parentOl.appendChild(li);
        } else if (line.trim().length === 0) {
            const emptyLine = document.createElement("DIV");
            emptyLine.append(document.createElement("BR"));
            fragment.appendChild(emptyLine);
        } else {
            // Insert any list in progress, and a new block for the current
            // line.
            [parentUl, parentOl].forEach((list) => list && fragment.appendChild(list));
            parentUl = parentOl = undefined;
            const block = document.createElement(line.startsWith("Title: ") ? "h2" : baseContainer);
            block.textContent = line;
            fragment.appendChild(block);
        }
        lineIndex += 1;
    }
    [parentUl, parentOl].forEach((list) => list && fragment.appendChild(list));
    return fragment;
};

export class TranslateDialog extends Component {
    static template = "html_editor.TranslateDialog";
    static components = { Dialog, Dropdown, DropdownItem };
    props = props({
        insert: t.function(),
        close: t.function(),
        sanitize: t.function(),
        baseContainer: t.string().optional("DIV"),
        originalText: t.string(),
        targetLang: t.object({
            languageCode: t.string(),
            languageName: t.string(),
        }),
        document: t.customValidator(t.any(), (p) => p.nodeType === Node.DOCUMENT_NODE),
    });

    setup() {
        const google_translate = new GoogleTranslator("translate_google", "Google Translate");
        this.translators = [google_translate];

        if (this.env.debug) {
            const chatgpt_translate = new ChatGPTTranslator("translate_gpt", "ChatGPT");
            this.translators.push(chatgpt_translate);
        }

        // check if it's a RTL language to adapt the dialog display accordingly
        const lang_base = this.props.targetLang.languageCode.split(/[-_]/)[0].toLowerCase();
        const isRTL = RTL_LANGUAGES.has(lang_base);

        this.notificationService = useService("notification");
        this.state = proxy({
            selectedMessageId: null,
            selectedTranslator: google_translate,
            messages: new Map(),
            translationInProgress: true,
            isRTL,
        });
        this.translate();
        onWillDestroy(() => {
            for (const translator of this.translators) {
                if (translator.pendingRpcPromise) {
                    translator.pendingRpcPromise.abort();
                    delete translator.pendingRpcPromise;
                }
            }
        });
    }

    formatContent(content) {
        const fragment = POSTPROCESS_GENERATED_CONTENT(
            content,
            this.props.baseContainer,
            this.props.document
        );
        let result = "";
        for (const child of fragment.children) {
            this.props.sanitize(child);
            result += child.outerHTML;
        }
        return markup(result);
    }

    onSelectedTranslator(translator) {
        if (this.state.selectedTranslator.id === translator.id) {
            return;
        }
        this.state.selectedTranslator = translator;
        this.state.translationInProgress = true;
        this.translate();
    }

    async translate(originalText = this.props.originalText, targetLang = this.props.targetLang) {
        const messageId = new Date().getTime();
        let translateResult;
        if (!originalText.trim()) {
            translateResult = {
                translatedText: "You didn't select any text.",
                isError: true,
            };
        } else {
            translateResult = await this.state.selectedTranslator.translate(
                originalText,
                targetLang
            );
        }

        if (!this.formatContent(translateResult.translatedText).length) {
            return {
                translatedText: "You didn't select any text.",
                isError: true,
            };
        }

        this.state.translationInProgress = false;
        this.state.messages.set(messageId, {
            translator: this.state.selectedTranslator.name,
            translatedText: translateResult.translatedText,
            isError: translateResult.isError,
        });
        // only select the new translation if there was no error
        if (!translateResult.isError) {
            this.state.selectedMessageId = messageId;
        }
    }

    _cancel() {
        this.props.close();
    }

    _confirm() {
        try {
            this.props.close();
            const translatedText = this.state.messages.get(
                this.state.selectedMessageId
            )?.translatedText;
            this.notificationService.add(_t("Your content was successfully generated."), {
                title: _t("Content generated"),
                type: "success",
            });
            const fragment = POSTPROCESS_GENERATED_CONTENT(
                translatedText || "",
                this.props.baseContainer,
                this.props.document
            );
            this.props.sanitize(fragment);
            this.props.insert(fragment);
        } catch (e) {
            this.props.close();
            throw e;
        }
    }
}
