function odoo_project_timesheet_db(project_timesheet) {

    //Store data in localstorage, { projects: [records(i.e. project_id, task_id, date, hours, descriptions etc)] }
    //When project_timesheet_model's load_stored_data is called it will create project model and add it into project collection, one project model even though same project is used twice or thrice in records
    project_timesheet.project_timesheet_db = openerp.Class.extend({
        init: function(options) {
            this.virtual_id_prefix = "virtual_id_";
            this.virtual_id_regex = /^virtual_id_.*$/;
        },
        load: function(name, def) {
            //To load data from localstorage
            var data = localStorage[name];
            if (data !== undefined && data !== "") {
                data = JSON.parse(data);
                return data;
            } else {
                return def || false;
            }
        },
        save: function(name, data) {
            //To save data in localstorage
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
        add_activities: function(activities) {
            var self = this;
            _.each(activities, function(activity) {self.add_activity(activity);});
        },
        add_activity: function(activity) {
            activity_id = activity.id;
            var activities = this.load("activities", []);
            // if the order was already stored, we overwrite its data
            for(var i = 0, len = activities.length; i < len; i++) {
                if(activities[i].id === activity_id){
                    activities[i] = activity;
                    this.save('activities',activities);
                    return activity_id;
                }
            }

            activities.push(activity);
            this.save('activities',activities);
        },
        remove_activity: function(activity) {
            var activities = this.load("activities", []);
            for(var i = 0, len = activities.length; i < len; i++){
                if(activities[i].id === activity.id){
                    activities[i] = activity;
                    activities.splice(i, 1);
                    break;
                }
            }
            this.save('activities',activities);
        },
        remove_project_activities: function(project_id) {
            var activities = this.load("activities", []);
            var indexes = [];
            for(var i = 0, len = activities.length; i < len; i++) {
                console.log("Inside remove_project_activities project_id are ::: ", activities[i].project_id[0], project_id, typeof activities[i].project_id[0], typeof project_id);
                if(activities[i].project_id[0] === project_id){
                    indexes.push(i);
                }
            }
            //_.each(indexes, function(index) {activities.splice(index, 1);});
            console.log("filtered_activities.length is before ::: ", activities.length);
            var filtered_activities = _.reject(activities, function(activity, index) { return _.contains(indexes, index); });
            console.log("filtered_activities.length is after ::: ", filtered_activities.length);
            this.save('activities', filtered_activities);
        },
        get_pending_records: function() {
            /*
             * This method will return Timesheet Lines which having some command that is it has been edited
             *  or line which having virtual_id that is to_create
             */ 
            var self = this;
            var activities = this.load('activities');
            pending_records = _.filter(activities, function(activity) {
                return (activity.command || (self.virtual_id_regex.test(activity.id)));
            });
            return pending_records.length;
        },
        get_current_timer_activity: function() {
            return this.load("timer_activity") || {};
        },
        set_current_timer_activity: function(data) {
            var current_timer_activity = this.load("timer_activity") || {};
            _.each(data, function(value, key) {
                current_timer_activity[key] = value;
            });
            this.save("timer_activity", current_timer_activity);
        }
    });
}