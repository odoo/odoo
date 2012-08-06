/*
 * py.js helpers and setup
 */
openerp.web.pyeval = function (instance) {
    instance.web.pyeval = {};

    var asJS = function (arg) {
        if (arg instanceof py.object) {
            return arg.toJSON();
        }
        return arg;
    };

    var datetime = new py.object();
    datetime.datetime = new py.type(function datetime() {
        throw new Error('datetime.datetime not implemented');
    });
    var date = datetime.date = new py.type(function date(y, m, d) {
        if (y instanceof Array) {
            d = y[2];
            m = y[1];
            y = y[0];
        }
        this.year = asJS(y);
        this.month = asJS(m);
        this.day = asJS(d);
    }, py.object, {
        strftime: function (args) {
            var f = asJS(args[0]), self = this;
            return new py.str(f.replace(/%([A-Za-z])/g, function (m, c) {
                switch (c) {
                case 'Y': return self.year;
                case 'm': return _.str.sprintf('%02d', self.month);
                case 'd': return _.str.sprintf('%02d', self.day);
                }
                throw new Error('ValueError: No known conversion for ' + m);
            }));
        }
    });
    date.__getattribute__ = function (name) {
        if (name === 'today') {
            return date.today;
        }
        throw new Error("AttributeError: object 'date' has no attribute '" + name +"'");
    };
    date.today = new py.def(function () {
        var d = new Date();
        return new date(d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate());
    });
    datetime.time = new py.type(function time() {
        throw new Error('datetime.time not implemented');
    });

    var time = new py.object();
    time.strftime = new py.def(function (args) {
        return date.today.__call__().strftime(args);
    });

    var relativedelta = new py.type(function relativedelta(args, kwargs) {
        if (!_.isEmpty(args)) {
            throw new Error('Extraction of relative deltas from existing datetimes not supported');
        }
        this.ops = kwargs;
    }, py.object, {
        __add__: function (other) {
            if (!(other instanceof datetime.date)) {
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
            return new datetime.date(year, month, day);
        },
        __radd__: function (other) {
            return this.__add__(other);
        },

        __sub__: function (other) {
            if (!(other instanceof datetime.date)) {
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
            return new datetime.date(year, month, day);
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
        }, _.extend({}, instance.connection.user_context));
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
                evaluated = py.eval(ctx.__debug), evaluation_context;
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
            uid: new py.float(instance.connection.uid),
            datetime: datetime,
            time: time,
            relativedelta: relativedelta,
            current_date: date.today.__call__().strftime(['%Y-%m-%d']),
        };
    };

    /**
     * @param {String} type "domains", "contexts" or "groupbys"
     * @param {Array} object domains or contexts to evaluate
     * @param {Object} [context] evaluation context
     */
    instance.web.pyeval.eval = function (type, object, context) {
        if (!context) { context = instance.web.pyeval.context()}
        switch(type) {
        case 'contexts': return eval_contexts(object, context);
        case 'domains': return eval_domains(object, context);
        case 'groupbys': return eval_groupbys(object, context);
        }
        throw new Error("Unknow evaluation type " + type)
    };
};
