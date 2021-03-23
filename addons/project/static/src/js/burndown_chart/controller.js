/** @odoo-module alias=project.BurndownChartController **/
import * as GraphController from 'web.GraphController';

export default GraphController.extend({
    /**
     * @override
     */
    updateButtons: function() {
        const result = this._super.apply(this, arguments);
        if (this.$buttons) {
            const state = this.model.get();
            this.$buttons
                .find('.o_graph_button[data-mode="pie"]')
                .addClass('d-none');
            this.$buttons
                .find('.o_graph_button[data-mode="stack"]')
                .data('stacked', state.stacked)
                .toggleClass('active', state.stacked)
                .toggleClass('o_hidden', state.mode === 'pie');
        }
        return result;
    }
});
