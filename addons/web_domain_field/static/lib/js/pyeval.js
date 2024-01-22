odoo.define('web.domain_field', function (require) {
    "use strict";

    var py_utils = require('web.py_utils');
    var session = require('web.session');


    var original_pyeval = py_utils.eval;
    var py = window.py;

    /** Copied from py_utils and not modified but required since not publicly
    exposed by web.py_utils**/

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
            // Don't add a test case like ``val === undefined``
            // this is intended to prevent letting crap pass
            // on the context without even knowing it.
            // If you face an issue from here, try to sanitize
            // the context upstream instead
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

   function ensure_evaluated(args, kwargs) {
        for (var i=0; i<args.length; ++i) {
            args[i] = eval_arg(args[i]);
        }
        for (var k in kwargs) {
            if (!kwargs.hasOwnProperty(k)) { continue; }
            kwargs[k] = eval_arg(kwargs[k]);
        }
    }
    /** End of unmodified methods copied from pyeval **/

    // We need to override the original method to be able to call our
    // Specialized version of pyeval for domain fields
    function eval_arg (arg) {
        if (typeof arg !== 'object' || !arg.__ref) {
            return arg;
        }
        switch (arg.__ref) {
        case 'domain': case 'compound_domain':
            return domain_field_pyeval('domains', [arg]);
        case 'context': case 'compound_context':
            return original_pyeval('contexts', [arg]);
        default:
            throw new Error(_t("Unknown nonliteral type ") + ' ' + arg.__ref);
        }
    }

    // Override eval_domains to add 3 lines in order to be able to use a field
    // value as domain
    function eval_domains(domains, evaluation_context) {
        evaluation_context = _.extend(py_utils.context(), evaluation_context || {});
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
                // Modified part or the original method
                if (domain in evaluation_context) {
                    var fail_parse_domain = false;
                    try {
                        var domain_parse = $.parseJSON(evaluation_context[domain]);
                        console.warn("`web_domain_field is deprecated. If you want to use this functionality you can assign a unserialised domain to a fields.Binary");
                    } catch (e) {
                        fail_parse_domain = true;
                    }
                    if (!fail_parse_domain) {
                        result_domain.push.apply(result_domain, domain_parse);
                        return;
                    }
                }
                // End of modifications

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


    // Override pyeval in order to call our specialized implementation of
    // eval_domains
    function domain_field_pyeval (type, object, context, options) {
        switch (type) {
        case 'domain':
        case 'domains':
            if (type === 'domain') {
                object = [object];
            }
            return eval_domains(object, context);
        default:
            return original_pyeval(type, object, context, options);
        }
    }

    function eval_domains_and_contexts(source) {
        // see Session.eval_context in Python
        return {
            context: domain_field_pyeval('contexts', source.contexts || [], source.eval_context),
            domain: domain_field_pyeval('domains', source.domains, source.eval_context),
            group_by: domain_field_pyeval('groupbys', source.group_by_seq || [], source.eval_context),
        };
    }


    py_utils.eval = domain_field_pyeval;
    py_utils.ensure_evaluated = ensure_evaluated;
    py_utils.eval_domains_and_contexts = eval_domains_and_contexts;

});
