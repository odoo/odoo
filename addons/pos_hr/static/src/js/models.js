odoo.define('pos_hr.employees', function (require) {
    "use strict";

var models = require('point_of_sale.models');

models.load_models([{
    model:  'hr.employee',
    fields: ['name', 'id', 'user_id'],
    domain: function(self){ return [['company_id', '=', self.config.company_id[0]], '|', ['user_id', '=', self.user.id], ['id', 'in', self.config.employee_ids]]; },
    loaded: function(self, employees) {
        if (self.config.module_pos_hr) {
            self.employees = employees;
            const currentCashier = self.get_cashier();
            for (let employee of self.employees) {
                const user = self.users.find(user => user.id === employee.user_id[0]);
                employee.role = user ? user.role : 'cashier';
                // When loading res.users, the current user is set as cashier.
                // We need to reset that using the employee record of the user
                // for consistency.
                if (user && user.id === currentCashier.id) {
                    self.set_cashier(employee);
                }
            }
        }
    }
}]);

var posmodel_super = models.PosModel.prototype;
models.PosModel = models.PosModel.extend({
    load_server_data: function () {
        var self = this;
        return posmodel_super.load_server_data.apply(this, arguments).then(function () {
            var employee_ids = _.map(self.employees, function(employee){return employee.id;});
            var records = self.rpc({
                model: 'hr.employee',
                method: 'get_barcodes_and_pin_hashed',
                args: [employee_ids],
            });
            return records.then(function (employee_data) {
                self.employees.forEach(function (employee) {
                    var data = _.findWhere(employee_data, {'id': employee.id});
                    if (data !== undefined){
                        employee.barcode = data.barcode;
                        employee.pin = data.pin;
                    }
                });
            });
        });
    },
});

});
