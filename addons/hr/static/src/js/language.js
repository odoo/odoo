/** @odoo-module **/

import FormController from 'web.FormController';
import FormView from 'web.FormView';
import viewRegistry from 'web.view_registry';

var EmployeeFormController = FormController.extend({
    saveRecord: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            if (arguments[0].indexOf('lang') >= 0) {
                self.do_action('reload_context');
            }
        });
    },
});

var EmployeeProfileFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: EmployeeFormController,
    }),
});

viewRegistry.add('hr_employee_profile_form', EmployeeProfileFormView);
export default EmployeeProfileFormView;
