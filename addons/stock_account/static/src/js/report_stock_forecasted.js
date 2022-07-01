odoo.define('stock_account.ReplenishReport', function (require) {
"use strict";


const core = require('web.core');
const ReplenishReport = require('stock.ReplenishReport');

const _t = core._t;

ReplenishReport.include({

    /**
     *
     * @override
     */
    _bindAdditionalActionHandlers: function () {
        this._super.apply(this, arguments);
        let rr = this.$el.find('iframe').contents().find('.o_report_replenishment_header');
        rr.on('click', '.o_report_open_valuation_report', this._onClickValuation.bind(this));
    },

    /**
     * Open the stock valuation report filtered to the products/product variants currently open in
     * forecast report
     *
     * @returns {Promise}
     */
     _onClickValuation: function (ev) {
        const templates = JSON.parse(ev.target.getAttribute('product-templates-ids'));
        const variants = JSON.parse(ev.target.getAttribute('product-variants-ids'));
        const context = Object.assign({}, this.context);
        if (templates) {
            context.search_default_product_tmpl_id = templates;
        } else {
            context.search_default_product_id = variants;
        }
        return this.do_action({
            name: _t('Stock Valuation'),
            res_model: 'stock.valuation.layer',
            type: 'ir.actions.act_window',
            view_mode: 'list,form',
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
            context: context,
        });
    }

});

return ReplenishReport;

});
