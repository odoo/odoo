function odoo_project_timesheet_widgets(project_timesheet) {
    //var QWeb = openerp.qweb,
    var QWeb = project_timesheet.qweb,
    _t = openerp._t;

    project_timesheet.project_timesheet_widget = openerp.Widget.extend({
        template: "ProjectTimesheet",
        init: function() {
            this._super.apply(this, arguments);
            /** Setup default session */
            //openerp.session = new instance.web.Session(); //May be store in this object, no need to store in openerp global
            //project_timesheet.project_timesheet_model = new project_timesheet.project_timesheet_model(openerp.session, {project_timesheet_widget: this}); //May be store in this
            project_timesheet.project_timesheet_model = new project_timesheet.project_timesheet_model({project_timesheet_widget: this}); //May be store in this, we'll not have session initially, need to discuss how to manage session
        },
        start: function() {
            this._super.apply(this, arguments);
            //Add the concept of screen, screen will decide which widgets to render at which position
            //var pt_activity = new project_timesheet.ActivityScreen(this, {});
            //pt_activity.replace(this.$el.find(".content_area"));
            //var pt_footer = new project_timesheet.FooterWidget(this, {});
            //pt_footer.replace(this.$el.find(".pt_footer"));
            this.build_widgets();
            this.screen_selector.set_default_screen();
        },
        build_widgets: function() {
            //Creates all widgets instances and add into this object
            /*----------------Screen------------------*/
            this.activity_screen = new project_timesheet.ActivityScreen(this, {project_timesheet_model: project_timesheet.project_timesheet_model});
            //Append all screen widget in screen element of this.$el, by default all will be hidden and then current screen will be visible
            this.activity_screen.appendTo(this.$('.screens'));

            this.add_activity_screen = new project_timesheet.AddActivityScreen(this, {project_timesheet_model: project_timesheet.project_timesheet_model});
            this.add_activity_screen.appendTo(this.$('.screens'));

            this.sync_screen = new project_timesheet.SyncScreen(this, {project_timesheet_model: project_timesheet.project_timesheet_model});
            this.sync_screen.appendTo(this.$('.screens'));

            this.stat_screen = new project_timesheet.StatisticScreen(this, {project_timesheet_model: project_timesheet.project_timesheet_model});
            this.stat_screen.appendTo(this.$('.screens'));

            /*----------------Screen Selector------------------*/
            //TODO: change activity screen to activity_list and add_activity to simply activity for proper naming convention
            this.screen_selector = new project_timesheet.ScreenSelector({
                project_timesheet_model: project_timesheet.project_timesheet_model,
                screen_set:{
                    'activity': this.activity_screen,
                    'sync' : this.sync_screen,
                    'add_activity': this.add_activity_screen,
                    'stat' : this.stat_screen,
                },
                default_screen: 'activity',
            });
        },
    });

    project_timesheet.FieldMany2One = openerp.Widget.extend({
        template: "FieldMany2One",
        init: function(parent, options) {
            this.model = options.model;
            this.classname = options.classname;
            this.label = options.label;
            this.id_for_input = options.id_for_input;
            this.project_timesheet_db = project_timesheet.project_timesheet_model.project_timesheet_db;
            this._super.apply(this, arguments);
        },
        start: function() {
            this._super.apply(this, arguments);
            this.prepare_autocomplete();
            this.$dropdown = this.$el.find(".pt_m2o_drop_down_button");
            this.$dropdown.on("click", function(event) {
                var $target = $(event.target).is("img") ? $(event.target).parent() : $(event.target);
                var $input = $target.siblings("input");
                $input.focus();
                $input.autocomplete("search");
            });
        },
        prepare_autocomplete: function() {
            var self = this;
            this.$input = this.$el.find("input");
            this.$input.autocomplete({
                source: function(req, resp) {
                    self.get_search_result(req.term).done(function(result) {
                        resp(result);
                    });
                },
                select: function(event, ui) {
                    isSelecting = true;
                    var item = ui.item;
                    
                    if (item.id) {
                        self.$input.data("id", item.id);
                        self.$input.val(item.name);
                        return false;
                    } else if (item.action) {
                        item.action(event);
                        return false;
                    }
                },
                focus: function(e, ui) {
                    e.preventDefault();
                },
                html: true,
                minLength: 0,
                delay: 250
            });
            // set position for list of suggestions box
            self.$input.autocomplete( "option", "position", { my : "left top", at: "left bottom" } );
            self.$input.autocomplete("widget").openerpClass();
            // used to correct a bug when selecting an element by pushing 'enter' in an editable list
            self.$input.keyup(function(e) {
                if (e.which === 13) { // ENTER
                    if (isSelecting)
                        e.stopPropagation();
                }
                isSelecting = false;
            });
        },
        get_search_result: function(term) {
            var self = this;
            var def = $.Deferred();
            var data = this.project_timesheet_db.load(this.model, []);
            if (!term) {
                var search_data = data;
            } else {
                var search_data = _.compact(_(data).map(function(x) {if (_.include(x[1], term)) {return x;}}));
            }
            var values = _.map(search_data, function(x) {
                x[1] = x[1].split("\n")[0];
                return {
                    label: _.str.escapeHTML(x[1]),
                    value: x[1],
                    name: x[1],
                    id: x[0],
                };
            });
            // quick create
            //var raw_result = _(data.result).map(function(x) {return x[1];});
            var raw_result = search_data.map(function(x) {return x[1];});
            if (term.length > 0 && !_.include(raw_result, term)) {
                values.push({
                    label: _.str.sprintf(_t('Create "<strong>%s</strong>"'),
                        $('<span />').text(term).html()),
                    action: function(e) {
                        self._quick_create(e, term);
                    },
                    classname: 'oe_m2o_dropdown_option'
                });
            }
            return def.resolve(values);
        },
        _quick_create: function(e, term) {
            //TO Implement, create virtual id and add into this.model_input as a data, instead of setting data we can set it in this object also
            var virtual_id = _.uniqueId(this.project_timesheet_db.virtual_id_prefix);
            $target = $(e.target);
            $target.data("id", virtual_id);
            $target.val(term);
        },
    });

    //TO REMOVE
    project_timesheet.FooterWidget = openerp.Widget.extend({
        template: "Footer",
        init: function() {
            this._super.apply(this, arguments);
        },
        start: function() {
            this._super.apply(this, arguments);
        }
    });
}