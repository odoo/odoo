odoo.define('web.CalendarModel', function (require) {
"use strict";

var AbstractModel = require('web.AbstractModel');
var Context = require('web.Context');
var core = require('web.core');
var fieldUtils = require('web.field_utils');
var session = require('web.session');
var time = require('web.time');

var _t = core._t;

var scales = [
    'day',
    'week',
    'month'
];

function dateToServer (date) {
    return date.clone().utc().locale('en').format('YYYY-MM-DD HH:mm:ss');
}

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
        var start = event.start.clone();
        var end = event.end && event.end.clone();

        // Detects allDay events (86400000 = 1 day in ms)
        if (event.allDay || (end && end.diff(start) % 86400000 === 0)) {
            event.allDay = true;
        }

        // Set end date if not existing
        if (!end || end.diff(start) < 0) { // undefined or invalid end date
            if (event.allDay) {
                end = start.clone();
            } else {
                // in week mode or day mode, convert allday event to event
                end = start.clone().add(2, 'h');
            }
        } else if (event.allDay) {
            // For an "allDay", FullCalendar gives the end day as the
            // next day at midnight (instead of 23h59).
            end.add(-1, 'days');
        }

        // An "allDay" event without the "all_day" option is not considered
        // as a 24h day. It's just a part of the day (by default: 7h-19h).
        if (event.allDay) {
            if (!this.mapping.all_day) {
                if (event.r_start) {
                    start.hours(event.r_start.hours())
                         .minutes(event.r_start.minutes())
                         .seconds(event.r_start.seconds())
                         .utc();
                    end.hours(event.r_end.hours())
                       .minutes(event.r_end.minutes())
                       .seconds(event.r_end.seconds())
                       .utc();
                } else {
                    // default hours in the user's timezone
                    start.hours(7).add(-this.getSession().getTZOffset(start), 'minutes');
                    end.hours(19).add(-this.getSession().getTZOffset(end), 'minutes');
                }
            }
        } else {
            start.add(-this.getSession().getTZOffset(start), 'minutes');
            end.add(-this.getSession().getTZOffset(end), 'minutes');
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

        data[this.mapping.date_start] = start;
        if (this.mapping.date_stop) {
            data[this.mapping.date_stop] = end;
        }

        if (this.mapping.date_delay) {
            data[this.mapping.date_delay] = (end.diff(start) <= 0 ? end.endOf('day').diff(start) : end.diff(start)) / 1000 / 3600;
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
     * @param {OdooEvent} event
     */
    createRecord: function (event) {
        var data = this.calendarEventToRecord(event.data.data);
        for (var k in data) {
            if (data[k] && data[k]._isAMomentObject) {
                data[k] = dateToServer(data[k]);
            }
        }
        return this._rpc({
                model: this.modelName,
                method: 'create',
                args: [data],
                context: event.data.options.context,
            });
    },
    /**
     * @todo I think this is dead code
     *
     * @param {any} ids
     * @param {any} model
     * @returns
     */
    deleteRecords: function (ids, model) {
        return this._rpc({
                model: model,
                method: 'unlink',
                args: [ids],
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
        this.fieldsInfo = params.fieldsInfo;
        this.mapping = params.mapping;
        this.mode = params.mode;       // one of month, week or day
        this.scales = params.scales;   // one of month, week or day

        // Check whether the date field is editable (i.e. if the events can be
        // dragged and dropped)
        this.editable = params.editable;
        this.creatable = params.creatable;

        // display more button when there are too much event on one day
        this.eventLimit = params.eventLimit;

        // fields to display color, e.g.: user_id.partner_id
        this.fieldColor = params.fieldColor;
        if (!this.preload_def) {
            this.preload_def = $.Deferred();
            $.when(
                this._rpc({model: this.modelName, method: 'check_access_rights', args: ["write", false]}),
                this._rpc({model: this.modelName, method: 'check_access_rights', args: ["create", false]}))
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

        // Use mode attribute in xml file to specify zoom timeline (day,week,month)
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
        this.setDate(this.data.target_date.clone().add(1, this.data.scale));
    },
    prev: function () {
        this.setDate(this.data.target_date.clone().add(-1, this.data.scale));
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
        if (params.domain) {
            this.data.domain = params.domain;
        }
        return this._loadCalendar();
    },
    /**
     * @param {Moment} start
     * @param {boolean} highlight
     */
    setDate: function (start, highlight) {
        this.data.start_date = this.data.end_date = this.data.target_date = this.data.highlight_date = start;
        this.data.start_date.utc().add(this.getSession().getTZOffset(this.data.start_date), 'minutes');

        switch (this.data.scale) {
            case 'month':
                this.data.start_date = this.data.start_date.clone().startOf('month').startOf('week');
                this.data.end_date = this.data.start_date.clone().add(5, 'week').endOf('week');
                break;
            case 'week':
                this.data.start_date = this.data.start_date.clone().startOf('week');
                this.data.end_date = this.data.end_date.clone().endOf('week');
                break;
            default:
                this.data.start_date = this.data.start_date.clone().startOf('day');
                this.data.end_date = this.data.end_date.clone().endOf('day');
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
        this.setDate(moment(new Date()));
    },
    toggleFullWidth: function () {
        var fullWidth = this.call('local_storage', 'getItem', 'calendar_fullWidth') !== 'true';
        this.call('local_storage', 'setItem', 'calendar_fullWidth', fullWidth);
    },
    /**
     * @param {Object} record
     * @param {integer} record.id
     * @returns {Deferred}
     */
    updateRecord: function (record) {
        // Cannot modify actual name yet
        var data = _.omit(this.calendarEventToRecord(record), 'name');
        for (var k in data) {
            if (data[k] && data[k]._isAMomentObject) {
                data[k] = dateToServer(data[k]);
            }
        }
        var context = new Context(this.data.context, {from_ui: true});
        return this._rpc({
            model: this.modelName,
            method: 'write',
            args: [[record.id], data],
            context: context
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Converts this.data.filters into a domain
     *
     * @private
     * @returns {Array}
     */
    _getFilterDomain: function () {
        // List authorized values for every field
        // fields with an active 'all' filter are skipped
        var authorizedValues = {};
        var avoidValues = {};

        _.each(this.data.filters, function (filter) {
            // Skip 'all' filters because they do not affect the domain
            if (filter.all) return;

            // Loop over subfilters to complete authorizedValues
            _.each(filter.filters, function (f) {
                if (filter.write_model) {
                    if (!authorizedValues[filter.fieldName])
                        authorizedValues[filter.fieldName] = [];

                    if (f.active) {
                        authorizedValues[filter.fieldName].push(f.value);
                    }
                } else {
                    if (!avoidValues[filter.fieldName])
                        avoidValues[filter.fieldName] = [];

                    if (!f.active) {
                        avoidValues[filter.fieldName].push(f.value);
                    }
                }
            });
        });

        // Compute the domain
        var domain = [];
        for (var field in authorizedValues) {
            domain.push([field, 'in', authorizedValues[field]]);
        }
        for (var field in avoidValues) {
            domain.push([field, 'not in', avoidValues[field]]);
        }

        return domain;
    },
    /**
     * @returns {Object}
     */
    _getFullCalendarOptions: function () {
        return {
            defaultView: (this.mode === "month")? "month" : ((this.mode === "week")? "agendaWeek" : ((this.mode === "day")? "agendaDay" : "agendaWeek")),
            header: false,
            selectable: this.creatable && this.create_right,
            selectHelper: true,
            editable: this.editable,
            droppable: true,
            navLinks: false,
            eventLimit: this.eventLimit, // allow "more" link when too many events
            snapMinutes: 15,
            longPressDelay: 500,
            eventResizableFromStart: true,
            weekNumbers: true,
            weekNumberTitle: _t("W"),
            allDayText: _t("All day"),
            views: {
                week: {
                    columnFormat: 'ddd ' + time.getLangDateFormat(),
                    titleFormat: time.getLangTimeFormat(),
                }
            },
            monthNames: moment.months(),
            monthNamesShort: moment.monthsShort(),
            dayNames: moment.weekdays(),
            dayNamesShort: moment.weekdaysShort(),
            firstDay: moment().startOf('week').isoWeekday(),
        };
    },
    /**
     * Return a domain from the date range
     *
     * @private
     * @returns {Array}
     */
    _getRangeDomain: function () {
        // Build OpenERP Domain to filter object by this.mapping.date_start field
        // between given start, end dates.
        var domain = [[this.mapping.date_start, '<=', dateToServer(this.data.end_date)]];
        if (this.mapping.date_stop) {
            domain.push([this.mapping.date_stop, '>=', dateToServer(this.data.start_date)]);
        } else if (!this.mapping.date_delay) {
            domain.push([this.mapping.date_start, '>=', dateToServer(this.data.start_date)]);
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
            return self._rpc({
                    model: self.modelName,
                    method: 'search_read',
                    context: self.data.context,
                    fields: self.fieldNames,
                    domain: self.data.domain.concat(self._getRangeDomain()).concat(self._getFilterDomain())
            })
            .then(function (events) {
                self._parseServerData(events);
                self.data.data = _.map(events, self._recordToCalendarEvent.bind(self));
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
        if (this.fieldColor) {
            var fieldName = this.fieldColor;
            _.each(events, function (event) {
                var value = event.record[fieldName];
                event.color_index = _.isArray(value) ? value[0] : value;
            });
            this.model_color = this.fields[fieldName].relation || element.model;
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
        return this._rpc({
                model: filter.write_model,
                method: 'search_read',
                domain: [["user_id", "=", session.uid]],
                fields: [filter.write_field],
            })
            .then(function (res) {
                var records = _.map(res, function (record) {
                    var _value = record[filter.write_field];
                    var value = _.isArray(_value) ? _value[0] : _value;
                    var f = _.find(filter.filters, function (f) {return f.value === value;});
                    var formater = fieldUtils.format[_.contains(['many2many', 'one2many'], field.type) ? 'many2one' : field.type];
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
                        'color_index': self.model_color === (field.relation || element.model) ? value : false,
                        'value': value,
                        'label': fieldUtils.format[field.type](_value, field),
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
            defs.push(self._rpc({
                    model: model,
                    method: 'name_get',
                    args: [_.uniq(ids)],
                })
                .then(function (res) {
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
     * parse the server values to javascript framwork
     *
     * @param {Object} data the server data to parse
     */
    _parseServerData: function (data) {
        var self = this;
        _.each(data, function(event) {
            _.each(self.fieldNames, function (fieldName) {
                event[fieldName] = self._parseServerValue(self.fields[fieldName], event[fieldName]);
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
            date_start = evt[this.mapping.date_start].clone();
            date_stop = this.mapping.date_stop ? evt[this.mapping.date_stop].clone() : null;
        } else {
            date_start = evt[this.mapping.date_start].clone().startOf('day');
            date_stop = this.mapping.date_stop ? evt[this.mapping.date_stop].clone().startOf('day') : null;
        }

        if (!date_stop && date_delay) {
            date_stop = date_start.clone().add(date_delay,'hours');
        }

        if (!all_day) {
            date_start.add(this.getSession().getTZOffset(date_start), 'minutes');
            date_stop.add(this.getSession().getTZOffset(date_stop), 'minutes');
        }

        if (this.mapping.all_day && evt[this.mapping.all_day]) {
            date_stop.add(1, 'days');
        }
        var isAllDay = this.fields[this.mapping.date_start].type === 'date' ||
                        this.mapping.all_day && evt[this.mapping.all_day] || false;
        var r = {
            'record': evt,
            'start': date_start,
            'end': date_stop,
            'r_start': date_start,
            'r_end': date_stop,
            'title': the_title,
            'allDay': isAllDay,
            'id': evt.id,
            'attendees':attendees,
        };

        if (this.mapping.all_day && evt[this.mapping.all_day]) {
            // r.start = date_start.format('YYYY-MM-DD');
            // r.end = date_stop.format('YYYY-MM-DD');
        } else if (this.data.scale === 'month' && this.fields[this.mapping.date_start].type !== 'date') {
            // In month, FullCalendar gives the end day as the
            // next day at midnight (instead of 23h59).
            date_stop.add(1, 'days');

            // allow to resize in month mode
            r.reset_allday = r.allDay;
            r.allDay = true;
            r.start = date_start.format('YYYY-MM-DD');
            r.end = date_stop.startOf('day').format('YYYY-MM-DD');
        }

        return r;
    },
});

});
