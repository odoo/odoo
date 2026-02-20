import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillDestroy, markup } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { GoogleTranslator, ChatGPTTranslator } from "./translator";

const POSTPROCESS_GENERATED_CONTENT = (content, baseContainer) => {
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
            li.innerText = line.trim().slice(2);
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
            li.innerText = line.slice(line.indexOf(".") + 2);
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
            block.innerText = line;
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
    static props = {
        insert: { type: Function },
        close: { type: Function },
        sanitize: { type: Function },
        baseContainer: { type: String, optional: true },
        originalText: String,
        targetLang: { type: Object, shape: { languageCode: String, languageName: String } },
    };
    static defaultProps = {
        baseContainer: "DIV",
    };

    setup() {
        const google_translate = new GoogleTranslator("translate_google", "Google Translate");
        const chatgpt_translate = new ChatGPTTranslator("translate_gpt", "ChatGPT");
        this.translators = [google_translate, chatgpt_translate];

        this.notificationService = useService("notification");
        this.state = useState({
            selectedMessageId: null,
            selectedTranslator: google_translate,
            messages: new Map(),
            translationInProgress: true,
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
        const fragment = POSTPROCESS_GENERATED_CONTENT(content, this.props.baseContainer);
        let result = "";
        for (const child of fragment.children) {
            this.props.sanitize(child, { IN_PLACE: true });
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
                this.props.baseContainer
            );
            this.props.sanitize(fragment, { IN_PLACE: true });
            this.props.insert(fragment);
        } catch (e) {
            this.props.close();
            throw e;
        }
    }
}
