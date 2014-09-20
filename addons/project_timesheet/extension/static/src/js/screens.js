function odoo_project_timesheet_screens(project_timesheet) {

    var QWeb = openerp.qweb,
    _t = openerp._t;

    project_timesheet.ScreenSelector = openerp.Class.extend({
        init: function(options){
            this.project_timesheet_model = options.project_timesheet_model;

            this.screen_set = options.screen_set || {};

            this.default_screen = options.default_screen;

            this.current_screen = null; 

            for(screen_name in this.screen_set){
                this.screen_set[screen_name].hide();
            }

        },
        add_screen: function(screen_name, screen){
            screen.hide();
            this.screen_set[screen_name] = screen;
            return this;
        },
        set_current_screen: function(screen_name, params, refresh){
            var screen = this.screen_set[screen_name];
            if(!screen){
                console.error("ERROR: set_current_screen("+screen_name+") : screen not found");
            }

            var old_screen_name = this.project_timesheet_model.get_screen_data('screen');

            this.project_timesheet_model.set_screen_data('screen', screen_name);

            if(params){
                this.project_timesheet_model.set_screen_data('params', params);
            }

            if( screen_name !== old_screen_name ){
                this.project_timesheet_model.set_screen_data('previous-screen',old_screen_name);
            }

            if ( refresh || screen !== this.current_screen){
                if(this.current_screen){
                    this.current_screen.close();
                    this.current_screen.hide();
                }
                this.current_screen = screen;
                this.current_screen.show();
            }
        },
        get_current_screen: function(){
            //return this.pos.get('selectedOrder').get_screen_data('screen') || this.default_screen;
            return this.project_timesheet_model.get_screen_data('screen') || this.default_screen;
        },
        back: function(){
            var previous = this.project_timesheet_model.get_screen_data('previous-screen');
            if(previous){
                this.set_current_screen(previous);
            }
        },
        get_current_screen_param: function(param){
            var params = this.project_timesheet_model.get_screen_data('params');
            return params ? params[param] : undefined;
        },
        set_default_screen: function(){
            this.set_current_screen(this.default_screen);
        },
    });

    project_timesheet.ScreenWidget = openerp.Widget.extend({ //Make sure we need to extend project_timesheet_widget or openerp.widget
        init: function(parent,options){
            this._super(parent,options);
            this.hidden = false;
        },
        // this method shows the screen and sets up all the widget related to this screen. Extend this method
        // if you want to alter the behavior of the screen.
        show: function(){
            var self = this;

            this.hidden = false;
            if(this.$el){
                this.$el.removeClass('oe_hidden');
            }
        },

        // this method is called when the screen is closed to make place for a new screen. this is a good place
        // to put your cleanup stuff as it is guaranteed that for each show() there is one and only one close()
        close: function(){
            //TO Implement
        },

        // this methods hides the screen. It's not a good place to put your cleanup stuff as it is called on the
        // POS initialization.
        hide: function(){
            this.hidden = true;
            if(this.$el){
                this.$el.addClass('oe_hidden');
            }
        },

        // we need this because some screens re-render themselves when they are hidden
        // (due to some events, or magic, or both...)  we must make sure they remain hidden.
        // the good solution would probably be to make them not re-render themselves when they
        // are hidden. 
        renderElement: function(){
            this._super();
            if(this.hidden){
                if(this.$el){
                    this.$el.addClass('oe_hidden');
                }
            }
        },
    });

    project_timesheet.ActivityScreen = project_timesheet.ScreenWidget.extend({
        template: "ActivityScreen",
        init: function(project_timesheet_widget, options) {
            this._super.apply(this, arguments);
            this.activities = options.project_timesheet_model.project_timesheet_db.get_activities();
        },
        start: function() {
            this._super.apply(this, arguments);
            this.pad_table_to(11);
        },
        pad_table_to: function(count) {
            
        },
        render: function() {
            QWeb.render('ActivityScreen', {widget: this, activities: this.activities});
        },
    });

    project_timesheet.ModifyActivityScreen = project_timesheet.ScreenWidget.extend({
        template: "ModifyActivityScreen",
        init: function(project_timesheet_widget, options) {
            this._super.apply(this, arguments);
        },
        start: function() {
            this._super.apply(this, arguments);
        }
    });

    project_timesheet.SyncScreen = project_timesheet.ScreenWidget.extend({
        template: "SyncScreen",
        init: function(project_timesheet_widget, options) {
            this._super.apply(this, arguments);
        },
        start: function() {
            this._super.apply(this, arguments);
        }
    });

    project_timesheet.StatisticScreen = project_timesheet.ScreenWidget.extend({
        template: "StatisticScreen",
        init: function(project_timesheet_widget, options) {
            this._super.apply(this, arguments);
        },
        start: function() {
            this._super.apply(this, arguments);
        }
    });
}