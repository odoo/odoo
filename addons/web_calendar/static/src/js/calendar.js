/*---------------------------------------------------------
 * OpenERP web_calendar
 *---------------------------------------------------------*/

openerp.web_calendar = function(openerp) {
QWeb.add_template('/web_calendar/static/src/xml/web_calendar.xml');
openerp.web.views.add('calendar', 'openerp.web_calendar.CalendarView');
openerp.web_calendar.CalendarView = openerp.web.View.extend({
// Dhtmlx scheduler ?
    init: function(parent, element_id, dataset, view_id, options) {
        this._super(parent, element_id);
        this.set_default_options(options);
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;
        this.domain = this.dataset.domain || [];
        this.context = this.dataset.context || {};
        this.has_been_loaded = $.Deferred();
        this.creating_event_id = null;
        this.dataset_events = [];
        if (this.options.action_views_ids.form) {
            this.form_dialog = new openerp.web_calendar.CalendarFormDialog(this, {}, this.options.action_views_ids.form, dataset);
            this.form_dialog.start();
        }
        this.COLOR_PALETTE = ['#f57900', '#cc0000', '#d400a8', '#75507b', '#3465a4', '#73d216', '#c17d11', '#edd400',
             '#fcaf3e', '#ef2929', '#ff00c9', '#ad7fa8', '#729fcf', '#8ae234', '#e9b96e', '#fce94f',
             '#ff8e00', '#ff0000', '#b0008c', '#9000ff', '#0078ff', '#00ff00', '#e6ff00', '#ffff00',
             '#905000', '#9b0000', '#840067', '#510090', '#0000c9', '#009b00', '#9abe00', '#ffc900' ];
        this.color_map = {};
    },
    start: function() {
        this.rpc("/web_calendar/calendarview/load", {"model": this.model, "view_id": this.view_id, 'toolbar': true}, this.on_loaded);
    },
    stop: function() {
        scheduler.clearAll();
    },
    on_loaded: function(data) {
        this.calendar_fields = {};
        this.ids = this.dataset.ids;
        this.color_values = [];
        this.info_fields = [];

        this.fields_view = data.fields_view;
        this.name = this.fields_view.name || this.fields_view.arch.attrs.string;
        this.view_id = this.fields_view.view_id;

        this.date_start = this.fields_view.arch.attrs.date_start;
        this.date_delay = this.fields_view.arch.attrs.date_delay;
        this.date_stop = this.fields_view.arch.attrs.date_stop;

        this.colors = this.fields_view.arch.attrs.colors;
        this.day_length = this.fields_view.arch.attrs.day_length || 8;
        this.color_field = this.fields_view.arch.attrs.color;
        this.fields =  this.fields_view.fields;

        //* Calendar Fields *
        this.calendar_fields.date_start = {'name': this.date_start, 'kind': this.fields[this.date_start].type};

        if (this.date_delay) {
            if (this.fields[this.date_delay].type != 'float') {
                throw new Error("Calendar view has a 'date_delay' type != float");
            }
            this.calendar_fields.date_delay = {'name': this.date_delay, 'kind': this.fields[this.date_delay].type};
        }
        if (this.date_stop) {
            this.calendar_fields.date_stop = {'name': this.date_stop, 'kind': this.fields[this.date_stop].type};
        }
        if (!this.date_delay && !this.date_stop) {
            throw new Error("Calendar view has none of the following attributes : 'date_stop', 'date_delay'");
        }

        for (var fld = 0; fld < this.fields_view.arch.children.length; fld++) {
            this.info_fields.push(this.fields_view.arch.children[fld].attrs.name);
        }
        this.$element.html(QWeb.render("CalendarView", {"fields_view": this.fields_view}));

        if (this.options.sidebar && this.options.sidebar_id) {
            this.sidebar = new openerp.web.Sidebar(this, this.options.sidebar_id);
            this.sidebar.start();
            this.sidebar.navigator = new openerp.web_calendar.SidebarNavigator(this.sidebar, this.sidebar.add_section('navigator', "Navigator"), this);
            this.sidebar.responsible = new openerp.web_calendar.SidebarResponsible(this.sidebar, this.sidebar.add_section('responsible', "Responsible"), this);
            this.sidebar.add_toolbar(data.fields_view.toolbar);
            this.set_common_sidebar_sections(this.sidebar);
            this.sidebar.do_unfold();
            this.sidebar.do_fold.add_last(this.refresh_scheduler);
            this.sidebar.do_unfold.add_last(this.refresh_scheduler);
            this.sidebar.do_toggle.add_last(this.refresh_scheduler);
        }

        this.init_scheduler();
        this.has_been_loaded.resolve();
        if (this.dataset.ids.length) {
            this.dataset.read_ids(this.dataset.ids, _.keys(this.fields), this.on_events_loaded);
        }
    },
    init_scheduler: function() {
        var self = this;
        scheduler.clearAll();
        if (this.fields[this.date_start]['type'] == 'time') {
            scheduler.config.xml_date = "%H:%M:%S";
        } else {
            scheduler.config.xml_date = "%Y-%m-%d %H:%i";
        }
        scheduler.config.api_date = "%Y-%m-%d %H:%i";
        scheduler.config.multi_day = true; //Multi day events are not rendered in daily and weekly views
        scheduler.config.start_on_monday = true;
        scheduler.config.scroll_hour = 8;
        scheduler.config.drag_resize = true;
        scheduler.config.drag_create = true;

        // Initialize Sceduler
        this.mode = this.mode || 'month';
        scheduler.init('openerp_scheduler', null, this.mode);

        scheduler.detachAllEvents();
        scheduler.attachEvent('onEventAdded', this.do_create_event);
        scheduler.attachEvent('onEventDeleted', this.do_delete_event);
        scheduler.attachEvent('onEventChanged', this.do_save_event);
        scheduler.attachEvent('onDblClick', this.do_edit_event);
        scheduler.attachEvent('onBeforeLightbox', this.do_edit_event);

        this.mini_calendar = scheduler.renderCalendar({
            container: this.sidebar.navigator.element_id,
            navigation: true,
            date: scheduler._date,
            handler: function(date, calendar) {
                scheduler.setCurrentView(date, 'day');
            }
        });
    },
    refresh_scheduler: function() {
        scheduler.setCurrentView(scheduler._date);
    },
    refresh_minical: function() {
        scheduler.updateCalendar(this.mini_calendar);
    },
    reload_event: function(id) {
        this.dataset.read_ids([id], _.keys(this.fields), this.on_events_loaded);
    },
    get_color: function(key) {
        if (this.color_map[key]) {
            return this.color_map[key];
        }
        var index = _.keys(this.color_map).length % this.COLOR_PALETTE.length;
        var color = this.COLOR_PALETTE[index];
        this.color_map[key] = color;
        return color;
    },
    on_events_loaded: function(events, fn_filter, no_filter_reload) {
        var self = this;

        //To parse Events we have to convert date Format
        var res_events = [],
            sidebar_items = {};
        for (var e = 0; e < events.length; e++) {
            var evt = events[e];
            if (!evt[this.date_start]) {
                this.notification.warn("Start date is not defined for event :", evt['id']);
                break;
            }

            if (this.color_field) {
                var filter = evt[this.color_field];
                if (filter) {
                    var filter_value = (typeof filter === 'object') ? filter[0] : filter;
                    if (typeof(fn_filter) === 'function' && !fn_filter(filter_value)) {
                        continue;
                    }
                    var filter_item = {
                        value: filter_value,
                        label: (typeof filter === 'object') ? filter[1] : filter,
                        color: this.get_color(filter_value)
                    }
                    if (!sidebar_items[filter_value]) {
                        sidebar_items[filter_value] = filter_item;
                    }
                    evt.color = filter_item.color;
                    evt.textColor = '#ffffff';
                }
            }

            if (this.fields[this.date_start]['type'] == 'date') {
                evt[this.date_start] = openerp.web.str_to_date(evt[this.date_start]).set({hour: 9}).toString('yyyy-MM-dd HH:mm:ss');
            }
            if (this.date_stop && evt[this.date_stop] && this.fields[this.date_stop]['type'] == 'date') {
                evt[this.date_stop] = openerp.web.str_to_date(evt[this.date_stop]).set({hour: 17}).toString('yyyy-MM-dd HH:mm:ss');
            }
            res_events.push(this.convert_event(evt));
        }
        scheduler.parse(res_events, 'json');
        this.refresh_scheduler();
        this.refresh_minical();
        if (!no_filter_reload) {
            this.sidebar.responsible.on_events_loaded(sidebar_items);
        }
    },
    convert_event: function(evt) {
        var date_start = openerp.web.str_to_datetime(evt[this.date_start]),
            date_stop = this.date_stop ? openerp.web.str_to_datetime(evt[this.date_stop]) : null,
            date_delay = evt[this.date_delay] || null,
            res_text = '',
            res_description = [];

        if (this.info_fields) {
            var fld = evt[this.info_fields[0]];
            res_text = (typeof fld == 'object') ? fld[fld.length -1] : res_text = fld;

            var sliced_info_fields = this.info_fields.slice(1);
            for (var sl_fld in sliced_info_fields) {
                var slc_fld = evt[sliced_info_fields[sl_fld]];
                if (typeof slc_fld == 'object') {
                    res_description.push(slc_fld[slc_fld.length - 1]);
                } else if (slc_fld) {
                    res_description.push(slc_fld);
                }
            }
        }
        if (!date_stop && date_delay) {
            date_stop = date_start.clone().addHours(date_delay);
        }
        var r = {
            'start_date': date_start.toString('yyyy-MM-dd HH:mm:ss'),
            'end_date': date_stop.toString('yyyy-MM-dd HH:mm:ss'),
            'text': res_text,
            'id': evt.id,
            'title': res_description.join()
        }
        if (evt.color) {
            r.color = evt.color;
        }
        if (evt.textColor) {
            r.textColor = evt.textColor;
        }
        return r;
    },
    do_create_event: function(event_id, event_obj) {
        var self = this,
            data = this.get_event_data(event_obj);
        this.dataset.create(data, function(r) {
            var id = parseInt(r.result, 10);
            self.dataset.ids.push(id);
            scheduler.changeEventId(event_id, id);
            self.refresh_minical();
        }, function(r, event) {
            self.creating_event_id = event_id;
            self.form_dialog.form.on_record_loaded(data);
            self.form_dialog.open();
            event.preventDefault();
        });
    },
    do_save_event: function(event_id, event_obj) {
        var self = this,
            data = this.get_event_data(event_obj);
        this.dataset.write(parseInt(event_id, 10), data, {}, function() {
            self.refresh_minical();
        });
    },
    do_delete_event: function(event_id, event_obj) {
        var self = this;
        // dhtmlx sends this event even when it does not exist in openerp.
        // Eg: use cancel in dhtmlx new event dialog
        if (_.indexOf(this.dataset.ids, parseInt(event_id, 10)) > -1) {
            this.dataset.unlink(parseInt(event_id, 10), function() {
                self.refresh_minical();
            });
        }
    },
    do_edit_event: function(event_id) {
        event_id = parseInt(event_id, 10);
        var index = _.indexOf(this.dataset.ids, event_id);
        if (index > -1) {
            this.dataset.index = index;
            this.form_dialog.form.do_show();
            this.form_dialog.open();
            return false;
        }
        return true;
    },
    get_event_data: function(event_obj) {
        var data = {
            name: event_obj.text
        };
        data[this.date_start] = openerp.web.datetime_to_str(event_obj.start_date);
        if (this.date_stop) {
            data[this.date_stop] = openerp.web.datetime_to_str(event_obj.end_date);
        }
        if (this.date_delay) {
            var diff_seconds = Math.round((event_obj.end_date.getTime() - event_obj.start_date.getTime()) / 1000);
            data[this.date_delay] = diff_seconds / 3600;
        }
        return data;
    },
    do_search: function(domains, contexts, groupbys) {
        var self = this;
        scheduler.clearAll();
        $.when(this.has_been_loaded).then(function() {
            self.rpc('/web/session/eval_domain_and_context', {
                domains: domains,
                contexts: contexts,
                group_by_seq: groupbys
            }, function (results) {
                // TODO: handle non-empty results.group_by with read_group
                self.dataset.context = self.context = results.context;
                self.dataset.domain = self.domain = results.domain;
                self.dataset.read_slice(_.keys(self.fields), {
                        offset:0,
                        limit: self.limit
                    }, function(events) {
                        self.dataset_events = events;
                        self.on_events_loaded(events);
                    }
                );
            });
        });
    },
    do_show: function () {
        var self = this;
        $.when(this.has_been_loaded).then(function() {
            self.$element.show();
            if (self.sidebar) {
                self.sidebar.$element.show();
            }
        });
    },
    do_hide: function () {
        this.$element.hide();
        if (this.sidebar) {
            this.sidebar.$element.hide();
        }
    },
    get_selected_ids: function() {
        // no way to select a record anyway
        return [];
    }
});

openerp.web_calendar.CalendarFormDialog = openerp.web.Dialog.extend({
    init: function(view, options, view_id, dataset) {
        this._super(view, options);
        this.dataset = dataset;
        this.view_id = view_id;
        this.view = view;
    },
    start: function() {
        this._super();
        this.form = new openerp.web.FormView(this, this.element_id, this.dataset, this.view_id, {
            sidebar: false,
            pager: false
        });
        this.form.start();
        this.form.on_created.add_last(this.on_form_dialog_saved);
        this.form.on_saved.add_last(this.on_form_dialog_saved);
    },
    on_form_dialog_saved: function() {
        var id = this.dataset.ids[this.dataset.index];
        if (this.view.creating_event_id) {
            scheduler.changeEventId(this.view.creating_event_id, id);
            this.view.creating_event_id = null;
        }
        this.view.reload_event(id);
        this.close();
    },
    on_close: function() {
        if (this.view.creating_event_id) {
            scheduler.deleteEvent(this.view.creating_event_id);
            this.view.creating_event_id = null;
        }
    }
});

openerp.web_calendar.SidebarResponsible = openerp.web.Widget.extend({
    init: function(parent, element_id, view) {
        this._super(parent, element_id);
        this.view = view;
        this.$element.delegate('input:checkbox', 'change', this.on_filter_click);
    },
    on_events_loaded: function(filters) {
        this.$element.html(QWeb.render('CalendarView.sidebar.responsible', { filters: filters }));
    },
    on_filter_click: function(e) {
        var responsibles = [],
            $e = $(e.target);
        this.$element.find('div.oe_calendar_responsible input:checked').each(function() {
            responsibles.push($(this).val());
        });
        scheduler.clearAll();
        if (responsibles.length) {
            this.view.on_events_loaded(this.view.dataset_events, function(filter_value) {
                return _.indexOf(responsibles, filter_value.toString()) > -1;
            }, true);
        } else {
            this.view.on_events_loaded(this.view.dataset_events, false, true);
        }
    }
});

openerp.web_calendar.SidebarNavigator = openerp.web.Widget.extend({
    init: function(parent, element_id, view) {
        this._super(parent, element_id);
        this.view = view;
    },
    on_events_loaded: function(events) {
    }
});
};

// DEBUG_RPC:rpc.request:('execute', 'addons-dsh-l10n_us', 1, '*', ('ir.filters', 'get_filters', u'res.partner'))
// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
