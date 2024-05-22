/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";

options.registry.SnippetGroup = options.Class.extend({
    /**
     * @override
     */
    async onBuilt() {
        await this._super(...arguments);
        this.trigger_up('open_add_snippet_dialog', {
            snippetGroup: this.$target[0].dataset.snippetGroup,
            initialSnippetEl: this.$target[0],
        });
    },
});
