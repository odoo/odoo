odoo.define('pos_hr.employees', function (require) {
    "use strict";

var models = require('point_of_sale.models');

models.load_models([{
    model:  'hr.employee',
    fields: ['name', 'id', 'user_id'],
    domain: function(self){
        return self.config.employee_ids.length > 0
            ? [
                  '&',
                  ['company_id', '=', self.config.company_id[0]],
                  '|',
                  ['user_id', '=', self.user.id],
                  ['id', 'in', self.config.employee_ids],
              ]
            : [['company_id', '=', self.config.company_id[0]]];
    },
    loaded: function(self, employees) {
        if (self.config.module_pos_hr) {
            self.employees = employees;
            self.employee_by_id = {};
            self.employees.forEach(function(employee) {
                self.employee_by_id[employee.id] = employee;
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
    after_load_server_data: function() {
        return posmodel_super.after_load_server_data.apply(this, arguments).then(() => {
            // Value starts at false when module_pos_hr is true.
            this.hasLoggedIn = !this.config.module_pos_hr;
        });
    },
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
    set_cashier: function(employee) {
        posmodel_super.set_cashier.apply(this, arguments);
        const selectedOrder = this.get_order();
        if (selectedOrder && !selectedOrder.get_orderlines().length) {
            // Order without lines can be considered to be un-owned by any employee.
            // We set the employee on that order to the currently set employee.
            selectedOrder.employee = employee;
        }
    }
});

var super_order_model = models.Order.prototype;
models.Order = models.Order.extend({
    initialize: function (attributes, options) {
        super_order_model.initialize.apply(this, arguments);
        if (!options.json) {
            this.employee = this.pos.get_cashier();
        }
    },
    init_from_JSON: function (json) {
        super_order_model.init_from_JSON.apply(this, arguments);
        if (this.pos.config.module_pos_hr && json.employee_id) {
            this.employee = this.pos.employee_by_id[json.employee_id];
        }
    },
    export_as_JSON: function () {
        const json = super_order_model.export_as_JSON.apply(this, arguments);
        if (this.pos.config.module_pos_hr) {
            json.employee_id = this.employee ? this.employee.id : false;
        }
        return json;
    },
});

});
