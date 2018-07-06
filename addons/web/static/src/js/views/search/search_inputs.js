odoo.define('web.search_inputs', function (require) {
"use strict";

var Context = require('web.Context');
var core = require('web.core');
var Domain = require('web.Domain');
var field_utils = require('web.field_utils');
var pyUtils = require('web.py_utils');
var time = require('web.time');
var utils = require('web.utils');
var Widget = require('web.Widget');

var _t = core._t;
var _lt = core._lt;

var Input = Widget.extend( /** @lends instance.web.search.Input# */{
    /**
     * @constructs instance.web.search.Input
     * @extends instance.web.Widget
     *
     * @param parent
     */
    init: function (parent) {
        this._super(parent);
        this.searchview = parent;
        this.load_attrs({});
    },
    /**
     * Fetch auto-completion values for the widget.
     *
     * The completion values should be an array of objects with keys category,
     * label, value prefixed with an object with keys type=section and label
     *
     * @param {String} value value to complete
     * @returns {jQuery.Deferred<null|Array>}
     */
    complete: function (value) {
        return $.when(null);
    },
    /**
     * Returns a Facet instance for the provided defaults if they apply to
     * this widget, or null if they don't.
     *
     * This default implementation will try calling
     * :js:func:`instance.web.search.Input#facet_for` if the widget's name
     * matches the input key
     *
     * @param {Object} defaults
     * @returns {jQuery.Deferred<null|Object>}
     */
    facet_for_defaults: function (defaults) {
        if (!this.attrs ||
            !(this.attrs.name in defaults && defaults[this.attrs.name])) {
            return $.when(null);
        }
        return this.facet_for(defaults[this.attrs.name]);
    },
    get_context: function () {
        throw new Error(
            "get_context not implemented for widget " + this.attrs.type);
    },
    get_groupby: function () {
        throw new Error(
            "get_groupby not implemented for widget " + this.attrs.type);
    },
    get_domain: function () {
        throw new Error(
            "get_domain not implemented for widget " + this.attrs.type);
    },
    load_attrs: function (attrs) {
        if (!_.isObject(attrs.modifiers)) {
            attrs.modifiers = attrs.modifiers ? JSON.parse(attrs.modifiers) : {};
        }
        this.attrs = attrs;
    },
    /**
     * Returns whether the input is "visible". The default behavior is to
     * query the ``modifiers.invisible`` flag on the input's description or
     * view node.
     *
     * @returns {Boolean}
     */
    visible: function () {
        return !this.attrs.modifiers.invisible;
    },
});

var Field = Input.extend( /** @lends instance.web.search.Field# */ {
    template: 'SearchView.field',
    default_operator: '=',
    /**
     * @constructs instance.web.search.Field
     * @extends instance.web.search.Input
     *
     * @param view_section
     * @param field
     * @param parent
     */
    init: function (view_section, field, parent) {
        this._super(parent);
        this.load_attrs(_.extend({}, field, view_section.attrs));
    },
    facet_for: function (value) {
        return $.when({
            field: this,
            category: this.attrs.string || this.attrs.name,
            values: [{label: String(value), value: value}]
        });
    },
    value_from: function (facetValue) {
        return facetValue.get('value');
    },
    get_context: function (facet) {
        var self = this;
        // A field needs a context to send when active
        var context = this.attrs.context;
        if (_.isEmpty(context) || !facet.values.length) {
            return;
        }
        var contexts = facet.values.map(function (facetValue) {
            return new Context(context)
                .set_eval_context({self: self.value_from(facetValue)});
        });

        if (contexts.length === 1) { return contexts[0]; }

        return _.extend(new Context(), {
            __contexts: contexts
        });
    },
    get_groupby: function () { },
    /**
     * Function creating the returned domain for the field, override this
     * methods in children if you only need to customize the field's domain
     * without more complex alterations or tests (and without the need to
     * change override the handling of filter_domain)
     *
     * @param {String} name the field's name
     * @param {String} operator the field's operator (either attribute-specified or default operator for the field
     * @param {Number|String} facet parsed value for the field
     * @returns {Array<Array>} domain to include in the resulting search
     */
    make_domain: function (name, operator, facet) {
        return [[name, operator, this.value_from(facet)]];
    },
    get_domain: function (facet) {
        if (!facet.values.length) { return; }

        var value_to_domain;
        var self = this;
        var domain = this.attrs.filter_domain;
        if (domain) {
            value_to_domain = function (facetValue) {
                return Domain.prototype.stringToArray(
                    domain,
                    {self: self.value_from(facetValue), raw_value: facetValue.attributes.value}
                );
            };
        } else {
            value_to_domain = function (facetValue) {
                return self.make_domain(
                    self.attrs.name,
                    self.attrs.operator || self.default_operator,
                    facetValue
                );
            };
        }
        var domains = facet.values.map(value_to_domain);
        if (domains.length === 1) {
            return domains[0];
        }

        _.each(domains, Domain.prototype.normalizeArray);
        var ors = _.times(domains.length - 1, _.constant("|"));
        return ors.concat.apply(ors, domains);
    }
});

/**
 * Implementation of the ``char`` OpenERP field type:
 *
 * * Default operator is ``ilike`` rather than ``=``
 *
 * * The Javascript and the HTML values are identical (strings)
 *
 * @class
 * @extends instance.web.search.Field
 */
var CharField = Field.extend( /** @lends instance.web.search.CharField# */ {
    default_operator: 'ilike',
    complete: function (value) {
        if (_.isEmpty(value)) { return $.when(null); }
        var label = _.str.sprintf(_.str.escapeHTML(
            _t("Search %(field)s for: %(value)s")), {
                field: '<em>' + _.escape(this.attrs.string) + '</em>',
                value: '<strong>' + _.escape(value) + '</strong>'});
        return $.when([{
            label: label,
            facet: {
                category: this.attrs.string,
                field: this,
                values: [{label: value, value: value}]
            }
        }]);
    }
});

var NumberField = Field.extend(/** @lends instance.web.search.NumberField# */{
    complete: function (value) {
        var val = this.parse(value);
        if (isNaN(val)) { return $.when(); }
        var label = _.str.sprintf(
            _t("Search %(field)s for: %(value)s"), {
                field: '<em>' + _.escape(this.attrs.string) + '</em>',
                value: '<strong>' + _.escape(value) + '</strong>'});
        return $.when([{
            label: label,
            facet: {
                category: this.attrs.string,
                field: this,
                values: [{label: value, value: val}]
            }
        }]);
    },
});

/**
 * @class
 * @extends instance.web.search.NumberField
 */
var IntegerField = NumberField.extend(/** @lends instance.web.search.IntegerField# */{
    error_message: _t("not a valid integer"),
    parse: function (value) {
        try {
            return field_utils.parse.integer(value);
        } catch (e) {
            return NaN;
        }
    }
});

/**
 * @class
 * @extends instance.web.search.NumberField
 */
var FloatField = NumberField.extend(/** @lends instance.web.search.FloatField# */{
    error_message: _t("not a valid number"),
    parse: function (value) {
        try {
            return field_utils.parse.float(value);
        } catch (e) {
            return NaN;
        }
    }
});

/**
 * Utility function for m2o & selection fields taking a selection/name_get pair
 * (value, name) and converting it to a Facet descriptor
 *
 * @param {instance.web.search.Field} field holder field
 * @param {Array} pair pair value to convert
 */
function facet_from(field, pair) {
    return {
        field: field,
        category: field.attrs.string,
        values: [{label: pair[1], value: pair[0]}]
    };
}

/**
 * @class
 * @extends instance.web.search.Field
 */
var SelectionField = Field.extend(/** @lends instance.web.search.SelectionField# */{
    // This implementation is a basic <select> field, but it may have to be
    // altered to be more in line with the GTK client, which uses a combo box
    // (~ jquery.autocomplete):
    // * If an option was selected in the list, behave as currently
    // * If something which is not in the list was entered (via the text input),
    //   the default domain should become (`ilike` string_value) but **any
    //   ``context`` or ``filter_domain`` becomes falsy, idem if ``@operator``
    //   is specified. So at least get_domain needs to be quite a bit
    //   overridden (if there's no @value and there is no filter_domain and
    //   there is no @operator, return [[name, 'ilike', str_val]]
    template: 'SearchView.field.selection',
    init: function () {
        this._super.apply(this, arguments);
        // prepend empty option if there is no empty option in the selection list
        this.prepend_empty = !_(this.attrs.selection).detect(function (item) {
            return !item[1];
        });
    },
    complete: function (needle) {
        var self = this;
        var results = _(this.attrs.selection).chain()
            .filter(function (sel) {
                var value = sel[0], label = sel[1];
                if (value === undefined || !label) { return false; }
                return label.toLowerCase().indexOf(needle.toLowerCase()) !== -1;
            })
            .map(function (sel) {
                return {
                    label: _.escape(sel[1]),
                    indent: true,
                    facet: facet_from(self, sel)
                };
            }).value();
        if (_.isEmpty(results)) { return $.when(null); }
        return $.when.call(null, [{
            label: _.escape(this.attrs.string)
        }].concat(results));
    },
    facet_for: function (value) {
        var match = _(this.attrs.selection).detect(function (sel) {
            return sel[0] === value;
        });
        if (!match) { return $.when(null); }
        return $.when(facet_from(this, match));
    }
});

var BooleanField = SelectionField.extend(/** @lends instance.web.search.BooleanField# */{
    /**
     * @constructs instance.web.search.BooleanField
     * @extends instance.web.search.BooleanField
     */
    init: function () {
        this._super.apply(this, arguments);
        this.attrs.selection = [
            [true, _t("Yes")],
            [false, _t("No")]
        ];
    }
});

/**
 * @class
 * @extends instance.web.search.DateField
 */
var DateField = Field.extend(/** @lends instance.web.search.DateField# */{
    value_from: function (facetValue) {
        return time.date_to_str(facetValue.get('value'));
    },
    complete: function (needle) {
        // Make sure the needle has a correct format before the creation of the moment object. See
        // issue https://github.com/moment/moment/issues/1407
        var t, v;
        try {
            t = (this.attrs && this.attrs.type === 'datetime') ? 'datetime' : 'date';
            v = field_utils.parse[t](needle, {type: t}, {timezone: true});
        } catch (e) {
            return $.when(null);
        }

        var m = moment(v, t === 'datetime' ? 'YYYY-MM-DD HH:mm:ss' : 'YYYY-MM-DD');
        if (!m.isValid()) { return $.when(null); }
        var date_string = field_utils.format[t](m, {type: t});
        var label = _.str.sprintf(_.str.escapeHTML(
            _t("Search %(field)s at: %(value)s")), {
                field: '<em>' + _.escape(this.attrs.string) + '</em>',
                value: '<strong>' + date_string + '</strong>'});
        return $.when([{
            label: label,
            facet: {
                category: this.attrs.string,
                field: this,
                values: [{label: date_string, value: m.toDate()}]
            }
        }]);
    }
});

/**
 * Implementation of the ``datetime`` openerp field type:
 *
 * * Uses the same widget as the ``date`` field type (a simple date)
 *
 * * Builds a slighly more complex, it's a datetime range (includes time)
 *   spanning the whole day selected by the date widget
 *
 * @class
 * @extends instance.web.DateField
 */
var DateTimeField = DateField.extend(/** @lends instance.web.search.DateTimeField# */{
    value_from: function (facetValue) {
        return time.datetime_to_str(facetValue.get('value'));
    }
});

var ManyToOneField = CharField.extend({
    default_operator: {},
    init: function (view_section, field, parent) {
        this._super(view_section, field, parent);
        this.searchview = parent;
    },

    complete: function (value) {
        if (_.isEmpty(value)) { return $.when(null); }
        var label = _.str.sprintf(_.str.escapeHTML(
            _t("Search %(field)s for: %(value)s")), {
                field: '<em>' + _.escape(this.attrs.string) + '</em>',
                value: '<strong>' + _.escape(value) + '</strong>'});
        return $.when([{
            label: label,
            facet: {
                category: this.attrs.string,
                field: this,
                values: [{label: value, value: value, operator: 'ilike'}]
            },
            expand: this.expand.bind(this),
        }]);
    },

    expand: function (needle) {
        var self = this;
        // FIXME: "concurrent" searches (multiple requests, mis-ordered responses)
        var context = pyUtils.eval(
            'contexts', [this.searchview.dataset.get_context()]);
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
                    name: needle,
                    args: args,
                    limit: 8,
                    context: context
                },
            })
            .then(function (results) {
                if (_.isEmpty(results)) { return null; }
                return _(results).map(function (result) {
                    return {
                        label: _.escape(result[1]),
                        facet: facet_from(self, result)
                    };
                });
            });
    },
    facet_for: function (value) {
        var self = this;
        if (value instanceof Array) {
            if (value.length === 2 && _.isString(value[1])) {
                return $.when(facet_from(this, value));
            }
            utils.assert(value.length <= 1,
                   _t("M2O search fields do not currently handle multiple default values"));
            // there are many cases of {search_default_$m2ofield: [id]}, need
            // to handle this as if it were a single value.
            value = value[0];
        }
        var context = pyUtils.eval('contexts', [this.searchview.dataset.get_context()]);

        return this._rpc({
                model: this.attrs.relation,
                method: 'name_get',
                args: [value],
                context: context,
            })
            .then(function (names) {
                if (_(names).isEmpty()) { return null; }
                return facet_from(self, names[0]);
            });
    },
    value_from: function (facetValue) {
        return facetValue.get('label');
    },
    make_domain: function (name, operator, facetValue) {
        operator = facetValue.get('operator') || operator;

        switch(operator){
        case this.default_operator:
            return [[name, '=', facetValue.get('value')]];
        case 'ilike':
            return [[name, 'ilike', facetValue.get('value')]];
        case 'child_of':
            return [[name, 'child_of', facetValue.get('value')]];
        }
        return this._super(name, operator, facetValue);
    },
    get_context: function (facet) {
        var values = facet.values;
        if (_.isEmpty(this.attrs.context) && values.length === 1) {
            var c = {};
            var v = values.at(0);
            if (v.get('operator') !== 'ilike') {
                c['default_' + this.attrs.name] = v.get('value');
            }
            return c;
        }
        return this._super(facet);
    }
});

var FilterGroup = Input.extend(/** @lends instance.web.search.FilterGroup# */{
    template: 'SearchView.filters',
    icon: "fa-filter",
    completion_label: _lt("Filter on: %s"),
    /**
     * Inclusive group of filters, creates a continuous "button" with clickable
     * sections (the normal display for filters is to be a self-contained button)
     *
     * @constructs instance.web.search.FilterGroup
     * @extends instance.web.search.Input
     *
     * @param {Array<instance.web.search.Filter>} filters elements of the group
     * @param {instance.web.SearchView} parent parent in which the filters are contained
     * @param {Object} intervalMapping, a key is a field name and the corresponding value
     *                   is the current interval used
     *                   (necessarily the field is of type 'date' or 'datetime')
     */
    init: function (filters, parent, intervalMapping, periodMapping) {
        // If all filters are group_by and we're not initializing a GroupbyGroup,
        // create a GroupbyGroup instead of the current FilterGroup
        if (!(this instanceof GroupbyGroup) &&
              _(filters).all(function (f) {
                  if (!f.attrs.context) { return false; }
                  var c = pyUtils.eval('context', f.attrs.context);
                  return !_.isEmpty(c.group_by);})) {
            return new GroupbyGroup(filters, parent, intervalMapping);
        }
        this._super(parent);
        this.filters = filters;
        this.searchview = parent;
        this.intervalMapping = intervalMapping;
        this.periodMapping = periodMapping || [];
        this.searchview.query.on('add remove change reset', this.proxy('search_change'));
    },
    start: function () {
        this.$el.on('click', 'a', this.proxy('toggle_filter'));
        return $.when(null);
    },
    /**
     * Handles change of the search query: any of the group's filter which is
     * in the search query should be visually checked in the drawer
     */
    search_change: function () {
        var self = this;
        var $filters = this.$el ? this.$el.removeClass('selected') : $();
        var facet = this.searchview.query.find(_.bind(this.match_facet, this));
        if (!facet) { return; }
        facet.values.each(function (v) {
            var i = _(self.filters).indexOf(v.get('value'));
            if (i === -1) { return; }
            $filters.filter(function () {
                return Number($(this).data('index')) === i;
            }).addClass('selected');
        });
    },
    /**
     * Matches the group to a facet, in order to find if the group is
     * represented in the current search query
     */
    match_facet: function (facet) {
        return facet.get('field') === this;
    },
    make_facet: function (values) {
        return {
            cat: 'filterCategory',
            category: _t("Filter"),
            icon: this.icon,
            separator: _t(" or "),
            values: values,
            field: this
        };
    },
    make_value: function (filter) {
        return {
            label: filter.attrs.string || filter.attrs.help || filter.attrs.name,
            value: filter
        };
    },
    facet_for_defaults: function (defaults) {
        var self = this;
        var fs = _(this.filters).chain()
            .filter(function (f) {
                return f.attrs && f.attrs.name && !!defaults[f.attrs.name];
            }).map(function (f) {
                return self.make_value(f);
            }).value();
        if (_.isEmpty(fs)) { return $.when(null); }
        return $.when(this.make_facet(fs));
    },
    /**
     * Fetches contexts for all enabled filters in the group
     *
     * @param {openerp.web.search.Facet} facet
     * @return {*} combined contexts of the enabled filters in this group
     */
    get_context: function (facet) {
        var contexts = facet.values.chain()
            .map(function (f) { return f.get('value').attrs.context; })
            .without('{}')
            .reject(_.isEmpty)
            .value();

        if (!contexts.length) { return; }
        if (contexts.length === 1) { return contexts[0]; }
        return _.extend(new Context(), {
            __contexts: contexts
        });
    },
    /**
     * Fetches group_by sequence for all enabled filters in the group
     *
     * @param {VS.model.SearchFacet} facet
     * @return {Array} enabled filters in this group
     */
    get_groupby: function (facet) {
        var self = this;
        return  facet.values.chain()
            .map(function (f) {
                var fieldName = f.get('value').attrs.fieldName;
                var defaultInterval = f.get('value').attrs.defaultInterval;
                var couple = _.findWhere(self.intervalMapping, {groupby: f.get('value')});
                var interval = couple ? couple.interval: undefined;
                var context = _.clone(f.get('value').attrs.context);
                if (context && interval) {
                    if (defaultInterval) {
                        context = context.replace(defaultInterval, interval);
                    } else if (fieldName){
                        context = context.replace(fieldName, fieldName + ':' + interval);
                    }
                }
                return context;
            })
            .without('{}')
            .reject(_.isEmpty)
            .value();
    },
    /**
     * Handles domains-fetching for all the filters within it: groups them.
     *
     * @param {VS.model.SearchFacet} facet
     * @param {boolean} noEvaluation determines if the domains are evaluated or not.
                            By default, domains are evaluated.
     * @return {*} combined domains of the enabled filters in this group
     */
    get_domain: function (facet, noEvaluation) {
        noEvaluation = noEvaluation || false;
        var self = this;
        var userContext = this.getSession().user_context;
        var domains = facet.values.chain()
            .map(function (f) {
                var filter = f.get('value');
                var attributes = filter.attrs;
                var domain = attributes.domain;
                var fieldName = attributes.date;
                if (!domain && fieldName) {
                    var couple = _.findWhere(self.periodMapping, {filter: filter});
                    var period = couple ? couple.period: 'this_month';
                    var type = couple ? couple.type: 'date';
                    domain = Domain.prototype.constructDomain(fieldName, period, type);
                }
                return domain;
            })
            .without('[]')
            .reject(_.isEmpty)
            .map(function (domain) {
                domain = domain.replace(/%%/g, '%');
                return domain;
            })
            .value();

        if (!domains.length) {
            return;
        }
        // domains belong the same groups. We need to make a union.
        var domain = pyUtils.assembleDomains(domains, 'OR');
        if (!noEvaluation) {
            return Domain.prototype.stringToArray(domain, userContext);
        }
        return domain;
    },
    toggle_filter: function (e) {
        e.preventDefault();
        e.stopPropagation();
        this.toggle(this.filters[Number($(e.target).parent().data('index'))]);
    },
    toggle: function (filter, options) {
        this.searchview.query.toggle(this.make_facet([this.make_value(filter)]), options);
    },
    is_visible: function () {
        return _.some(this.filters, function (filter) {
            return !filter.attrs.invisible;
        });
    },
    complete: function (item) {
        var self = this;
        item = item.toLowerCase();
        var facet_values = _(this.filters).chain()
            .filter(function (filter) { return filter.visible(); })
            .filter(function (filter) {
                var at = {
                    string: filter.attrs.string || '',
                    help: filter.attrs.help || '',
                    name: filter.attrs.name || ''
                };
                var include = _.str.include;
                return include(at.string.toLowerCase(), item)
                    || include(at.help.toLowerCase(), item)
                    || include(at.name.toLowerCase(), item);
            })
            .map(this.make_value)
            .value();
        if (_(facet_values).isEmpty()) { return $.when(null); }
        return $.when(_.map(facet_values, function (facet_value) {
            return {
                label: _.str.sprintf(self.completion_label.toString(),
                                     _.escape(facet_value.label)),
                facet: self.make_facet([facet_value])
            };
        }));
    },
    /*
     * @param {Object} intervalMapping
     */
    updateIntervalMapping: function (intervalMapping) {
        this.intervalMapping = intervalMapping;
    },
    /*
     * @param {Object} periodMapping
     */
    updatePeriodMapping: function (periodMapping) {
        this.intervalMapping = periodMapping;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

});

var GroupbyGroup = FilterGroup.extend({
    icon: 'fa-bars',
    completion_label: _lt("Group by: %s"),
    init: function (filters, parent) {
        this._super.apply(this, arguments);
        this.searchview = parent;
        // Not flanders: facet unicity is handled through the
        // (category, field) pair of facet attributes. This is all well and
        // good for regular filter groups where a group matches a facet, but for
        // groupby we want a single facet. So cheat: add an attribute on the
        // view which proxies to the first GroupbyGroup, so it can be used
        // for every GroupbyGroup and still provides the various methods needed
        // by the search view. Use weirdo name to avoid risks of conflicts
        if (!this.searchview._s_groupby) {
            this.searchview._s_groupby = {
                help: "See GroupbyGroup#init",
                get_context: this.proxy('get_context'),
                get_domain: this.proxy('get_domain'),
                get_groupby: this.proxy('get_groupby')
            };
        }
    },
    match_facet: function (facet) {
        return facet.get('field') === this.searchview._s_groupby;
    },
    make_facet: function (values) {
        return {
            cat: 'groupByCategory',
            category: _t("Group By"),
            icon: this.icon,
            separator: " > ",
            values: values,
            field: this.searchview._s_groupby
        };
    }
});

var Filter = Input.extend(/** @lends instance.web.search.Filter# */{
    template: 'SearchView.filter',
    /**
     * Implementation of the OpenERP filters (button with a context and/or
     * a domain sent as-is to the search view)
     *
     * Filters are only attributes holder, the actual work (compositing
     * domains and contexts, converting between facets and filters) is
     * performed by the filter group.
     *
     * @constructs instance.web.search.Filter
     * @extends instance.web.search.Input
     *
     * @param node
     * @param parent
     */
    init: function (node, parent) {
        this._super(parent);
        this.load_attrs(node.attrs);
    },
    facet_for: function () { return $.when(null); },
    get_context: function () { },
    get_domain: function () { },
});

/**
 * Registry of search fields, called by :js:class:`instance.web.SearchView` to
 * find and instantiate its field widgets.
 */

core.search_widgets_registry
    .add('char', CharField)
    .add('text', CharField)
    .add('html', CharField)
    .add('boolean', BooleanField)
    .add('integer', IntegerField)
    .add('id', IntegerField)
    .add('float', FloatField)
    .add('monetary', FloatField)
    .add('selection', SelectionField)
    .add('datetime', DateTimeField)
    .add('date', DateField)
    .add('many2one', ManyToOneField)
    .add('many2many', CharField)
    .add('one2many', CharField);


return {
    FilterGroup: FilterGroup,
    Filter: Filter,
    Field: Field,
    GroupbyGroup: GroupbyGroup,
};

});
