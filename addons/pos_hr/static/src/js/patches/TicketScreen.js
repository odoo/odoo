odoo.define('pos_hr.TicketScreen', function (require) {
    'use strict';

    const TicketScreen = require('point_of_sale.TicketScreen');
    const { patch } = require('web.utils');

    patch(TicketScreen.prototype, 'pos_hr', {
        getEmployee(order) {
            const employee = this.env.model.getRecord('hr.employee', order.employee_id);
            if (employee) {
                return employee.name;
            } else {
                return this._super(...arguments);
            }
        },
    });

    return TicketScreen;
});
