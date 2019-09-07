odoo.define('web.SearchBarAutoCompleteSources', function (require) {
"use strict";

var Class = require('web.Class');
var core = require('web.core');
var Domain = require('web.Domain');
var field_utils = require('web.field_utils');
var mixins = require('web.mixins');
var pyUtils = require('web.py_utils');
var ServicesMixin = require('web.ServicesMixin');
var time = require('web.time');

var _t = core._t;
var _lt = core._lt;

var FilterInterface = Class.extend(mixins.EventDispatcherMixin, {
    completion_label: _lt("%s"),
    /**
     * @override
     * @param {Object} filter
     */
    init: function (parent, filter) {
        mixins.EventDispatcherMixin.init.call(this);
        this.setParent(parent);

        this.filter = filter;
    },
    /**
     * Fetch auto-completion values for the widget.
     *
     * The completion values should be an array of objects with keys facet and
     * label. They will be used by search_bar in @_onAutoCompleteSelected.
     *
     * @param {string} value value to getAutocompletionValues
     * @returns {Promise<null|Array>}
     */
    getAutocompletionValues: function (value) {
        var result;
        value = value.toLowerCase();
        if (fuzzy.test(value, this.filter.description)) {
            result = [{
                label: _.str.sprintf(this.completion_label.toString(),
                                         _.escape(this.filter.description)),
                facet: {
                    filter: this.filter,
                },
            }];
        }
        return Promise.resolve(result);
    },
});

var Filter = FilterInterface.extend({
    completion_label: _lt("Filter on: %s"),
});

var GroupBy = FilterInterface.extend({
    completion_label: _lt("Group by: %s"),
});

var Field = FilterInterface.extend(ServicesMixin, {
    default_operator: '=',
    /**
     * @override
     * @param {Object} field
     * @param {Object} filter
     * @param {Object} context needed for extra rpc (i.e. m2o)
     */
    init: function (parent, filter, field, context) {
        this._super.apply(this, arguments);

        this.field = field;
        this.filter = filter;
        this.attrs = _.extend({}, field, filter.attrs);
        this.context = context;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getAutocompletionValues: function (value) {
        return Promise.resolve([{
            label: this._getAutocompletionLabel(value),
            facet: this._getFacetValue(value),
        }]);
    },
    /**
     * TODO: the domain logic (getDomain, operator, etc.) should not be put here
     * (this has nothing to do with the autocomplete sources).
     *
     * This method is used by the ControlPanelModel when setting the
     * `filter_domain`.
     *
     * @param {Object[]} values
     * @returns {string}
     */
    getDomain: function (values) {
        if (!values.length) { return; }

        var valueToDomain;
        var self = this;
        var domain = this.attrs.filter_domain;
        if (domain) {
            valueToDomain = function (facetValue) {
                return Domain.prototype.stringToArray(
                    domain,
                    {
                        // these are the values that can be used in search view
                        // fields `filter_domain` attribute
                        self: self._valueFrom(facetValue),
                        raw_value: facetValue.value,
                    }
                );
            };
        } else {
            valueToDomain = function (facetValue) {
                return self._makeDomain(
                    self.attrs.name,
                    self.attrs.operator || self.default_operator,
                    facetValue
                );
            };
        }
        var domains = values.map(valueToDomain);

        domains = domains.map(Domain.prototype.arrayToString);
        return pyUtils.assembleDomains(domains, 'OR');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {any} value
     * @returns {string}
     */
    _getAutocompletionLabel: function (value) {
        return _.str.sprintf(_.str.escapeHTML(
            _t("Search %(field)s for: %(value)s")), {
                field: '<em>' + _.escape(this.attrs.string) + '</em>',
                value: '<strong>' + _.escape(value) + '</strong>'});
    },
    /**
     * @private
     * @param {any} value
     * @returns {Object}
     */
    _getFacetValue: function (value) {
        return {
            filter: this.filter,
            values: [{label: value, value: value}],
        };
    },
    /**
     * Function creating the returned domain for the field, override this
     * methods in children if you only need to customize the field's domain
     * without more complex alterations or tests (and without the need to
     * change override the handling of filter_domain)
     *
     * @private
     * @param {String} name the field's name
     * @param {String} operator the field's operator (either attribute-specified or default operator for the field
     * @param {Number|String} facet parsed value for the field
     * @returns {Array<Array>} domain to include in the resulting search
     */
    _makeDomain: function (name, operator, facet) {
        return [[name, operator, this._valueFrom(facet)]];
    },
    /**
     * @private
     * @param {Object} facetValue
     * @param {any} facetValue.value
     * @returns {any}
     */
    _valueFrom: function (facetValue) {
        return facetValue.value;
    },
});

var CharField = Field.extend({
    default_operator: 'ilike',

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getAutocompletionValues: function (value) {
        if (_.isEmpty(value)) { return Promise.resolve(null); }
        return this._super.apply(this, arguments);
    },
});

var NumberField = Field.extend({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getAutocompletionValues: function (value) {
        var val = this.parse(value);
        if (isNaN(val)) { return Promise.resolve(); }
        return this._super.apply(this, arguments);
    },
});

var IntegerField = NumberField.extend({
    error_message: _t("not a valid integer"),
    parse: function (value) {
        try {
            return field_utils.parse.integer(value);
        } catch (e) {
            return NaN;
        }
    },
});

var FloatField = NumberField.extend({
    error_message: _t("not a valid number"),
    parse: function (value) {
        try {
            return field_utils.parse.float(value);
        } catch (e) {
            return NaN;
        }
    },
});

var SelectionField = Field.extend({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getAutocompletionValues: function (value) {
        var self = this;
        var results = _(this.attrs.selection).chain()
            .filter(function (sel) {
                var selValue = sel[0], label = sel[1];
                if (selValue === undefined || !label) { return false; }
                return label.toLowerCase().indexOf(value.toLowerCase()) !== -1;
            })
            .map(function (sel) {
                return {
                    label: _.escape(sel[1]),
                    indent: true,
                    facet: self._getFacetValue(sel)
                };
            }).value();
        if (_.isEmpty(results)) { return Promise.resolve(null); }
        return Promise.resolve([{
            label: _.escape(this.attrs.string)
        }].concat(results));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {any} value
     * @returns {Object}
     */
    _getFacetValue: function (value) {
        return {
            filter: this.filter,
            values: [{label: value[1], value: value[0]}],
        };
    },
});

var BooleanField = SelectionField.extend({
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);

        this.attrs.selection = [
            [true, _t("Yes")],
            [false, _t("No")]
        ];
    },
});

var DateField = Field.extend({
    /**
     * @override
     */
    getAutocompletionValues: function (value) {
        // Make sure the value has a correct format before the creation of the moment object. See
        // issue https://github.com/moment/moment/issues/1407
        var t, v;
        try {
            t = (this.attrs && this.attrs.type === 'datetime') ? 'datetime' : 'date';
            v = field_utils.parse[t](value, {type: t}, {timezone: true});
        } catch (e) {
            return Promise.resolve(null);
        }

        var m = moment(v, t === 'datetime' ? 'YYYY-MM-DD HH:mm:ss' : 'YYYY-MM-DD');
        if (!m.isValid()) { return Promise.resolve(null); }
        var dateString = field_utils.format[t](m, {type: t});
        var label = this._getAutocompletionLabel(dateString);
        var facet = this._getFacetValue(dateString, m.toDate());
        return Promise.resolve([{
            label: label,
            facet: facet,
        }]);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getAutocompletionLabel: function (value) {
        return _.str.sprintf(_.str.escapeHTML(
            _t("Search %(field)s at: %(value)s")), {
                field: '<em>' + _.escape(this.attrs.string) + '</em>',
                value: '<strong>' + value + '</strong>'});
    },
    /**
     * @override
     * @param {any} rawValue
     */
    _getFacetValue: function (value, rawValue) {
        var facet = this._super.apply(this, arguments);
        facet.values[0].value = rawValue;
        return facet;
    },
    /**
     * @override
     */
    _valueFrom: function (facetValue) {
        return time.date_to_str(facetValue.value);
    },
});

var DateTimeField = DateField.extend({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _valueFrom: function (facetValue) {
        return time.datetime_to_str(facetValue.value);
    },
});

var ManyToOneField = CharField.extend({
    default_operator: {},

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getAutocompletionValues: function (value) {
        if (_.isEmpty(value)) { return Promise.resolve(null); }
        var label = this._getAutocompletionLabel(value);
        return Promise.resolve([{
            label: label,
            facet: this._getFacetValue(value),
            expand: this._expand.bind(this),
        }]);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getExpandedFacetValue: function (value) {
        return {
            filter: this.filter,
            values: [{label: value[1], value: value[0]}],
        };
    },
    /**
     * @override
     */
    _getFacetValue: function (value) {
        return {
            filter: this.filter,
            values: [{label: value, value: value, operator: 'ilike'}],
        };
    },
    /**
     * @override
     */
    _expand: function (value) {
        var self = this;
        var args = this.attrs.domain;
        if (typeof args === 'string') {
            try {
                args = Domain.prototype.stringToArray(args);
            } catch(e) {
                args = [];
            }
        }
        return this._rpc({
                model: this.attrs.relation,
                method: 'name_search',
                kwargs: {
                    name: value,
                    args: args,
                    limit: 8,
                    context: this.context,
                },
            })
            .then(function (results) {
                if (_.isEmpty(results)) { return null; }
                return _(results).map(function (result) {
                    return {
                        label: _.escape(result[1]),
                        facet: self._getExpandedFacetValue(result)
                    };
                });
            });
    },
    /**
     * @override
     */
    _makeDomain: function (name, operator, facetValue) {
        operator = facetValue.operator || operator;

        switch(operator){
        case this.default_operator:
            return [[name, '=', facetValue.value]];
        case 'ilike':
            return [[name, 'ilike', facetValue.value]];
        case 'child_of':
            return [[name, 'child_of', facetValue.value]];
        }
        return this._super(name, operator, facetValue);
    },
    /**
     * @override
     */
    _valueFrom: function (facetValue) {
        return facetValue.label;
    },
});

return {
    BooleanField: BooleanField,
    CharField: CharField,
    DateField: DateField,
    DateTimeField: DateTimeField,
    Field: Field,
    Filter: Filter,
    FloatField: FloatField,
    GroupBy: GroupBy,
    IntegerField: IntegerField,
    ManyToOneField: ManyToOneField,
    NumberField: NumberField,
    SelectionField: SelectionField,
};

});
