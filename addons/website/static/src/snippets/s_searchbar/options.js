/** @odoo-module **/

import options from 'web_editor.snippets.options';

options.registry.SearchBar = options.Class.extend({
    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    setSearchType: function (previewMode, widgetValue, params) {
        const form = this.$target.parents('form');
        form.attr('action', params.formAction);

        if (!previewMode) {
            this.trigger_up('snippet_edition_request', {exec: () => {
                const widget = this._requestUserValueWidgets('order_opt')[0];
                const orderBy = widget.getValue("selectDataAttribute");
                const order = widget.$el.find("we-button[data-select-data-attribute='" + orderBy + "']")[0];
                if (order.classList.contains("d-none")) {
                    const defaultOrder = widget.$el.find("we-button[data-name='order_name_asc_opt']")[0];
                    defaultOrder.click(); // open
                    defaultOrder.click(); // close
                }
            }});
        }
    },

    setOrderBy: function (previewMode, widgetValue, params) {
        const form = this.$target.parents('form');
        form.find(".o_search_order_by").attr("value", widgetValue);
    },
});

export default {
    SearchBar: options.registry.SearchBar,
};
