import { SIGNATURE_CLASS } from "@html_editor/main/signature_plugin";
import { wrapInlinesInBlocks } from "@html_editor/utils/dom";
import { childNodes } from "@html_editor/utils/dom_traversal";

import { Composer } from "@mail/core/common/composer";
import { createDocumentFragmentFromContent } from "@mail/utils/common/html";

import { markup, toRaw, useEffect } from "@odoo/owl";

import { patch } from "@web/core/utils/patch";
import { renderToElement } from "@web/core/utils/render";
import { fixInvalidHTML } from "@html_editor/utils/sanitize";
import { MAIL_PLUGINS } from "./plugins/plugin_sets";
import { Wysiwyg } from "@html_editor/wysiwyg";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { isEmpty } from "@mail/utils/common/format";

patch(Composer, {
    components: { ...Composer.components, Wysiwyg },
});

patch(Composer.prototype, {
    setup() {
        super.setup();
        this.wysiwyg = {
            config: this.wysiwygConfigs,
            editor: undefined,
        };
        this.suggestion = null;
        useEffect(
            (focus) => {
                if (focus && this.wysiwyg.editor) {
                    this.wysiwyg.editor.shared.selection.setCursorEnd(
                        this.wysiwyg.editor.editable.lastChild
                    );
                    this.wysiwyg.editor.shared.selection.focusEditable();
                    this.wysiwyg.editor.editable.focus();
                }
            },
            () => [this.props.autofocus + this.props.composer.autofocus, this.props.placeholder]
        );
    },
    get wysiwygConfigs() {
        return {
            content: fixInvalidHTML(this.props.composer.htmlBody) || "<p><br></p>",
            placeholder: this.placeholder,
            disableVideo: true,
            Plugins: MAIL_PLUGINS,
            classList: ["o-mail-Composer-input", "o-mail-Composer-inputStyle"],
            onChange: this.onChange.bind(this),
            onBlur: this.onBlurWysiwyg.bind(this),
            onEditorReady: () => {
                this.wysiwyg.editor.shared.selection.setCursorEnd(
                    this.wysiwyg.editor.editable.lastChild
                );
                this.wysiwyg.editor.shared.history.addStep();
            },
            suggestionPLuginDependencies: {
                composer: this.props.composer,
                suggestionService: useService("mail.suggestion"),
            },
            composerPLuginDependencies: {
                placeholder: this.placeholder,
                onInput: this.onInput.bind(this),
                onBeforePaste: this.onBeforePaste.bind(this),
                onFocusin: this.onFocusin.bind(this),
                onFocusout: this.onFocusout.bind(this),
                onKeydown: this.onKeydown.bind(this),
            },
        };
    },
    get hasSuggestions() {
        return (
            super.hasSuggestions || Boolean(document.querySelector(".o-mail-Composer-suggestion"))
        );
    },
    saveContent() {
        const composer = toRaw(this.props.composer);
        const saveContentToLocalStorage = (htmlBody, emailAddSignature) => {
            const config = {
                emailAddSignature,
                htmlBody,
            };
            browser.localStorage.setItem(composer.localId, JSON.stringify(config));
        };
        if (this.state.isFullComposerOpen) {
            this.fullComposerBus.trigger("SAVE_CONTENT", {
                onSaveContent: saveContentToLocalStorage,
            });
        } else {
            saveContentToLocalStorage(composer.htmlBody, true);
        }
        super.saveContent();
    },
    restoreContent() {
        const composer = toRaw(this.props.composer);
        try {
            const config = JSON.parse(browser.localStorage.getItem(composer.localId));
            if (config.htmlBody) {
                composer.emailAddSignature = config.emailAddSignature;
                composer.htmlBody = config.htmlBody;
            }
        } catch {
            browser.localStorage.removeItem(composer.localId);
        }
        super.saveContent();
    },
    onClickInsertCannedResponse() {
        const composer = toRaw(this.props.composer);
        if (!isEmpty(this.props.composer.htmlBody)) {
            this.wysiwyg.editor.shared.dom.insert("\u00A0");
        }
        this.wysiwyg.editor.shared.dom.insert("::");
        this.wysiwyg.editor.shared.history.addStep();
        this.wysiwyg.editor.shared.suggestion.start({
            delimiter: "::",
            search: "",
        });
        if (!this.ui.isSmall || !this.env.inChatter) {
            composer.autofocus++;
        }
        super.onClickInsertCannedResponse();
    },
    onInput(ev) {
        super.onInput();
    },
    addEmoji(str) {
        this.wysiwyg.editor.shared.dom.insert(str + "\u00A0");
        this.wysiwyg.editor.shared.history.addStep();
        if (this.ui.isSmall && !this.env.inChatter) {
            return false;
        } else {
            this.wysiwyg.editor.shared.selection.focusEditable();
        }
        super.addEmoji(str);
    },
    clear() {
        if (this.wysiwyg.editor?.editable) {
            this.wysiwyg.editor.editable.innerHTML = "<p><br/></p>";
            this.wysiwyg.editor.shared.selection.setCursorEnd(
                this.wysiwyg.editor.editable.lastChild
            );
            this.wysiwyg.editor.shared.history.addStep();
        }
        super.clear();
    },
    onChange() {
        this.props.composer.htmlBody = this.wysiwyg.editor.getContent();
    },
    onBlurWysiwyg() {
        this.props.composer.htmlBody = this.wysiwyg.editor.getContent();
    },
    /**
     * @param {Editor} editor
     */
    onLoadWysiwyg(editor) {
        this.wysiwyg.editor = editor;
        this.state.isHtmlEditor = true;
    },
    onBeforePaste(selection, ev) {
        if (!this.allowUpload) {
            return;
        }
        if (!ev.clipboardData?.items) {
            return;
        }
        const nonImgFiles = [...ev.clipboardData.items]
            .filter((item) => item.kind === "file" && !item.type.includes("image/"))
            .map((item) => item.getAsFile());
        if (nonImgFiles === 0) {
            return;
        }
        ev.preventDefault();
        for (const file of nonImgFiles) {
            this.attachmentUploader.uploadFile(file);
        }
    },
    /**
     * Construct an editor friendly html representation of the body.
     *
     * @param {string|ReturnType<markup>} defaultBody
     * @param {string|ReturnType<markup>} [signature=""]
     * @returns {ReturnType<markup>}
     */
    formatDefaultBodyForFullComposer(defaultBody, signature = "") {
        const fragment = createDocumentFragmentFromContent(defaultBody).body;
        if (!fragment.firstChild) {
            fragment.append(document.createElement("BR"));
        }
        if (signature) {
            const signatureEl = renderToElement("html_editor.Signature", {
                signature,
                signatureClass: SIGNATURE_CLASS,
            });
            fragment.append(signatureEl);
        }
        const container = document.createElement("DIV");
        container.append(...childNodes(fragment));
        wrapInlinesInBlocks(container, { baseContainerNodeName: "DIV" });
        return markup(container.innerHTML);
    },
});
