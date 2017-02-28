odoo.define("web.Domain", function (require) {
"use strict";

var collections = require("web.collections");
var pyeval = require("web.pyeval");

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
     * @param {Object} [evalContext] - in case the given domain is a string, an
     *                               evaluation context might be needed
     */
    init: function (domain, evalContext) {
        this._super.apply(this, arguments);
        if (domain === true || domain === false || domain === undefined) {
            this._data = domain || false;
        } else {
            this._parse(this.normalizeArray(_.clone(this.stringToArray(domain, evalContext))));
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
            if (!(this._data[0] in values)) {
                throw new Error(_.str.sprintf(
                    "Unknown field %s in domain",
                    this._data[0]
                ));
            }
            var fieldValue = values[this._data[0]];

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
                    return _.contains(
                        _.isArray(this._data[2]) ? this._data[2] : [this._data[2]],
                        fieldValue
                    );
                case "not in":
                    return !_.contains(
                        _.isArray(this._data[2]) ? this._data[2] : [this._data[2]],
                        fieldValue
                    );
                case "like":
                    return (fieldValue.toLowerCase().indexOf(this._data[2].toLowerCase()) >= 0);
                case "ilike":
                    return (fieldValue.indexOf(this._data[2]) >= 0);
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
        if (!_.isString(domain)) return domain;
        return pyeval.eval("domain", domain || "[]", evalContext);
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
});

return Domain;
});
