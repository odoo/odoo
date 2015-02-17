openerp.project_timesheet = function(openerp) {

	//Main widget to instantiate the app
	openerp.project_timesheet.ProjectTimesheet = openerp.Widget.extend({
		start: function(){
			self = this;

			// Load session, if there is any :
			this.session = new openerp.Session();
            this.session.session_reload().then(function(){
            	// Set demo data in local storage. TO REMOVE LATER
            	// var test_data = [
	            //     {
	            //         "session_user":"admin",
	            //         "session_uid":1,
	            //         "session_server":"http://localhost:8069",
	            //         "data":{
	            //         	"next_aal_id":4,
	            //         	"next_project_id":3,
	            //         	"next_task_id":4,
	            //             "settings":{
	            //                 "default_project":{
	            //                     "id":1,
	            //                     "name":"Implementation"
	            //                 },
	            //                 "minimal_duration":15,
	            //                 "time_unit":15
	            //             },
	            //             "projects":[
	            //                 {
	            //                     "id":1,
	            //                     "name":"Implementation"
	            //                 },
	            //                 {
	            //                     "id":2,
	            //                     "name":"Testing"
	            //                 }
	            //             ],
	            //             "tasks": [
	            //                 {
	            //                     "id":1,
	            //                     "name":"C#",
	            //                     "project_id" : 1

	            //                 },
	            //                 {
	            //                     "id":2,
	            //                     "name":"Python",
	            //                     "project_id":1
	            //                 },
	            //                 {
	            //                     "id":3,
	            //                     "name":"Perl",
	            //                     "project_id":1
	            //                 }                       
	            //             ],
	            //             "account_analytic_lines":[
	            //                 {
	            //                     "server_id":undefined,
	            //                     "id":1,
	            //                     "desc":"/",
	            //                     "unit_amount":1,
	            //                     "project_id":1,
	            //                     "task_id":1,
	            //                     "date":"2015-02-09",
	            //                     "write_date":"2015-02-10 16:03:21"
	            //                 },
	            //                 {
	            //                     "server_id":undefined,
	            //                     "id":2,
	            //                     "desc":"Conversion from py 2.7 to 3.3",
	            //                     "unit_amount":2,
	            //                     "project_id":1,
	            //                     "task_id":2,
	            //                     "date":"2015-02-09",
	            //                     "write_date":"2015-02-10 16:03:21"

	            //                 },
	            //                 {
	            //                     "server_id":undefined,
	            //                     "id":3,
	            //                     "desc":"/",
	            //                     "unit_amount":0.5,
	            //                     "date":"2015-02-09",
	            //                     "write_date":"2015-02-10 16:03:21"
	            //                 }
	            //             ],
	            //             "day_plan":[
	            //                 {"task_id" : 1},
	            //                 {"task_id" : 2}
	            //             ]
	            //         }
	            //     },
	            //     {
	            //        "session_user":"demoUser",
	            //        "session_uid":1,
	            //         "session_server":"http://localhost:8069",
	            //         "data":{} 
	            //     }
	            // ];

            	// localStorage.setItem("pt_data", JSON.stringify(test_data));


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
            this.getParent().day_planner_screen.show();
        },
        goto_settings: function(){
        	this.hide();
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

        },
        test_fct: function(){
            debugger
            //this.load_server_data();
        },
        load_server_data: function(){
        	parent = this.getParent();
            
        	//aal : 
            var account_analytic_line_model = new openerp.Model("account.analytic.line");
            account_analytic_line_model.query(["id", "user_id", "task_id", "name", "unit_amount", "date", "account_id", '__last_update', 'is_timesheet'])
            	.filter([["user_id", "=", parent.session.uid]
            		,["is_timesheet","=",true]
            		,["date",">", openerp.date_to_str(moment().subtract(30, 'days')._d)]])
            	.all().then(function(aal){
            		var task_model = new openerp.Model('project.task');
            		task_model.query(["id","name", "project_id","user_id"])
            			.filter([["user_id", "=", parent.session.uid]])
            			.all().then(function(tasks){
            				var project_model = new openerp.Model('project.project');
            				project_model.query(["id", "name","tasks","user_id"])
            					.filter([["members", '=', parent.session.uid]])
            					.all().then(function(projects){
            						// Sync check : keep most recent etc.
            					});
            			});
            		// Do work on AALs
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
        		placeholder: self.data.settings.default_project.name,
        		data: {results : self.data.projects , text : 'name'},
        		formatSelection: format,
				formatResult: formatRes,
				createSearchChoice: function(user_input, new_choice){
					res = {
						id : self.data.next_project_id,
						name : user_input,
						isNew: true
					};
					return res;
				},
        	});
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
        },
        on_change_default_project: function(event){
        	var selected_project = {
    			name : event.added.name,
    			id : event.added.id
        	};
        	if(event.added.isNew){
        		self.data.next_project_id++;
        		self.data.projects.push(selected_project);
    		}
    		self.data.settings.default_project = selected_project;
    		self.getParent().update_localStorage();
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
        // start : function(){
        // 	this.initialize_project_selector();
        // 	this.initialize_task_selector();
        // },
        initialize_project_selector: function(){
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
				createSearchChoice: function(user_input, new_choice){
					res = {
						id : self.data.next_project_id,
						name : user_input,
						isNew: true
					};
					return res;
				},
                // Show the create item in second position, reducing risk of duplicate entries
                createSearchChoicePosition: function(list, item) {
                    list.splice(1, 0, item);
                },
				initSelection : function(element, callback){
					var data = {id: self.activity.project_id, name : self.get_project_name(self.activity.project_id)};
					callback(data);
				}
        	});
        },
        // Initialization of select2 for tasks
        initialize_task_selector: function(){
        	function format(item) {return item.name}
        	function formatRes(item){
        		if(item.isNew){
        			return "Create Task : " + item.name;
        		}
        		else{
        			return item.name;
        		}
        	}
            var task_list = _.where(self.data.tasks, {project_id : self.activity.project_id});
        	this.$('.pt_activity_task').select2({
        		data: {results : task_list , text : 'name'},
        		formatSelection: format,
				formatResult: formatRes,
				createSearchChoice: function(user_input, new_choice){
					res = {
						id : self.data.next_task_id,
						name : user_input,
						isNew: true,
                        project_id: self.activity.project_id
					};
					return res;
				},
                // Show the create item in second position, reducing risk of duplicate entries
                createSearchChoicePosition: function(list, item) {
                    list.splice(1, 0, item);
                },
                initSelection : function(element, callback){
                    var data = {id: self.activity.task_id, name : self.get_task_name(self.activity.task_id)};
                    callback(data);
                }
        	});
        },
        on_change_task: function(event){
        	var selected_task = {
    			name : event.added.name,
    			id : event.added.id,
                project_id: event.added.project_id
        	};
        	if(event.added.isNew){
        		self.data.next_task_id++;
        		self.data.tasks.push(selected_task);
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
			// TODO Task list! + project? 
	        // if(!_.isUndefined(this.activity.project)){
	        //     this.tasks = _.where(this.project_timesheet_model.tasks, {project_id : this.activity.project.id});
	        // }
            this.renderElement();
            this.initialize_project_selector();
            this.initialize_task_selector();
        },
        save_changes: function(){
            //TODO Save here
            var old_activity = _.findWhere(this.data.account_analytic_lines,  {id:parseInt(this.activity.id)})
            // If this condition is true, it means that the activity is a newly created one :
            if(_.isUndefined(old_activity)){
                new_length = this.data.account_analytic_lines.push({id : self.data.next_aal_id});
                old_activity = this.data.account_analytic_lines[new_length - 1];
                self.data.next_aal_id++;
            }
            old_activity.project_id = this.activity.project_id
            old_activity.task_id = this.activity.task_id
            old_activity.desc = this.activity.desc
            old_activity.unit_amount = this.activity.unit_amount
            old_activity.date = this.activity.date
            
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