odoo.define('pos_hr.CashierName', function (require) {
    'use strict';

    const CashierName = require('point_of_sale.CashierName');
    const { patch } = require('web.utils');

    patch(CashierName.prototype, 'pos_hr', {
        async selectCashier() {
            if (!this.env.model.config.module_pos_hr) return;
            const selectionList = this.env.model.getRecords('hr.employee').map((employee) => {
                return {
                    id: employee.id,
                    label: employee.name,
                    isSelected: employee.id === this.env.model.data.uiState.activeEmployeeId,
                };
            });
            this.env.model.actionHandler({ name: 'actionSelectEmployee', args: [{ selectionList }] });
        },
    });

    return CashierName;
});
