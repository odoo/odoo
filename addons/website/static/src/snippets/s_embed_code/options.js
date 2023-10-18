/** @odoo-module **/
import { Dialog } from "@web/core/dialog/dialog";
import { CodeEditor } from "@web/core/code_editor/code_editor";
import options from '@web_editor/js/editor/snippets.options';
import { _t } from "@web/core/l10n/translation";

import { Component, useState } from "@odoo/owl";

class CodeEditorDialog extends Component {
    static template = "website.s_embed_code_dialog";
    static components = { Dialog, CodeEditor };
    setup() {
        this.state = useState({ value: this.props.value });
    }
    onCodeChange(newValue) {
        this.state.value = newValue;
    }
    onConfirm() {
        this.props.confirm(this.state.value);
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
        const code = $container.html().trim();

        await new Promise(resolve => {
            this.dialog.add(CodeEditorDialog, {
                title: _t("Edit embedded code"),
                value: code,
                mode: "xml",
                confirm: (newValue) => {
                   $container[0].innerHTML = newValue;
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
