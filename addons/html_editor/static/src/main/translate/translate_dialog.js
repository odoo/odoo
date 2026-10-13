import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillDestroy, useProps, proxy, t, usePlugin } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { GoogleTranslator, ChatGPTTranslator } from "./translator";
import { DebugModePlugin } from "@web/core/debug_mode_plugin";

const RTL_LANGUAGES = new Set(["ar", "he", "fa", "ur", "yi", "ps", "ku", "sd", "ug", "dv", "ha"]);

export class TranslateDialog extends Component {
    static components = { Dialog, Dropdown, DropdownItem };
    static template = "html_editor.TranslateDialog";

    props = useProps({
        baseContainer: t.string().optional("DIV"),
        close: t.function(),
        document: t.customValidator(t.object(), (p) => p.nodeType === Node.DOCUMENT_NODE),
        insert: t.function(),
        fragment: t.customValidator(t.object(), (p) => p.nodeType === Node.DOCUMENT_FRAGMENT_NODE),
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

        if (this.debugMode.isActive()) {
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

    async translate(
        fragment = this.props.fragment,
        targetLang = this.props.targetLang,
        baseContainer = this.props.baseContainer,
        document = this.props.document
    ) {
        const messageId = new Date().getTime();
        let translateResult;
        if (!fragment.textContent.trim()) {
            translateResult = {
                translatedContent: { textContent: "You didn't select any text." },
                isError: true,
            };
        } else {
            translateResult = await this.state.selectedTranslator.translate(
                fragment,
                targetLang,
                baseContainer,
                document
            );
        }
        if (!translateResult.isError && !translateResult.translatedContent?.textContent?.trim()) {
            translateResult = {
                translatedContent: { textContent: "The translation returned empty content." },
                isError: true,
            };
        }

        this.state.translationInProgress = false;
        this.state.messages.set(messageId, {
            translator: this.state.selectedTranslator.name,
            translatedContent: translateResult.isError
                ? translateResult.translatedContent
                : this.props.sanitize(translateResult.translatedContent),
            isError: translateResult.isError,
        });
        // only select the new translation if there was no error and under non-debug mode
        if (!translateResult.isError && !this.debugMode.isActive()) {
            this.state.selectedMessageId = messageId;
        }
    }

    _cancel() {
        this.props.close();
    }

    _confirm() {
        try {
            this.props.close();
            const translatedContent = this.state.messages.get(
                this.state.selectedMessageId
            )?.translatedContent;
            this.notificationService.add(_t("Your content was successfully generated."), {
                title: _t("Content generated"),
                type: "success",
            });
            this.props.insert(translatedContent);
        } catch (e) {
            this.props.close();
            throw e;
        }
    }
}
