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

    //TODO: Allow tab key creation, when user enters text and press tab key, it should create many2one record
    project_timesheet.FieldMany2One = openerp.Widget.extend({
        template: "FieldMany2One",
        init: function(parent, options) {
            this.model = options.model;
            this.classname = options.classname;
            this.label = options.label;
            this.id_for_input = options.id_for_input;
            this.project_timesheet_db = project_timesheet.project_timesheet_model.project_timesheet_db;
            this._super.apply(this, arguments);
            this.set({value: false});
        },
        start: function() {
            this._super.apply(this, arguments);
            this.prepare_autocomplete();
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
                if (e.which === $.ui.keyCode.TAB && self._drop_shown) {
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
            //if (!term) {
            //    var search_data = data;
            //} else {
            //    var search_data = _.compact(_(data).map(function(x) {if (x[1].toLowerCase().contains(term.toLowerCase())) {return x;}}));
            //}
            var values = _.map(search_data, function(x) {
                var label = _.str.escapeHTML(x[1].split("\n")[0]);
                if (self.model == "tasks") {
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
            //TO Implement, create virtual id and add into this.model_input as a data, instead of setting data we can set it in this object also
            var virtual_id = _.uniqueId(this.project_timesheet_db.virtual_id_prefix);
            this.$input.data("id", virtual_id);
            this.set({value: virtual_id});
            this.$input.val(term);
        },
        add_id: function(id, name) {
            this.$input.data("id", id);
            this.set({value: id});
            this.$input.val(name);
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
        },
        renderElement: function() {
            this.activities = this.project_timesheet_db.get_activities();
            this.activities = _.filter(this.activities, function(activity) {return activity.command != 2;});
            this.replaceElement(QWeb.render(this.template, {widget: this, activities: this.activities}));
        },
        format_duration: function(field_val) {
            if(!field_val) {
                return;
            }
            var data = field_val.toString().split(".");
            if (data[1]) {
                data[1] = Math.round((field_val%1)*60);
                if (data[1] == 60) {
                    data[1] = 0;
                    data[0] = parseInt(data[0]) + 1;
                }
            }
            return data.join(":");
        },
        get_total: function() {
            var total = 0;
            _.each(this.activities, function(activity) { total += activity.hours;});
            return this.format_duration(total);
        }
    });

}