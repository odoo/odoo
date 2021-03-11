odoo.define('web.CalendarModel', function (require) {
"use strict";

var AbstractModel = require('web.AbstractModel');
var Context = require('web.Context');
var core = require('web.core');
var fieldUtils = require('web.field_utils');
var session = require('web.session');

var _t = core._t;

function dateToServer (date) {
    return date.clone().utc().locale('en').format('YYYY-MM-DD HH:mm:ss');
}

return AbstractModel.extend({
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.end_date = null;
        var week_start = _t.database.parameters.week_start;
        // calendar uses index 0 for Sunday but Odoo stores it as 7
        this.week_start = week_start !== undefined && week_start !== false ? week_start % 7 : moment().startOf('week').day();
        this.week_stop = this.week_start + 6;
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

        var isDateEvent = this.fields[this.mapping.date_start].type === 'date';
        // An "allDay" event without the "all_day" option is not considered
        // as a 24h day. It's just a part of the day (by default: 7h-19h).
        if (event.allDay) {
            if (!this.mapping.all_day && !isDateEvent) {
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
                    start.hours(7);
                    end.hours(19);
                }
                start.add(-this.getSession().getTZOffset(start), 'minutes');
                end.add(-this.getSession().getTZOffset(end), 'minutes');
            }
        } else {
            start.add(-this.getSession().getTZOffset(start), 'minutes');
            end.add(-this.getSession().getTZOffset(end), 'minutes');
        }

        if (this.mapping.all_day) {
            if (event.record) {
                data[this.mapping.all_day] =
                    (this.data.scale !== 'month' && event.allDay) ||
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
            if (this.data.scale !== 'month' || (this.data.scale === 'month' && !event.drop)) {
                data[this.mapping.date_delay] = (end.diff(start) <= 0 ? end.endOf('day').diff(start) : end.diff(start)) / 1000 / 3600;
            }
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
    __get: function () {
        return _.extend({}, this.data, {
            fields: this.fields
        });
    },
    /**
     * @override
     * @param {any} params
     * @returns {Promise}
     */
    __load: function (params) {
        var self = this;
        this.modelName = params.modelName;
        this.fields = params.fields;
        this.fieldNames = params.fieldNames;
        this.fieldsInfo = params.fieldsInfo;
        this.mapping = params.mapping;
        this.mode = params.mode;       // one of month, week or day
        this.scales = params.scales;   // one of month, week or day
        this.scalesInfo = params.scalesInfo;

        // Check whether the date field is editable (i.e. if the events can be
        // dragged and dropped)
        this.editable = params.editable;
        this.creatable = params.creatable;

        // display more button when there are too much event on one day
        this.eventLimit = params.eventLimit;

        // fields to display color, e.g.: user_id.partner_id
        this.fieldColor = params.fieldColor;
        if (!this.preloadPromise) {
            this.preloadPromise = new Promise(function (resolve, reject) {
                Promise.all([
                    self._rpc({model: self.modelName, method: 'check_access_rights', args: ["write", false]}),
                    self._rpc({model: self.modelName, method: 'check_access_rights', args: ["create", false]})
                ]).then(function (result) {
                    var write = result[0];
                    var create = result[1];
                    self.write_right = write;
                    self.create_right = create;
                    resolve();
                }).guardedCatch(reject);
            });
        }

        this.data = {
            domain: params.domain,
            context: params.context,
            // get in arch the filter to display in the sidebar and the field to read
            filters: params.filters,
        };

        this.setDate(params.initialDate);
        // Use mode attribute in xml file to specify zoom timeline (day,week,month)
        // by default month.
        this.setScale(params.mode);

        _.each(this.data.filters, function (filter) {
            if (filter.avatar_field && !filter.avatar_model) {
                filter.avatar_model = self.modelName;
            }
        });

        return this.preloadPromise.then(this._loadCalendar.bind(this));
    },
    /**
     * Move the current date range to the next period
     */
    next: function () {
        this.setDate(this.data.target_date.clone().add(1, this.data.scale));
    },
    /**
     * Move the current date range to the previous period
     */
    prev: function () {
        this.setDate(this.data.target_date.clone().add(-1, this.data.scale));
    },
    /**
     * @override
     * @param {Object} [params.context]
     * @param {Array} [params.domain]
     * @returns {Promise}
     */
    __reload: function (handle, params) {
        if (params.domain) {
            this.data.domain = params.domain;
        }
        if (params.context) {
            this.data.context = params.context;
        }
        return this._loadCalendar();
    },
    /**
     * @param {Moment} start. in local TZ
     */
    setDate: function (start) {
        // keep highlight/target_date in localtime
        this.data.highlight_date = this.data.target_date = start.clone();
        this.data.start_date = this.data.end_date = start;
        switch (this.data.scale) {
            case 'year': {
                const yearStart = this.data.start_date.clone().startOf('year');
                let yearStartDay = this.week_start;
                if (yearStart.day() < yearStartDay) {
                    // the 1st of January is before our week start (e.g. week start is Monday, and
                    // 01/01 is Sunday), so we go one week back
                    yearStartDay -= 7;
                }
                this.data.start_date = yearStart.day(yearStartDay).startOf('day');
                this.data.end_date = this.data.end_date.clone()
                    .endOf('year').day(this.week_stop).endOf('day');
                break;
            }
            case 'month':
                var monthStart = this.data.start_date.clone().startOf('month');

                var monthStartDay;
                if (monthStart.day() >= this.week_start) {
                    // the month's first day is after our week start
                    // Then we are in the right week
                    monthStartDay = this.week_start;
                } else {
                    // The month's first day is before our week start
                    // Then we should go back to the the previous week
                    monthStartDay = this.week_start - 7;
                }

                this.data.start_date = monthStart.day(monthStartDay).startOf('day');
                this.data.end_date = this.data.start_date.clone().add(5, 'week').day(this.week_stop).endOf('day');
                break;
            case 'week':
                var weekStart = this.data.start_date.clone().startOf('week');
                var weekStartDay = this.week_start;
                if (this.data.start_date.day() < this.week_start) {
                    // The week's first day is after our current day
                    // Then we should go back to the previous week
                    weekStartDay -= 7;
                }
                this.data.start_date = this.data.start_date.clone().day(weekStartDay).startOf('day');
                this.data.end_date = this.data.end_date.clone().day(weekStartDay + 6).endOf('day');
                break;
            default:
                this.data.start_date = this.data.start_date.clone().startOf('day');
                this.data.end_date = this.data.end_date.clone().endOf('day');
        }
        // We have set start/stop datetime as definite begin/end boundaries of a period (month, week, day)
        // in local TZ (what is the begining of the week *I am* in ?)
        // The following code:
        // - converts those to UTC using our homemade method (testable)
        // - sets the moment UTC flag to true, to ensure compatibility with third party libs
        var manualUtcDateStart = this.data.start_date.clone().add(-this.getSession().getTZOffset(this.data.start_date), 'minutes');
        var formattedUtcDateStart = manualUtcDateStart.format('YYYY-MM-DDTHH:mm:ss') + 'Z';
        this.data.start_date = moment.utc(formattedUtcDateStart);

        var manualUtcDateEnd = this.data.end_date.clone().add(-this.getSession().getTZOffset(this.data.start_date), 'minutes');
        var formattedUtcDateEnd = manualUtcDateEnd.format('YYYY-MM-DDTHH:mm:ss') + 'Z';
        this.data.end_date = moment.utc(formattedUtcDateEnd);
    },
    /**
     * @param {string} scale the scale to set
     */
    setScale: function (scale) {
        if (!_.contains(this.scales, scale)) {
            scale = "week";
        }
        this.data.scale = scale;
        this.setDate(this.data.target_date);
    },
    /**
     * Move the current date range to the period containing today
     */
    today: function () {
        this.setDate(moment(new Date()));
    },
    /**
     * @param {Object} record
     * @param {integer} record.id
     * @returns {Promise}
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
            args: [[parseInt(record.id, 10)], data],
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
                    if (!f.active) {
                        if (!avoidValues[filter.fieldName])
                            avoidValues[filter.fieldName] = [];

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
            if (avoidValues[field].length > 0) {
                domain.push([field, 'not in', avoidValues[field]]);
            }
        }

        return domain;
    },
    /**
     * @private
     * @returns {Object}
     */
    _getFullCalendarOptions: function () {
        var format12Hour = {
            hour: 'numeric',
            minute: '2-digit',
            omitZeroMinute: true,
            meridiem: 'short'
        };
        var format24Hour = {
            hour: 'numeric',
            minute: '2-digit',
            hour12: false,
        };
        return {
            defaultView: this.scalesInfo[this.mode || 'week'],
            header: false,
            selectable: this.creatable && this.create_right,
            selectMirror: true,
            editable: this.editable,
            droppable: true,
            navLinks: false,
            eventLimit: this.eventLimit, // allow "more" link when too many events
            snapMinutes: 15,
            longPressDelay: 500,
            eventResizableFromStart: true,
            nowIndicator: true,
            weekNumbers: true,
            weekNumbersWithinDays: true,
            weekNumberCalculation: function (date) {
                // Since FullCalendar v4 ISO 8601 week date is preferred so we force the old system
                return moment(date).week();
            },
            weekLabel: _t("Week"),
            allDayText: _t("All day"),
            monthNames: moment.months(),
            monthNamesShort: moment.monthsShort(),
            dayNames: moment.weekdays(),
            dayNamesShort: moment.weekdaysShort(),
            firstDay: this.week_start,
            slotLabelFormat: _t.database.parameters.time_format.search("%H") !== -1 ? format24Hour : format12Hour,
            allDaySlot: this.mapping.all_day || this.fields[this.mapping.date_start].type === 'date',
        };
    },
    /**
     * Return a domain from the date range
     *
     * @private
     * @returns {Array} A domain containing datetimes start and stop in UTC
     *  those datetimes are formatted according to server's standards
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
     * @private
     * @returns {Promise}
     */
    _loadCalendar: function () {
        var self = this;
        this.data.fc_options = this._getFullCalendarOptions();

        var defs = _.map(this.data.filters, this._loadFilter.bind(this));

        return Promise.all(defs).then(function () {
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
                return Promise.all([
                    self._loadColors(self.data, self.data.data),
                    self._loadRecordsToFilters(self.data, self.data.data)
                ]);
            });
        });
    },
    /**
     * @private
     * @param {any} element
     * @param {any} events
     * @returns {Promise}
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
        return Promise.resolve();
    },
    /**
     * @private
     * @param {any} filter
     * @returns {Promise}
     */
    _loadFilter: function (filter) {
        if (!filter.write_model) {
            return Promise.resolve();
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
     * @private
     * @param {any} element
     * @param {any} events
     * @returns {Promise}
     */
    _loadRecordsToFilters: function (element, events) {
        var self = this;
        var new_filters = {};
        var to_read = {};
        var defs = [];
        var color_filter = {};

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
            var undefined_fs = [];
            _.each(events, function (event) {
                var data =  event.record[fieldName];
                if (!_.contains(['many2many', 'one2many'], field.type)) {
                    data = [data];
                } else {
                    to_read[field.relation] = (to_read[field.relation] || []).concat(data);
                }
                _.each(data, function (_value) {
                    var value = _.isArray(_value) ? _value[0] : _value;
                    var f = {
                        'color_index': self.model_color === (field.relation || element.model) ? value : false,
                        'value': value,
                        'label': fieldUtils.format[field.type](_value, field) || _t("Undefined"),
                        'avatar_model': field.relation || element.model,
                    };
                    // if field used as color does not have value then push filter in undefined_fs,
                    // such filters should come last in filter list with Undefined string, later merge it with fs
                    value ? fs.push(f) : undefined_fs.push(f);
                });
            });
            _.each(_.union(fs, undefined_fs), function (f) {
                var f1 = _.findWhere(filter.filters, _.omit(f, 'color_index'));
                if (f1) {
                    f1.display = true;
                } else {
                    f.display = f.active = true;
                    filter.filters.push(f);
                }
            });

            if (filter.color_model && filter.field_color) {
                var ids = filter.filters.reduce((acc, f) => {
                    if (!f.color_index && f.value) {
                        acc.push(f.value);
                    }
                    return acc;
                }, []);
                if (!color_filter[filter.color_model]) {
                    color_filter[filter.color_model] = {};
                }
                if (ids.length) {
                    defs.push(self._rpc({
                        model: filter.color_model,
                        method: 'read',
                        args: [_.uniq(ids), [filter.field_color]],
                    })
                    .then(function (res) {
                        _.each(res, function (c) {
                            color_filter[filter.color_model][c.id] = c[filter.field_color];
                        });
                    }));
                }
            }
        });

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
        return Promise.all(defs).then(function () {
            _.each(self.data.filters, function (filter) {
                if (filter.write_model) {
                    return;
                }
                if (filter.filters.length && (filter.filters[0].avatar_model in to_read)) {
                    _.each(filter.filters, function (f) {
                        f.label = to_read[f.avatar_model][f.value];
                    });
                }
                if (filter.color_model && filter.field_color) {
                    _.each(filter.filters, function (f) {
                        if (!f.color_index) {
                            f.color_index = color_filter[filter.color_model] && color_filter[filter.color_model][f.value];
                        }
                    });
                }
            });
        });
    },
    /**
     * parse the server values to javascript framwork
     *
     * @private
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
     *
     * @private
     * @param {Object} evt
     */
    _recordToCalendarEvent: function (evt) {
        var date_start;
        var date_stop;
        var date_delay = evt[this.mapping.date_delay] || 1.0,
            all_day = this.fields[this.mapping.date_start].type === 'date' ||
                this.mapping.all_day && evt[this.mapping.all_day] || false,
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
        var r = {
            'record': evt,
            'start': date_start.local(true).toDate(),
            'end': date_stop.local(true).toDate(),
            'r_start': date_start.clone().local(true).toDate(),
            'r_end': date_stop.clone().local(true).toDate(),
            'title': the_title,
            'allDay': all_day,
            'id': evt.id,
            'attendees':attendees,
        };

        if (!(this.mapping.all_day && evt[this.mapping.all_day]) && this.data.scale === 'month' && this.fields[this.mapping.date_start].type !== 'date') {
            r.showTime = true;
        }

        return r;
    },
});

});
