function odoo_project_timesheet_db(project_timesheet) {
    project_timesheet.project_timesheet_db = openerp.Class.extend({
        init: function() {
            this._super.apply(this, arguments);
        },
        //To load data from localstorage
        load: function(name, data) {
            //TO Implement
        },
        //To save data in localstorage
        save: function(name) {
            //TO Implement
        },
    });
}