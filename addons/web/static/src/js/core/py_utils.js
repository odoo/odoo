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

/**
 * Returns a timedelta object which represents the timezone offset between the
 * local timezone and the UTC time.
 *
 * This is very useful to generate datetime strings which are 'timezone'
 * dependant.  For example, we can now write this to generate the correct
 * datetime string representing "this morning in the user timezone":
 *
 * "datetime.datetime.now().replace(hour=0,minute=0,second=0) + tz_offset()).strftime('%Y-%m-%d %H:%M:%S')"
 * @returns {datetime.timedelta}
 */
function tz_offset() {
    var offset= new Date().getTimezoneOffset();
    var kwargs = {minutes: py.float.fromJSON(offset)};
    return py.PY_call(py.extras.datetime.timedelta,[],kwargs);
}


function pycontext() {
    return {
        datetime: py.extras.datetime,
        context_today: context_today,
        time: py.extras.time,
        relativedelta: py.extras.relativedelta,
        current_date: py.PY_call(
            py.extras.time.strftime, [py.str.fromJSON('%Y-%m-%d')]),
        tz_offset: tz_offset,
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

/**
 * Assemble domains into a single domains using an 'OR' or an 'AND' operator.
 *
 * .. note:
 *
 *      - this function does not evaluate anything inside the domain.  This
 *        is actually quite critical because this allows the manipulation of
 *        unevaluated (dynamic) domains.
 *      - this function gives a normalized domain as result,
 *      - applied on a list of length 1, it returns the domain normalized.
 *
 * @param {string[]} domains list of string representing domains
 * @param {"AND" | "OR"} operator used to combine domains (default "AND")
 * @returns {string} normalized domain
 */
function assembleDomains(domains, operator) {
    var ASTs = domains.map(_getPyJSAST);
    if (operator === "OR") {
        operator = py.tokenize("'|'")[0];
    } else {
        operator = py.tokenize("'&'")[0];
    }
    var result = _getPyJSAST("[]");
    var normalizedDomains = ASTs
                .filter(function (AST) {
                    return AST.first.length > 0;
                })
                .map(_normalizeDomainAST);
    if (normalizedDomains.length > 0) {
        result.first = normalizedDomains.reduce(function (acc, ast) {
            return acc.concat(ast.first);
        },
        _.times(normalizedDomains.length - 1, _.constant(operator))
        );
    }
    return _formatAST(result);
}
/**
 * Normalize a domain via its string representation.
 *
 * Note: this function does not evaluate anything inside the domain.  This is
 * actually quite critical because this allows the manipulation of unevaluated
 * (dynamic) domains.
 *
 * @param {string} domain string representing a domain
 * @returns {string} normalized domain
 */
function normalizeDomain (domain) {
    return _formatAST(_normalizeDomainAST(_getPyJSAST(domain)));
}

//--------------------------------------------------------------------------
// Private
//--------------------------------------------------------------------------

// Binding power for prefix operator is not accessible in the AST generated by
// py.js, so we have to hardcode some values here
var BINDING_POWERS = {
    or: 30,
    and: 40,
    not: 50,
};

/**
 * @private
 * Convert a python AST (generated by py.js) to a string form, which should
 * represent the same AST.
 *
 * @param {Object} ast a valid AST obtained by py.js, which represent a python
 *   expression
 * @param {integer} [lbp=0] a binding power. This is necessary to be able to
 *   format sub expressions: the + sub expression in "3 * (a + 2)" should be
 *   formatted with parenthesis, because its binding power is lower than the
 *   binding power of *.
 * @returns {string}
 */
function _formatAST(ast, lbp) {
    lbp = lbp || 0;
    switch (ast.id) {
        // basic values
        case "(number)":
            return String(ast.value);
        case "(string)":
            // ast.value is a string that may contain a mix of single and double quotes.
            // But we need to return a string that represents the string ast.value.
            // We use for that JSON.stringify. It will return a string with quotes correctly
            // escaped. For instance, for x = `""` JSON.stringify(x) is `"\"\""`.
            // But this means that if we pass several times here, escapes will be
            // done again and again, leading to a profusion of backslashes that we don't want.
            // For fun consider y = `\\` and y = JSON.stringify(y).
            // This is why we first deescape particular characters in ast.value.
            return JSON.stringify(ast.value.replace(/(\\(['"\\]))/g,"\$2"));
        case "(constant)":
            return ast.value;
        case "(name)":
            return ast.value;
        case "[":
            if (ast.second) {
                // read a value in a dictionary: d['a']
                return _formatAST(ast.first) + '[' + _formatAST(ast.second) + ']';
            } else {
                // list: [1, 2]
                var values = ast.first.map(_formatAST);
                return '[' + values.join(', ') + ']';
            }
        case "{":
            var keyValues = ast.first.map(function (kv) {
                return _formatAST(kv[0]) + ': ' + _formatAST(kv[1]);
            });
            return '{' + keyValues.join(', ') + '}';

        // relations
        case "=":
            return _formatAST(ast.first) + ' ' + ast.id + ' ' + _formatAST(ast.second);
        // operators
        case "-":
        case "+":
        case "~":
        case "*":
        case "**":
        case "%":
        case "//":
        case "and":
        case "or":
            if (ast.second) {
                // infix
                var r = _formatAST(ast.first, ast.lbp) + ' ' + ast.id + ' ' + _formatAST(ast.second, ast.lbp);
                if (ast.lbp < lbp) {
                    r = '(' + r + ')';
                }
                return r;
            }
            // prefix
            // real lbp is not accessible, it is inside a closure
            var actualBP = BINDING_POWERS[ast.id] || 130;
            return ast.id + _formatAST(ast.first, actualBP);
        case ".":
            return _formatAST(ast.first, ast.lbp) + '.' + _formatAST(ast.second);
        case "not":
            return "not " + _formatAST(ast.first);
        case "(comparator)":
            var operator = ast.operators[0];
            return _formatAST(ast.expressions[0]) + ' ' + operator + ' ' + _formatAST(ast.expressions[1]);

        // function call
        case "(":
            if (ast.second) {
                // this is a function call: f(a, b)
                return _formatAST(ast.first) + '(' + ast.second.map(_formatAST).join(', ') + ')';
            } else {
                // this is a tuple
                return '(' + ast.first.map(_formatAST).join(', ') + ')';
            }
    }
    throw new Error("Unimplemented python construct");
}

/**
 * @private
 * Get the PyJs AST representing a domain starting from is string representation
 *
 * @param {string} domain string representing a domain
 * @returns {PyJS AST} PyJS AST representation of domain
 */
function _getPyJSAST(domain) {
    return py.parse(py.tokenize(domain));
}

/**
 * @private
 *
 * Normalize a domain, at the level of the AST.
 *
 * Note: this function does not evaluate anything inside the domain.  This is
 * actually quite critical because this allows the manipulation of unevaluated
 * (dynamic) domains.
 *
 * @param {PyJS AST} domain valid AST representing a domain
 * @returns {PyJS AST} normalized domain AST
 */
function _normalizeDomainAST(domain) {
    var expected = 1;
    for (var i = 0; i < domain.first.length; i++) {
        var value = domain.first[i].value;
        if (value === '&' || value === '|') {
            expected++;
        } else if (value !== '!') {
            expected--;
        }
    }
    var andOperator = py.tokenize("'&'")[0];

    if (expected < 0) {
        domain.first.unshift.apply(domain.first, _.times(Math.abs(expected), _.constant(andOperator)));
    }

    return domain;
}

return {
    context: pycontext,
    ensure_evaluated: ensure_evaluated,
    eval: pyeval,
    eval_domains_and_contexts: eval_domains_and_contexts,
    py_eval: py_eval,
    normalizeDomain: normalizeDomain,
    assembleDomains: assembleDomains,
    _getPyJSAST: _getPyJSAST,
    _formatAST: _formatAST,
    _normalizeDomainAST: _normalizeDomainAST,
};
});
