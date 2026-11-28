import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Component, markup, onWillDestroy, useProps, proxy, t, usePlugin } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { GoogleTranslator, ChatGPTTranslator } from "./translator";
import { parseHTML } from "@html_editor/utils/html";
import { DebugModePlugin } from "@web/core/debug_mode_plugin";
import { user } from "@web/core/user";

const RTL_LANGUAGES = new Set(["ar", "he", "fa", "ur", "yi", "ps", "ku", "sd", "ug", "dv", "ha"]);

export class TranslateDialog extends Component {
    static components = { Dialog, Dropdown, DropdownItem };
    static template = "html_editor.TranslateDialog";

    props = useProps({
        close: t.function(),
        document: t.customValidator(t.object(), (p) => p.nodeType === Node.DOCUMENT_NODE),
        onConfirm: t.function(),
        originalHtml: t.string(),
        sanitize: t.function(),
        targetLang: t.object({
            languageCode: t.string(),
            languageName: t.string(),
        }),
    });

    debugMode = usePlugin(DebugModePlugin);

    setup() {
        const google_translate = new GoogleTranslator("translate_google", "Google Translate");
        this.translators = [google_translate];

        if (this.debugMode.isActive() && user.isInternalUser) {
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

    onSelectedTranslator(translator) {
        if (this.state.selectedTranslator.id === translator.id) {
            return;
        }
        this.state.selectedTranslator = translator;
        this.state.translationInProgress = true;
        this.translate();
    }

    /**
     * Sanitize the given HTML and return it as markup for the preview, or
     * `null` if it has no text content.
     *
     * @param {string} html
     * @returns {import("@odoo/owl").Markup | null}
     */
    getPreview(html) {
        const fragment = parseHTML(this.props.document, html || "");
        if (!fragment.textContent.trim()) {
            return null;
        }
        this.props.sanitize(fragment);
        const container = this.props.document.createElement("div");
        container.append(fragment);
        return markup(container.innerHTML);
    }

    async translate(originalHtml = this.props.originalHtml, targetLang = this.props.targetLang) {
        const messageId = new Date().getTime();
        const message = { translator: this.state.selectedTranslator.name };
        if (!parseHTML(this.props.document, originalHtml).textContent.trim()) {
            message.isError = true;
            message.content = _t("You didn't select any text.");
        } else {
            const result = await this.state.selectedTranslator.translate(originalHtml, targetLang);
            const preview = !result.isError && this.getPreview(result.translatedHtml);
            if (preview) {
                message.isError = false;
                message.content = preview;
                message.translatedHtml = result.translatedHtml;
            } else {
                message.isError = true;
                message.content = result.isError
                    ? result.message
                    : _t("The translation returned empty content.");
            }
        }

        this.state.translationInProgress = false;
        this.state.messages.set(messageId, message);
        // only select the new translation if there was no error and under non-debug mode
        if (!message.isError && !this.debugMode.isActive()) {
            this.state.selectedMessageId = messageId;
        }
    }

    _cancel() {
        this.props.close();
    }

    _confirm() {
        try {
            this.props.close();
            const translatedHtml = this.state.messages.get(
                this.state.selectedMessageId
            )?.translatedHtml;
            this.notificationService.add(_t("Your content was successfully generated."), {
                title: _t("Content generated"),
                type: "success",
            });
            this.props.onConfirm(translatedHtml);
        } catch (e) {
            this.props.close();
            throw e;
        }
    }
}
