function odoo_project_timesheet_db(project_timesheet) {

    //Store data in localstorage, { projects: [records(i.e. project_id, task_id, date, hours, descriptions etc)] }
    //When project_timesheet_model's load_stored_data is called it will create project model and add it into project collection, one project model even though same project is used twice or thrice in records
    project_timesheet.project_timesheet_db = openerp.Class.extend({
        init: function(options) {
            this.virtual_id_prefix = "virtual_id_";
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
            return this.load("activities", []);
        },
        get_activity_by_id: function(id) {
            var activities = this.load("activities", []);
            var activity = {};
            for(var i=0; i<activities.length; i++) {
                if (activities[i].id == id) {
                    activity = activities[i];
                    break;
                }
            }
            return activity;
        },
        //TODO: We should handle it better way, if same id activity is there then replace it otherwise add it and then save whole activities list in db
        add_activities: function(activities) {
            //This method will replace activities, inshort reload with new activities
            //var activities = this.load("activities", []);
            //activities = activities.concat(data);
            this.save("activities", activities);
        },
        add_activity: function(activity) {
            activity_id = activity.id;
            var activities = this.load("activities", []);
            // if the order was already stored, we overwrite its data
            for(var i = 0, len = activities.length; i < len; i++){
                if(activities[i].id === activity_id){
                    activities[i] = activity;
                    this.save('activities',activities);
                    return activity_id;
                }
            }

            activities.push(activity);
            this.save('activities',activities);
        },
    });
}