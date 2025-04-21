import options from "@web_editor/js/editor/snippets.options";

options.registry.countdown = options.registry.countdown.extend({
    /**
     * Override UI visibility to handle new endAction values.
     *
     * @override
     */
    updateUIVisibility: async function () {
        await this._super(...arguments);
        const dataset = this.$target[0].dataset;

        // End Action UI
        this.$el.find('.toggle-edit-message')
            .toggleClass('d-none', 
                dataset.endAction === 'prevent_sale_zero_priced_product' ||
                dataset.endAction === 'hide_product'
            );
    },
});
