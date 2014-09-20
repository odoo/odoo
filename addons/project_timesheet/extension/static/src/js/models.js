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
            this.project_timesheet_widget = attributes.project_timesheet_widget;
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
            this.id = null; //If no real id, we will have virtual id, at sync time virtual id will be skipped while sending data to server
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

    //Once data has been sync, read project, then task and activities and store it into localstorage also
    //While sync read model, this following model's save_to_server will fetch project, and project will fetch task in format such that its one2many

    project_timesheet.project_timesheet_model = Backbone.Model.extend({
        initialize: function(session, attributes) {
            Backbone.Model.prototype.initialize.call(this, attributes);
            this.session = session;
            this.set({
                projects: new project_timesheet.ProjectCollection()
            });
            this.project_timesheet_db = new project_timesheet.project_timesheet_db();
            this.screen_data = {};  // see ScreenSelector
        },
        add_new_project: function() {
            //TO Implement, will create new object of model and add it into collection
        },
        load_stored_data: function() {
            //TO Implement, this will load localstorage data and call add project, add project will call add task, add task will call add activity
        },
        set_screen_data: function(key,value){
            if(arguments.length === 2){
                this.screen_data[key] = value;
            }else if(arguments.length === 1){
                for(key in arguments[0]){
                    this.screen_data[key] = arguments[0][key];
                }
            }
        },
        //return screen data based on key passed
        get_screen_data: function(key){
            return this.screen_data[key];
        },
        save_to_server: function() {
            //TO Implement, this method will save data to server
        },
        flush_data: function() {
            //TO Implement, this method will flush localstorage data once it has been sync
        },
        //Note here
        //Here we will have logic of add projects, which will add project models' instance in this.get('projects').add(project)
    });

}