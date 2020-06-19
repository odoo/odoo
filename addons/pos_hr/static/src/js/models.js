odoo.define('pos_hr.employees', function (require) {
    "use strict";

var models = require('point_of_sale.models');

models.load_models([{
    model:  'hr.employee',
    fields: ['name', 'id', 'user_id'],
    domain: function(self){ return [['company_id', '=', self.config.company_id[0]]]; },
    loaded: function(self, employees) {
        if (self.config.module_pos_hr) {
            if (self.config.employee_ids.length > 0) {
                self.employees = employees.filter(function(employee) {
                    return self.config.employee_ids.includes(employee.id) || employee.user_id[0] === self.user.id;
                });
            } else {
                self.employees = employees;
            }
            self.employees.forEach(function(employee) {
                var hasUser = self.users.some(function(user) {
                    if (user.id === employee.user_id[0]) {
                        employee.role = user.role;
                        return true;
                    }
                    return false;
                });
                if (!hasUser) {
                    employee.role = 'cashier';
                }
            });
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
