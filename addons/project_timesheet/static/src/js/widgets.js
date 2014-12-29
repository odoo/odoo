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
        },
        prepare_autocomplete: function() {
            var self = this;
            this.$input = this.$el.find("textarea");
            this.$input.textext({
                plugins: 'arrow autocomplete',
                autocomplete: {
                    render: function(suggestion) {
                        return $('<span class="text-label"/>').
                                 data('index', suggestion['index']).html(suggestion['label']);
                    }
                },
                ext: {
                    autocomplete: {
                        selectFromDropdown: function() {
                            this.trigger('hideDropdown');
                            self.$input.trigger('change');
                            var index = Number(this.selectedSuggestionElement().children().children().data('index'));
                            var data = self.search_result[index];
                            if (data.id) {
                                self.add_id(data.id, data.name);
                            } else {
                                self.ignore_blur = true;
                                data.action();
                            }
                            this.trigger('setSuggestions', {result : []});
                        },
                    },
                    itemManager: {
                        itemToString: function(item) {
                            return item.name;
                        },
                    },
                    core: {
                        onSetInputData: function(e, data) {
                            if (data === '') {
                                this._plugins.autocomplete._suggestions = null;
                            }
                            this.input().val(data);
                        },
                    },
                },
            }).bind('hideDropdown', function() {
                self._drop_shown = false;
            }).bind('showDropdown', function() {
                self._drop_shown = true;
            }).bind('getSuggestions', function(e, data) {
                var _this = this;
                query = (data ? data.query : '') || '';
                self.get_search_result(query).done(function(result){
                    self.search_result = result;
                    $(_this).trigger(
                        'setSuggestions',
                        { result : _.map(result, function(el, i) {
                            return _.extend(el, {index:i});
                        }) });
                });
            });
            self.$input
            /*
            .focusin(function () {
                self.trigger('focused');
                self.ignore_blur = false;
            })
            .focusout(function() {
                self.$input.trigger("setInputData", "");
                if (!self.ignore_blur) {
                    self.trigger('blurred');
                }
            })
            */
            .keydown(function(e) {
                if (e.which === 9 && self._drop_shown) {
                    self.$input.textext()[0].autocomplete().selectFromDropdown();
                }
            });
        },
        get_search_result: function(term) {
            var self = this;
            var def = $.Deferred();
            var data;
            if(this.model) {
                data = this.model.name_search(term);
            }
            var search_data = data;
            var values = _.map(search_data, function(x) {
                var label = _.str.escapeHTML(x[1].split("\n")[0]);
                if (self.search_model == "task") {
                    var task_name = x[1].split("\n")[0];
                    var priority = parseInt(x[1].split("\n")[1]) || 0; //TODO: For now, we will move this logic for task m2o special logic uisng include
                    if(priority) {
                        var span = "<span class='glyphicon glyphicon-star pull-right'></span>";
                        var $spans = Array(priority+1).join(span);
                        label = "<span>"+_.str.escapeHTML(task_name)+"</span>"+$spans;
                    }
                }
                x[1] = x[1].split("\n")[0];
                return {
                    //label: _.str.escapeHTML(x[1]),
                    label: label,
                    value: x[1],
                    name: x[1],
                    id: x[0],
                };
            });
            // quick create
            var raw_result = search_data ? search_data.map(function(x) {return x[1];}) : [];
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
            var virtual_id = this.project_timesheet_db.get_unique_id();
            this.$input.data("id", virtual_id); //TO Remove: we use this.get('value') to check
            this.set({display_string: term, value: virtual_id});
            this.$input.val(term);
        },
        add_id: function(id, name) {
            this.$input.data("id", id); //TO Remove: we use this.get('value') to check
            this.$input.val(name);
            this.set({display_string: name, value: id});
        },
        display_string: function(field_val) {
            if (this.get("effective_readonly")) {
                this.$el.find("#"+this.id_for_input).text(field_val[1]);
                this.$el.find("#"+this.id_for_input).data("id", field_val[0]); //TO Remove: we use this.get('value') to check
            } else {
                this.$el.find("#"+this.id_for_input).val(field_val[1]);
                this.$el.find("#"+this.id_for_input).data("id", field_val[0]); //TO Remove: we use this.get('value') to check
            }
        },
        input_changed: function() {
            if (this.get('display_string') !== this.$input.val()) {
                if (this.$input.val() === "") {
                    this.set({display_string: this.$input.val(), value: false});
                }
            }
        },
    });

    project_timesheet.ActivityListView = openerp.Widget.extend({
        template: "ActivityList",
        init: function() {
            this._super.apply(this, arguments);
            this.project_timesheet_model = project_timesheet.project_timesheet_model;
            this.project_timesheet_db = this.project_timesheet_model.project_timesheet_db;
            this.activities = [];
        },
        start: function() {
            this._super.apply(this, arguments);
            this.$(".pt_error").popover({
                'placement': 'auto top',
                'container': this.$el,
                'html': true,
                'trigger': 'hover',
                'animation': false,
                'toggle': 'popover',
                'delay': {'show': 300, 'hide': 100}
            });
        },
        renderElement: function() {
            this.activities = this.project_timesheet_db.get_activities();
            this.activities = _.filter(this.activities, function(activity) {return activity.command != 2;});
            this.replaceElement(QWeb.render(this.template, {widget: this, activities: this.activities}));
        },
        format_duration: function(field_val) {
            return project_timesheet.format_duration(field_val);
        },
        get_total: function() {
            var total = 0;
            _.each(this.activities, function(activity) { total += activity.unit_amount;});
            return this.format_duration(total);
        }
    });

}