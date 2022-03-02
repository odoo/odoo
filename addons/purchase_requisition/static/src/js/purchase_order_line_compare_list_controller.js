/** @odoo-module **/

import ListController from 'web.ListController';

const PurchaseOrderLineCompareListController = ListController.extend({

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    init: function (parent, model, renderer, params) {
        this.context = renderer.state.getContext();
        this.best_date_ids = this.context.params.best_date_ids;
        this.best_price_ids = this.context.params.best_price_ids;
        this.best_price_unit_ids = this.context.params.best_price_unit_ids;
        return this._super(...arguments);
    },

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------
    /**
     * @override
     */
    _onButtonClicked: function (ev) {
        if (ev.data.attrs.class && ev.data.attrs.class.split(' ').includes('o_clear_qty_buttons')) {
            ev.stopPropagation();
            var self = this;
            return this._callButtonAction(ev.data.attrs, ev.data.record).then(() => {
                const context = this.model.localData[0] && this.model.localData[0].getContext() || {};
                return self._rpc({
                    model: "purchase.order",
                    method: 'get_tender_best_lines',
                    args: [self.context.active_id],
                    context: context,
                }).then((best_lines) => {
                    self.renderer.best_date_ids = best_lines[0] || [];
                    self.renderer.best_price_ids = best_lines[1] || [];
                    self.renderer.best_price_unit_ids = best_lines[2] || [];
                    self.reload();
                });
            });
        } else {
            this._super.apply(this, arguments);
        }
    },

    _onHeaderButtonClicked: async function (node) {
        await this._super(...arguments);
        if (node.attrs.name && node.attrs.name === 'action_clear_quantities') {
            const context = this.model.localData[0] && this.model.localData[0].getContext() || {};
            const best_lines = await this._rpc({
                model: 'purchase.order',
                method: 'get_tender_best_lines',
                args: this.context.active_ids,
                context,
            });
            this.renderer.best_date_ids = best_lines[0];
            this.renderer.best_price_ids = best_lines[1];
            this.renderer.best_price_unit_ids = best_lines[2];
            this.reload();
        }
    },
});

export default PurchaseOrderLineCompareListController;
