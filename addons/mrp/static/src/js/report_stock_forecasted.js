/** @odoo-module */

import ReplenishReport from 'stock.ReplenishReport';
import { qweb } from 'web.core';

export const MrpReplenishReport = ReplenishReport.include({
    willStart: function() {
        const readPromise = this._rpc({
            model: this.resModel,
            method: 'read',
            args: [this.productId],
            kwargs: { fields: ['bom_ids'] },
        }).then(res => {
            this.bomId = res[0].bom_ids && res[0].bom_ids[0];
        });
        return Promise.all([this._super(...arguments), readPromise]);
    },

    _renderButtons: function () {
        this._super(...arguments);
        if (this.bomId) {
            const $newButtons = $(qweb.render('mrp_replenish_report_buttons', {}));
            this.$buttons.append($newButtons);
            this.$buttons.on('click', '.o_bom_overview_report', this._onClickBomOverview.bind(this));
        }
    },

    _onClickBomOverview: function () {
        this.do_action("mrp.action_report_mrp_bom", {
            additional_context: {
                active_id: this.bomId,
            },
        });
    }
});
