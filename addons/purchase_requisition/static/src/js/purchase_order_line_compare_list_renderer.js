/** @odoo-module **/

import ListRenderer from 'web.ListRenderer';


const PurchaseOrderLineCompareListRenderer = ListRenderer.extend({

    init: function (parent, state, params) {
        this._super(...arguments);
        this.best_date_ids = this.state.context.params.best_date_ids;
        this.best_price_ids = this.state.context.params.best_price_ids;
        this.best_price_unit_ids = this.state.context.params.best_price_unit_ids;
    },

    /**
     * @override
     * @private
     * @returns {Promise}
     */
     _renderRow: function (record) {
        const $tr = this._super(...arguments);
        if (this.best_date_ids.includes(record.res_id)) {
            $tr.find('[name="date_planned"]').toggleClass('text-success');
        }
        if (this.best_price_ids.includes(record.res_id)) {
            $tr.find('[name="price_subtotal"]').toggleClass('text-success');
        }
        if (this.best_price_unit_ids.includes(record.res_id)) {
            $tr.find('[name="price_unit"]').toggleClass('text-success');
        }
        return $tr;
    }
});

export default PurchaseOrderLineCompareListRenderer;
