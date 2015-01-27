function odoo_project_timesheet_models(project_timesheet) {

    project_timesheet.account_analytic_line_model = Backbone.Model.extend({
        initialize: function(attributes, options) {
            Backbone.Model.prototype.initialize.call(this, attributes);
            this.id = options.id || null;
            this.date = options.date || null;
            this.task_id = options.task_id || null;
            this.project_id = options.project_id || null;
            this.name = options.name || null; //Actually description field
            this.unit_amount = options.unit_amount || null;
            this.reference_id = options.reference_id || null;
        },
        export_as_JSON: function() {
            return {
                id: this.id,
                date: this.date || project_timesheet.datetime_to_str(new moment()._d),
                name: this.name || '/',
                unit_amount: this.unit_amount,
                task_id: this.task_id,
                project_id: this.project_id,
                reference_id: this.reference_id,
                user_id: project_timesheet.session.uid,
                
            };
        },
    });

    project_timesheet.TaskActivityCollection = Backbone.Collection.extend({
        model: project_timesheet.task_activity_model,
    });

    project_timesheet.Task_model = Backbone.Model.extend({
        initialize: function(attributes, options) {

        },
        load_tasks: function(sessions_username, session_server){
            var stored_data = JSON.parse(localStorage.getItem("pt_data"));

            debugger
        }
    });

    project_timesheet.TaskCollection = Backbone.Collection.extend({
        model: project_timesheet.task_model,
    });

    project_timesheet.Project_model = Backbone.Model.extend({
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
        add_task: function(data) {
            tasks_collection = this.get("tasks");
            if (tasks_collection.get(data.task_id[0])) {
                var task_model = tasks_collection.get(data.task_id[0]);
            } else {
                var task = new project_timesheet.task_model({project_timesheet_db: this.project_timesheet_db}, {id: data['task_id'][0], name: data['task_id'][1], project_id: data['project_id'][0], priority: data['priority']});
                this.get('tasks').add(task);
            }
        },
        name_search: function(term) {
            /*
             * This method will search into task collection and will return key, value pairs for tasks
             */
            var tasks = this.get('tasks');
            var search_result = [];
            var task_models = tasks.models;
            for (var i = 0; i < task_models.length; i++) {
                search_result.push([task_models[i].id, task_models[i].name+"\n"+task_models[i].priority]);
            }
            if (term) {
                search_result = _.compact(_(search_result).map(function(x) {if (x[1].toLowerCase().indexOf(term.toLowerCase()) !== -1) {return x;}}));
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


    //tac additions here
    // Main model, used to hold info such as the current screen or user.
    project_timesheet.project_timesheet_model = Backbone.Model.extend({
        initialize: function(attributes) {

            var self = this;
            self.ready = $.Deferred();

            self.projects;
            self.tasks;
            self.day_plan;
            self.account_analytic_lines;
            

            this.project_timesheet_widget = attributes.project_timesheet_widget;
            self.db = new project_timesheet.project_timesheet_db();
            this.selected_screen = "no screen yet !";

            // Session management
            project_timesheet.session = new project_timesheet.Session();
            this.session_reloading = project_timesheet.session.session_reload();

            this.session_reloading.done(function(){
                var user_data = self.db.load_data(project_timesheet.session.username, project_timesheet.session.server);
                var data = user_data.data;
                self.projects = data.projects;
                self.tasks = data.tasks;
                self.account_analytic_lines = data.account_analytic_lines;
                self.day_plan = data.day_plan;
                self.settings = data.settings;                

                _.each(self.account_analytic_lines, function(account_analytic_line){

                    var this_task = _.findWhere(self.tasks, {id:account_analytic_line.task_id});
                    if(! _.isUndefined(this_task)){
                       account_analytic_line.task_name = this_task.name;
                    }

                    var this_project = _.findWhere(self.projects, {id:account_analytic_line.project_id});
                    if(! _.isUndefined(this_project)){
                        account_analytic_line.project_name = this_project.name;
                    }
                });

                _.each(self.tasks, function(task){
                    var this_project = _.findWhere(self.projects, {id:task.project_id});
                    if(! _.isUndefined(this_project)){
                        task.project_name = this_project.name;
                    }
                });

                _.each(self.day_plan, function(day_activity){
                    
                    var this_task = _.findWhere(self.tasks, {id:day_activity.task_id});
                    if(! _.isUndefined(this_task)){
                       day_activity.task_name = this_task.name;
                    }

                    var this_project = _.findWhere(self.projects, {id:day_activity.project_id});
                    if(! _.isUndefined(this_project)){
                        day_activity.project_name = this_project.name;
                    }
                });

                self.ready.resolve();
            });
            
        }
    });


    // project_timesheet.project_timesheet_model = Backbone.Model.extend({
    //     initialize: function(attributes) {
    //         debugger
    //         var self = this;
    //         var callback_function;
    //         Backbone.Model.prototype.initialize.call(this, attributes);
    //         this.project_timesheet_widget = attributes.project_timesheet_widget;
    //         this.def = $.Deferred();
    //         this.ready = $.Deferred();
    //         this.set({
    //             projects: new project_timesheet.ProjectCollection(),
    //             activities: new project_timesheet.TaskActivityCollection(),
    //         });
    //         this.project_timesheet_db = new project_timesheet.project_timesheet_db();
    //         this.screen_data = {};  //see ScreenSelector
    //         //Try to check localstorage having session, we do not reload session like web module(core.js), instead stored in localstorage to keep persistent origin
    //         if(!project_timesheet.session && !_.isEmpty(this.project_timesheet_db.load("session", {}))) {
    //             var stored_session = this.project_timesheet_db.load("session", {});
    //             //project_timesheet.session = new openerp.Session(undefined, stored_session['origin'], {session_id: stored_session['session_id']});
    //             project_timesheet.session = new openerp.Session(undefined, stored_session['origin'], {use_cors: true});
    //         }
    //         //If we have stored session then replace project_timesheet.session with new Session object with stored session origin
    //         if (!_.isEmpty(project_timesheet.session)) {
    //             callback_function = function () {
    //                 //Important Note: check_session_id may replace session_id each time when server_origin is different then origin,
    //                 //so we will update the localstorage session
    //                 self.project_timesheet_db.save("session", project_timesheet.session);
    //                 console.log("Here we go, you can do rpc, we having session ID.");
    //             };
    //             //this.def = project_timesheet.session.check_session_id();
    //             this.def = project_timesheet.session.session_reload();
    //         } else {
    //             callback_function = function () {
    //                 //TODO: To check we should clear activitie here or not ?
    //                 //Check Scenario: Login with db1, open project timesheet interface, do some entries, logout from that database from backend view and login with other db, still old db localstorage will be there
    //                 //self.project_timesheet_db.clear('activities');
    //                 project_timesheet.session = session;
    //                 self.project_timesheet_db.save("session", project_timesheet.session);
    //             };
    //             //If we do not have previous stored session then try to check whether we having session with window origin (say for example session with localhost:9000)
    //             console.log("Inside elseeee, we do not have old session stored with origin in db");
    //             var isLocal = location.protocol === "file:";
    //             if (isLocal) {
    //                 this.def.reject();
    //             } else {
    //                 var window_origin = location.protocol + "//" + location.host;
    //                 var session = new openerp.Session(undefined, window_origin, {use_cors: true});
    //                 this.def = session.session_reload();
    //             }
    //         }
    //         //Always Load locally stored data, whether server is running(or def may fail, because server is not up, still we will load local data)
    //         this.def.done(function() {
    //             callback_function();
    //             self.load_server_data().done(function() {
    //                 self.load_stored_data();
    //                 new project_timesheet.Model(project_timesheet.session, "ir.model.data")
    //                 .call("get_object_reference", ['hr_timesheet', 'menu_hr_timesheet_report_all'])
    //                 .then(function (result) {
    //                     if (result) {
    //                         self.reporting_menu_src = project_timesheet.session.origin + "/web?#menu_id=" + result[1];
    //                     }
    //                     self.ready.resolve();
    //                 });
    //             });
    //         }).fail(function() {
    //             self.load_stored_data();
    //             self.ready.reject();
    //         });
    //     },
    //     //TODO: Change name, save_activity or set_activity, this method is used in different context, like it is also used for set delete activity(rewrite)
    //     add_activity: function(data) {
    //         var activity_collection = this.get("activities");
    //         if(activity_collection.get(data.id)) {
    //             var activity_model = activity_collection.get(data.id);
    //             _.extend(activity_model, {id: data['id'], name: data['name'], task_id: data['task_id'], project_id: data['project_id'], unit_amount: data['unit_amount'], command: data['command']});
    //         } else {
    //             var activity = new project_timesheet.task_activity_model({project_timesheet_model: this, project_timesheet_db: this.project_timesheet_db}, {id: data['id'], name: data['name'], unit_amount: data['unit_amount'], date: data['date'], task_id: data['task_id'], project_id: data['project_id'], reference_id: data['reference_id'], command: data['command'], __last_update: data['__last_update'] });
    //             this.get('activities').add(activity);
    //         }
    //         this.project_timesheet_db.add_activity(data); //instead of data, use project.exportAsJson();
    //     },
    //     add_project: function(data) {
    //         //this method will create new object of model if data having virtual_id and add it into collection, then it will call add task for that collection model
    //         //It also finds project model from collection and add task in that model if project_id passed in data is already available
    //         //We can find model by id, coolection.get(id of model(e.g. id of project model)), id is magic attribute of model
    //         if (!data.project_id) {
    //             return;
    //         }
    //         var projects_collection = this.get("projects");
    //         if(projects_collection.get(data.project_id[0])) {
    //             var project_model = projects_collection.get(data.project_id[0]);
    //             if (data.task_id && data.task_id.length) { 
    //                 project_model.add_task(data);
    //             }
    //         } else {
    //             var project = new project_timesheet.project_model({project_timesheet_model: this, project_timesheet_db: this.project_timesheet_db}, {id: data['project_id'][0], name: data['project_id'][1]});
    //             if (data.task_id && data.task_id.length) {
    //                 project.add_task(data);
    //             }
    //             this.get('projects').add(project);
    //         }
    //     },
    //     name_search: function(term) {
    //         /*
    //         * This method searches into porjects collection and will return key,value pairs for projects.
    //         */
    //         var projects = this.get('projects');
    //         var search_result = [];
    //         var project_models = projects.models;
    //         for (var i = 0; i < project_models.length; i++) {
    //             search_result.push([project_models[i].id, project_models[i].name]);
    //         }
    //         if (term) {
    //             search_result = _.compact(_(search_result).map(function(x) {if (x[1].toLowerCase().indexOf(term.toLowerCase()) !== -1) {return x;}}));
    //         }
    //         return search_result;
    //     },
    //     load_stored_data: function() {
    //         //We should simply call add_project method for activity_record which having project and task details, 
    //         //project model will call add_task, also check if project model is also available then will not create new model else create new model and push it into projects collection
    //         var self = this;
    //         var stored_activities = this.project_timesheet_db.load("activities");
    //         _.each(stored_activities, function(record) {
    //             self.add_activity(record);
    //             self.add_project(record);
    //         });
    //         this.project_timesheet_db.initialize_unique_id();
    //         this.project_timesheet_db.initialize_reference_sequence();
    //     },
    //     load_server_data: function() {
    //         var self = this;
    //         //Load last 30 days data and updated localstorage and then reload models(done by load_stored_data method)
    //         var momObj = new moment();
    //         var end_date = project_timesheet.datetime_to_str(momObj._d);
    //         var start_date = project_timesheet.datetime_to_str(momObj.subtract(30, "days")._d);
    //         return new project_timesheet.Model(project_timesheet.session, "hr.analytic.timesheet").call("load_data", {
    //             domain: [["date", ">=", start_date], ["date", "<=", end_date]],
    //             fields: ["id", "write_date", "create_date", "user_id", "task_id", "name", "unit_amount", "date", "account_id", 'reference_id', '__last_update']
    //         }).then(function(work_activities) {
    //             self.project_timesheet_db.add_activities(work_activities);
    //             return new project_timesheet.Model(project_timesheet.session, "res.users").call("name_get", [project_timesheet.session.uid]).then(function(result) {
    //                 project_timesheet.session.display_username = result ? result[0][1] : project_timesheet.session.username;
    //             });
    //         }).promise();
    //     },
    //     //TO REMOVE: If not necessary
    //     set_screen_data: function(key,value){
    //         if(arguments.length === 2){
    //             this.screen_data[key] = value;
    //         }else if(arguments.length === 1){
    //             for(key in arguments[0]){
    //                 this.screen_data[key] = arguments[0][key];
    //             }
    //         }
    //     },
    //     //TO REMOVE: If not necessary
    //     get_screen_data: function(key){
    //         //this method returns screen data based on key passed
    //         return this.screen_data[key];
    //     },
    //     check_session: function(){
    //         var self = this;
    //         if (_.isEmpty(this.project_timesheet_db.get_project_timesheet_session())) {
    //             return new project_timesheet.Model(project_timesheet.session, "project.timesheet.session").call("get_session", []).done(function(project_timesheet_session) {
    //                 console.log("project_timesheet_session is ::: ", project_timesheet_session);
    //                 self.project_timesheet_db.add_project_timesheet_session({session_id: project_timesheet_session.session_id, login_number: project_timesheet_session.login_number});
    //             }).promise();
    //         }
    //     },
    //     save_to_server: function() {
    //         var self = this;
    //         this.defs = [];
    //         var defer = $.Deferred();
    //         var records = [];
    //         project_timesheet.blockUI();
    //         var reference_id;
    //         var generate_reference_id = function() { //May be move this function in db
    //             var project_timesheet_session = self.project_timesheet_db.get_project_timesheet_session();
    //             self.project_timesheet_db.sequence += 1;
    //             return project_timesheet_session.session_id.toString() + "-" + project_timesheet_session.login_number.toString() + "-" + (self.project_timesheet_db.sequence);
    //         };
    //         $.when(self.check_session()).done(function(){
    //             var activity_collection = self.get('activities');
    //             var activity_models = activity_collection.models;
    //             for (var i = 0; i < activity_models.length; i++) {
    //                 var json_data = activity_models[i].export_as_JSON();
    //                 if (!_.isUndefined(json_data.command)) {
    //                     //If reference_id is not there then create unique Reference ID
    //                     if (!json_data.reference_id) {
    //                         reference_id = generate_reference_id();
    //                         _.extend(activity_models[i], {'reference_id': reference_id});
    //                         json_data['reference_id'] = reference_id;
    //                         self.project_timesheet_db.add_activity(json_data);
    //                     }
    //                     records.push(json_data);
    //                 }
    //             }
    //             //Load data domain sent in sync_data so that it returns fresh data of last 30 days
    //             var momObj = new moment();
    //             var end_date = project_timesheet.datetime_to_str(momObj._d);
    //             var start_date = project_timesheet.datetime_to_str(momObj.subtract(30, "days")._d);
    //             var load_data_domain = [["date", ">=", start_date], ["date", "<=", end_date]];
    //             self.defs.push(new project_timesheet.Model(project_timesheet.session, "hr.analytic.timesheet").call("sync_data", [records, load_data_domain]).then(function(result) {
    //                 self.sync_complete(result);
    //             }).always(function() {
    //                 project_timesheet.unblockUI();
    //             }));
    //             return $.when.apply($, self.defs).then(function() {
    //                 self.load_stored_data();
    //                 defer.resolve();
    //             });
    //         });
    //         return defer;
    //     },
    //     reset_collections: function() {
    //         var project_collection = this.get("projects");
    //         var activity_collection = this.get("activities");
    //         project_collection.reset();
    //         activity_collection.reset();
    //     },
    //     sync_complete: function(sync_result) {
    //         //This method will flush localstorage activities once it has been sync
    //         //TODO: Remove project_timesheet_session and reload with new fetched session, if session is new then we should also start sequence from 0
    //         this.project_timesheet_db.flush_activities();
    //         this.reset_collections();
    //         //this.project_timesheet_db.clear('session');
    //         //this.project_timesheet_db.initialize_reference_sequence();
    //         this.project_timesheet_db.add_activities(sync_result.activities);
    //     },
    //     close_project_timesheet_session: function() {
    //         var project_timesheet_session = this.project_timesheet_db.get_project_timesheet_session();
    //         return new project_timesheet.Model(project_timesheet.session, "project.timesheet.session").call("close_session", [project_timesheet_session.session_id]).promise();
    //     },
    //     get_pending_records: function() {
    //        return this.project_timesheet_db.get_pending_records();
    //     }
    // });

}