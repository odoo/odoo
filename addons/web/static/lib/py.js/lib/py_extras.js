(function (py) {
"use strict";

/**
 * This file add extra functionality to the python interpreter exported by py.js
 *
 * Main extra functionality is about time management, more precisely:
 * - date
 * - datetime
 * - relativedelta
 *
 * These python modules are exported in the py.extras object, and can be added
 * to the evaluation context.  For example,
 *
 *  var context = {
 *      datetime: py.extras.datetime,
 *      date: py.extras.date,
 *      time: py.extras.time,
 *  };
 *  var result = py.eval(some_python_expression, context);
 */

/*
 * py.js helpers and setup
 */

/**
 * computes (Math.floor(a/b), a%b and passes that to the callback.
 *
 * returns the callback's result
 */
function divmod (a, b, fn) {
    var mod = a%b;
    // in python, sign(a % b) === sign(b). Not in JS. If wrong side, add a
    // round of b
    if (mod > 0 && b < 0 || mod < 0 && b > 0) {
        mod += b;
    }
    return fn(Math.floor(a/b), mod);
}

/**
 * Passes the fractional and integer parts of x to the callback, returns
 * the callback's result
 */
function modf(x, fn) {
    var mod = x%1;
    if (mod < 0) {
        mod += 1;
    }
    return fn(mod, Math.floor(x));
}

function assert(bool) {
    if (!bool) {
        throw new Error("AssertionError");
    }
}


var obj = function () {};
obj.prototype = py.object;
var asJS = function (arg) {
    if (arg instanceof obj) {
        return arg.toJSON();
    }
    return arg;
};

var datetime = py.PY_call(py.object);

var zero = py.float.fromJSON(0);

// Port from pypy/lib_pypy/datetime.py
var DAYS_IN_MONTH = [null, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
var DAYS_BEFORE_MONTH = [null];
var dbm = 0;

for (var i=1; i<DAYS_IN_MONTH.length; ++i) {
    DAYS_BEFORE_MONTH.push(dbm);
    dbm += DAYS_IN_MONTH[i];
}

function is_leap(year) {
    return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
}

function days_before_year(year) {
    var y = year - 1;
    return y*365 + Math.floor(y/4) - Math.floor(y/100) + Math.floor(y/400);
}

function days_in_month(year, month) {
    if (month === 2 && is_leap(year)) {
        return 29;
    }
    return DAYS_IN_MONTH[month];
}

function days_before_month(year, month) {
    var post_leap_feb = month > 2 && is_leap(year);
    return DAYS_BEFORE_MONTH[month] + (post_leap_feb ? 1 : 0);
}

function ymd2ord(year, month, day) {
    var dim = days_in_month(year, month);
    if (!(1 <= day && day <= dim)) {
        throw new Error("ValueError: day must be in 1.." + dim);
    }
    return days_before_year(year) +
           days_before_month(year, month) +
           day;
}

function get_quarter_number(month) {
    return Math.ceil(month / 3);
}

function get_quarter(year, month) {
    var quarter_number = get_quarter_number(month);
    var month_from = ((quarter_number - 1) * 3) + 1
    var date_from = {year: year, month: month_from, day: 1}
    var date_to = {year: year, month: month_from + 2, day: days_in_month(year, month)}
    return [date_from, date_to];
}

function get_day_of_week(year, month, day) {
    // Since JavaScript is a piece of garbage, months start at 0
    var d = new Date(year, month - 1, day);
    // Convert to ISO8601: Monday = 0 ... Sunday = 6
    return (d.getDay() + 6) % 7;
}

var DI400Y = days_before_year(401);
var DI100Y = days_before_year(101);
var DI4Y = days_before_year(5);

function ord2ymd(n) {
    --n;
    var n400, n100, n4, n1, n0;
    divmod(n, DI400Y, function (_n400, n) {
        n400 = _n400;
        divmod(n, DI100Y, function (_n100, n) {
            n100 = _n100;
            divmod(n, DI4Y, function (_n4, n) {
                n4 = _n4;
                divmod(n, 365, function (_n1, n) {
                    n1 = _n1;
                    n0 = n;
                });
            });
        });
    });

    n = n0;
    var year = n400 * 400 + 1 + n100 * 100 + n4 * 4 + n1;
    if (n1 == 4 || n100 == 100) {
        assert(n0 === 0);
        return {
            year: year - 1,
            month: 12,
            day: 31
        };
    }

    var leapyear = n1 === 3 && (n4 !== 24 || n100 == 3);
    assert(leapyear == is_leap(year));
    var month = (n + 50) >> 5;
    var preceding = DAYS_BEFORE_MONTH[month] + ((month > 2 && leapyear) ? 1 : 0);
    if (preceding > n) {
        --month;
        preceding -= DAYS_IN_MONTH[month] + ((month === 2 && leapyear) ? 1 : 0);
    }
    n -= preceding;
    return {
        year: year,
        month: month,
        day: n+1
    };
}

/**
 * Converts the stuff passed in into a valid date, applying overflows as needed
 */
function tmxxx(year, month, day, hour, minute, second, microsecond) {
    hour = hour || 0; minute = minute || 0; second = second || 0;
    microsecond = microsecond || 0;

    if (microsecond < 0 || microsecond > 999999) {
        divmod(microsecond, 1000000, function (carry, ms) {
            microsecond = ms;
            second += carry;
        });
    }
    if (second < 0 || second > 59) {
        divmod(second, 60, function (carry, s) {
            second = s;
            minute += carry;
        });
    }
    if (minute < 0 || minute > 59) {
        divmod(minute, 60, function (carry, m) {
            minute = m;
            hour += carry;
        });
    }
    if (hour < 0 || hour > 23) {
        divmod(hour, 24, function (carry, h) {
            hour = h;
            day += carry;
        });
    }
    // That was easy.  Now it gets muddy:  the proper range for day
    // can't be determined without knowing the correct month and year,
    // but if day is, e.g., plus or minus a million, the current month
    // and year values make no sense (and may also be out of bounds
    // themselves).
    // Saying 12 months == 1 year should be non-controversial.
    if (month < 1 || month > 12) {
        divmod(month-1, 12, function (carry, m) {
            month = m + 1;
            year += carry;
        });
    }
    // Now only day can be out of bounds (year may also be out of bounds
    // for a datetime object, but we don't care about that here).
    // If day is out of bounds, what to do is arguable, but at least the
    // method here is principled and explainable.
    var dim = days_in_month(year, month);
    if (day < 1 || day > dim) {
        // Move day-1 days from the first of the month.  First try to
        // get off cheap if we're only one day out of range (adjustments
        // for timezone alone can't be worse than that).
        if (day === 0) {
            --month;
            if (month > 0) {
                day = days_in_month(year, month);
            } else {
                --year; month=12; day=31;
            }
        } else if (day == dim + 1) {
            ++month;
            day = 1;
            if (month > 12) {
                month = 1;
                ++year;
            }
        } else {
            var r = ord2ymd(ymd2ord(year, month, 1) + (day - 1));
            year = r.year;
            month = r.month;
            day = r.day;
        }
    }
    return {
        year: year,
        month: month,
        day: day,
        hour: hour,
        minute: minute,
        second: second,
        microsecond: microsecond
    };
}

datetime.timedelta = py.type('timedelta', null, {
    __init__: function () {
        var args = py.PY_parseArgs(arguments, [
            ['days', zero], ['seconds', zero], ['microseconds', zero],
            ['milliseconds', zero], ['minutes', zero], ['hours', zero],
            ['weeks', zero]
        ]);

        var d = 0, s = 0, m = 0;
        var days = args.days.toJSON() + args.weeks.toJSON() * 7;
        var seconds = args.seconds.toJSON()
                    + args.minutes.toJSON() * 60
                    + args.hours.toJSON() * 3600;
        var microseconds = args.microseconds.toJSON()
                         + args.milliseconds.toJSON() * 1000;

        // Get rid of all fractions, and normalize s and us.
        // Take a deep breath <wink>.
        var daysecondsfrac = modf(days, function (dayfrac, days) {
            d = days;
            if (dayfrac) {
                return modf(dayfrac * 24 * 3600, function (dsf, dsw) {
                    s = dsw;
                    return dsf;
                });
            }
            return 0;
        });

        var secondsfrac = modf(seconds, function (sf, s) {
            seconds = s;
            return sf + daysecondsfrac;
        });
        divmod(seconds, 24*3600, function (days, seconds) {
            d += days;
            s += seconds;
        });
        // seconds isn't referenced again before redefinition

        microseconds += secondsfrac * 1e6;
        divmod(microseconds, 1000000, function (seconds, microseconds) {
            divmod(seconds, 24*3600, function (days, seconds) {
                d += days;
                s += seconds;
                m += Math.round(microseconds);
            });
        });

        // Carrying still possible here?

        this.days = d;
        this.seconds = s;
        this.microseconds = m;
    },
    __str__: function () {
        var hh, mm, ss;
        divmod(this.seconds, 60, function (m, s) {
            divmod(m, 60, function (h, m) {
                hh = h;
                mm = m;
                ss = s;
            });
        });
        var s = _.str.sprintf("%d:%02d:%02d", hh, mm, ss);
        if (this.days) {
            s = _.str.sprintf("%d day%s, %s",
                this.days,
                (this.days != 1 && this.days != -1) ? 's' : '',
                s);
        }
        if (this.microseconds) {
            s = _.str.sprintf("%s.%06d", s, this.microseconds);
        }
        return py.str.fromJSON(s);
    },
    __eq__: function (other) {
        if (!py.PY_isInstance(other, datetime.timedelta)) {
            return py.False;
        }

        return (this.days === other.days
            && this.seconds === other.seconds
            && this.microseconds === other.microseconds)
                ? py.True : py.False;
    },
    __add__: function (other) {
        if (!py.PY_isInstance(other, datetime.timedelta)) {
            return py.NotImplemented;
        }
        return py.PY_call(datetime.timedelta, [
            py.float.fromJSON(this.days + other.days),
            py.float.fromJSON(this.seconds + other.seconds),
            py.float.fromJSON(this.microseconds + other.microseconds)
        ]);
    },
    __radd__: function (other) { return this.__add__(other); },
    __sub__: function (other) {
        if (!py.PY_isInstance(other, datetime.timedelta)) {
            return py.NotImplemented;
        }
        return py.PY_call(datetime.timedelta, [
            py.float.fromJSON(this.days - other.days),
            py.float.fromJSON(this.seconds - other.seconds),
            py.float.fromJSON(this.microseconds - other.microseconds)
        ]);
    },
    __rsub__: function (other) {
        if (!py.PY_isInstance(other, datetime.timedelta)) {
            return py.NotImplemented;
        }
        return this.__neg__().__add__(other);
    },
    __neg__: function () {
        return py.PY_call(datetime.timedelta, [
            py.float.fromJSON(-this.days),
            py.float.fromJSON(-this.seconds),
            py.float.fromJSON(-this.microseconds)
        ]);
    },
    __pos__: function () { return this; },
    __mul__: function (other) {
        if (!py.PY_isInstance(other, py.float)) {
            return py.NotImplemented;
        }
        var n = other.toJSON();
        return py.PY_call(datetime.timedelta, [
            py.float.fromJSON(this.days * n),
            py.float.fromJSON(this.seconds * n),
            py.float.fromJSON(this.microseconds * n)
        ]);
    },
    __rmul__: function (other) { return this.__mul__(other); },
    __div__: function (other) {
        if (!py.PY_isInstance(other, py.float)) {
            return py.NotImplemented;
        }
        var usec = ((this.days * 24 * 3600) + this.seconds) * 1000000
                    + this.microseconds;
        return py.PY_call(
            datetime.timedelta, [
                zero, zero, py.float.fromJSON(usec / other.toJSON())]);
    },
    __floordiv__: function (other) { return this.__div__(other); },
    total_seconds: function () {
        return py.float.fromJSON(
            this.days * 86400
          + this.seconds
          + this.microseconds / 1000000);
    },
    __nonzero__: function () {
        return (!!this.days || !!this.seconds || !!this.microseconds)
            ? py.True
            : py.False;
    }
});

datetime.datetime = py.type('datetime', null, {
    __init__: function () {
        var zero = py.float.fromJSON(0);
        var args = py.PY_parseArgs(arguments, [
            'year', 'month', 'day',
            ['hour', zero], ['minute', zero], ['second', zero],
            ['microsecond', zero], ['tzinfo', py.None]
        ]);
        for(var key in args) {
            if (!args.hasOwnProperty(key)) { continue; }
            this[key] = asJS(args[key]);
        }
    },
    __eq__: function (other) {
        return (this.year === other.year
             && this.month === other.month
             && this.day === other.day
             && this.hour === other.hour
             && this.minute === other.minute
             && this.second === other.second
             && this.microsecond === other.microsecond
             && this.tzinfo === other.tzinfo)
            ? py.True : py.False;
    },
    replace: function () {
        var args = py.PY_parseArgs(arguments, [
            ['year', py.None], ['month', py.None], ['day', py.None],
            ['hour', py.None], ['minute', py.None], ['second', py.None],
            ['microsecond', py.None] // FIXME: tzinfo, can't use None as valid input
        ]);
        var params = {};
        for(var key in args) {
            if (!args.hasOwnProperty(key)) { continue; }

            var arg = args[key];
            params[key] = (arg === py.None ? this[key] : asJS(arg));
        }
        return py.PY_call(datetime.datetime, params);
    },
    start_of: function() {
        var args = py.PY_parseArgs(arguments, 'granularity');
        var granularity = args.granularity.toJSON();
        if (granularity === 'year') {
            return py.PY_call(datetime.datetime, [this.year, 1, 1]);
        } else if (granularity === 'quarter') {
            var quarter = get_quarter(this.year, this.month)[0];
            return py.PY_call(datetime.datetime, [quarter.year, quarter.month, quarter.day]);
        } else if (granularity === 'month') {
            return py.PY_call(datetime.datetime, [this.year, this.month, 1]);
        } else if (granularity === 'week') {
            var dow = get_day_of_week(this.year, this.month, this.day);
            return py.PY_call(datetime.datetime, [this.year, this.month, this.day - dow]);
        } else if (granularity === 'day') {
            return py.PY_call(datetime.datetime, [this.year, this.month, this.day]);
        } else if (granularity === 'hour') {
            return py.PY_call(datetime.datetime, [this.year, this.month, this.day, this.hour]);
        } else {
            throw new Error(
                'ValueError: ' + granularity + ' is not a supported granularity, supported ' +
                ' granularities are: year, quarter, month, week, day and hour.'
            )
        }
    },
    end_of: function () {
        var args = py.PY_parseArgs(arguments, 'granularity');
        var granularity = args.granularity.toJSON();
        var min = [23, 59, 59];
        if (granularity === 'year') {
            return py.PY_call(datetime.datetime, [this.year, 12, 31].concat(min));
        } else if (granularity === 'quarter') {
            var quarter = get_quarter(this.year, this.month)[1];
            return py.PY_call(
                datetime.datetime, [quarter.year, quarter.month, quarter.day].concat(min)
            );
        } else if (granularity === 'month') {
            var dom = days_in_month(this.year, this.month);
            return py.PY_call(datetime.datetime, [this.year, this.month, dom].concat(min));
        } else if (granularity === 'week') {
            var dow = get_day_of_week(this.year, this.month, this.day);
            return py.PY_call(
                datetime.datetime, [this.year, this.month, this.day + (6 - dow)].concat(min)
            );
        } else if (granularity === 'day') {
            return py.PY_call(datetime.datetime, [this.year, this.month, this.day].concat(min));
        } else if (granularity === 'hour') {
            return py.PY_call(
                datetime.datetime, [this.year, this.month, this.day, this.hour, 59, 59]
            );
        } else {
            throw new Error(
                'ValueError: ' + granularity + ' is not a supported granularity, supported ' +
                ' granularities are: year, quarter, month, week, day and hour.'
            )
        }
    },
    add: function() {
        var args = py.PY_parseArgs(arguments, [
            ['years', py.None], ['months', py.None], ['days', py.None],
            ['hours', py.None], ['minutes', py.None], ['seconds', py.None],
        ]);
        return py.PY_add(this, py.PY_call(relativedelta, {
            'years': args.years,
            'months': args.months,
            'days': args.days,
            'hours': args.hours,
            'minutes': args.minutes,
            'seconds': args.seconds,
        }));
    },
    subtract: function() {
        var args = py.PY_parseArgs(arguments, [
            ['years', py.None], ['months', py.None], ['days', py.None],
            ['hours', py.None], ['minutes', py.None], ['seconds', py.None],
        ]);
        var params = {};
        for (var key in args) {
            params[key] = (args[key] === py.None ? args[key] : py.float.fromJSON(-asJS(args[key])));
        }
        return py.PY_add(this, py.PY_call(relativedelta, params));
    },
    strftime: function () {
        var self = this;
        var args = py.PY_parseArgs(arguments, 'format');
        return py.str.fromJSON(args.format.toJSON()
            .replace(/%([A-Za-z])/g, function (m, c) {
                switch (c) {
                case 'Y': return _.str.sprintf('%04d', self.year);
                case 'm': return _.str.sprintf('%02d', self.month);
                case 'd': return _.str.sprintf('%02d', self.day);
                case 'H': return _.str.sprintf('%02d', self.hour);
                case 'M': return _.str.sprintf('%02d', self.minute);
                case 'S': return _.str.sprintf('%02d', self.second);
                }
                throw new Error('ValueError: No known conversion for ' + m);
            }));
    },
    to_utc: function () {
        var d = new Date(this.year, this.month, this.day, this.hour, this.minute, this.second);
        var offset = d.getTimezoneOffset();
        var kwargs = {minutes: py.float.fromJSON(offset)};
        var timedelta = py.PY_call(py.extras.datetime.timedelta,[],kwargs);
        var s = tmxxx(this.year, this.month, this.day + timedelta.days, this.hour, this.minute, this.second + timedelta.seconds);
        return datetime.datetime.fromJSON(s.year, s.month, s.day, s.hour, s.minute, s.second);
    },
    now: py.classmethod.fromJSON(function () {
        var d = new Date();
        return py.PY_call(datetime.datetime, [
            d.getFullYear(), d.getMonth() + 1, d.getDate(),
            d.getHours(), d.getMinutes(), d.getSeconds(),
            d.getMilliseconds() * 1000]);
    }),
    today: py.classmethod.fromJSON(function () {
        var dt_class = py.PY_getAttr(datetime, 'datetime');
        return py.PY_call(py.PY_getAttr(dt_class, 'now'));
    }),
    utcnow: py.classmethod.fromJSON(function () {
        var d = new Date();
        return py.PY_call(datetime.datetime,
            [d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate(),
             d.getUTCHours(), d.getUTCMinutes(), d.getUTCSeconds(),
             d.getUTCMilliseconds() * 1000]);
    }),

    combine: py.classmethod.fromJSON(function () {
        var args = py.PY_parseArgs(arguments, 'date time');
        return py.PY_call(datetime.datetime, [
            py.PY_getAttr(args.date, 'year'),
            py.PY_getAttr(args.date, 'month'),
            py.PY_getAttr(args.date, 'day'),
            py.PY_getAttr(args.time, 'hour'),
            py.PY_getAttr(args.time, 'minute'),
            py.PY_getAttr(args.time, 'second')
        ]);
    }),
    toJSON: function () {
        return new Date(
            this.year,
            this.month - 1,
            this.day,
            this.hour,
            this.minute,
            this.second,
            this.microsecond / 1000);
    },
    __add__: function (other) {
        if (!py.PY_isInstance(other, datetime.timedelta)) {
            return py.NotImplemented;
        }
        var s = tmxxx(this.year, this.month, this.day + other.days, this.hour, this.minute, this.second + other.seconds);
        return datetime.datetime.fromJSON(s.year, s.month, s.day, s.hour, s.minute, s.second);
    },
    __sub__: function (other) {
        if (py.PY_isInstance(other, datetime.timedelta)) {
            return py.PY_add(this, py.PY_negative(other));
        }
        return py.NotImplemented;
    },
    fromJSON: function (year, month, day, hour, minute, second) {
        return py.PY_call(datetime.datetime, [year, month, day, hour, minute, second]);
    },
});

datetime.date = py.type('date', null, {
    __init__: function () {
        var args = py.PY_parseArgs(arguments, 'year month day');
        this.year = asJS(args.year);
        this.month = asJS(args.month);
        this.day = asJS(args.day);
    },
    strftime: function () {
        var self = this;
        var args = py.PY_parseArgs(arguments, 'format');
        return py.str.fromJSON(args.format.toJSON()
            .replace(/%([A-Za-z])/g, function (m, c) {
                switch (c) {
                case 'Y': return self.year;
                case 'm': return _.str.sprintf('%02d', self.month);
                case 'd': return _.str.sprintf('%02d', self.day);
                }
                throw new Error('ValueError: No known conversion for ' + m);
            }));
    },
    __eq__: function (other) {
        return (this.year === other.year
             && this.month === other.month
             && this.day === other.day)
            ? py.True : py.False;
    },
    replace: function () {
        var args = py.PY_parseArgs(arguments, [
            ['year', py.None], ['month', py.None], ['day', py.None]
        ]);
        var params = {};
        for(var key in args) {
            if (!args.hasOwnProperty(key)) { continue; }

            var arg = args[key];
            params[key] = (arg === py.None ? this[key] : asJS(arg));
        }
        return py.PY_call(datetime.date, params);
    },
    start_of: function() {
        var args = py.PY_parseArgs(arguments, 'granularity');
        var granularity = args.granularity.toJSON();
        if (granularity === 'year') {
            return py.PY_call(datetime.date, [this.year, 1, 1]);
        } else if (granularity === 'quarter') {
            var quarter = get_quarter(this.year, this.month)[0];
            return py.PY_call(datetime.date, [quarter.year, quarter.month, quarter.day]);
        } else if (granularity === 'month') {
            return py.PY_call(datetime.date, [this.year, this.month, 1]);
        } else if (granularity === 'week') {
            var dow = get_day_of_week(this.year, this.month, this.day);
            return py.PY_call(datetime.date, [this.year, this.month, this.day - dow]);
        } else if (granularity === 'day') {
            return py.PY_call(datetime.date, [this.year, this.month, this.day]);
        } else {
            throw new Error(
                'ValueError: ' + granularity + ' is not a supported granularity, supported ' +
                ' granularities are: year, quarter, month, week and day.'
            )
        }
    },
    end_of: function () {
        var args = py.PY_parseArgs(arguments, 'granularity');
        var granularity = args.granularity.toJSON();
        if (granularity === 'year') {
            return py.PY_call(datetime.date, [this.year, 12, 31]);
        } else if (granularity === 'quarter') {
            var quarter = get_quarter(this.year, this.month)[1];
            return py.PY_call(datetime.date, [quarter.year, quarter.month, quarter.day]);
        } else if (granularity === 'month') {
            var dom = days_in_month(this.year, this.month);
            return py.PY_call(datetime.date, [this.year, this.month, dom]);
        } else if (granularity === 'week') {
            var dow = get_day_of_week(this.year, this.month, this.day);
            return py.PY_call(datetime.date, [this.year, this.month, this.day + (6 - dow)]);
        } else if (granularity === 'day') {
            return py.PY_call(datetime.date, [this.year, this.month, this.day]);
        } else {
            throw new Error(
                'ValueError: ' + granularity + ' is not a supported granularity, supported ' +
                ' granularities are: year, quarter, month, week and day.'
            )
        }
    },
    add: function() {
        var args = py.PY_parseArgs(arguments, [
            ['years', py.None], ['months', py.None], ['days', py.None],
        ]);
        return py.PY_add(this, py.PY_call(relativedelta, {
            'years': args.years,
            'months': args.months,
            'days': args.days,
        }));
    },
    subtract: function() {
        var args = py.PY_parseArgs(arguments, [
            ['years', py.None], ['months', py.None], ['days', py.None],
        ]);
        var params = {};
        for (var key in args) {
            params[key] = (args[key] === py.None ? args[key] : py.float.fromJSON(-asJS(args[key])));
        }
        return py.PY_add(this, py.PY_call(relativedelta, params));
    },
    __add__: function (other) {
        if (!py.PY_isInstance(other, datetime.timedelta)) {
            return py.NotImplemented;
        }
        var s = tmxxx(this.year, this.month, this.day + other.days);
        return datetime.date.fromJSON(s.year, s.month, s.day);
    },
    __radd__: function (other) { return this.__add__(other); },
    __sub__: function (other) {
        if (py.PY_isInstance(other, datetime.timedelta)) {
            return py.PY_add(this, py.PY_negative(other));
        }
        if (py.PY_isInstance(other, datetime.date)) {
            // FIXME: getattr and sub API methods
            return py.PY_call(datetime.timedelta, [
                py.PY_subtract(
                    py.PY_call(py.PY_getAttr(this, 'toordinal')),
                    py.PY_call(py.PY_getAttr(other, 'toordinal')))
            ]);
        }
        return py.NotImplemented;
    },
    toordinal: function () {
        return py.float.fromJSON(ymd2ord(this.year, this.month, this.day));
    },
    weekday: function () {
        return  py.float.fromJSON((this.toordinal().toJSON()+6)%7);
    },
    fromJSON: function (year, month, day) {
        return py.PY_call(datetime.date, [year, month, day]);
    },
    today: py.classmethod.fromJSON(function () {
        var d = new Date ();
        return py.PY_call(datetime.date, [
            d.getFullYear(), d.getMonth() + 1, d.getDate()]);
    }),
});

datetime.time = py.type('time', null, {
    __init__: function () {
        var zero = py.float.fromJSON(0);
        var args = py.PY_parseArgs(arguments, [
            ['hour', zero], ['minute', zero], ['second', zero], ['microsecond', zero],
            ['tzinfo', py.None]
        ]);

        for(var k in args) {
            if (!args.hasOwnProperty(k)) { continue; }
            this[k] = asJS(args[k]);
        }
    }
});

var time = py.PY_call(py.object);
time.strftime = py.PY_def.fromJSON(function () {
    var args  = py.PY_parseArgs(arguments, 'format');
    var dt_class = py.PY_getAttr(datetime, 'datetime');
    var d = py.PY_call(py.PY_getAttr(dt_class, 'utcnow'));
    return py.PY_call(py.PY_getAttr(d, 'strftime'), [args.format]);
});

var args = _.map(('year month day hour minute second '
                + 'years months weeks days hours minutes seconds '
                + 'weekday leapdays yearday nlyearday').split(' '), function (arg) {
    switch (arg) {
        case 'years':case 'months':case 'days':case 'leapdays':case 'weeks':
        case 'hours':case 'minutes':case 'seconds':
        return [arg, zero];
    case 'year':case 'month':case 'day':case 'weekday':
    case 'hour':case 'minute':case 'second':
    case 'yearday':case 'nlyearday':
        return [arg, null];
    default:
        throw new Error("Unknown relativedelta argument " + arg);
    }
});
args.unshift('*');

var _utils = {
    monthrange: function (year, month) {
        if (month < 1 || month > 12) {
            throw new Error("Illegal month " + month);
        }

        var day1 = this.weekday(year, month, 1);
        var ndays = this.mdays[month] + (month == this.February && this.isleap(year));
        return [day1, ndays];
    },
    weekday: function (year, month, day) {
        var date = py.PY_call(datetime.date, [year, month, day]);
        return py.PY_call(py.PY_getAttr(date, 'weekday'));
    },
    isleap: function (year) {
        return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
    },
    mdays: [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31],
    January: 1,
    February: 2
};

var relativedelta = py.type('relativedelta', null, {
    __init__: function () {
        this.ops = py.PY_parseArgs(arguments, args);
        this.ops.days = py.float.fromJSON(
            asJS(this.ops.days) + asJS(this.ops.weeks) * 7
        );

        var yday = zero;
        if (this.ops.nlyearday) {
            yday = this.ops.nlyearday;
        } else if (this.ops.yearday) {
            yday = this.ops.yearday;
            if (asJS(this.ops.yearday) > 59) {
                this.ops.leapdays = py.float.fromJS(-1);
            }
        }
        if (py.PY_isTrue(yday)) {
            var ydayidx = [31, 59, 90, 120, 151, 181, 212,
                           243, 273, 304, 334, 366];
            for(var idx=0; idx<ydayidx.length; ++idx) {
                var ydays = ydayidx[idx];
                if (asJS(yday) <= ydays) {
                    this.ops.month = py.float.fromJSON(idx+1);
                    if (!idx) {
                        this.ops.day = yday;
                    } else {
                        this.ops.day = py.PY_subtract(
                            yday,
                            py.float.fromJSON(ydayidx[idx-1])
                        );
                    }
                    break;
                }
            }
            if (idx === ydayidx.length) {
                throw new Error("Invalid year day (" + asJS(yday) + ")");
            }
        }
        this._fix();
    },
    _fix: function () {
        var self = this;
        var months = asJS(this.ops.months);
        if (Math.abs(months) > 11) {
            var s = months > 0 ? 1 : -1;
            divmod(months * s, 12, function (years, months) {
                self.ops.months = py.float.fromJSON(months*s);
                self.ops.years = py.float.fromJSON(
                    asJS(self.ops.years) + years*s);
            });
        }
        this._has_time = 0;
    },
    __add__: function (other) {
        if (!(py.PY_isInstance(other, datetime.date) ||
            py.PY_isInstance(other, datetime.datetime))) {
            return py.NotImplemented;
        }
        // TODO: test this whole mess
        var year = (asJS(this.ops.year) || asJS(other.year)) + asJS(this.ops.years);
        var month = asJS(this.ops.month) || asJS(other.month);
        var months;
        if (months = asJS(this.ops.months)) {
            if (Math.abs(months) < 1 || Math.abs(months) > 12) {
                throw new Error("Can only use relative months between -12 and +12");
            }
            month += months;
            if (month > 12) {
                year += 1;
                month -= 12;
            }
            if (month < 1) {
                year -= 1;
                month += 12;
            }
        }

        var day = Math.min(_utils.monthrange(year, month)[1],
                           asJS(this.ops.day) || asJS(other.day));

        var repl = {
            year: py.float.fromJSON(year),
            month: py.float.fromJSON(month),
            day: py.float.fromJSON(day)
        };

        if (py.PY_isInstance(other, datetime.datetime)) {
            repl.hour = py.float.fromJSON(asJS(this.ops.hour) || asJS(other.hour));
            repl.minute = py.float.fromJSON(asJS(this.ops.minute) || asJS(other.minute));
            repl.second = py.float.fromJSON(asJS(this.ops.second) || asJS(other.second));
        }

        var days = asJS(this.ops.days);
        if (py.PY_isTrue(this.ops.leapdays) && month > 2 && _utils.isleap(year)) {
            days += asJS(this.ops.leapdays);
        }

        var ret = py.PY_add(
            py.PY_call(py.PY_getAttr(other, 'replace'), repl),
            py.PY_call(datetime.timedelta, {
                days: py.float.fromJSON(days),
                hours: py.float.fromJSON(asJS(this.ops.hours)),
                minutes: py.float.fromJSON(asJS(this.ops.minutes)),
                seconds: py.float.fromJSON(asJS(this.ops.seconds))
            })
        );

        if (this.ops.weekday) {
            // FIXME: only handles numeric weekdays, not decorated
            var weekday = asJS(this.ops.weekday), nth = 1;
            var jumpdays = (Math.abs(nth) - 1) * 7;

            var ret_weekday = asJS(py.PY_call(py.PY_getAttr(ret, 'weekday')));
            if (nth > 0) {
                jumpdays += (7-ret_weekday+weekday) % 7;
            } else {
                jumpdays += (ret_weekday - weekday) % 7;
                jumpdays *= -1;
            }
            ret = py.PY_add(
                ret,
                py.PY_call(datetime.timedelta, {
                    days: py.float.fromJSON(jumpdays)
                })
            );
        }

        return ret;
    },
    __radd__: function (other) {
        return this.__add__(other);
    },
    __rsub__: function (other) {
        return this.__neg__().__radd__(other);
    },
    __neg__: function () {
        return py.PY_call(relativedelta, {
            years: py.PY_negative(this.ops.years),
            months: py.PY_negative(this.ops.months),
            days: py.PY_negative(this.ops.days),
            leapdays: this.ops.leapdays,
            hours: py.PY_negative(this.ops.hours),
            minutes: py.PY_negative(this.ops.minutes),
            seconds: py.PY_negative(this.ops.seconds),
            year: this.ops.year,
            month: this.ops.month,
            day: this.ops.day,
            weekday: this.ops.weekday,
            hour: this.ops.hour,
            minute: this.ops.minute,
            second: this.ops.second
        });
    }
});

py.extras = {
    datetime: datetime,
    time: time,
    relativedelta: relativedelta,
};

})(typeof exports === 'undefined' ? py : exports);
