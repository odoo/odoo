function odoo_project_timesheet_db(project_timesheet) {

    //Store data in localstorage, { projects: [records(i.e. project_id, task_id, date, hours, descriptions etc)] }
    //When project_timesheet_model's load_stored_data is called it will create project model and add it into project collection, one project model even though same project is used twice or thrice in records
    project_timesheet.project_timesheet_db = openerp.Class.extend({
        init: function(options) {
            //TO Implement initializers
        },
        //To load data from localstorage
        load: function(name, def) {
            var data = localStorage[name];
            if (data !== undefined && data !== "") {
                data = JSON.parse(data);
                return data;
            } else {
                return def || false;
            }
        },
        //To save data in localstorage
        save: function(name, data) {
            localStorage[name] = JSON.stringify(data);
        },
        get_activities: function() {
            //TO Implement
        },
        add_activities: function(data) {
            var activities = this.load("activities", []);
            activities = activities.concat(data);
            this.save("activities", activities);
        },
        add_activity: function(data) {
            //TO Implement, add single activity
        },
    });
}