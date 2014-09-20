function odoo_project_timesheet_db(project_timesheet) {

    //Store data in localstorage, { projects: [records(i.e. project_id, task_id, date, hours, descriptions etc)] }
    //When project_timesheet_model's load_stored_data is called it will create project model and add it into project collection, one project model even though same project is used twice or thrice in records
    project_timesheet.project_timesheet_db = openerp.Class.extend({
        init: function(options) {
            //TO Implement initializers
        },
        //To load data from localstorage
        load: function(name, data) {
            //TO Implement
        },
        //To save data in localstorage
        save: function(name) {
            //TO Implement
        },
        get_activities: function() {
            //TO Implement
        },
    });
}