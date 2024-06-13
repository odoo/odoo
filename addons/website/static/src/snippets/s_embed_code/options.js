/** @odoo-module **/
import { Dialog } from "@web/core/dialog/dialog";
import { CodeEditor } from "@web/core/code_editor/code_editor";
import { useService } from "@web/core/utils/hooks";
import options from '@web_editor/js/editor/snippets.options';
import { _t } from "@web/core/l10n/translation";
import { EditHeadBodyDialog } from "@website/components/edit_head_body_dialog/edit_head_body_dialog";
import { cloneContentEls } from "@website/js/utils";

import { Component, useState } from "@odoo/owl";

class CodeEditorDialog extends Component {
    static template = "website.s_embed_code_dialog";
    static components = { Dialog, CodeEditor };
    static props = {
        title: String,
        value: String,
        mode: String,
        confirm: Function,
        close: Function,
    };
    setup() {
        this.dialog = useService("dialog");
        this.state = useState({ value: this.props.value });
    }
    onCodeChange(newValue) {
        this.state.value = newValue;
    }
    onConfirm() {
        this.props.confirm(this.state.value);
        this.props.close();
    }
    onInjectHeadOrBody() {
        this.dialog.add(EditHeadBodyDialog);
        this.props.close();
    }
}

options.registry.EmbedCode = options.Class.extend({
    init() {
        this._super(...arguments);
        this.dialog = this.bindService("dialog");
    },
    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    async editCode() {
        const $container = this.$target.find('.s_embed_code_embedded');
        const templateEl = this.$target[0].querySelector("template.s_embed_code_saved");
        const embedContent = templateEl.innerHTML.trim();

        await new Promise(resolve => {
            this.dialog.add(CodeEditorDialog, {
                title: _t("Edit embedded code"),
                value: embedContent,
                mode: "xml",
                confirm: (newValue) => {
                    // Removes scripts tags from the DOM as we don't want them
                    // to interfere during edition, but keeps them in a
                    // `<template>` that will be saved to the database.
                    templateEl.content.replaceChildren(cloneContentEls(newValue, true));
                    $container[0].replaceChildren(cloneContentEls(newValue));
                }
            }, {
                onClose: resolve,
            });
        });
    },
});

export default {
    EmbedCode: options.registry.EmbedCode,
};
