function odoo_project_timesheet_models(project_timesheet) {

    project_timesheet.task_activity_model = Backbone.Model.extend({
        initialize: function(attributes, options) {
            Backbone.Model.prototype.initialize.call(this, attributes);
            this.id = options.id || null;
            this.date = options.date || null;
            this.task_id = options.task_id || null;
            this.name = options.name || null; //Actually description field
            this.hours = options.hours || null;
            this.command = options.command || 0;
        },
        export_as_JSON: function() {
            return {
                id: this.id,
                date: this.date,
                name: this.name,
                hours: this.hours,
                command: this.command,
            };
        },
    });

    project_timesheet.TaskActivityCollection = Backbone.Collection.extend({
        model: project_timesheet.task_activity_model,
    });

    //Note: Regarding project already connected or not ? state: "connecting", //There will be two state, connecting and connected, if record is modified then again state will be changed and localstorage will be updated
    project_timesheet.task_model = Backbone.Model.extend({
        initialize: function(attributes, options) {
            Backbone.Model.prototype.initialize.call(this, attributes);
            this.project_timesheet_widget = attributes.project_timesheet_widget;
            this.project_timesheet_db = attributes.project_timesheet_db;
            this.id = options.id || null;
            this.name = options.name || null;
            this.project_id = options.project_id || null;
            this.set({
                task_activities: new project_timesheet.TaskActivityCollection(),
            });
        },
        export_as_JSON: function() {
            //TO Implement, will return task record along with its activities collection
            var self = this;
            var work_records = [];
            (this.get('task_activities')).each(_.bind( function(item) {
                var exported_data = item.export_as_JSON();
                if (self.project_timesheet_db.virtual_id_regex.test(exported_data.id)) {
                    delete exported_data.id;
                    delete exported_data.command;
                    exported_data['user_id'] = project_timesheet.session.uid;
                    work_records.push([0, 0, exported_data]);
                } else if(exported_data.command == 1) {
                    var id = exported_data.id;
                    delete exported_data.id;
                    delete exported_data.command;
                    work_records.push([1, id, exported_data]);
                } else if (exported_data.command == 2) {
                    var id = exported_data.id;
                    delete exported_data.id;
                    delete exported_data.command;
                    work_records.push([1, id, exported_data]);
                } else {
                    var id = exported_data.id;
                    work_records.push([4, id, false]); //link the record if no condition match
                }
            }, this));
            return {
                id: this.id,
                name: this.name,
                work_ids: work_records,
            };
        },
        add_activity: function(data) {
            //TO Implement, will create new model object of activity and add it into activities collection
            var task_activity = new project_timesheet.task_activity_model({}, {id: data['id'], name: data['name'], task_id: data['task_id'][0], date: data['date'], hours: data['hours'], command: (data['command'] || 0)});
            this.get('task_activities').add(task_activity);
        },
    });

    project_timesheet.TaskCollection = Backbone.Collection.extend({
        model: project_timesheet.task_model,
    });

    project_timesheet.project_model = Backbone.Model.extend({
        initialize: function(attributes, options) {
            Backbone.Model.prototype.initialize.call(this, attributes);
            this.project_timesheet_model = attributes.project_timesheet_model;
            this.project_timesheet_db = attributes.project_timesheet_db;
            this.id = options.id || null; //If no real id, we will have virtual id, at sync time virtual id will be skipped while sending data to server
            this.name = options.name || null;
            this.set({
                tasks: new project_timesheet.TaskCollection(),
            });
        },
        export_as_JSON: function() {
            //TO Implement, will return project record along with its task collection
            var self = this;
            var tasks = [];
            (this.get('tasks')).each(_.bind( function(item) {
                var exported_data = item.export_as_JSON();
                if (self.project_timesheet_db.virtual_id_regex.test(exported_data.id)) {
                    delete exported_data.id;
                    tasks.push([0, 0, exported_data]);
                } else {
                    var id = exported_data.id;
                    delete exported_data.id;
                    tasks.push([1, id, exported_data]);
                }
            }, this));
            return {
                id: this.id,
                name: this.name,
                tasks: tasks,
            };
        },
        add_task: function(data) {
            tasks_collection = this.get("tasks");
            if (tasks_collection.get(data.task_id[0])) {
                var task_model = tasks_collection.get(data.task_id[0]);
                task_model.add_activity(data);
            } else {
                var task = new project_timesheet.task_model({project_timesheet_db: this.project_timesheet_db}, {id: data['task_id'][0], name: data['task_id'][1], project_id: data['project_id'][0]});
                task.add_activity(data);
                this.get('tasks').add(task);
            }
        },
        name_search: function(term) {
            /*
             * This method will search into task collection and will return key, value pairs for tasks
             */
            console.log("name_search for task collection ::: ");
            var tasks = this.get('tasks');
            var search_result = [];
            var task_models = tasks.models;
            for (var i = 0; i < task_models.length; i++) {
                search_result.push([task_models[i].id, task_models[i].name]);
            }
            if (term) {
                search_result = _.compact(_(search_result).map(function(x) {if (x[1].toLowerCase().contains(term.toLowerCase())) {return x;}}));
            }
            return search_result;
        }
    });

    project_timesheet.ProjectCollection = Backbone.Collection.extend({
        model: project_timesheet.project_model,
    });

    //Once data has been sync, read project, then task and activities and store it into localstorage also
    //While sync read model, this following model's save_to_server will fetch project, and project will fetch task in format such that its one2many
    //Also add the logic of destroy model

    project_timesheet.project_timesheet_model = Backbone.Model.extend({
        initialize: function(attributes) {
            var self = this;
            Backbone.Model.prototype.initialize.call(this, attributes);
            this.project_timesheet_widget = attributes.project_timesheet_widget;
            var def = $.Deferred();
            this.set({
                projects: new project_timesheet.ProjectCollection()
            });
            this.project_timesheet_db = new project_timesheet.project_timesheet_db();
            this.screen_data = {};  //see ScreenSelector
            //Try to check localstorage having session, we do not reload session like web module(core.js), instead stored in localstorage to keep persistent origin
            console.log("project_timesheet is ::: ", project_timesheet, openerp);
            if(!project_timesheet.session && !_.isEmpty(this.project_timesheet_db.load("session", {}))) {
                var stored_session = this.project_timesheet_db.load("session", {});
                //project_timesheet.session = new openerp.Session(undefined, stored_session['origin'], {session_id: stored_session['session_id']});
                project_timesheet.session = new openerp.Session(undefined, stored_session['origin']);
            }
            //If we have stored session then replace project_timesheet.session with new Session object with stored session origin
            if (!_.isEmpty(project_timesheet.session)) {
                project_timesheet.session.check_session_id().done(function() {
                    //Important Note: check_session_id may replace session_id each time when server_origin is different then origin,
                    //so we will update the localstorage session
                    self.project_timesheet_db.save("session", project_timesheet.session);
                    console.log("Here we go, you can do rpc, we having session ID.");
                    console.log("project_timesheet.session is ::: ", project_timesheet.session);
                    //Load server data and update localstorage
                    def = self.load_server_data();
                }).fail(function() {
                    def.reject();
                });
            } else {
                //If we do not have previous stored session then try to check whether we having session with window origin (say for example session with localhost:9000)
                console.log("Inside elseeee, we do not have old session stored with origin in db");
                var window_origin = location.protocol + "//" + location.host;
                var session = new openerp.Session(undefined, window_origin);
                session.session_reload().done(function() {
                    console.log("We having session with window origin ::: ");
                    project_timesheet.session = session;
                    def = self.load_server_data();
                }).fail(function() {
                    def.reject();
                });
            }
            //Always Load locally stored data, whether server is running(or def may fail, because server is not up, still we will load local data)
            $.when(def).always(function() {
                self.load_stored_data();
            });
        },
        add_project: function(data) {
            //this method will create new object of model if data having virtual_id and add it into collection, then it will call add task for that collection model
            //It also finds project model from collection and add task in that model if project_id passed in data is already available
            //We can find model by id, coolection.get(id of model(e.g. id of project model)), id is magic attribute of model
            var projects_collection = this.get("projects");
            if(projects_collection.get(data.project_id[0])) {
                var project_model = projects_collection.get(data.project_id[0]);
                project_model.add_task(data);
            } else {
                var project = new project_timesheet.project_model({project_timesheet_model: this, project_timesheet_db: this.project_timesheet_db}, {id: data['project_id'][0], name: data['project_id'][1]});
                project.add_task(data);
                this.get('projects').add(project);
            }
            this.project_timesheet_db.add_activity(data); //instead of data, use project.exportAsJson();
        },
        name_search: function(term) {
            /*
            * This method searches into porjects collection and will return key,value pairs for projects.
            */
            var projects = this.get('projects');
            var search_result = [];
            var project_models = projects.models;
            for (var i = 0; i < project_models.length; i++) {
                search_result.push([project_models[i].id, project_models[i].name]);
            }
            if (term) {
                search_result = _.compact(_(search_result).map(function(x) {if (x[1].toLowerCase().contains(term.toLowerCase())) {return x;}}));
            }
            return search_result;
        },
        load_stored_data: function() {
            //We should simply call add_project method for activity_record which having project and task details, 
            //project model will call add_task, also check if project model is also available then will not create new model else create new model and push it into projects collection
            var self = this;
            console.log("Inside load_stored_data ::: ");
            var stored_activities = this.project_timesheet_db.load("activities");
            _.each(stored_activities, function(record) {
                self.add_project(record);
            });
        },
        load_server_data: function() {
            var self = this;
            //Load last 30 days data and updated localstorage and then reload models(done by load_stored_data method)
            var momObj = new moment();
            var end_date = project_timesheet.datetime_to_str(momObj._d);
            var start_date = project_timesheet.datetime_to_str(momObj.subtract(30, "days")._d);
            return new project_timesheet.Model(project_timesheet.session, "project.task.work").call("search_read", {
                domain: [["date", ">=", start_date], ["date", "<=", end_date]],
                fields: ["id", "task_id", "name", "hours", "date"]
            }).then(function(work_activities) {
                var tasks = _.pluck(work_activities, "task_id");
                tasks = _.pluck(_.groupBy(tasks), 0);
                return new project_timesheet.Model(project_timesheet.session, "project.task").call("search_read", {
                    domain: [["id", "in", _.map(tasks, function(task) {return task[0];})]],
                    fields: ['id', 'project_id', "priority"]
                }).then(function(tasks_read) {
                    var projects = [];
                    //set project_id in activities, where task_id is projects.id
                    _.each(tasks_read, function(task) {
                        var activities = _.filter(work_activities, function(activity) {return activity.task_id[0] == task.id});
                        _.each(activities, function(activity) {
                            activity['project_id'] = task['project_id'];
                        });
                    });
                    self.project_timesheet_db.add_activities(work_activities);
                });
            });
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
            //TODO: Load model data in JSON format, check whether project is to create, task is to create, and activity is to create, write or delete
            //Once we done with data collection from model, save each record by calling project's create method, remove record from localstorage and then in last reload last 30 days data, that is call load_server_data
            //If record is failed in record creation then do not remove it from localstorage and keep it's state = pending'
            var self = this;
            this.defs = [];
            var records = [];
            var project_collection = this.get('projects');
            var project_models = project_collection.models;
            for (var i = 0; i < project_models.length; i++) {
                records.push(project_models[i].export_as_JSON());
            }
            _.each(records, function(record) {
                if (self.project_timesheet_db.virtual_id_regex.test(record.id)) {
                    delete record.id;
                    self.defs.push(new project_timesheet.Model(project_timesheet.session, "project.project").call("create", [record]).then(function(res) {
                        //Remove record from localstorage if create success
                    }));
                } else {
                    var id = record.id;
                    delete record.id;
                    self.defs.push(new project_timesheet.Model(project_timesheet.session, "project.project").call("write", [id, record]).then(function(res) {
                        //Remove record from localstorage if create success
                    }));
                }
            });
            console.log("records collected are ::: ", records);
            return $.when.apply($, this.defs).then(function(){
                //Load latest data of 30 days
                console.log("Inside project create loop completed ::: ");
            });
        },
        flush_data: function() {
            //TO Implement, this method will flush localstorage data once it has been sync
        },
        get_pending_records: function() {
           return this.project_timesheet_db.get_pending_records();
        }
        //Note here
        //Here we will have logic of add projects, which will add project models' instance in this.get('projects').add(project)
    });

}