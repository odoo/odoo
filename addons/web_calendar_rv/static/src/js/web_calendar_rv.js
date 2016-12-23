/**
 * Created by pmccaffrey on 2/13/15.
 */

openerp.web_calendar_rv = function (instance) {
    var _t = instance.web._t,
        _lt = instance.web._lt,
        QWeb = instance.web.qweb,
        web_calendar = instance.web_calendar;

    getOdooFCResources = function (calendar) {

        var favorites = [];
        var currentUserId = calendar.dataset.context.uid;
        results = []
        $.ajaxSetup({async: false});

        new openerp.web.Model("res.users").query(["partner_id"]).filter([["id", "=", currentUserId]]).first()
            .done(
            function (item) {
                itemId = item.partner_id[0];
                results[itemId] = {id: itemId, 'name': item.partner_id[1]};
            })

        new openerp.web.Model("calendar.contacts").query(["partner_id"]).filter([["user_id", "=", currentUserId]]).all().then(function (data) {

            _.each(data, function (item) {
                itemId = item.partner_id[0];
                results[itemId] = {id: itemId, 'name': item.partner_id[1]};
            });
        });

        _.each(results, function (result) {
            favorites.push(result);
        });
        $.ajaxSetup({async: true});
        return favorites;

    };

    web_calendar.CalendarView.prototype.get_fc_init_options = function () {
        //Documentation here : http://arshaw.com/fullcalendar/docs/
        shortTimeformat = 'h:mm a';
        var dateFormat = 'MMM Do, YYYY';
        var self = this;
        return {
            weekNumberTitle: _t("W"),
            allDayText: _t("All day"),
            buttonText: {
                today: _t("Today"),
                month: _t("Month"),
                week: _t("Week"),
                day: _t("Day")
            },
            monthNames: Date.CultureInfo.monthNames,
            monthNamesShort: Date.CultureInfo.abbreviatedMonthNames,
            dayNames: Date.CultureInfo.dayNames,
            dayNamesShort: Date.CultureInfo.abbreviatedDayNames,
            firstDay: Date.CultureInfo.firstDayOfWeek,
            weekNumbers: false,
            axisFormat: shortTimeformat.replace(/:mm/, '(:mm)'),
            timeFormat: {
                // for agendaWeek and agendaDay
                agenda: shortTimeformat, // 5:00 - 6:30
                // for all other views
                '': 'h a'  // 7pm
            },
            titleFormat: {
                month: 'MMMM YYYY',
                week: dateFormat,
                day: dateFormat
            },
            columnFormat: {
                month: 'ddd',
                week: 'ddd ' + dateFormat,
                day: 'dddd ' + dateFormat
            },
            weekMode: 'liquid',
            aspectRatio: 1.8,
            snapMinutes: 15,
            resources: getOdooFCResources(self),
            defaultView: (this.mode == "month") ? "month" :
                (this.mode == "week" ? "agendaWeek" :
                    (this.mode == "day" ? "agendaDay" : "agendaWeek")),
            header: {
                left: 'prev,next today',
                center: 'title',
                right: 'month,agendaWeek,resourceDay'
            },
            selectable: !this.options.read_only_mode && this.create_right,
            selectHelper: true,
            editable: !this.options.read_only_mode,
            droppable: true,

            // callbacks

            eventDrop: function (event, _day_delta, _minute_delta, _all_day, _revertFunc) {
                var data = self.get_event_data(event);
                self.proxy('update_record')(event._id, data); // we don't revert the event, but update it.
            },
            eventResize: function (event, _day_delta, _minute_delta, _revertFunc) {
                var data = self.get_event_data(event);
                self.proxy('update_record')(event._id, data);
            },
            eventRender: function (event, element, view) {
                element.find('.fc-event-title').html(event.title);
            },
            eventAfterRender: function (event, element, view) {
                if ((view.name !== 'month') && (((event.end - event.start) / 60000) <= 30)) {
                    //if duration is too small, we see the html code of img
                    var current_title = $(element.find('.fc-event-time')).text();
                    var new_title = current_title.substr(0, current_title.indexOf("<img") > 0 ? current_title.indexOf("<img") : current_title.length);
                    element.find('.fc-event-time').html(new_title);
                }
            },
            eventClick: function (event) {
                self.open_event(event._id, event.title);
            },
            select: function (start_date, end_date, all_day, _js_event, _view) {
                var data_template = self.get_event_data({
                    start: start_date,
                    end: end_date,
                    allDay: all_day
                });
                self.open_quick_create(data_template);

            },
            unselectAuto: false
        };
    };

    /**
     * Transform OpenERP event object to fullcalendar event object
     */
        web_calendar.CalendarView.prototype.event_data_transform = function (evt) {
            var self = this;

            var date_delay = evt[this.date_delay] || 1.0,
                all_day = this.all_day ? evt[this.all_day] : false,
                res_computed_text = '',
                the_title = '',
                attendees = [];

            if (!all_day) {
                date_start = instance.web.auto_str_to_date(evt[this.date_start]);
                date_stop = this.date_stop ? instance.web.auto_str_to_date(evt[this.date_stop]) : null;
            }
            else {
                date_start = instance.web.auto_str_to_date(evt[this.date_start].split(' ')[0], 'start');
                date_stop = this.date_stop ? instance.web.auto_str_to_date(evt[this.date_stop].split(' ')[0], 'start') : null; //.addSeconds(-1) : null;
            }

            if (this.info_fields) {
                var temp_ret = {};
                res_computed_text = this.how_display_event;

                _.each(this.info_fields, function (fieldname) {
                    var value = evt[fieldname];
                    if (_.contains(["many2one", "one2one"], self.fields[fieldname].type)) {
                        if (value === false) {
                            temp_ret[fieldname] = null;
                        }
                        else if (value instanceof Array) {
                            temp_ret[fieldname] = value[1]; // no name_get to make
                        }
                        else {
                            throw new Error("Incomplete data received from dataset for record " + evt.id);
                        }
                    }
                    else if (_.contains(["one2many", "many2many"], self.fields[fieldname].type)) {
                        if (value === false) {
                            temp_ret[fieldname] = null;
                        }
                        else if (value instanceof Array) {
                            temp_ret[fieldname] = value; // if x2many, keep all id !
                        }
                        else {
                            throw new Error("Incomplete data received from dataset for record " + evt.id);
                        }
                    }
                    else {
                        temp_ret[fieldname] = value;
                    }
                    res_computed_text = res_computed_text.replace("[" + fieldname + "]", temp_ret[fieldname]);
                });


                if (res_computed_text.length) {
                    the_title = res_computed_text;
                }
                else {
                    var res_text = [];
                    _.each(temp_ret, function (val, key) {
                        res_text.push(val);
                    });
                    the_title = res_text.join(', ');
                }
                the_title = _.escape(the_title);


                the_title_avatar = '';

                if (!_.isUndefined(this.attendee_people)) {
                    var MAX_ATTENDEES = 3;
                    var attendee_showed = 0;
                    var attendee_other = '';

                    _.each(temp_ret[this.attendee_people],
                        function (the_attendee_people) {
                            attendees.push(the_attendee_people);
                            attendee_showed += 1;
                            if (attendee_showed <= MAX_ATTENDEES) {
                                if (self.avatar_model !== null) {
                                    the_title_avatar += '<img title="' + self.all_attendees[the_attendee_people] + '" class="attendee_head"  \
                                                            src="/web/binary/image?model=' + self.avatar_model + '&field=image_small&id=' + the_attendee_people + '"></img>';
                                }
                                else {
                                    if (!self.colorIsAttendee || the_attendee_people != temp_ret[self.color_field]) {
                                        tempColor = (self.all_filters[the_attendee_people] !== undefined)
                                            ? self.all_filters[the_attendee_people].color
                                            : (self.all_filters[-1] ? self.all_filters[-1].color : 1);
                                        the_title_avatar += '<i class="fa fa-user attendee_head color_' + tempColor + '" title="' + self.all_attendees[the_attendee_people] + '" ></i>';
                                    }//else don't add myself
                                }
                            }
                            else {
                                attendee_other += self.all_attendees[the_attendee_people] + ", ";
                            }
                        }
                    );
                    if (attendee_other.length > 2) {
                        the_title_avatar += '<span class="attendee_head" title="' + attendee_other.slice(0, -2) + '">+</span>';
                    }
                    the_title = the_title_avatar + the_title;
                }
            }

            if (!date_stop && date_delay) {
                date_stop = date_start.clone().addHours(date_delay);
            }
            var r = {
                'start': date_start.toString('yyyy-MM-dd HH:mm:ss'),
                'end': date_stop.toString('yyyy-MM-dd HH:mm:ss'),
                'title': the_title,
                'allDay': (this.fields[this.date_start].type == 'date' || (this.all_day && evt[this.all_day]) || false),
                'id': evt.id,
                'attendees': attendees
            };
            if (!self.useContacts || self.all_filters[evt[this.color_field]] !== undefined) {
                if (this.color_field && evt[this.color_field]) {
                    var color_key = evt[this.color_field];
                    if (typeof color_key === "object") {
                        color_key = color_key[0];
                    }
                    r.className = 'cal_opacity calendar_color_' + this.get_color(color_key);
                }
            }
            else { // if form all, get color -1
                r.className = 'cal_opacity calendar_color_' + self.all_filters[-1].color;
            }
            return r;
        };

    web_calendar.CalendarView.prototype.do_search = function (domain, context, _group_by) {
        var self = this;
        if (!self.all_filters) {
            self.all_filters = {}
        }

        if (!_.isUndefined(this.event_source)) {
            this.$calendar.fullCalendar('removeEventSource', this.event_source);
        }
        this.event_source = {
            events: function (start, end, callback) {
                var current_event_source = self.event_source;
                self.dataset.read_slice(_.keys(self.fields), {
                    offset: 0,
                    domain: self.get_range_domain(domain, start, end),
                    context: context
                }).done(function (events) {
                    if (self.dataset.index === null) {
                        if (events.length) {
                            self.dataset.index = 0;
                        }
                    } else if (self.dataset.index >= events.length) {
                        self.dataset.index = events.length ? 0 : null;
                    }

                    if (self.event_source !== current_event_source) {
                        console.log("Consecutive ``do_search`` called. Cancelling.");
                        return;
                    }

                    if (!self.useContacts) {  // If we use all peoples displayed in the current month as filter in sidebars
                        var filter_value;
                        var filter_item;

                        self.now_filter_ids = [];

                        _.each(events, function (e) {
                            filter_value = e[self.color_field][0];
                            if (!self.all_filters[e[self.color_field][0]]) {
                                filter_item = {
                                    value: filter_value,
                                    label: e[self.color_field][1],
                                    color: self.get_color(filter_value),
                                    avatar_model: (_.str.toBoolElse(self.avatar_filter, true) ? self.avatar_filter : false ),
                                    is_checked: true
                                };
                                self.all_filters[e[self.color_field][0]] = filter_item;
                            }
                            if (!_.contains(self.now_filter_ids, filter_value)) {
                                self.now_filter_ids.push(filter_value);
                            }
                        });

                        if (self.sidebar) {
                            self.sidebar.filter.events_loaded();
                            self.sidebar.filter.set_filters();

                            events = $.map(events, function (e) {
                                if (_.contains(self.now_filter_ids, e[self.color_field][0]) && self.all_filters[e[self.color_field][0]].is_checked) {
                                    return e;
                                }
                                return null;
                            });
                        }

                    }
                    else { //WE USE CONTACT
                        if (self.attendee_people !== undefined) {
                            //if we don't filter on 'Everybody's Calendar
                            if (!self.all_filters[-1] || !self.all_filters[-1].is_checked) {
                                var checked_filter = $.map(self.all_filters, function (o) {
                                    if (o.is_checked) {
                                        return o.value;
                                    }
                                });
                                // If we filter on contacts... we keep only events from coworkers
                                events = $.map(events, function (e) {
                                    if (_.intersection(checked_filter, e[self.attendee_people]).length) {
                                        return e;
                                    }
                                    return null;
                                });
                            }
                        }


                    }

                    var all_attendees = $.map(events, function (e) {
                        return e[self.attendee_people];
                    });
                    all_attendees = _.chain(all_attendees).flatten().uniq().value();

                    self.all_attendees = {};
                    if (self.avatar_title !== null) {
                        new instance.web.Model(self.avatar_title).query(["name"]).filter([["id", "in", all_attendees]]).all().then(function (result) {
                            _.each(result, function (item) {
                                self.all_attendees[item.id] = item.name;
                            });
                        }).done(function () {
                            return self.perform_necessary_name_gets(events).then(callback);
                        });
                    }
                    else {
                        _.each(all_attendees, function (item) {
                            self.all_attendees[item] = '';
                        });
                        return self.perform_necessary_name_gets(events).then(callback);
                    }
                });
            },
            eventDataTransform: function (event) {
                return self.event_data_transform(event);
            }
        };
        this.$calendar.fullCalendar('addEventSource', this.event_source);
    };

    web_calendar.CalendarView.prototype.get_range_domain = function (domain, start, end) {
        var format = function (momentDateObj) {
            return momentDateObj.format("YYYY-MM-DD");
        };

        extend_domain = [[this.date_start, '>=', format(start.clone())],
            [this.date_start, '<=', format(end.clone())]];

        if (this.date_stop) {
            //add at start
            extend_domain.splice(0, 0, '|', '|', '&');
            //add at end
            extend_domain.push(
                '&',
                [this.date_start, '<=', format(start.clone())],
                [this.date_stop, '>=', format(start.clone())],
                '&',
                [this.date_start, '<=', format(end.clone())],
                [this.date_stop, '>=', format(start.clone())]
            );
            //final -> (A & B) | (C & D) | (E & F) ->  | | & A B & C D & E F
        }
        return new instance.web.CompoundDomain(domain, extend_domain);
    };

    web_calendar.SidebarFilter = instance.web.Widget.extend({
        events: {
            'change input:checkbox': 'filter_click'
        },
        init: function (parent, view) {
            this._super(parent);
            this.view = view;
        },
        set_filters: function () {
            var self = this;
            _.forEach(self.view.all_filters, function (o) {
                if (_.contains(self.view.now_filter_ids, o.value)) {
                    self.$('div.oe_calendar_responsible input[value=' + o.value + ']').prop('checked', o.is_checked);
                }
            });
        },
        events_loaded: function (filters) {
            var self = this;
            if (filters == null) {
                filters = [];
                _.forEach(self.view.all_filters, function (o) {
                    if (_.contains(self.view.now_filter_ids, o.value)) {
                        filters.push(o);
                    }
                });
            }
            this.$el.html(QWeb.render('CalendarView.sidebar.responsible', {filters: filters}));
        },
        filter_click: function (e) {
            var self = this;
            if (self.view.all_filters[0] && e.target.value == self.view.all_filters[0].value) {
                self.view.all_filters[0].is_checked = e.target.checked;
            } else {
                self.view.all_filters[parseInt(e.target.value)].is_checked = e.target.checked;
            }
            self.view.$calendar.fullCalendar('refetchEvents');
        },
        set_distroy_filters: function () {
            var self = this;
            // When mouse-enter the favorite list it will show the 'X' for removing partner from the favorite list.
            if (self.view.useContacts) {
                self.$('.oe_calendar_all_responsibles').on('mouseenter mouseleave', function (e) {
                    self.$('.oe_remove_follower').toggleClass('hidden', e.type == 'mouseleave');
                });
            }
        },
        addInputBox: function () {
            var self = this;
            if (this.dfm)
                return;
            this.dfm = new instance.web.form.DefaultFieldManager(self);
            this.dfm.extend_field_desc({
                partner_id: {
                    relation: "res.partner"
                }
            });
            this.ir_model_m2o = new instance.web.form.FieldMany2One(self.dfm, {
                attrs: {
                    class: 'oe_add_input_box',
                    name: "partner_id",
                    type: "many2one",
                    options: '{"no_open": True}',
                    placeholder: _t("Add Favorite Calendar"),
                }
            });
            this.ir_model_m2o.insertAfter($('div.oe_calendar_filter'));
            this.ir_model_m2o.on('change:value', self, function () {
                self.add_filter();
            });
        },
        add_filter: function () {
            var self = this;
            new instance.web.Model("res.users").query(["partner_id"]).filter([["id", "=", this.view.dataset.context.uid]]).first().done(function (result) {
                $.map(self.ir_model_m2o.display_value, function (element, index) {
                    if (result.partner_id[0] != index) {
                        self.ds_message = new instance.web.DataSetSearch(self, 'calendar.contacts');
                        self.ds_message.call("create", [{'partner_id': index}]);
                    }
                });
            });
            new reload_favorite_list(this);
        },
        destroy_filter: function (e) {
            var self = this;
            this.$(".oe_remove_follower").on('click', function (e) {
                self.ds_message = new instance.web.DataSetSearch(self, 'calendar.contacts');
                if (!confirm(_t("Do you really want to delete this filter from favorite?"))) {
                    return false;
                }
                var id = $(e.currentTarget)[0].dataset.id;
                self.ds_message.call('search', [[['partner_id', '=', parseInt(id)]]]).then(function (record) {
                    return self.ds_message.unlink(record);
                }).done(function () {
                    new reload_favorite_list(self);
                });
            });
        },
    });
}