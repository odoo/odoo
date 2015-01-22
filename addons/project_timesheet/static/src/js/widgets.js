function odoo_project_timesheet_widgets(project_timesheet) {
    //var QWeb = openerp.qweb,
    var QWeb = project_timesheet.qweb,
    _t = openerp._t;

    project_timesheet.project_timesheet_widget = openerp.Widget.extend({
        template: "ProjectTimesheet",
        init: function() {
            this._super.apply(this, arguments);
            project_timesheet.project_timesheet_model = new project_timesheet.project_timesheet_model({project_timesheet_widget: this}); //May be store in this, we'll not have session initially, need to discuss how to manage session
        },
        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            $.when(project_timesheet.project_timesheet_model.ready).always(function() {
                self.build_widgets();
                self.screen_selector.set_default_screen();
            });
        },
        build_widgets: function() {
            //Creates all widgets instances and add into this object
            /*----------------Screen------------------*/

            //Append all screen widget in screen element of this.$el, by default all will be hidden and then current screen will be visible
            this.welcome_screen = new project_timesheet.Welcome_screen(this, {project_timesheet_model: project_timesheet.project_timesheet_model});
            this.welcome_screen.appendTo(this.$('.screens'));

            this.day_planner_screen = new project_timesheet.Day_planner_screen(this, {project_timesheet_model: project_timesheet.project_timesheet_model});
            this.day_planner_screen.appendTo(this.$('.screens'));

            this.settings_screen = new project_timesheet.Settings_screen(this, {project_timesheet_model: project_timesheet.project_timesheet_model});
            this.settings_screen.appendTo(this.$('.screens'));

            /*----------------Screen Selector------------------*/
            this.screen_selector = new project_timesheet.ScreenSelector({
                project_timesheet_model: project_timesheet.project_timesheet_model,
                screen_set:{
                    'welcome_screen': this.welcome_screen,
                    'day_planner_screen' : this.day_planner_screen,
                    'settings_screen' : this.settings_screen
                },
                default_screen: 'welcome_screen',
            });
        },
    });

    project_timesheet.FieldMany2One = openerp.Widget.extend({
        template: "FieldMany2One",
        init: function(parent, options) {
            this.model = options.model;
            this.search_model = options.search_model;
            this.classname = options.classname;
            this.label = options.label;
            this.placeholder = options.placeholder;
            this.id_for_input = options.id_for_input;
            this.project_timesheet_db = project_timesheet.project_timesheet_model.project_timesheet_db;
            this._drop_shown = false;
            this._super.apply(this, arguments);
            this.set({value: false, display_string: false, effective_readonly: false});
        },
        start: function() {
            this._super.apply(this, arguments);
            this.prepare_autocomplete();
            this.on("change:effective_readonly", this, this.reinitialize);
            this.$el.find("textarea").change(_.bind(this.input_changed, this));
        },
        reinitialize: function() {
            //this.destroy_content();
            this.renderElement();
            //this.initialize_content();
        }
    });

    // project_timesheet.ActivityListView = openerp.Widget.extend({
    //     template: "ActivityList",
    //     init: function() {
    //         this._super.apply(this, arguments);
    //         this.project_timesheet_model = project_timesheet.project_timesheet_model;
    //         this.project_timesheet_db = this.project_timesheet_model.project_timesheet_db;
    //         this.activities = [];
    //     },
    //     start: function() {
    //         this._super.apply(this, arguments);
    //         this.$(".pt_error").popover({
    //             'placement': 'auto top',
    //             'container': this.$el,
    //             'html': true,
    //             'trigger': 'hover',
    //             'animation': false,
    //             'toggle': 'popover',
    //             'delay': {'show': 300, 'hide': 100}
    //         });
    //     },
    //     renderElement: function() {
    //         this.activities = this.project_timesheet_db.get_activities();
    //         this.activities = _.filter(this.activities, function(activity) {return activity.command != 2;});
    //         this.replaceElement(QWeb.render(this.template, {widget: this, activities: this.activities}));
    //     },
    //     format_duration: function(field_val) {
    //         return project_timesheet.format_duration(field_val);
    //     },
    //     get_total: function() {
    //         var total = 0;
    //         _.each(this.activities, function(activity) { total += activity.unit_amount;});
    //         return this.format_duration(total);
    //     }
    // });

}