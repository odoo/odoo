/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";

options.registry.sale_order_display = options.Class.extend({    
    onBuilt() {
        this._refreshWidget();
    },

    async displayConfirmed(previewMode, value, params) {
        this.$target[0].dataset.showConfirm = value === 'true';
        this._refreshWidget();
    },

    async displayView(previewMode, value, params) {
        this.$target[0].dataset.view = value;
        this._refreshWidget();
    },

    async displayLimit(previewMode, value, params) {
        this.$target[0].dataset.limit = value;
        this._refreshWidget();
    },

    _refreshWidget() {
        this.trigger_up('widgets_start_request', {
            $target: this.$target,
            editableMode: true,
        });
    },

    _computeWidgetState(methodName) {
        const el = this.$target[0];
        if (!el) {
            return this._super(...arguments);
        };

        switch (methodName) {
            case "displayConfirmed": return el.dataset?.showConfirm ?? 'false';
            case "displayView": return el.dataset?.view ?? 'list';
            case "displayLimit": return el.dataset?.limit ?? '3';
            default: return this._super(...arguments);
        }
    }

});

export default {
    sale_order_display: options.registry.sale_order_display,
};
