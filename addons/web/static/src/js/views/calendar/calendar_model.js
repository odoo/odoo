odoo.define('web.CalendarModel', function (require) {
"use strict";

var AbstractModel = require('web.AbstractModel');
var field_utils = require('web.field_utils');
var session = require('web.session');
var time = require('web.time');
var core = require('web.core');
var data = require('web.data');

var _t = core._t;

var scales = [
    'day',
    'week',
    'month'
];

return AbstractModel.extend({
    init: function () {
        this._super.apply(this, arguments);
        this.end_date = null;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Transform fullcalendar event object to OpenERP Data object
     */
    calendarEventToRecord: function (event) {
        // Normalize event_end without changing fullcalendars event.
        var data = {'name': event.title};
        var start = moment(new Date(event.start));
        var end = moment(new Date(event.end));

        //Bug when we move an all_day event from week or day view, we don't have
        // a date.end or duration...
        if (end === null || end.diff(start) < 0) {
            end = start.clone().add(1, 'h');
        }

        if (event.allDay) {
            if (this.scale === 'month') {
                if (event.r_start) {
                    start.hours(event.r_start.hours())
                         .minutes(event.r_start.minutes())
                         .seconds(event.r_start.seconds())
                         .utc();
                    end.add(-1, 'days')
                       .hours(event.r_end.hours())
                       .minutes(event.r_end.minutes())
                       .seconds(event.r_end.seconds())
                       .utc();
                } else {
                    start.utc();
                    end.utc();
                }
            } else if (this.mapping.all_day) {
                start.utc().startOf('day');
                end.utc().startOf('day');
            } else {
                start.utc().hours(7);
                end.utc().hours(19);
            }
        } else {
            var offset = start.utcOffset();
            start.utc().add(-offset, 'minutes');
            end.utc().add(-offset, 'minutes');
        }

        if (this.mapping.all_day) {
            if (event.record) {
                data[this.mapping.all_day] =
                    (this.scale !== 'month' && event.allDay) ||
                    event.record[this.mapping.all_day] &&
                    end.diff(start) < 10 ||
                    false;
            } else {
                data[this.mapping.all_day] = event.allDay;
            }
        }

        data[this.mapping.date_start] = time.datetime_to_str(start.toDate());
        if (this.mapping.date_delay) {
            data[this.mapping.date_delay] = (end.diff(start) <= 0 ? end.endOf('day').diff(start) : end.diff(start)) / 1000 / 3600;
        }

        if (this.mapping.date_stop) {
            data[this.mapping.date_stop] = time.datetime_to_str(end.toDate());
        }

        return data;
    },
    /**
     * @param {Object} filter
     * @returns {boolean}
     */
    changeFilter: function (filter) {
        var Filter = this.data.filters[filter.fieldName];
        if (filter.value === 'all') {
            Filter.all = filter.active;
        }
        var f = _.find(Filter.filters, function (f) {
            return f.value === filter.value;
        });
        if (f) {
            if (f.active !== filter.active) {
                f.active = filter.active;
            } else {
                return false;
            }
        } else if (filter.active) {
            Filter.filters.push({
                value: filter.value,
                active: true,
            });
        }
        return true;
    },
    /**
     * @todo I think this is dead code
     *
     * @param {any} ids
     * @param {any} model
     * @returns
     */
    deleteRecords: function (ids, model) {
        return this.performModelRPC(model, 'unlink', [ids], {
            context: session.user_context, // todo: combine with view context
        });
    },
    /**
     * @override
     * @returns {Object}
     */
    get: function () {
        return _.extend({}, this.data, {
            fields: this.fields
        });
    },
    /**
     * @override
     * @param {any} params
     * @returns {Deferred}
     */
    load: function (params) {
        var self = this;
        this.modelName = params.modelName;
        this.fields = params.fields;
        this.fieldNames = params.fieldNames;
        this.mapping = params.mapping;
        this.mode = params.mode;       // one of month, week or day
        this.scales = params.scales;   // one of month, week or day

        // Check whether the date field is editable (i.e. if the events can be
        // dragged and dropped)
        this.editable = params.editable;

        // display more button when there are too much event on one day
        this.eventLimit = params.eventLimit;

        // fields to display color, e.g.: user_id.partner_id
        this.field_color = params.field_color;
        if (!this.preload_def) {
            var def;
            if (this.field_color) {
                var fields = this.field_color.split('.');
                if (fields.length > 1) {
                    def = new $.Deferred();
                    if (!this.model_color) {
                        var dataset = new data.DataSetSearch(this, this.fields[fields[0]].relation, params.context, []);
                        this.loadFieldView(dataset, false, 'form').then(function (fieldView) {
                            self.model_color = fieldView.fields[fields[1]].relation;
                            def.resolve();
                        });
                    } else {
                        def.resolve();
                    }
                }
            }

            this.preload_def = $.Deferred();
            $.when(
                def,
                this.performModelRPC(this.modelName, 'check_access_rights', ["write", false]),
                this.performModelRPC(this.modelName, 'check_access_rights', ["create", false]))
            .then(function (write, create) {
                self.write_right = write;
                self.create_right = create;
                self.preload_def.resolve();
            });
        }

        this.data = {
            domain: params.domain,
            context: params.context,
            // get in arch the filter to display in the sidebar and the field to read
            filters: params.filters,
        };

        // Use scale_zoom attribute in xml file to specify zoom timeline (day,week,month)
        // by default month.
        this.setDate(params.initialDate, true);
        this.setScale(params.mode);

        _.each(this.data.filters, function (filter) {
            if (filter.avatar_field && !filter.avatar_model) {
                filter.avatar_model = self.modelName;
            }
        });

        return this.preload_def.then(this._loadCalendar.bind(this));
    },
    next: function () {
        this.setDate(moment(this.data.target_date).add(1, this.data.scale));
    },
    prev: function () {
        this.setDate(moment(this.data.target_date).add(-1, this.data.scale));
    },
    /**
     * @todo: this should not work. it ignores the domain/context
     *
     * @override
     * @param {any} _handle ignored
     * @param {any} _params ignored ? really ?
     * @returns {Deferred}
     */
    reload: function (_handle, params) {
        return this._loadCalendar();
    },
    /**
     * @param {any} start
     * @param {any} highlight
     */
    setDate: function (start, highlight) {
        this.data.start_date = this.data.end_date = this.data.target_date = this.data.highlight_date = new Date(start);
        switch (this.data.scale) {
            case 'month':
                this.data.start_date = moment(this.data.start_date)
                                            .startOf('month')
                                            .startOf('week')
                                            .toDate();
                this.data.end_date = moment(this.data.start_date)
                                            .add(5, 'week')
                                            .endOf('week')
                                            .toDate();
                break;
            case 'week':
                this.data.start_date = moment(this.data.start_date)
                                            .startOf('week')
                                            .toDate();
                this.data.end_date = moment(this.data.end_date)
                                            .endOf('week')
                                            .toDate();
                break;
            default:
                this.data.start_date = moment(this.data.start_date)
                                            .startOf('day')
                                            .toDate();
                this.data.end_date = moment(this.data.end_date)
                                            .endOf('day')
                                            .toDate();
        }
        if (highlight) {
            this.data.highlight_date = this.data.target_date;
        }
    },
    setScale: function (scale) {
        if (!_.contains(scales, scale)) {
            scale = "week";
        }
        this.data.scale = scale;
        this.setDate(this.data.target_date);
    },
    today: function () {
        this.setDate(new Date());
    },
    toggleFullWidth: function () {
        var fullWidth = this.call('local_storage', 'getItem', 'calendar_fullWidth') !== 'true';
        this.call('local_storage', 'setItem', 'calendar_fullWidth', fullWidth);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _getFilterDomain: function () {
        var domain = [];
        _.each(this.data.filters, function (filter) {
            if (filter.all) return;
            var nb = {};
            var not = {};
            var contains = {};
            _.each(filter.filters, function (f) {
                if (!contains[filter.fieldName]) {
                    contains[filter.fieldName] = [];
                    not[filter.fieldName] = [];
                    nb[filter.fieldName] = 0;
                }
                if (f.value === 'all' && f.active) {
                    contains[filter.fieldName].all = true;
                } else {
                    nb[filter.fieldName]++;
                }

                if (f.active && contains[filter.fieldName].indexOf(f.value) === -1) {
                    contains[filter.fieldName].push(f.value);
                }
                if (!f.active && not[filter.fieldName].indexOf(f.value) === -1) {
                    not[filter.fieldName].push(f.value);
                }
            });

            for (var field in contains) {
                if (contains[field].all || contains[field].length === nb[field]) {
                    continue;
                }
                if (contains[field].length) {
                    domain.push([field, 'in', contains[field]]);
                } else if (not[field].length && not[field].length !== nb[field]) {
                    domain.push([field, 'not in', not[field]]);
                }
            }
        });
        return domain;
    },
    /**
     * @returns {Object}
     */
    _getFullCalendarOptions: function () {
        return {
            defaultView: (this.mode === "month")? "month" : ((this.mode === "week")? "agendaWeek" : ((this.mode === "day")? "agendaDay" : "agendaWeek")),
            header: false,
            selectable: this.editable && this.create_right,
            selectHelper: true,
            editable: this.editable,
            droppable: true,
            navLinks: false,
            eventLimit: this.eventLimit, // allow "more" link when too many events
            snapMinutes: 15,
            eventResizableFromStart: true,
            weekNumberCalculation: function (date) {
                return moment(date).week();
            },
            weekNumberTitle: _t("W"),
            allDayText: _t("All day"),
            views: {
                week: {
                    columnFormat: 'ddd ' + time.strftime_to_moment_format(_t.database.parameters.date_format),
                }
            },
            monthNames: moment.months(),
            monthNamesShort: moment.monthsShort(),
            dayNames: moment.weekdays(),
            dayNamesShort: moment.weekdaysShort(),
        };
    },
    _getRangeDomain: function () {
        // Build OpenERP Domain to filter object by this.mapping.date_start field
        // between given start, end dates.
        var format = time.datetime_to_str;
        var domain = [[this.mapping.date_start, '<=', format(this.data.end_date)]];
        if (this.mapping.date_stop) {
            domain.push([this.mapping.date_stop, '>=', format(this.data.start_date)]);
        } else if (!this.mapping.date_delay) {
            domain.push([this.mapping.date_start, '>=', format(this.data.start_date)]);
        }
        return domain;
    },
    /**
     * @returns {Deferred}
     */
    _loadCalendar: function () {
        var self = this;
        this.data.fullWidth = this.call('local_storage', 'getItem', 'calendar_fullWidth') === 'true';
        this.data.fc_options = this._getFullCalendarOptions();

        var defs = _.map(this.data.filters, this._loadFilter.bind(this));

        return $.when.apply($, defs).then(function () {
            return self.performRPC('/web/dataset/search_read', {
                model: self.modelName,
                context: self.data.context,
                domain: self.data.domain.concat(self._getRangeDomain()).concat(self._getFilterDomain()),
                fields: self.fieldNames,
            }).then(function (events) {
                self.data.data = _.map(events.records, self._recordToCalendarEvent.bind(self));
                return $.when(
                    self._loadColors(self.data, self.data.data),
                    self._loadRecordsToFilters(self.data, self.data.data)
                );
            });
        });
    },
    /**
     * @param {any} element
     * @param {any} events
     * @returns {Deferred}
     */
    _loadColors: function (element, events) {
        if (this.field_color) {
            var fields = this.field_color.split('.');
            var first = fields[0];
            var self = this;

            if (fields.length === 1) {
                _.each(events, function (event) {
                    var value = event.record[first];
                    event.color_index = _.isArray(value) ? value[0] : value;
                });
                this.model_color = this.fields[first].relation || element.model;
            } else {
                var model = this.fields[first].relation;
                var ids = [];
                _.each(events, function (event) {
                    ids.push(event.record[first][0]);
                });
                ids = _.uniq(ids);

                return self.performModelRPC(model, 'read', [ids, [fields[1]]]).then(function (res) {
                    res = _.object(_.pluck(res, ['id']), _.pluck(res, [fields[1]]));
                    _.each(events, function (event) {
                        var value = res[event.record[first][0]];
                        event.color_index = _.isArray(value) ? value[0] : value;
                    });
                });
            }
        }
        return $.Deferred().resolve();
    },
    /**
     * @param {any} filter
     * @returns {Deferred}
     */
    _loadFilter: function (filter) {
        if (!filter.write_model) {
            return;
        }

        var field = this.fields[filter.fieldName];
        return this.performRPC('/web/dataset/search_read', {
            model: filter.write_model,
            domain: [["user_id", "=", session.uid]],
            fields: [filter.write_field]
        }).then(function (res) {
            var records = _.map(res.records, function (record) {
                var _value = record[filter.write_field];
                var value = _.isArray(_value) ? _value[0] : _value;
                var f = _.find(filter.filters, function (f) {return f.value === value;});
                var formater = field_utils.format[_.contains(['many2many', 'one2many'], field.type) ? 'many2one' : field.type];
                return {
                    'id': record.id,
                    'value': value,
                    'label': formater(_value, field),
                    'active': !f || f.active,
                };
            });
            records.sort(function (f1,f2) {
                return _.string.naturalCmp(f2.label, f1.label);
            });

            // add my profile
            if (field.relation === 'res.partner' || field.relation === 'res.users') {
                var value = field.relation === 'res.partner' ? session.partner_id : session.uid;
                var me = _.find(records, function (record) {
                    return record.value === value;
                });
                if (me) {
                    records.splice(records.indexOf(me), 1);
                } else {
                    var f = _.find(filter.filters, function (f) {return f.value === value;});
                    me = {
                        'value': value,
                        'label': session.name + _t(" [Me]"),
                        'active': !f || f.active,
                    };
                }
                records.unshift(me);
            }
            // add all selection
            records.push({
                'value': 'all',
                'label': field.relation === 'res.partner' || field.relation === 'res.users' ? _t("Everybody's calendars") : _t("Everything"),
                'active': filter.all,
            });

            filter.filters = records;
        });
    },
    /**
     * @param {any} element
     * @param {any} events
     * @returns {Deferred}
     */
    _loadRecordsToFilters: function (element, events) {
        var self = this;
        var new_filters = {};
        var to_read = {};
        _.each(this.data.filters, function (filter, fieldName) {
            var field = self.fields[fieldName];

            new_filters[fieldName] = filter;
            if (filter.write_model) {
                if (field.relation === self.model_color) {
                    _.each(filter.filters, function (f) {
                        f.color_index = f.value;
                    });
                }
                return;
            }

            _.each(filter.filters, function (filter) {
                filter.display = !filter.active;
            });

            var fs = [];
            _.each(events, function (event) {
                var data =  event.record[fieldName];
                if (!_.contains(['many2many', 'one2many'], field.type)) {
                    data = [data];
                } else {
                    to_read[field.relation] = (to_read[field.relation] || []).concat(data);
                }
                _.each(data, function (_value) {
                    var value = _.isArray(_value) ? _value[0] : _value;
                    fs.push({
                        'color': self.model_color === (field.relation || element.model) ? value : false,
                        'value': value,
                        'label': field_utils.format[field.type](_value, field),
                        'avatar_model': field.relation || element.model,
                    });
                });
            });
            _.each(fs, function (f) {
                var f1 = _.findWhere(filter.filters, f);
                if (f1) {
                    f1.display = true;
                } else {
                    f.display = f.active = true;
                    filter.filters.push(f);
                }
            });
        });

        var defs = [];
        _.each(to_read, function (ids, model) {
            defs.push(self.performModelRPC(model, 'name_get', [_.uniq(ids)]).then(function (res) {
                to_read[model] = _.object(res);
            }));
        });
        return $.when.apply($, defs).then(function () {
            _.each(self.data.filters, function (filter) {
                if (filter.write_model) {
                    return;
                }
                if (filter.filters.length && (filter.filters[0].avatar_model in to_read)) {
                    _.each(filter.filters, function (f) {
                        f.label = to_read[f.avatar_model][f.value];
                    });   
                }
            });
        });
    },
    /**
     * Transform OpenERP event object to fullcalendar event object
     */
    _recordToCalendarEvent: function (evt) {
        var date_start;
        var date_stop;
        var date_delay = evt[this.mapping.date_delay] || 1.0,
            all_day = this.mapping.all_day ? evt[this.mapping.all_day] : false,
            the_title = '',
            attendees = [];

        if (!all_day) {
            date_start = time.auto_str_to_date(evt[this.mapping.date_start]);
            date_stop = this.mapping.date_stop ? time.auto_str_to_date(evt[this.mapping.date_stop]) : null;
        } else {
            date_start = time.auto_str_to_date(evt[this.mapping.date_start].split(' ')[0],'start');
            date_stop = this.mapping.date_stop ? time.auto_str_to_date(evt[this.mapping.date_stop].split(' ')[0],'start') : null;
        }

        if (!date_stop && date_delay) {
            var m_start = moment(date_start).add(date_delay,'hours');
            date_stop = m_start.toDate();
        }

        date_start = moment(date_start);
        date_stop = moment(date_stop);

        var r = {
            'record': evt,
            'start': date_start.format('YYYY-MM-DD HH:mm:ss'),
            'end': date_stop.format('YYYY-MM-DD HH:mm:ss'),
            'r_start':date_start.clone(),
            'r_end':date_stop.clone(),
            'title': the_title,
            'allDay': this.mapping.all_day && evt[this.mapping.all_day] || false,
            'id': evt.id,
            'attendees':attendees,
        };

        if (this.mapping.all_day && evt[this.mapping.all_day]) {
            // r.start = date_start.format('YYYY-MM-DD');
            // r.end = date_stop.format('YYYY-MM-DD');
        } else if (this.data.scale === 'month' && this.fields[this.mapping.date_start].type !== 'date') {
            // allow to resize in month mode
            r.reset_allday = r.allDay;
            r.allDay = true;
            r.start = date_start.format('YYYY-MM-DD');
            r.end = date_stop.clone().add(1, 'day').startOf('day').format('YYYY-MM-DD');
        }

        return r;
    },
});

});
