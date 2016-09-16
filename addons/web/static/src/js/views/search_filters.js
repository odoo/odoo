odoo.define('web.search_filters', function (require) {
"use strict";

var core = require('web.core');
var datepicker = require('web.datepicker');
var formats = require('web.formats');
var Widget = require('web.Widget');

var _t = core._t;
var _lt = core._lt;

var ExtendedSearchProposition = Widget.extend(/** @lends instance.web.search.ExtendedSearchProposition# */{
    template: 'SearchView.extended_search.proposition',
    events: {
        'change .o_searchview_extended_prop_field': 'changed',
        'change .o_searchview_extended_prop_op': 'operator_changed',
        'click .o_searchview_extended_delete_prop': function (e) {
            e.stopPropagation();
            this.getParent().remove_proposition(this);
        },
    },
    /**
     * @constructs instance.web.search.ExtendedSearchProposition
     * @extends instance.web.Widget
     *
     * @param parent
     * @param fields
     */
    init: function (parent, fields) {
        this._super(parent);
        this.fields = _(fields).chain()
            .map(function(val, key) { return _.extend({}, val, {'name': key}); })
            .filter(function (field) { return !field.deprecated && field.searchable; })
            .sortBy(function(field) {return field.string;})
            .value();
        this.attrs = {_: _, fields: this.fields, selected: null};
        this.value = null;
    },
    start: function () {
        return this._super().done(this.proxy('changed'));
    },
    changed: function() {
        var nval = this.$(".o_searchview_extended_prop_field").val();
        if(this.attrs.selected === null || this.attrs.selected === undefined || nval != this.attrs.selected.name) {
            this.select_field(_.detect(this.fields, function(x) {return x.name == nval;}));
        }
    },
    operator_changed: function (e) {
        this.value.show_inputs($(e.target));
    },
    /**
     * Selects the provided field object
     *
     * @param field a field descriptor object (as returned by fields_get, augmented by the field name)
     */
    select_field: function(field) {
        var self = this;
        if(this.attrs.selected !== null && this.attrs.selected !== undefined) {
            this.value.destroy();
            this.value = null;
            this.$('.o_searchview_extended_prop_op').html('');
        }
        this.attrs.selected = field;
        if(field === null || field === undefined) {
            return;
        }

        var type = field.type;
        var Field = core.search_filters_registry.get_any([type, "char"]);

        this.value = new Field(this, field);
        _.each(this.value.operators, function(operator) {
            $('<option>', {value: operator.value})
                .text(String(operator.text))
                .appendTo(self.$('.o_searchview_extended_prop_op'));
        });
        var $value_loc = this.$('.o_searchview_extended_prop_value').show().empty();
        this.value.appendTo($value_loc);

    },
    get_filter: function () {
        if (this.attrs.selected === null || this.attrs.selected === undefined)
            return null;
        var field = this.attrs.selected,
            op_select = this.$('.o_searchview_extended_prop_op')[0],
            operator = op_select.options[op_select.selectedIndex];

        return {
            attrs: {
                domain: this.value.get_domain(field, operator),
                string: this.value.get_label(field, operator),
            },
            children: [],
            tag: 'filter',
        };
    },
});

ExtendedSearchProposition.Field = Widget.extend({
    init: function (parent, field) {
        this._super(parent);
        this.field = field;
    },
    get_label: function (field, operator) {
        var format;
        switch (operator.value) {
        case '∃': case '∄': format = _t('%(field)s %(operator)s'); break;
        default: format = _t('%(field)s %(operator)s "%(value)s"'); break;
        }
        return this.format_label(format, field, operator);
    },
    format_label: function (format, field, operator) {
        return _.str.sprintf(format, {
            field: field.string,
            // According to spec, HTMLOptionElement#label should return
            // HTMLOptionElement#text when not defined/empty, but it does
            // not in older Webkit (between Safari 5.1.5 and Chrome 17) and
            // Gecko (pre Firefox 7) browsers, so we need a manual fallback
            // for those
            operator: operator.label || operator.text,
            value: this
        });
    },
    get_domain: function (field, operator) {
        switch (operator.value) {
        case '∃': return [[field.name, '!=', false]];
        case '∄': return [[field.name, '=', false]];
        default: return [[field.name, operator.value, this.get_value()]];
        }
    },
    show_inputs: function ($operator) {
        var $value = this.$el.parent();
        switch ($operator.val()) {
            case '∃':
            case '∄':
                $value.hide();
                break;
            default:
                $value.show();
        }
    },
    /**
     * Returns a human-readable version of the value, in case the "logical"
     * and the "semantic" values of a field differ (as for selection fields,
     * for instance).
     *
     * The default implementation simply returns the value itself.
     *
     * @return {String} human-readable version of the value
     */
    toString: function () {
        return this.get_value();
    }
});

ExtendedSearchProposition.Char = ExtendedSearchProposition.Field.extend({
    tagName: 'input',
    attributes: {
        type: 'text'
    },
    operators: [
        {value: "ilike", text: _lt("contains")},
        {value: "not ilike", text: _lt("doesn't contain")},
        {value: "=", text: _lt("is equal to")},
        {value: "!=", text: _lt("is not equal to")},
        {value: "∃", text: _lt("is set")},
        {value: "∄", text: _lt("is not set")}
    ],
    get_value: function() {
        return this.$el.val();
    }
});

ExtendedSearchProposition.DateTime = ExtendedSearchProposition.Field.extend({
    tagName: 'span',
    attributes: {
        type: 'datetime'
    },
    operators: [
        {value: "=", text: _lt("is equal to")},
        {value: "!=", text: _lt("is not equal to")},
        {value: ">", text: _lt("greater than")},
        {value: "<", text: _lt("less than")},
        {value: ">=", text: _lt("greater than or equal to")},
        {value: "<=", text: _lt("less than or equal to")},
        {value: "between", text: _lt("is between")},
        {value: "∃", text: _lt("is set")},
        {value: "∄", text: _lt("is not set")}
    ],
    widget: function () { return datepicker.DateTimeWidget; },
    get_value: function() {
        return this.datewidget_1.get_value();
    },
    get_domain: function (field, operator) {
        switch (operator.value) {
        case '∃': 
            return [[field.name, '!=', false]];
        case '∄': 
            return [[field.name, '=', false]];
        case 'between':
            return [[field.name, '>=', this.datewidget_1.get_value()], [field.name,'<=', this.datewidget_2.get_value()]];
        default: 
            return [[field.name, operator.value, this.get_value()]];
        }
    },
    show_inputs: function ($operator) {
        this._super($operator);
        if ($operator.val() === 'between') {
            if (!this.datewidget_2) {
                this.datewidget_2 = new (this.widget())(this);
                this.datewidget_2.appendTo(this.$el);
            }
            else {
                this.datewidget_2.$el.show();
            }
        }
        else {
            if (this.datewidget_2) {
                this.datewidget_2.$el.hide();
            }
        }
    },
    toString: function () {
        var str = formats.format_value(this.get_value(), { type:this.attributes['type'] });
        if (this.datewidget_2 && this.datewidget_2.get_value()) {
            str += ' and ' + formats.format_value(this.datewidget_2.get_value(), { type:this.attributes['type'] });
        }
        return str;
    },
    start: function() {
        var ready = this._super();
        this.datewidget_1 = new (this.widget())(this);
        this.datewidget_1.appendTo(this.$el);
        return ready;
    }
});

ExtendedSearchProposition.Date = ExtendedSearchProposition.DateTime.extend({
    attributes: {
        type: 'date'
    },
    widget: function () { return datepicker.DateWidget; },
});

ExtendedSearchProposition.Integer = ExtendedSearchProposition.Field.extend({
    tagName: 'input',
    attributes: {
        type: 'number',
        value: '0',
    },
    operators: [
        {value: "=", text: _lt("is equal to")},
        {value: "!=", text: _lt("is not equal to")},
        {value: ">", text: _lt("greater than")},
        {value: "<", text: _lt("less than")},
        {value: ">=", text: _lt("greater than or equal to")},
        {value: "<=", text: _lt("less than or equal to")},
        {value: "∃", text: _lt("is set")},
        {value: "∄", text: _lt("is not set")}
    ],
    toString: function () {
        return this.$el.val();
    },
    get_value: function() {
        try {
            var val =this.$el.val();
            return formats.parse_value(val === "" ? 0 : val, {'widget': 'integer'});
        } catch (e) {
            return "";
        }
    }
});

ExtendedSearchProposition.Id = ExtendedSearchProposition.Integer.extend({
    operators: [{value: "=", text: _lt("is")}]
});

ExtendedSearchProposition.Float = ExtendedSearchProposition.Field.extend({
    template: 'SearchView.extended_search.proposition.float',
    operators: [
        {value: "=", text: _lt("is equal to")},
        {value: "!=", text: _lt("is not equal to")},
        {value: ">", text: _lt("greater than")},
        {value: "<", text: _lt("less than")},
        {value: ">=", text: _lt("greater than or equal to")},
        {value: "<=", text: _lt("less than or equal to")},
        {value: "∃", text: _lt("is set")},
        {value: "∄", text: _lt("is not set")}
    ],
    init: function (parent) {
        this._super(parent);
        this.decimal_point = _t.database.parameters.decimal_point;
    },
    toString: function () {
        return this.$el.val();
    },
    get_value: function() {
        try {
            var val =this.$el.val();
            return formats.parse_value(val === "" ? 0.0 : val, {'widget': 'float'});
        } catch (e) {
            return "";
        }
    }
});

ExtendedSearchProposition.Selection = ExtendedSearchProposition.Field.extend({
    template: 'SearchView.extended_search.proposition.selection',
    operators: [
        {value: "=", text: _lt("is")},
        {value: "!=", text: _lt("is not")},
        {value: "∃", text: _lt("is set")},
        {value: "∄", text: _lt("is not set")}
    ],
    toString: function () {
        var select = this.$el[0];
        var option = select.options[select.selectedIndex];
        return option.label || option.text;
    },
    get_value: function() {
        return this.$el.val();
    }
});

ExtendedSearchProposition.Boolean = ExtendedSearchProposition.Field.extend({
    tagName: 'span',
    operators: [
        {value: "=", text: _lt("is true")},
        {value: "!=", text: _lt("is false")}
    ],
    get_label: function (field, operator) {
        return this.format_label(
            _t('%(field)s %(operator)s'), field, operator);
    },
    get_value: function() {
        return true;
    }
});

core.search_filters_registry
    .add('char', ExtendedSearchProposition.Char)
    .add('text', ExtendedSearchProposition.Char)
    .add('one2many', ExtendedSearchProposition.Char)
    .add('many2one', ExtendedSearchProposition.Char)
    .add('many2many', ExtendedSearchProposition.Char)
    .add('datetime', ExtendedSearchProposition.DateTime)
    .add('date', ExtendedSearchProposition.Date)
    .add('integer', ExtendedSearchProposition.Integer)
    .add('float', ExtendedSearchProposition.Float)
    .add('monetary', ExtendedSearchProposition.Float)
    .add('boolean', ExtendedSearchProposition.Boolean)
    .add('selection', ExtendedSearchProposition.Selection)
    .add('id', ExtendedSearchProposition.Id);

return {
    ExtendedSearchProposition: ExtendedSearchProposition
};

});
