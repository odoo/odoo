odoo.define("web.Domain", function (require) {
"use strict";

var collections = require("web.collections");
var pyUtils = require("web.py_utils");
var py = window.py; // look py.js

/**
 * The Domain Class allows to work with a domain as a tree and provides tools
 * to manipulate array and string representations of domains.
 */
var Domain = collections.Tree.extend({
    /**
     * @constructor
     * @param {string|Array|boolean|undefined} domain
     *        The given domain can be:
     *            * a string representation of the Python prefix-array
     *              representation of the domain.
     *            * a JS prefix-array representation of the domain.
     *            * a boolean where the "true" domain match all records and the
     *              "false" domain does not match any records.
     *            * undefined, considered as the false boolean.
     *            * a number, considered as true except 0 considered as false.
     * @param {Object} [evalContext] - in case the given domain is a string, an
     *                               evaluation context might be needed
     */
    init: function (domain, evalContext) {
        this._super.apply(this, arguments);
        if (_.isArray(domain) || _.isString(domain)) {
            this._parse(this.normalizeArray(_.clone(this.stringToArray(domain, evalContext))));
        } else {
            this._data = !!domain;
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Evaluates the domain with a set of values.
     *
     * @param {Object} values - a mapping {fieldName -> fieldValue} (note: all
     *                        the fields used in the domain should be given a
     *                        value otherwise the computation will break)
     * @returns {boolean}
     */
    compute: function (values) {
        if (this._data === true || this._data === false) {
            // The domain is a always-true or a always-false domain
            return this._data;
        } else if (_.isArray(this._data)) {
            // The domain is a [name, operator, value] entity
            // First check if we have the field value in the field values set
            // and if the first part of the domain contains 'parent.field'
            // get the value from the parent record.
            var isParentField = false;
            var fieldName = this._data[0];
            // We split the domain first part and check if it's a match
            // for the syntax 'parent.field'.
            var parentField = this._data[0].split('.');
            if ('parent' in values && parentField.length === 2) {
                fieldName = parentField[1];
                isParentField = parentField[0] === 'parent' &&
                    fieldName in values.parent;
            }
            if (!(this._data[0] in values) && !(isParentField)) {
                throw new Error(_.str.sprintf(
                    "Unknown field %s in domain",
                    this._data[0]
                ));
            }
            var fieldValue;
            if (!isParentField) {
                fieldValue = values[fieldName];
            } else {
                fieldValue = values.parent[fieldName];
            }

            switch (this._data[1]) {
                case "=":
                case "==":
                    return _.isEqual(fieldValue, this._data[2]);
                case "!=":
                case "<>":
                    return !_.isEqual(fieldValue, this._data[2]);
                case "<":
                    return (fieldValue < this._data[2]);
                case ">":
                    return (fieldValue > this._data[2]);
                case "<=":
                    return (fieldValue <= this._data[2]);
                case ">=":
                    return (fieldValue >= this._data[2]);
                case "in":
                    return _.intersection(
                        _.isArray(this._data[2]) ? this._data[2] : [this._data[2]],
                        _.isArray(fieldValue) ? fieldValue : [fieldValue],
                    ).length !== 0;;
                case "not in":
                    return _.intersection(
                        _.isArray(this._data[2]) ? this._data[2] : [this._data[2]],
                        _.isArray(fieldValue) ? fieldValue : [fieldValue],
                    ).length === 0;
                case "like":
                    return (fieldValue.toLowerCase().indexOf(this._data[2].toLowerCase()) >= 0);
                case "=like":
                    var regExp = new RegExp(this._data[2].toLowerCase().replace(/([.\[\]\{\}\+\*])/g, '\\\$1').replace(/%/g, '.*'));
                    return regExp.test(fieldValue.toLowerCase());
                case "ilike":
                    return (fieldValue.indexOf(this._data[2]) >= 0);
                case "=ilike":
                    return new RegExp(this._data[2].replace(/%/g, '.*'), 'i').test(fieldValue);
                default:
                    throw new Error(_.str.sprintf(
                        "Domain %s uses an unsupported operator",
                        this._data
                    ));
            }
        } else { // The domain is a set of [name, operator, value] entitie(s)
            switch (this._data) {
                case "&":
                    return _.every(this._children, function (child) {
                        return child.compute(values);
                    });
                case "|":
                    return _.some(this._children, function (child) {
                        return child.compute(values);
                    });
                case "!":
                    return !this._children[0].compute(values);
            }
        }
    },
    /**
     * Return the JS prefix-array representation of this domain. Note that all
     * domains that use the "false" domain cannot be represented as such.
     *
     * @returns {Array} JS prefix-array representation of this domain
     */
    toArray: function () {
        if (this._data === false) {
            throw new Error("'false' domain cannot be converted to array");
        } else if (this._data === true) {
            return [];
        } else {
            var arr = [this._data];
            return arr.concat.apply(arr, _.map(this._children, function (child) {
                return child.toArray();
            }));
        }
    },
    /**
     * @returns {string} representation of the Python prefix-array
     *                   representation of the domain
     */
    toString: function () {
        return Domain.prototype.arrayToString(this.toArray());
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Initializes the tree representation of the domain according to its given
     * JS prefix-array representation. Note: the given array is considered
     * already normalized.
     *
     * @private
     * @param {Array} domain - normalized JS prefix-array representation of
     *                       the domain
     */
    _parse: function (domain) {
        this._data = (domain.length === 0 ? true : domain[0]);
        if (domain.length <= 1) return;

        var expected = 1;
        for (var i = 1 ; i < domain.length ; i++) {
            if (domain[i] === "&" || domain[i] === "|") {
                expected++;
            } else if (domain[i] !== "!") {
                expected--;
            }

            if (!expected) {
                i++;
                this._addSubdomain(domain.slice(1, i));
                this._addSubdomain(domain.slice(i));
                break;
            }
        }
    },

    /**
     * Adds a domain as a child (e.g. if the current domain is ["|", A, B],
     * using this method with a ["&", C, D] domain will result in a
     * ["|", "|", A, B, "&", C, D]).
     * Note: the internal tree representation is automatically simplified.
     *
     * @param {Array} domain - normalized JS prefix-array representation of a
     *                       domain to add
     */
    _addSubdomain: function (domain) {
        if (!domain.length) return;
        var subdomain = new Domain(domain);

        if (!subdomain._children.length || subdomain._data !== this._data) {
            this._children.push(subdomain);
        } else {
            var self = this;
            _.each(subdomain._children, function (childDomain) {
                self._children.push(childDomain);
            });
        }
    },

    //--------------------------------------------------------------------------
    // Static
    //--------------------------------------------------------------------------

    /**
     * Converts JS prefix-array representation of a domain to a string
     * representation of the Python prefix-array representation of this domain.
     *
     * @static
     * @param {Array|string} domain
     * @returns {string}
     */
    arrayToString: function (domain) {
        if (_.isString(domain)) return domain;
        return JSON.stringify(domain || [])
            .replace(/null/g, "None")
            .replace(/false/g, "False")
            .replace(/true/g, "True");
    },
    /*
     * @param {string} fieldName
     * @param {string} period
     * @param {string} type ('date' or 'datetime')
     * @param {string} comparisonPeriod
     * @returns {string} a domain in string form
     */
    constructDomain: function (fieldName, period, type, comparisonPeriod) {
        var leftBoundaryParams, rightBoundaryParams;
        var offsetPeriodParams;
        function makeInterval () {
            switch (comparisonPeriod) {
                case 'previous_period':
                    _.each(offsetPeriodParams, function (value, key) {
                        if (!leftBoundaryParams[key] ||_.isNumber(leftBoundaryParams[key])) {
                            leftBoundaryParams[key] = value + (leftBoundaryParams[key] || 0);
                        } else {
                            leftBoundaryParams[key] = value + ' + ' + leftBoundaryParams[key];
                        }
                        if (!rightBoundaryParams[key] || _.isNumber(rightBoundaryParams[key])) {
                            rightBoundaryParams[key] = value + (rightBoundaryParams[key] || 0);
                        } else {
                            rightBoundaryParams[key] = value + ' + ' + rightBoundaryParams[key];
                        }
                    });
                    break;
                case 'previous_year':
                    leftBoundaryParams.years = leftBoundaryParams.years ? leftBoundaryParams.years - 1 : -1;
                    rightBoundaryParams.years = rightBoundaryParams.years ? rightBoundaryParams.years - 1 : -1;
                  break;
            }

            var stringifyParams = function (value, key) {
                return key + '=' + value;
            };
            var leftBoundaryStringifyParams = _.map(leftBoundaryParams, stringifyParams).join(', ');
            var rightBoundaryStringifyParams = _.map(rightBoundaryParams, stringifyParams).join(', ');

            if (type === 'date') {
                return "['&'," +
                    "('" + fieldName + "', '>=', (context_today() + relativedelta(" + leftBoundaryStringifyParams + ")).strftime('%Y-%m-%d'))," +
                    "('" + fieldName + "', '<', (context_today() + relativedelta(" + rightBoundaryStringifyParams + ")).strftime('%Y-%m-%d'))"+
                    "]";
            }
            else {
                return "['&'," +
                    "('" + fieldName + "', '>=', " +
                    "(datetime.datetime.combine(context_today() + relativedelta(" + leftBoundaryStringifyParams + "), datetime.time(0,0,0)).to_utc()).strftime('%Y-%m-%d %H:%M:%S'))," +
                    "('" + fieldName + "', '<', " +
                    "(datetime.datetime.combine(context_today() + relativedelta(" + rightBoundaryStringifyParams + "), datetime.time(0,0,0)).to_utc()).strftime('%Y-%m-%d %H:%M:%S'))"+
                    "]";
            }
        }
        switch (period) {
            case 'today':
                leftBoundaryParams = {};
                rightBoundaryParams = {days: 1};
                offsetPeriodParams = {days: -1};
                return makeInterval();
            case 'this_week':
                leftBoundaryParams = {weeks: -1, days: 1, weekday: 0};
                rightBoundaryParams = {days: 1, weekday: 0};
                offsetPeriodParams = {weeks: -1};
                return makeInterval();
            case 'this_month':
                leftBoundaryParams = {day: 1};
                rightBoundaryParams = {day: 1, months: 1};
                offsetPeriodParams = {months: -1};
                return makeInterval();
            case 'this_quarter':
                leftBoundaryParams = {months: '- (context_today().month - 1) % 3', day: 1};
                rightBoundaryParams = {months: '3 - (context_today().month - 1) % 3', day: 1};
                offsetPeriodParams = {months: -3};
                return makeInterval();
            case 'this_year':
                leftBoundaryParams = {month: 1, day: 1};
                rightBoundaryParams = {month: 1, day: 1, years: 1};
                offsetPeriodParams = {years: -1};
                return makeInterval();
            case 'yesterday':
                leftBoundaryParams = {days: -1};
                rightBoundaryParams = {};
                offsetPeriodParams = {days: -1};
                return makeInterval();
            case 'last_week':
                leftBoundaryParams = {weeks: -2, days: 1, weekday: 0};
                rightBoundaryParams = {weeks: -1, days: 1, weekday: 0};
                offsetPeriodParams = {weeks: -1};
                return makeInterval();
            case 'last_month':
                leftBoundaryParams = {months: -1, day: 1};
                rightBoundaryParams = {day: 1};
                offsetPeriodParams = {months: -1};
                return makeInterval();
            case 'last_quarter':
                leftBoundaryParams = {months: '- 3 - (context_today().month - 1) % 3', day: 1};
                rightBoundaryParams = {months: '- (context_today().month - 1) % 3', day: 1};
                offsetPeriodParams = {months: -3};
                return makeInterval();
            case 'last_year':
                leftBoundaryParams = {month: 1, day: 1, years: -1};
                rightBoundaryParams = {month: 1, day: 1};
                offsetPeriodParams = {years: -1};
                return makeInterval();
            case 'last_7_days':
                leftBoundaryParams = {days: -7};
                rightBoundaryParams = {};
                offsetPeriodParams = {days: -7};
                return makeInterval();
            case 'last_30_days':
                leftBoundaryParams = {days: -30};
                rightBoundaryParams = {};
                offsetPeriodParams = {days: -30};
                return makeInterval();
            case 'last_365_days':
                leftBoundaryParams = {days: -365};
                rightBoundaryParams = {};
                offsetPeriodParams = {days: -365};
                return makeInterval();
            case 'last_5_years':
                leftBoundaryParams = {years: -5};
                rightBoundaryParams = {};
                offsetPeriodParams = {years: -5};
                return makeInterval();
        }
    },
    /**
     * Converts a string representation of the Python prefix-array
     * representation of a domain to a JS prefix-array representation of this
     * domain.
     *
     * @static
     * @param {string|Array} domain
     * @param {Object} [evalContext]
     * @returns {Array}
     */
    stringToArray: function (domain, evalContext) {
        if (!_.isString(domain)) return _.clone(domain);
        return pyUtils.eval("domain", domain ? domain.replace(/%%/g, '%') : "[]", evalContext);
    },
    /**
     * Makes implicit "&" operators explicit in the given JS prefix-array
     * representation of domain (e.g [A, B] -> ["&", A, B])
     *
     * @static
     * @param {Array} domain - the JS prefix-array representation of the domain
     *                       to normalize (! will be normalized in-place)
     * @returns {Array} the normalized JS prefix-array representation of the
     *                  given domain
     */
    normalizeArray: function (domain) {
        var expected = 1;
        _.each(domain, function (item) {
            if (item === "&" || item === "|") {
                expected++;
            } else if (item !== "!") {
                expected--;
            }
        });
        if (expected < 0) {
            domain.unshift.apply(domain, _.times(Math.abs(expected), _.constant("&")));
        }
        return domain;
    },
    /**
     * Converts JS prefix-array representation of a domain to a python condition
     *
     * @static
     * @param {Array} domain
     * @returns {string}
     */
    domainToCondition: function (domain) {
        if (!domain.length) {
            return 'True';
        }
        var self = this;
        function consume(stack) {
            var len = stack.length;
            if (len <= 1) {
                return stack;
            } else if (stack[len-1] === '|' || stack[len-1] === '&' || stack[len-2] === '|' || stack[len-2] === '&') {
                return stack;
            } else if (len == 2) {
                stack.splice(-2, 2, stack[len-2] + ' and ' + stack[len-1]);
            } else if (stack[len-3] == '|') {
                if (len === 3) {
                    stack.splice(-3, 3, stack[len-2] + ' or ' + stack[len-1]);
                } else {
                    stack.splice(-3, 3, '(' + stack[len-2] + ' or ' + stack[len-1] + ')');
                }
            } else {
                stack.splice(-3, 3, stack[len-2] + ' and ' + stack[len-1]);
            }
            consume(stack);
        }

        var stack = [];
        _.each(domain, function (dom) {
            if (dom === '|' || dom === '&') {
                stack.push(dom);
            } else {
                var operator = dom[1] === '=' ? '==' : dom[1];
                if (!operator) {
                    throw new Error('Wrong operator for this domain');
                }
                if (operator === '!=' && dom[2] === false) { // the field is set
                    stack.push(dom[0]);
                } else if (dom[2] === null || dom[2] === true || dom[2] === false) {
                    stack.push(dom[0] + ' ' + (operator === '!=' ? 'is not ' : 'is ') + (dom[2] === null ? 'None' : (dom[2] ? 'True' : 'False')));
                } else {
                    stack.push(dom[0] + ' ' + operator + ' ' + JSON.stringify(dom[2]));
                }
                consume(stack);
            }
        });

        if (stack.length !== 1) {
            throw new Error('Wrong domain');
        }

        return stack[0];
    },
    /**
     * Converts python condition to a JS prefix-array representation of a domain
     *
     * @static
     * @param {string} condition
     * @returns {Array}
     */
    conditionToDomain: function (condition) {
        if (!condition || condition.match(/^\s*(True)?\s*$/)) {
            return [];
        }

        var ast = py.parse(py.tokenize(condition));


        function astToStackValue (node) {
            switch (node.id) {
                case '(name)': return node.value;
                case '.': return astToStackValue(node.first) + '.' + astToStackValue(node.second);
                case '(string)': return node.value;
                case '(number)': return node.value;
                case '(constant)': return node.value === 'None' ? null : node.value === 'True' ? true : false;
                case '[': return _.map(node.first, function (node) {return astToStackValue(node);});
            }
        }
        function astToStack (node) {
            switch (node.id) {
                case '(name)': return [[astToStackValue(node), '!=', false]];
                case '.': return [[astToStackValue(node.first) + '.' + astToStackValue(node.second), '!=', false]];
                case 'not': return [[astToStackValue(node.first), '=', false]];

                case 'or': return ['|'].concat(astToStack(node.first)).concat(astToStack(node.second));
                case 'and': return ['&'].concat(astToStack(node.first)).concat(astToStack(node.second));
                case '(comparator)':
                    if (node.operators.length !== 1) {
                        throw new Error('Wrong condition to convert in domain');
                    }
                    var right = astToStackValue(node.expressions[0]);
                    var left = astToStackValue(node.expressions[1]);
                    var operator = node.operators[0];
                    switch (operator) {
                        case 'is': operator = '='; break;
                        case 'is not': operator = '!='; break;
                        case '==': operator = '='; break;
                    }
                    return [[right, operator, left]];
                default:
                    throw "Condition cannot be transformed into domain";
            }
        }

        return astToStack(ast);
    },
});

return Domain;
});
