/*
 * py.js helpers and setup
 */
openerp.web.pyeval = function (instance) {
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
        strftime: function () {
            var self = this;
            var args = py.PY_parseArgs(arguments, 'format');
            return py.str.fromJSON(args.format.toJSON()
                .replace(/%([A-Za-z])/g, function (m, c) {
                    switch (c) {
                    case 'Y': return self.year;
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
            var d = new Date();
            return py.PY_call(datetime.datetime,
                [d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate(),
                 d.getUTCHours(), d.getUTCMinutes(), d.getUTCSeconds(),
                 d.getUTCMilliseconds() * 1000]);
        }),
        today: py.classmethod.fromJSON(function () {
            var d = new Date();
            return py.PY_call(datetime.datetime,
                [d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate()]);
        }),
        combine: py.classmethod.fromJSON(function () {
            var args = py.PY_parseArgs(arguments, 'date time');
            return py.PY_call(datetime.datetime, [
                // FIXME: should use getattr
                args.date.year,
                args.date.month,
                args.date.day,
                args.time.hour,
                args.time.minute,
                args.time.second
            ]);
        })
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
        today: py.classmethod.fromJSON(function () {
            var d = new Date();
            return py.PY_call(
                datetime.date, [d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate()]);
        })
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
        // FIXME: needs PY_getattr
        var d = py.PY_call(datetime.__getattribute__('datetime')
                                   .__getattribute__('now'));
        var args = [].slice.call(arguments);
        return py.PY_call.apply(
            null, [d.__getattribute__('strftime')].concat(args));
    });

    var relativedelta = py.type('relativedelta', null, {
        __init__: function () {
            this.ops = py.PY_parseArgs(arguments,
                '* year month day hour minute second microsecond '
                + 'years months weeks days hours minutes secondes microseconds '
                + 'weekday leakdays yearday nlyearday');
        },
        __add__: function (other) {
            if (py.PY_call(py.isinstance, [datetime.date]) !== py.True) {
                return py.NotImplemented;
            }
            // TODO: test this whole mess
            var year = asJS(this.ops.year) || asJS(other.year);
            if (asJS(this.ops.years)) {
                year += asJS(this.ops.years);
            }

            var month = asJS(this.ops.month) || asJS(other.month);
            if (asJS(this.ops.months)) {
                month += asJS(this.ops.months);
                // FIXME: no divmod in JS?
                while (month < 1) {
                    year -= 1;
                    month += 12;
                }
                while (month > 12) {
                    year += 1;
                    month -= 12;
                }
            }

            var lastMonthDay = new Date(year, month, 0).getDate();
            var day = asJS(this.ops.day) || asJS(other.day);
            if (day > lastMonthDay) { day = lastMonthDay; }
            var days_offset = ((asJS(this.ops.weeks) || 0) * 7) + (asJS(this.ops.days) || 0);
            if (days_offset) {
                day = new Date(year, month-1, day + days_offset).getDate();
            }
            // TODO: leapdays?
            // TODO: hours, minutes, seconds? Not used in XML domains
            // TODO: weekday?
            // FIXME: use date.replace
            return py.PY_call(datetime.date, [
                py.float.fromJSON(year),
                py.float.fromJSON(month),
                py.float.fromJSON(day)
            ]);
        },
        __radd__: function (other) {
            return this.__add__(other);
        },

        __sub__: function (other) {
            if (py.PY_call(py.isinstance, [datetime.date]) !== py.True) {
                return py.NotImplemented;
            }
            // TODO: test this whole mess
            var year = asJS(this.ops.year) || asJS(other.year);
            if (asJS(this.ops.years)) {
                year -= asJS(this.ops.years);
            }

            var month = asJS(this.ops.month) || asJS(other.month);
            if (asJS(this.ops.months)) {
                month -= asJS(this.ops.months);
                // FIXME: no divmod in JS?
                while (month < 1) {
                    year -= 1;
                    month += 12;
                }
                while (month > 12) {
                    year += 1;
                    month -= 12;
                }
            }

            var lastMonthDay = new Date(year, month, 0).getDate();
            var day = asJS(this.ops.day) || asJS(other.day);
            if (day > lastMonthDay) { day = lastMonthDay; }
            var days_offset = ((asJS(this.ops.weeks) || 0) * 7) + (asJS(this.ops.days) || 0);
            if (days_offset) {
                day = new Date(year, month-1, day - days_offset).getDate();
            }
            // TODO: leapdays?
            // TODO: hours, minutes, seconds? Not used in XML domains
            // TODO: weekday?
            return py.PY_call(datetime.date, [
                py.float.fromJSON(year),
                py.float.fromJSON(month),
                py.float.fromJSON(day)
            ]);
        },
        __rsub__: function (other) {
            return this.__sub__(other);
        }
    });

    var eval_contexts = function (contexts, evaluation_context) {
        evaluation_context = evaluation_context || {};
        return _(contexts).reduce(function (result_context, ctx) {
            // __eval_context evaluations can lead to some of `contexts`'s
            // values being null, skip them as well as empty contexts
            if (_.isEmpty(ctx)) { return result_context; }
            var evaluated = ctx;
            switch(ctx.__ref) {
            case 'context':
                evaluated = py.eval(ctx.__debug, evaluation_context);
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
        }, _.extend({}, instance.session.user_context));
    };
    var eval_domains = function (domains, evaluation_context) {
        var result_domain = [];
        _(domains).each(function (domain) {
            switch(domain.__ref) {
            case 'domain':
                result_domain.push.apply(
                    result_domain, py.eval(domain.__debug, evaluation_context));
                break;
            case 'compound_domain':
                var eval_context = eval_contexts([domain.__eval_context]);
                result_domain.push.apply(
                    result_domain, eval_domains(
                        domain.__domains, _.extend(
                            {}, evaluation_context, eval_context)));
                break;
            default:
                result_domain.push.apply(result_domain, domain);
            }
        });
        return result_domain;
    };
    var eval_groupbys = function (contexts, evaluation_context) {
        var result_group = [];
        _(contexts).each(function (ctx) {
            var group;
            var evaluated = ctx;
            switch(ctx.__ref) {
            case 'context':
                evaluated = py.eval(ctx.__debug, evaluation_context);
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
        return {
            uid: py.float.fromJSON(instance.session.uid),
            datetime: datetime,
            time: time,
            relativedelta: relativedelta,
            current_date: py.PY_call(
                time.strftime, [py.str.fromJSON('%Y-%m-%d')]),
        };
    };

    /**
     * @param {String} type "domains", "contexts" or "groupbys"
     * @param {Array} object domains or contexts to evaluate
     * @param {Object} [context] evaluation context
     */
    instance.web.pyeval.eval = function (type, object, context) {
        context = _.extend(instance.web.pyeval.context(), context || {});
        context['context'] = py.dict.fromJSON(context);

        switch(type) {
        case 'contexts': return eval_contexts(object, context);
        case 'domains': return eval_domains(object, context);
        case 'groupbys': return eval_groupbys(object, context);
        }
        throw new Error("Unknow evaluation type " + type)
    };
};
