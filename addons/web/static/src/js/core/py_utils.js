odoo.define('web.py_utils', function (require) {
"use strict";

var core = require('web.core');

var _t = core._t;
var py = window.py; // to silence linters

// recursively wraps JS objects passed into the context to attributedicts
// which jsonify back to JS objects
function wrap(value) {
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
}

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
    __len__: function () {
        return Object.keys(this._store).length;
    },
    __nonzero__: function () {
        return py.PY_size(this) > 0 ? py.True : py.False;
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
    __len__: function () {
        return this._store.length;
    },
    __nonzero__: function () {
        return py.PY_size(this) > 0 ? py.True : py.False;
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

function wrap_context(context) {
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
}

function eval_contexts(contexts, evaluation_context) {
    evaluation_context = _.extend(pycontext(), evaluation_context || {});
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
}

function eval_domains(domains, evaluation_context) {
    evaluation_context = _.extend(pycontext(), evaluation_context || {});
    var result_domain = [];
    // Normalize only if the first domain is the array ["|"] or ["!"]
    var need_normalization = (
        domains &&
        domains.length > 0 &&
        domains[0].length === 1 &&
        (domains[0][0] === "|" || domains[0][0] === "!")
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
        default:
            domain_array_to_combine = domain;
        }
        if (need_normalization) {
            domain_array_to_combine = get_normalized_domain(domain_array_to_combine);
        }
        result_domain.push.apply(result_domain, domain_array_to_combine);
    });
    return result_domain;
}

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

function eval_groupbys(contexts, evaluation_context) {
    evaluation_context = _.extend(pycontext(), evaluation_context || {});
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
}

/**
 * Returns the current local date, which means the date on the client (which can be different
 * compared to the date of the server).
 *
 * @return {datetime.date}
 */
function context_today() {
    var d = new Date();
    return py.PY_call(
        py.extras.datetime.date, [d.getFullYear(), d.getMonth() + 1, d.getDate()]);
}


function pycontext() {
    return {
        datetime: py.extras.datetime,
        context_today: context_today,
        time: py.extras.time,
        relativedelta: py.extras.relativedelta,
        current_date: py.PY_call(
            py.extras.time.strftime, [py.str.fromJSON('%Y-%m-%d')]),
    };
}

/**
 * @param {String} type "domains", "contexts" or "groupbys"
 * @param {Array} object domains or contexts to evaluate
 * @param {Object} [context] evaluation context
 */
function pyeval(type, object, context) {
    context = _.extend(pycontext(), context || {});

    //noinspection FallthroughInSwitchStatementJS
    switch(type) {
    case 'context':
    case 'contexts':
        if (type === 'context') {
            object = [object];
        }
        return eval_contexts(object, context);
    case 'domain':
    case 'domains':
        if (type === 'domain')
            object = [object];
        return eval_domains(object, context);
    case 'groupbys':
        return eval_groupbys(object, context);
    }
    throw new Error("Unknow evaluation type " + type);
}

function eval_arg(arg) {
    if (typeof arg !== 'object' || !arg.__ref) { return arg; }
    switch(arg.__ref) {
    case 'domain':
        return pyeval('domains', [arg]);
    case 'context': case 'compound_context':
        return pyeval('contexts', [arg]);
    default:
        throw new Error(_t("Unknown nonliteral type ") + ' ' + arg.__ref);
    }
}

/**
 * If args or kwargs are unevaluated contexts or domains (compound or not),
 * evaluated them in-place.
 *
 * Potentially mutates both parameters.
 *
 * @param args
 * @param kwargs
 */
function ensure_evaluated(args, kwargs) {
    for (var i=0; i<args.length; ++i) {
        args[i] = eval_arg(args[i]);
    }
    for (var k in kwargs) {
        if (!kwargs.hasOwnProperty(k)) { continue; }
        kwargs[k] = eval_arg(kwargs[k]);
    }
}

function eval_domains_and_contexts(source) {
    // see Session.eval_context in Python
    return {
        context: pyeval('contexts', source.contexts || [], source.eval_context),
        domain: pyeval('domains', source.domains, source.eval_context),
        group_by: pyeval('groupbys', source.group_by_seq || [], source.eval_context),
    };
}

function py_eval(expr, context) {
    return py.eval(expr, _.extend({}, context || {}, {"true": true, "false": false, "null": null}));
}


return {
    context: pycontext,
    ensure_evaluated: ensure_evaluated,
    eval: pyeval,
    eval_domains_and_contexts: eval_domains_and_contexts,
    py_eval: py_eval,
};

});
