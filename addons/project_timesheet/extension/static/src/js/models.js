function odoo_project_timesheet_models(project_timesheet) {

    project_timesheet.task_activity_model = Backbone.Model.extend({
        initialize: function(session, attributes) {
            Backbone.Model.prototype.initialize.call(this, attributes);
            this.session = session;
            this.id = null;
            this.date = null;
            this.task_id = null;
            this.description = null;
            this.hours = null;
        },
        export_as_json: function() {
            //TO Implement, will return activity record
        },
    });

    project_timesheet.TaskActivityCollection = Backbone.Collection.extend({
        model: project_timesheet.task_activity_model,
    });

    project_timesheet.task_model = Backbone.Model.extend({
        initialize: function(session, attributes) {
            Backbone.Model.prototype.initialize.call(this, attributes);
            this.session = session;
            this.id = null;
            this.name = null;
            this.project_id = null;
            this.task_activities = new project_timesheet.TaskActivityCollection();
        },
        export_as_json: function() {
            //TO Implement, will return task record along with its activities collection
        },
        add_new_activity: function() {
            //TO Implement, will create new model object of activity and add it into activities collection
        },
    });

    project_timesheet.TaskCollection = Backbone.Collection.extend({
        model: project_timesheet.task_model,
    });

    project_timesheet.project_model = Backbone.Model.extend({
        initialize: function(session, attributes) {
            Backbone.Model.prototype.initialize.call(this, attributes);
            this.session = session;
            this.id = null;
            this.name = null;
            this.tasks = new project_timesheet.TaskCollection();
        },
        export_as_json: function() {
            //TO Implement, will return project record along with its task collection
        },
        add_new_task: function() {
            //TO Implement, will create new model object of task and add it into tasks collection
        },
    });

    project_timesheet.ProjectCollection = Backbone.Collection.extend({
        model: project_timesheet.project_model,
    });

    project_timesheet.project_timesheet_model = Backbone.Model.extend({
        initialize: function(session, attributes) {
            Backbone.Model.prototype.initialize.call(this, attributes);
            this.session = session;
            this.set({
                projects: new project_timesheet.ProjectCollection()
            });
        },
        add_new_project: function() {
            //TO Implement, will create new object of model and add it into collection
        },
    });

}