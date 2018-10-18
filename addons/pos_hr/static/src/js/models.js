odoo.define('pos_hr.employees', function (require) {
    "use strict";

var models = require('point_of_sale.models');

models.load_models([{
    model:  'res.users',
    fields: ['name','groups_id'],
    domain: function(self){ return [['company_id','=',self.user.company_id[0]],'|', ['groups_id','=', self.config.group_pos_manager_id[0]],['groups_id','=', self.config.group_pos_user_id[0]]]; },
    loaded: function(self,users){
        // we attribute a role to the user, 'cashier' or 'manager', depending
        // on the group the user belongs.
        self.users = users;
        self.users.forEach(function(user) {
            user.role = 'cashier';
            user.groups_id.some(function(group_id) {
                if (group_id === self.config.group_pos_manager_id[0]) {
                    user.role = 'manager';
                    return true;
                }
            });
            // replace the current user with its updated version
            if (user.id === self.user.id) {
                self.user = user;
                self.employee = self.user;
            }
        });
    },
},{
    model:  'hr.employee',
    fields: ['name', 'id', 'barcode', 'pin', 'user_id'],
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
});
