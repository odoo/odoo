openerp.project_timesheet = function(openerp) {

	//Main widget to instantiate the app
	openerp.project_timesheet.ProjectTimesheet = openerp.Widget.extend({
		start: function(){
			self = this;

			// Load session, if there is any :
			this.session = new openerp.Session();
            this.session.session_reload().then(function(){
            	// Set demo data in local storage. TO REMOVE LATER
            	var test_data = [
	                {
	                    "session_user":"admin",
	                    "session_uid":1,
	                    "session_server":"http://localhost:8069",
	                    "data":{
	                    	"next_aal_id":9,
	                    	"next_project_id":3,
	                    	"next_task_id":4,
	                        "settings":{
	                            "default_project_id":undefined,
	                            "minimal_duration":15,
	                            "time_unit":15
	                        },
	                        "projects":[
	                            // {
	                            //     "id":1,
	                            //     "name":"Implementation"
	                            // },
	                            // {
	                            //     "id":2,
	                            //     "name":"Testing"
	                            // }
	                        ],
	                        "tasks": [
	                            // {
	                            //     "id":1,
	                            //     "name":"C#",
	                            //     "project_id" : 1

	                            // },
	                            // {
	                            //     "id":2,
	                            //     "name":"Python",
	                            //     "project_id":1
	                            // },
	                            // {
	                            //     "id":3,
	                            //     "name":"Perl",
	                            //     "project_id":1
	                            // }                       
	                        ],
	                        "account_analytic_lines":[
	                            {
	                                "server_id":undefined,
	                                "id":1,
	                                "desc":"/",
	                                "unit_amount":1,
	                                "project_id":1,
	                                "task_id":1,
	                                "date":"2015-02-09",
	                                "write_date":"2015-02-19 12:45:29"
	                            },
	                            {
	                                "server_id":undefined,
	                                "id":2,
	                                "desc":"Conversion from py 2.7 to 3.3",
	                                "unit_amount":2,
	                                "project_id":1,
	                                "task_id":2,
	                                "date":"2015-02-09",
	                                "write_date":"2015-02-19 12:45:26"

	                            },
	                            {
	                                "server_id":undefined,
	                                "id":3,
	                                "desc":"/",
	                                "unit_amount":0.5,
	                                "date":"2015-02-09",
	                                "write_date":"2015-02-10 16:03:21"
	                            },
	                        ],
	                        "day_plan":[
	                            {"task_id" : 1},
	                            {"task_id" : 2}
	                        ]
	                    }
	                },
	                {
	                   "session_user":"demoUser",
	                   "session_uid":1,
	                    "session_server":"http://localhost:8069",
	                    "data":{} 
	                }
	            ];
                // Comment or uncomment following line to reset demo data
            	localStorage.setItem("pt_data", JSON.stringify(test_data));


            	// Load (demo) data from local storage
            	self.stored_data = JSON.parse(localStorage.getItem("pt_data"));
             	self.user_local_data = _.findWhere(self.stored_data, {session_user : self.session.username})
             	self.data = self.user_local_data.data;

             	//Load templates for widgets
            	self.load_template().then(function(){
					self.build_widgets();
				});
            });
		},
		load_template: function(){
            var self = this;
            return openerp.session.rpc('/web/proxy/load', {path: "/project_timesheet/static/src/xml/project_timesheet.xml"}).then(function(xml) {
                openerp.qweb.add_template(xml);
            });
        },
        build_widgets: function(){
        	this.activities_screen = new openerp.project_timesheet.Activities_screen(this);
        	this.activities_screen.appendTo(this.$el);
        	this.activities_screen.show();

        	this.day_planner_screen = new openerp.project_timesheet.Day_planner_screen(this);
        	this.day_planner_screen.appendTo(this.$el);
        	this.day_planner_screen.hide();

        	this.settings_screen = new openerp.project_timesheet.Settings_screen(this);
        	this.settings_screen.appendTo(this.$el);
        	this.settings_screen.hide();

        	this.edit_activity_screen = new openerp.project_timesheet.Edit_activity_screen(this);
        	this.edit_activity_screen.appendTo(this.$el);
        	this.edit_activity_screen.hide();
        },
        update_localStorage: function(){
        	localStorage.setItem("pt_data", JSON.stringify(this.stored_data));
        }
	});

	// Basic screen widget, inherited by all screens
	openerp.project_timesheet.BasicScreenWidget = openerp.Widget.extend({
		events:{
            "click .pt_day_planner_link" : "goto_day_planner",
            "click .pt_settings_link" : "goto_settings",
            "click .pt_activities_link" : "goto_activities",
            "click .pt_validate_btn" : "goto_activities"
        },
		init: function(parent){
			this._super(parent);
			this.data = this.getParent().data;
		},
		show: function(){
            this.$el.show();
        },
        hide: function(){
            this.$el.hide();
        },
		goto_day_planner: function(){
            this.hide();
            this.getParent().day_planner_screen.renderElement();
            this.getParent().day_planner_screen.show();
        },
        goto_settings: function(){
        	this.hide();
            this.getParent().settings_screen.renderElement();
            this.getParent().settings_screen.initialize_project_selector();
            this.getParent().settings_screen.show();
        },
        goto_activities: function(){
        	this.hide();
            this.getParent().activities_screen.show();
        },
        // Methods that might be moved later if necessary :
        get_project_name: function(project_id){
        	project = _.findWhere(self.data.projects, {id : project_id});
        	if (!_.isUndefined(project)){
        		return project.name;
        	}
        	else{
        		return "No project selected yet";
        	}
        },
        get_task_name: function(task_id){
        	task = _.findWhere(self.data.tasks, {id : task_id})
        	if (!_.isUndefined(task)){
        		return task.name;
        	}
        	else{
        		return "No task selected yet";
        	}
        },

        //Utility methods to format and validate time
        
        // Takes a decimal hours and converts it to hh:mm string representation
	    // e.g. 1.5 => "01:30"
	    unit_amount_to_hours_minutes: function(unit_amount){
	        if(_.isUndefined(unit_amount)){
	            return ["00","00"];
	        }

	        var minutes = Math.round((unit_amount % 1) * 60);
	        var hours = Math.floor(unit_amount);

	        if(minutes < 10){
	            minutes = "0" + minutes.toString();
	        }
	        else{
	            minutes = minutes.toString();
	        }
	        if(hours < 10){
	            hours = "0" + hours.toString();
	        }
	        else{
	            hours = hours.toString();
	        }

	        return hours + ":" + minutes;
	    },

	    // Takes a string as input and tries to parse it as a hh:mm duration/ By default, strings without ":" are considered to be hh. 
	    // We use % 1 to avoid accepting NaN as an integer.
	    validate_duration: function(hh_mm){
	        var time = hh_mm.split(":");
	        if(time.length === 1){
	            var hours = parseInt(time[0]);
	            if(hours % 1 != 0){
	                return undefined;
	            }
	            if (hours < 10){
	                return "0" + hours.toString() + ":00";
	            }
	            else{
	                return hours.toString() + ":00";
	            }
	        }
	        else if(time.length === 2){
	            var hours = parseInt(time[0]);
	            var minutes = parseInt(time[1]);
	            if((hours % 1 === 0) && (minutes % 1 === 0) && minutes < 61){
	                if(minutes < 10){
	                    minutes = "0" + minutes.toString();
	                }
	                else{
	                    minutes = minutes.toString();
	                }
	                if(hours < 10){
	                    hours = "0" + hours.toString();
	                }
	                else{
	                    hours = hours.toString();
	                }

	                return hours + ":" + minutes;
	            }
	            else{
	                return undefined;
	            }
	        }
	        else{
	            return undefined;
	        }

	    },

	    hh_mm_to_unit_amount: function(hh_mm){
	        var time = hh_mm.split(":");
	        if(time.length === 1){
	            return parseInt(time[0]);
	        }
	        else if(time.length === 2){
	            var hours = parseInt(time[0]);
	            var minutes = parseInt(time[1]);
	            return Math.round((hours + (minutes / 60 )) * 100) / 100;
	        }
	        else{
	            return undefined;
	        }
	            
	    }

	});

	openerp.project_timesheet.Activities_screen = openerp.project_timesheet.BasicScreenWidget.extend({
        template: "activities_screen",
        init: function(parent) {
            self = this;
            self.screen_name = "Activities";
            self._super(parent);
            // Events specific to this screen
            _.extend(self.events,
                {
                    "click .pt_button_plus_activity":"goto_create_activity_screen",
                    "click .pt_activity":"edit_activity",
                    "click .pt_btn_start_activity":"start_activity",
                    "click .pt_btn_stop_activity":"stop_activity",
                    "click .pt_test_btn":"test_fct"
                }
            );
            self.account_analytic_lines = self.data.account_analytic_lines;
        },
        //Go to the create / edit activity
        goto_create_activity_screen: function(){
            this.getParent().edit_activity_screen.re_render();
            this.hide();
            this.getParent().edit_activity_screen.show();
        },
        // Go to the edit screen to edit a specific activity
        edit_activity: function(event){
			this.getParent().edit_activity_screen.re_render(event.currentTarget.dataset.activity_id);
            this.hide();
            this.getParent().edit_activity_screen.show();
        },
        start_activity: function(){
            this.$(".pt_btn_start_activity").html('<span class="glyphicon glyphicon-stop" aria-hidden="true"></span> Stop </a>');
            this.$(".pt_btn_start_activity").toggleClass("pt_btn_start_activity pt_btn_stop_activity");
        },
        stop_activity: function(){
            this.$(".pt_btn_stop_activity").html('<span class="glyphicon glyphicon-play" aria-hidden="true"></span> Start</a>');
            this.$(".pt_btn_stop_activity").toggleClass("pt_btn_start_activity pt_btn_stop_activity");

        },
        test_fct: function(){
            self = this;
            this.sync();
            this.renderElement();    
        },
        sync: function(){
            var account_analytic_line_model = new openerp.Model("account.analytic.line");
            sv_lines = account_analytic_line_model.call("test_fct" , []).then(function(sv_lines){
                console.log(sv_lines);
            });
            
        },
        old_load_server_data: function(){
            var account_analytic_line_model = new openerp.Model("account.analytic.line");
            var task_model = new openerp.Model('project.task');
            var project_model = new openerp.Model('project.project');
            var aals_to_update = [];

            self = this;
        	var parent = this.getParent();
            console.log("Down sync starting")
            account_analytic_line_model.query(["id", "user_id", "task_id", "name", "unit_amount", "date", "account_id", '__last_update', 'is_timesheet'])
            	.filter([["user_id", "=", parent.session.uid]
            		,["is_timesheet","=",true]
            		,["date",">", openerp.date_to_str(moment().subtract(30, 'days')._d)]])
            	.all()
                .then(function(aals){
                    // aals available
                    // list of task ids referenced in aals:
                    var aals_with_task = _.filter(aals, function(aal){
                        return aal.task_id;
                    });
                    var task_ids_list = _.map(aals_with_task , function(aal){return aal.task_id[0]});

                    // In theory, all aals should have an account_id, but we still make a check
                    var aals_with_account = _.filter(aals, function(aal){
                        return aal.account_id;
                    });
                    var account_ids_list = _.map(aals_with_account , function(aal){return aal.account_id[0]});

            		task_model.query(["id","name", "project_id","user_id"])
            			.filter(['|' , ["user_id", "=", parent.session.uid] , ["id","in",task_ids_list]])
            			.all()
                        .then(function(tasks){
                            //tasks available
                            var tasks_with_project = _.filter(tasks, function(task){
                                return task.project_id;
                            });
                            var project_ids_list = _.map(tasks_with_project , function(task){return task.project_id[0]});

            				project_model.query(["id", "name","tasks","members", "analytic_account_id"])
            					.filter([ '|' 
                                    , '|'
                                    , ["id", "in" , project_ids_list] 
                                    , ["members", '=', parent.session.uid]
                                    , ["analytic_account_id" , "in" , account_ids_list] ])
            					.all().then(function(projects){
                                    // Projects available
                                    
                                    // Write new projects to localstorage: 
                                    _.each(projects, function(project){
                                        //Small preprocessing, used later:
                                        project.analytic_account_id = project.analytic_account_id[0];
                                        //
                                        local_project = _.findWhere(parent.data.projects, {server_id : project.id});
                                        if(_.isUndefined(local_project)){
                                            parent.data.projects.push({
                                                id : parent.data.next_project_id,
                                                server_id : project.id,
                                                name : project.name
                                            });
                                            parent.data.next_project_id++;
                                            parent.update_localStorage();
                                        }
                                    });

                                    // Write new tasks to localstorage:
                                    _.each(tasks, function(task){
                                        local_task = _.findWhere(parent.data.tasks, {server_id : task.id});
                                        if(_.isUndefined(local_task)){
                                            // Find local project_id :
                                            local_project = _.findWhere(parent.data.projects, {server_id : task.project_id[0]});
                                            parent.data.tasks.push({
                                                id : parent.data.next_task_id,
                                                server_id : task.id,
                                                name : task.name,
                                                project_id : local_project.id
                                            });
                                            parent.data.next_task_id++;
                                            parent.update_localStorage();
                                        }
                                    });

                                    // Write new aals to localStorage
                                    _.each(aals, function(aal){
                                        local_aal = _.findWhere(parent.data.account_analytic_lines, {server_id : aal.id});
                                        if(_.isUndefined(local_aal)){
                                            project = _.findWhere(projects, {analytic_account_id : aal.account_id[0]});
                                            // If the AAL has no project we don't import it.
                                            if(project){
                                                local_project = _.findWhere(parent.data.projects, {server_id : project.id});
                                                project_id = local_project.id;
                                                if(aal.task_id){
                                                    task = _.findWhere(parent.data.tasks, {server_id : aal.task_id[0]});
                                                    task_id = task.id;
                                                }
                                                else{
                                                    task_id = undefined;
                                                }
                                                parent.data.account_analytic_lines.push({
                                                    id : parent.data.next_aal_id,
                                                    server_id : aal.id,
                                                    desc : aal.name,
                                                    unit_amount : aal.unit_amount,
                                                    task_id : task_id,
                                                    project_id : project_id,
                                                    write_date : aal.__last_update,
                                                    date : aal.date
                                                });
                                                parent.data.next_aal_id++;
                                                parent.update_localStorage();

                                            }
                                        }
                                        else{
                                            // If the local version is more recent
                                            // We'll need to update it on the sv
                                            if(openerp.str_to_datetime(local_aal.write_date) > openerp.str_to_datetime(aal.__last_update)){
                                                aals_to_update.push(local_aal);

                                            }
                                            // If the remote version is more recent
                                            // We will update the local version.
                                            else if(openerp.str_to_datetime(local_aal.write_date) < openerp.str_to_datetime(aal.__last_update)){
                                                project = _.findWhere(projects, {analytic_account_id : aal.account_id[0]});
                                                local_project = _.findWhere(parent.data.projects, {server_id : project.id});
                                                local_task = _.findWhere(parent.data.tasks, {server_id : aal.task_id[0]});

                                                _.extend(local_aal,{
                                                    desc : aal.name,
                                                    unit_amount : aal.unit_amount,
                                                    task_id : local_task.id,
                                                    project_id : local_project.id,
                                                    write_date : aal.__last_update,
                                                    date : aal.date
                                                });
                                                parent.update_localStorage();
                                            }
                                        }
                                    });
                                    // Sorting to have most recent aals on top of screen.
                                    parent.data.account_analytic_lines.sort(function(a,b){
                                        return openerp.str_to_datetime(b.write_date) - openerp.str_to_datetime(a.write_date);
                                    });
                                    parent.update_localStorage();
                                    parent.activities_screen.renderElement();
            					}).then(function(){
                                    // Sync to server
                                    console.log("Up sync starting");
                                    self.project_defs = [];
                                    // Projects sync
                                    _.each(parent.data.projects, function(project){
                                        if(_.isUndefined(project.server_id)){
                                            // Create project on server
                                            self.project_defs.push(project_model.call('create', [{name : project.name , use_tasks : true , invoice_on_timesheets : true }]).then(function(project_server_id){
                                                project.server_id = project_server_id;
                                                parent.update_localStorage();
                                            }));
                                        }
                                    });

                                    $.when.apply($, self.project_defs).then(function() {
                                        console.log("projects synced");
                                        //Tasks sync:
                                        self.task_defs = [];
                                        _.each(parent.data.tasks, function(task){
                                            if(_.isUndefined(task.server_id)){
                                                // Find the server_id of this task :
                                                var project_server_id = _.findWhere(parent.data.projects, {id : task.project_id}).server_id;
                                                self.task_defs.push(task_model.call('create', [{name : task.name, project_id : project_server_id}]).then(function(task_server_id){
                                                    task.server_id = task_server_id;
                                                    parent.update_localStorage();
                                                }));
                                            }
                                        });
                                        $.when.apply($, self.task_defs).then(function() {
                                            console.log("Tasks synced");
                                            // AALS sync:
                                            self.aals_defs = [];
                                            _.each(parent.data.account_analytic_lines, function(aal){
                                                // New AALs created from the UI
                                                if(_.isUndefined(aal.server_id)){
                                                    // Find the server_id of the task and project of the aal
                                                    var project_server_id = _.findWhere(parent.data.projects, {id : aal.project_id}).server_id;
                                                    // We need to call the server to find the analytic account linked to the project
                                                    project_model.query(["analytic_account_id"]).filter([["id" , "=" , project_server_id]]).first().then(function(server_account_id){
                                                        var task_server_id;
                                                        if (aal.task_id){
                                                            task_server_id = _.findWhere(parent.data.tasks, {id : aal.task_id}).server_id;
                                                        }
                                                        var new_aal = {
                                                            name : aal.desc,
                                                            account_id : server_account_id.analytic_account_id[0],
                                                            is_timesheet : true,
                                                            unit_amount : aal.unit_amount,
                                                            project_id : project_server_id,
                                                            task_id : task_server_id
                                                        };
                                                        context = new openerp.web.CompoundContext({'default_is_timesheet': true});
                                                        self.aals_defs.push(account_analytic_line_model.call('create', [new_aal], {context : context}).then(function(aal_server_id){
                                                            aal.server_id = aal_server_id;
                                                            parent.update_localStorage();
                                                        }));
                                                    });
                                                }
                                            });
                                            // AAls that need to be updated or deleted
                                            $.when.apply($, self.aals_defs).then(function() {
                                                _.each(aals_to_update, function(aal){
                                                    var project_server_id = _.findWhere(parent.data.projects, {id : aal.project_id}).server_id;
                                                    // We need to call the server to find the analytic account linked to the project
                                                    project_model.query(["analytic_account_id"]).filter([["id" , "=" , project_server_id]]).first().then(function(server_account_id){
                                                        var task_server_id;
                                                        if (aal.task_id){
                                                            task_server_id = _.findWhere(parent.data.tasks, {id : aal.task_id}).server_id;
                                                        }
                                                        var new_aal = {
                                                            name : aal.desc,
                                                            account_id : server_account_id.analytic_account_id[0],
                                                            is_timesheet : true,
                                                            unit_amount : aal.unit_amount,
                                                            project_id : project_server_id,
                                                            task_id : task_server_id
                                                        };
                                                        account_analytic_line_model.call('write', [aal.server_id , new_aal]);
                                                    });
                                                });
                                            });
                                        });
                                    });
                                });
            			});
            	});
        }
    });

    openerp.project_timesheet.Day_planner_screen = openerp.project_timesheet.BasicScreenWidget.extend({
        template: "day_planner_screen",
        init: function(parent) {
        	this._super(parent);
            this.screen_name = "Day Planner";
            _.extend(self.events,
                {
                    "click .pt_day_plan_select":"add_to_day_plan"
                }
            );
            this.tasks = this.data.tasks;
        },
        add_to_day_plan: function(event){
            console.log(event.currentTarget.dataset.task_id);
        }
    });

    openerp.project_timesheet.Settings_screen = openerp.project_timesheet.BasicScreenWidget.extend({
        template: "settings_screen",
        init: function(parent) {
        	self = this;
            this._super(parent);
            this.screen_name = "Settings";
            _.extend(self.events,
                {
                    "change input.pt_minimal_duration":"on_change_minimal_duration",
                    "change input.pt_time_unit":"on_change_time_unit",
                    "change input.pt_default_project_select2":"on_change_default_project"
                }
            );
        },
        start: function(){
            this.initialize_project_selector();
        },
        initialize_project_selector: function(){
            self = this;
            // Initialization of select2 for projects
            function format(item) {return item.name}
            function formatRes(item){
                if(item.isNew){
                    return "Create Project : " + item.name;
                }
                else{
                    return item.name;
                }
            }
            this.$('.pt_default_project_select2').select2({
                data: {results : self.data.projects , text : 'name'},
                formatSelection: format,
                formatResult: formatRes,
                createSearchChoicePosition : 'bottom',
                placeholder: "No default project",
                allowClear: true,
                createSearchChoice: function(user_input, new_choice){
                    //Avoid duplictate projects
                    var duplicate = _.find(self.data.projects, function(project){
                        return (project.name.toUpperCase() === user_input.trim().toUpperCase());
                    });
                    if (duplicate){
                        return undefined;
                    }
                    res = {
                        id : self.data.next_project_id,
                        name : user_input.trim(),
                        isNew: true,
                    };
                    return res;
                },
                initSelection : function(element, callback){
                    var data = {id: self.data.settings.default_project_id, name : self.get_project_name(self.data.settings.default_project_id)};
                    callback(data);
                }
            }).select2('val',[]);
        },
        on_change_default_project: function(event){
            self = this;
            // "cleared" case
            if(_.isUndefined(event.added)){
                self.data.settings.default_project_id = undefined;
            }
            // "Select" case
            else{
                var selected_project = {
                    name : event.added.name,
                    id : event.added.id
                };
                if(event.added.isNew){
                    self.data.next_project_id++;
                    self.data.projects.push(selected_project);
                }
                self.data.settings.default_project_id = selected_project.id;
            }
            self.getParent().update_localStorage();
            
        },
        on_change_minimal_duration: function(){
            //TODO Check that input is an int between 0 and 60
            this.data.settings.minimal_duration = (this.$("input.pt_minimal_duration").val());
            this.getParent().update_localStorage();
        },
        on_change_time_unit: function(){
        	//TODO Check that input is an int between 0 and 60
            this.data.settings.time_unit = (this.$("input.pt_time_unit").val());
            this.getParent().update_localStorage();
        }
    });
	//TODO : clean up select2 inittialize method and re-rendering logic
    openerp.project_timesheet.Edit_activity_screen = openerp.project_timesheet.BasicScreenWidget.extend({
        template: "edit_activity_screen",
        init: function(parent) {
        	self = this;
        	this._super(parent);
            this.screen_name = "Edit Activity";
            _.extend(self.events,
                {
                    "change input.pt_activity_duration":"on_change_duration",
                    "change textarea.pt_description":"on_change_description",
                    "change input.pt_activity_project":"on_change_project",
                    "change input.pt_activity_task":"on_change_task",
                    "click .pt_discard_changes":"discard_changes",
                    "click .pt_validate_edit_btn" : "save_changes"
                }
            );
            this.activity = {
                project_id: undefined,
                task_id: undefined,
                desc:"/",
                unit_amount: undefined,
                date: (openerp.date_to_str(new Date()))
            };
        },
        initialize_project_selector: function(){
            self = this;
        	// Initialization of select2 for projects
        	function format(item) {return item.name}
        	function formatRes(item){
        		if(item.isNew){
        			return "Create Project : " + item.name;
        		}
        		else{
        			return item.name;
        		}
        	}
        	this.$('.pt_activity_project').select2({
        		data: {results : self.data.projects , text : 'name'},
        		formatSelection: format,
				formatResult: formatRes,
                createSearchChoicePosition : 'bottom',
				createSearchChoice: function(user_input, new_choice){
                    //Avoid duplictate projects in one project
                    var duplicate = _.find(self.data.projects, function(project){
                        return (project.name.toUpperCase() === user_input.trim().toUpperCase());
                    });
                    if (duplicate){
                        return undefined;
                    }
                    res = {
                        id : self.data.next_project_id,
                        name : user_input.trim(),
                        isNew: true,
                    };
                    return res;
                },
				initSelection : function(element, callback){
					var data = {id: self.activity.project_id, name : self.get_project_name(self.activity.project_id)};
					callback(data);
				}
        	});
        },
        // Initialization of select2 for tasks
        initialize_task_selector: function(){
            self = this;
        	function format(item) {return item.name}
        	function formatRes(item){
        		if(item.isNew){
        			return "Create Task : " + item.name;
        		}
        		else{
        			return item.name;
        		}
        	}
            self.task_list = _.where(self.data.tasks, {project_id : self.activity.project_id});
        	this.$('.pt_activity_task').select2({
        		data: {results : self.task_list , text : 'name'},
        		formatSelection: format,
				formatResult: formatRes,
                createSearchChoicePosition : 'bottom',
				createSearchChoice: function(user_input, new_choice){
                    //Avoid duplictate tasks in one project
                    var duplicate = _.find(self.task_list, function(task){
                        return (task.name.toUpperCase() === user_input.trim().toUpperCase());
                    });
                    if (duplicate){
                        return undefined;
                    }
					res = {
						id : self.data.next_task_id,
						name : user_input.trim(),
						isNew: true,
                        project_id: self.activity.project_id
					};
					return res;
				},
                initSelection : function(element, callback){
                    var data = {id: self.activity.task_id, name : self.get_task_name(self.activity.task_id)};
                    callback(data);
                }
        	});
        },
        on_change_task: function(event){
            self = this;
        	var selected_task = {
    			name : event.added.name,
    			id : event.added.id,
                project_id: event.added.project_id
        	};
        	if(event.added.isNew){
        		self.data.next_task_id++;
        		self.data.tasks.push(selected_task);
                self.task_list.push(selected_task);
        		self.getParent().update_localStorage();
    		}
    		self.activity.task_id = selected_task.id;
        },
        on_change_project: function(event){
        	var selected_project = {
    			name : event.added.name,
    			id : event.added.id
        	};
        	if(event.added.isNew){
        		self.data.next_project_id++;
        		self.data.projects.push(selected_project);
        		self.getParent().update_localStorage();
    		}
    		self.activity.project_id = selected_project.id;
            // If the project has been changed, we reset the task.
            self.activity.task_id = undefined;
            self.initialize_task_selector();
        },
        on_change_duration: function(event){
            var duration = self.validate_duration(this.$("input.pt_activity_duration").val());
            if(_.isUndefined(duration)){
                this.$("input.pt_activity_duration").val("00:00");
                this.$("input.pt_activity_duration + p").text("Please entre a valid duration in the hh:mm format, such as 01:30");
            }
            else{
                this.$("input.pt_activity_duration").val(duration);
                this.$("input.pt_activity_duration + p").text("");
                
                this.activity.unit_amount = self.hh_mm_to_unit_amount(duration);
            }
        },
        on_change_description: function(event){
            this.activity.desc = this.$("textarea.pt_description").val();
        },

        // Function to re-render the screen with a new activity.
        // we use clone to work on a temporary version of activity.
        re_render: function(activity_id){
        	if(!_.isUndefined(activity_id)){
	            this.activity = _.clone(_.findWhere(this.data.account_analytic_lines,  {id:parseInt(activity_id)}));
			}
            else if(!_.isUndefined(self.data.settings.default_project_id)){
                this.activity.project_id = self.data.settings.default_project_id;
            }

            this.renderElement();
            this.initialize_project_selector();
            this.initialize_task_selector();
        },
        save_changes: function(){
            // Validation step :  The only compulsory field is project.
            if(_.isUndefined(this.activity.project_id)){
                this.$('.pt_save_msg').show(0).delay(5000).hide(0);
                return
            } 

            var old_activity = _.findWhere(this.data.account_analytic_lines,  {id:parseInt(this.activity.id)})
            // If this condition is true, it means that the activity is a newly created one :
            if(_.isUndefined(old_activity)){
                this.data.account_analytic_lines.unshift({id : self.data.next_aal_id});
                old_activity = this.data.account_analytic_lines[0];
                self.data.next_aal_id++;
            }
            old_activity.project_id = this.activity.project_id;
            old_activity.task_id = this.activity.task_id;
            old_activity.desc = this.activity.desc;
            old_activity.unit_amount = this.activity.unit_amount;
            old_activity.date = this.activity.date;
            old_activity.write_date = openerp.datetime_to_str(new Date());
            
            this.data.account_analytic_lines.sort(function(a,b){
                return openerp.str_to_datetime(b.write_date) - openerp.str_to_datetime(a.write_date);
            });
            this.getParent().update_localStorage();            

            //To empty screen data
            this.reset_activity();
            this.getParent().activities_screen.renderElement();
            this.goto_activities();
        },
        discard_changes: function(){
            this.reset_activity();
            this.goto_activities();
        },
        reset_activity: function(){
            this.activity = {
                project_id: undefined,
                task_id: undefined,
                desc:"/",
                unit_amount: undefined,
                date: (openerp.date_to_str(new Date()))
            };

            if (!_.isUndefined(self.data.settings.default_project)){
                this.activity.project = self.data.settings.default_project;
            }
        }
    });
};