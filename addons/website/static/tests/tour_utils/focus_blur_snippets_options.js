/** @odoo-module **/

import options from "web_editor.snippets.options";

const FocusBlur = options.Class.extend({
    onFocus() {
        window.focusBlurSnippetsResult.push(`focus ${this.focusBlurName}`);
    },
    onBlur() {
        window.focusBlurSnippetsResult.push(`blur ${this.focusBlurName}`);
    },
});

options.registry.FocusBlurParent = FocusBlur.extend({focusBlurName: 'parent'});
options.registry.FocusBlurChild1 = FocusBlur.extend({focusBlurName: 'child1'});
options.registry.FocusBlurChild2 = FocusBlur.extend({focusBlurName: 'child2'});
