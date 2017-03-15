/*
 * py.js helpers and setup
 */
(function() {

    var instance = openerp;

    instance.web.pyeval = {};

    var obj = function () {};
    obj.prototype = py.object;
    var asJS = function (arg) {
        if (arg instanceof obj) {
            return arg.toJSON();
        }
        return arg;
    };

    var datetime = py.PY_call(py.object);

    /**
     * computes (Math.floor(a/b), a%b and passes that to the callback.
     *
     * returns the callback's result
     */
    var divmod = function (a, b, fn) {
        var mod = a%b;
        // in python, sign(a % b) === sign(b). Not in JS. If wrong side, add a
        // round of b
        if (mod > 0 && b < 0 || mod < 0 && b > 0) {
            mod += b;
        }
        return fn(Math.floor(a/b), mod);
    };
    /**
     * Passes the fractional and integer parts of x to the callback, returns
     * the callback's result
     */
    var modf = function (x, fn) {
        var mod = x%1;
        if (mod < 0) {
            mod += 1;
        }
        return fn(mod, Math.floor(x));
    };
    var zero = py.float.fromJSON(0);

    // Port from pypy/lib_pypy/datetime.py
    var DAYS_IN_MONTH = [null, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    var DAYS_BEFORE_MONTH = [null];
    var dbm = 0;
    for (var i=1; i<DAYS_IN_MONTH.length; ++i) {
        DAYS_BEFORE_MONTH.push(dbm);
        dbm += DAYS_IN_MONTH[i];
    }
    var is_leap = function (year) {
        return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
    };
    var days_before_year = function (year) {
        var y = year - 1;
        return y*365 + Math.floor(y/4) - Math.floor(y/100) + Math.floor(y/400);
    };
    var days_in_month = function (year, month) {
        if (month === 2 && is_leap(year)) {
            return 29;
        }
        return DAYS_IN_MONTH[month];
    };
    var days_before_month = function (year, month) {
        var post_leap_feb = month > 2 && is_leap(year);
        return DAYS_BEFORE_MONTH[month]
             + (post_leap_feb ? 1 : 0);
    };
    var ymd2ord = function (year, month, day) {
        var dim = days_in_month(year, month);
        if (!(1 <= day && day <= dim)) {
            throw new Error("ValueError: day must be in 1.." + dim);
        }
        return days_before_year(year)
             + days_before_month(year, month)
             + day;
    };
    var DI400Y = days_before_year(401);
    var DI100Y = days_before_year(101);
    var DI4Y = days_before_year(5);
    var assert = function (bool) {
        if (!bool) {
            throw new Error("AssertionError");
        }
    };
    var ord2ymd = function (n) {
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
    };

    /**
     * Converts the stuff passed in into a valid date, applying overflows as needed
     */
    var tmxxx = function (year, month, day, hour, minute, second, microsecond) {
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
    };
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
        now: py.classmethod.fromJSON(function () {
            var d = new Date;
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
            var d = new Date;
            return py.PY_call(datetime.date, [
                d.getFullYear(), d.getMonth() + 1, d.getDate()]);
        }),
    });
    /**
        Returns the current local date, which means the date on the client (which can be different
        compared to the date of the server).

        @return {datetime.date}
    */
    var context_today = function() {
        var d = new Date();
        return py.PY_call(
            datetime.date, [d.getFullYear(), d.getMonth() + 1, d.getDate()]);
    };
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

    var args = _.map(('year month day '
                    + 'years months weeks days '
                    + 'weekday leapdays yearday nlyearday').split(' '), function (arg) {
        switch (arg) {
        case 'years':case 'months':case 'days':case 'leapdays':case 'weeks':
            return [arg, zero];
        case 'year':case 'month':case 'day':case 'weekday':
        case 'yearday':case 'nlyearday':
            return [arg, null];
        default:
            throw new Error("Unknown relativedelta argument " + arg);
        }
    });
    args.unshift('*');
    var utils = {
        divmod: function (x, y) {
            var rem = x % y;
            return {
                div: (x - rem) / y,
                mod: rem
            };
        },
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
            return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0)
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
            var months = asJS(this.ops.months);
            if (Math.abs(months) > 11) {
                var s = months > 0 ? 1 : -1;
                var r = utils.divmod(months * s, 12);
                this.ops.months = py.float.fromJSON(r.mod*s);
                this.ops.years = py.float.fromJSON(
                    asJS(this.ops.years) + r.div*s);
            }
            this._has_time = 0;
        },
        __add__: function (other) {
            if (!py.PY_isInstance(other, datetime.date)) {
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

            var day = Math.min(utils.monthrange(year, month)[1],
                               asJS(this.ops.day) || asJS(other.day));

            var repl = {
                year: py.float.fromJSON(year),
                month: py.float.fromJSON(month),
                day: py.float.fromJSON(day)
            };

            var days = asJS(this.ops.days);
            if (py.PY_isTrue(this.ops.leapdays) && month > 2 && utils.isleap(year)) {
                days += asJS(this.ops.leapdays);
            }

            var ret = py.PY_add(
                py.PY_call(py.PY_getAttr(other, 'replace'), repl),
                py.PY_call(datetime.timedelta, {
                    days: py.float.fromJSON(days)
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
                year: this.ops.year,
                month: this.ops.month,
                day: this.ops.day,
                weekday: this.ops.weekday
            });
        }
    });

    // recursively wraps JS objects passed into the context to attributedicts
    // which jsonify back to JS objects
    var wrap = function (value) {
        if (value === null) { return py.None; }

        switch (typeof value) {
        case 'undefined': throw new Error("No conversion for undefined");
        case 'boolean': return py.bool.fromJSON(value);
        case 'number': return py.float.fromJSON(value);
        case 'string': return py.str.fromJSON(value);
        }

        switch(value.constructor) {
        case Object: return wrapping_dict.fromJSON(value);
        case Array: return wrapping_list.fromJSON(value);
        }

        throw new Error("ValueError: unable to wrap " + value);
    };
    var wrapping_dict = py.type('wrapping_dict', null, {
        __init__: function () {
            this._store = {};
        },
        __getitem__: function (key) {
            var k = key.toJSON();
            if (!(k in this._store)) {
                throw new Error("KeyError: '" + k + "'");
            }
            return wrap(this._store[k]);
        },
        __getattr__: function (key) {
            return this.__getitem__(py.str.fromJSON(key));
        },
        get: function () {
            var args = py.PY_parseArgs(arguments, ['k', ['d', py.None]]);

            if (!(args.k.toJSON() in this._store)) { return args.d; }
            return this.__getitem__(args.k);
        },
        fromJSON: function (d) {
            var instance = py.PY_call(wrapping_dict);
            instance._store = d;
            return instance;
        },
        toJSON: function () {
            return this._store;
        },
    });
    var wrapping_list = py.type('wrapping_list', null, {
        __init__: function () {
            this._store = [];
        },
        __getitem__: function (index) {
            return wrap(this._store[index.toJSON()]);
        },
        fromJSON: function (ar) {
            var instance = py.PY_call(wrapping_list);
            instance._store = ar;
            return instance;
        },
        toJSON: function () {
            return this._store;
        },
    });
    var wrap_context = function (context) {
        for (var k in context) {
            if (!context.hasOwnProperty(k)) { continue; }
            var val = context[k];

            if (val === null) { continue; }
            if (val.constructor === Array) {
                context[k] = wrapping_list.fromJSON(val);
            } else if (val.constructor === Object
                       && !py.PY_isInstance(val, py.object)) {
                context[k] = wrapping_dict.fromJSON(val);
            }
        }
        return context;
    };

    var eval_contexts = function (contexts, evaluation_context) {
        evaluation_context = _.extend(instance.web.pyeval.context(), evaluation_context || {});
        return _(contexts).reduce(function (result_context, ctx) {
            // __eval_context evaluations can lead to some of `contexts`'s
            // values being null, skip them as well as empty contexts
            if (_.isEmpty(ctx)) { return result_context; }
            if (_.isString(ctx)) {
                // wrap raw strings in context
                ctx = { __ref: 'context', __debug: ctx };
            }
            var evaluated = ctx;
            switch(ctx.__ref) {
            case 'context':
                evaluation_context.context = evaluation_context;
                evaluated = py.eval(ctx.__debug, wrap_context(evaluation_context));
                break;
            case 'compound_context':
                var eval_context = eval_contexts([ctx.__eval_context]);
                evaluated = eval_contexts(
                    ctx.__contexts, _.extend({}, evaluation_context, eval_context));
                break;
            }
            // add newly evaluated context to evaluation context for following
            // siblings
            _.extend(evaluation_context, evaluated);
            return _.extend(result_context, evaluated);
        }, {});
    };
    var eval_domains = function (domains, evaluation_context) {
        evaluation_context = _.extend(instance.web.pyeval.context(), evaluation_context || {});
        var result_domain = [];
        // Normalize only if the first domain is the array ["|"] or ["!"]
        var need_normalization = (
            domains.length > 0
            && domains[0].length === 1
            && (domains[0][0] === "|" || domains[0][0] === "!")
        );
        _(domains).each(function (domain) {
            if (_.isString(domain)) {
                // wrap raw strings in domain
                domain = { __ref: 'domain', __debug: domain };
            }
            var domain_array_to_combine;
            switch(domain.__ref) {
            case 'domain':
                evaluation_context.context = evaluation_context;
                domain_array_to_combine = py.eval(domain.__debug, wrap_context(evaluation_context));
                break;
            case 'compound_domain':
                var eval_context = eval_contexts([domain.__eval_context]);
                domain_array_to_combine = eval_domains(
                    domain.__domains,
                    _.extend({}, evaluation_context, eval_context)
                );
                break;
            default:
                domain_array_to_combine = domain;
            }
            if (need_normalization) {
                domain_array_to_combine = get_normalized_domain(domain_array_to_combine);
            }
            result_domain.push.apply(result_domain, domain_array_to_combine);
        });
        return result_domain;

        /**
         * Returns a normalized copy of the given domain array. Normalization is
         * is making the implicit "&" at the start of the domain explicit, e.g.
         * [A, B, C] would become ["&", "&", A, B, C].
         *
         * @param {Array} domain_array
         * @returns {Array} normalized copy of the given array
         */
        function get_normalized_domain(domain_array) {
            var expected = 1; // Holds the number of expected domain expressions
            _.each(domain_array, function (item) {
                if (item === "&" || item === "|") {
                    expected++;
                } else if (item !== "!") {
                    expected--;
                }
            });
            var new_explicit_ands = _.times(-expected, _.constant("&"));
            return new_explicit_ands.concat(domain_array);
        }
    };
    var eval_groupbys = function (contexts, evaluation_context) {
        evaluation_context = _.extend(instance.web.pyeval.context(), evaluation_context || {});
        var result_group = [];
        _(contexts).each(function (ctx) {
            if (_.isString(ctx)) {
                // wrap raw strings in context
                ctx = { __ref: 'context', __debug: ctx };
            }
            var group;
            var evaluated = ctx;
            switch(ctx.__ref) {
            case 'context':
                evaluation_context.context = evaluation_context;
                evaluated = py.eval(ctx.__debug, wrap_context(evaluation_context));
                break;
            case 'compound_context':
                var eval_context = eval_contexts([ctx.__eval_context]);
                evaluated = eval_contexts(
                    ctx.__contexts, _.extend({}, evaluation_context, eval_context));
                break;
            }
            group = evaluated.group_by;
            if (!group) { return; }
            if (typeof group === 'string') {
                result_group.push(group);
            } else if (group instanceof Array) {
                result_group.push.apply(result_group, group);
            } else {
                throw new Error('Got invalid groupby {{'
                        + JSON.stringify(group) + '}}');
            }
            _.extend(evaluation_context, evaluated);
        });
        return result_group;
    };

    instance.web.pyeval.context = function () {
        return _.extend({
            datetime: datetime,
            context_today: context_today,
            time: time,
            relativedelta: relativedelta,
            current_date: py.PY_call(
                time.strftime, [py.str.fromJSON('%Y-%m-%d')]),
        }, instance.session.user_context);
    };

    /**
     * @param {String} type "domains", "contexts" or "groupbys"
     * @param {Array} object domains or contexts to evaluate
     * @param {Object} [context] evaluation context
     */
    instance.web.pyeval.eval = function (type, object, context, options) {
        options = options || {};
        context = _.extend(instance.web.pyeval.context(), context || {});

        //noinspection FallthroughInSwitchStatementJS
        switch(type) {
        case 'context':
        case 'contexts':
            if (type === 'context')
                object = [object];
            return eval_contexts((options.no_user_context ? [] : [instance.session.user_context]).concat(object), context);
        case 'domain':
        case 'domains':
            if (type === 'domain')
                object = [object];
            return eval_domains(object, context);
        case 'groupbys':
            return eval_groupbys(object, context);
        }
        throw new Error("Unknow evaluation type " + type);
    };

    var eval_arg = function (arg) {
        if (typeof arg !== 'object' || !arg.__ref) { return arg; }
        switch(arg.__ref) {
        case 'domain': case 'compound_domain':
            return instance.web.pyeval.eval('domains', [arg]);
        case 'context': case 'compound_context':
            return instance.web.pyeval.eval('contexts', [arg]);
        default:
            throw new Error(instance.web._t("Unknown nonliteral type " + arg.__ref));
        }
    };
    /**
     * If args or kwargs are unevaluated contexts or domains (compound or not),
     * evaluated them in-place.
     *
     * Potentially mutates both parameters.
     *
     * @param args
     * @param kwargs
     */
    instance.web.pyeval.ensure_evaluated = function (args, kwargs) {
        for (var i=0; i<args.length; ++i) {
            args[i] = eval_arg(args[i]);
        }
        for (var k in kwargs) {
            if (!kwargs.hasOwnProperty(k)) { continue; }
            kwargs[k] = eval_arg(kwargs[k]);
        }
    };
    instance.web.pyeval.eval_domains_and_contexts = function (source) {
        return new $.Deferred(function (d) {setTimeout(function () {
            var result;
            try {
                result = instance.web.pyeval.sync_eval_domains_and_contexts(source);
            }
            catch (e) {
                result = { error: {
                    code: 400,
                    message: instance.web._t("Evaluation Error"),
                    data: {
                        type: 'local_exception',
                        debug: _.str.sprintf(
                                instance.web._t("Local evaluation failure\n%s\n\n%s"),
                                e.message, JSON.stringify(source))
                    }
                }};
            }
            d.resolve(result);
        }, 0); });
    };
    instance.web.pyeval.sync_eval_domains_and_contexts = function (source) {
        var contexts = ([instance.session.user_context] || []).concat(source.contexts);
        // see Session.eval_context in Python
        return {
            context: instance.web.pyeval.eval('contexts', contexts),
            domain: instance.web.pyeval.eval('domains', source.domains),
            group_by: instance.web.pyeval.eval('groupbys', source.group_by_seq || [])
        };
    };
})();
