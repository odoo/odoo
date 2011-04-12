openerp.base.search = function(openerp) {

openerp.base.SearchView = openerp.base.Controller.extend({
    init: function(view_manager, session, element_id, dataset, view_id, defaults) {
        this._super(session, element_id);
        this.view_manager = view_manager;
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;

        this.defaults = defaults || {};

        this.inputs = [];
        this.enabled_filters = [];

        this.has_focus = false;
    },
    start: function() {
        //this.log('Starting SearchView '+this.model+this.view_id)
        return this.rpc("/base/searchview/load", {"model": this.model, "view_id":this.view_id}, this.on_loaded);
    },
    show: function () {
        this.$element.show();
    },
    hide: function () {
        this.$element.hide();
    },
    /**
     * Builds a list of widget rows (each row is an array of widgets)
     *
     * @param {Array} items a list of nodes to convert to widgets
     * @param {Object} fields a mapping of field names to (ORM) field attributes
     * @returns Array
     */
    make_widgets: function (items, fields) {
        var rows = [],
            row = [];
        rows.push(row);
        var filters = [];
        _.each(items, function (item) {
            if (filters.length && item.tag !== 'filter') {
                row.push(
                    new openerp.base.search.FilterGroup(
                        filters, this));
                filters = [];
            }

            if (item.tag === 'newline') {
                row = [];
                rows.push(row);
            } else if (item.tag === 'filter') {
                if (!this.has_focus) {
                    item.attrs.default_focus = '1';
                    this.has_focus = true;
                }
                filters.push(
                    new openerp.base.search.Filter(
                        item, this));
            } else if (item.tag === 'separator') {
                // a separator is a no-op
            } else {
                if (item.tag === 'group') {
                    // TODO: group and field should be fetched from registries, maybe even filters
                    row.push(
                        new openerp.base.search.Group(
                            item, this, fields));
                } else if (item.tag === 'field') {
                    if (!this.has_focus) {
                        item.attrs.default_focus = '1';
                        this.has_focus = true;
                    }
                    row.push(
                        this.make_field(
                            item, fields[item['attrs'].name]));
                }
            }
        }, this);
        if (filters.length) {
            row.push(new openerp.base.search.FilterGroup(filters, this));
        }

        return rows;
    },
    /**
     * Creates a field for the provided field descriptor item (which comes
     * from fields_view_get)
     *
     * @param {Object} item fields_view_get node for the field
     * @param {Object} field fields_get result for the field
     * @returns openerp.base.search.Field
     */
    make_field: function (item, field) {
        try {
            return new (openerp.base.search.fields.get_object(field.type))
                        (item, field, this);
        } catch (e) {
            if (! e instanceof openerp.base.KeyNotFound) {
                throw e;
            }
            // KeyNotFound means unknown field type
            console.group('Unknown field type ' + field.type);
            console.error('View node', item);
            console.info('View field', field);
            console.info('In view', this);
            console.groupEnd();
            return null;
        }
    },
    on_loaded: function(data) {
        var lines = this.make_widgets(
            data.fields_view['arch'].children,
            data.fields_view.fields);

        // for extended search view
        var ext = new openerp.base.search.ExtendedSearch(null, data.fields_view.fields);
        lines.push([ext]);
        this.inputs.push(ext);
        
        var render = QWeb.render("SearchView", {
            'view': data.fields_view['arch'],
            'lines': lines,
            'defaults': this.defaults
        });
        this.$element.html(render);

        var f = this.$element.find('form');
        this.$element.find('form')
                .submit(this.do_search)
                .bind('reset', this.do_clear);
        // start() all the widgets
        _(lines).chain().flatten().each(function (widget) {
            widget.start();
        });
    },
    /**
     * Performs the search view collection of widget data.
     *
     * If the collection went well (all fields are valid), then triggers
     * :js:func:`openerp.base.SearchView.on_search`.
     *
     * If at least one field failed its validation, triggers
     * :js:func:`openerp.base.SearchView.on_invalid` instead.
     *
     * @param e jQuery event object coming from the "Search" button
     */
    do_search: function (e) {
        if (e && e.preventDefault) { e.preventDefault(); }

        //debugger;
        var domains = [], contexts = [];

        var errors = [];

        _.each(this.inputs, function (input) {
            try {
                var domain = input.get_domain();
                if (domain) {
                    domains.push(domain);
                }

                var context = input.get_context();
                if (context) {
                    contexts.push(context);
                }
            } catch (e) {
                if (e instanceof openerp.base.search.Invalid) {
                    errors.push(e);
                } else {
                    throw e;
                }
            }
        });

        if (errors.length) {
            this.on_invalid(errors);
            return;
        }

        // TODO: do we need to handle *fields* with group_by in their context?
        var groupbys = _(this.enabled_filters)
                .chain()
                .map(function (filter) { return filter.get_context();})
                .compact()
                .value();

        this.on_search(domains, contexts, groupbys);
    },
    /**
     * Triggered after the SearchView has collected all relevant domains and
     * contexts.
     *
     * It is provided with an Array of domains and an Array of contexts, which
     * may or may not be evaluated (each item can be either a valid domain or
     * context, or a string to evaluate in order in the sequence)
     *
     * It is also passed an array of contexts used for group_by (they are in
     * the correct order for group_by evaluation, which contexts may not be)
     *
     * @event
     * @param {Array} domains an array of literal domains or domain references
     * @param {Array} contexts an array of literal contexts or context refs
     * @param {Array} groupbys ordered contexts which may or may not have group_by keys
     */
    on_search: function (domains, contexts, groupbys) {
    },
    /**
     * Triggered after a validation error in the SearchView fields.
     *
     * Error objects have three keys:
     * * ``field`` is the name of the invalid field
     * * ``value`` is the invalid value
     * * ``message`` is the (in)validation message provided by the field
     *
     * @event
     * @param {Array} errors a never-empty array of error objects
     */
    on_invalid: function (errors) {
        this.notification.notify("Invalid Search", "triggered from search view");
    },
    do_clear: function (e) {
        if (e && e.preventDefault) { e.preventDefault(); }
        this.on_clear();
    },
    /**
     * Triggered when the search view gets cleared
     *
     * @event
     */
    on_clear: function () {  },
    /**
     * Called by a filter propagating its state changes
     *
     * @param {openerp.base.search.Filter} filter a filter which got toggled
     * @param {Boolean} default_enabled filter got enabled through the default values, at render time.
     */
    do_toggle_filter: function (filter, default_enabled) {
        if (default_enabled || filter.is_enabled()) {
            this.enabled_filters.push(filter);
        } else {
            this.enabled_filters = _.without(
                this.enabled_filters, filter);
        }

        if (!default_enabled) {
            // selecting a filter after initial loading automatically
            // triggers refresh
            this.$element.find('form').submit();
        }
    }
});

/** @namespace */
openerp.base.search = {};
/**
 * Registry of search fields, called by :js:class:`openerp.base.SearchView` to
 * find and instantiate its field widgets.
 */
openerp.base.search.fields = new openerp.base.Registry({
    'char': 'openerp.base.search.CharField',
    'text': 'openerp.base.search.CharField',
    'boolean': 'openerp.base.search.BooleanField',
    'integer': 'openerp.base.search.IntegerField',
    'float': 'openerp.base.search.FloatField',
    'selection': 'openerp.base.search.SelectionField',
    'datetime': 'openerp.base.search.DateTimeField',
    'date': 'openerp.base.search.DateField',
    'one2many': 'openerp.base.search.OneToManyField',
    'many2one': 'openerp.base.search.ManyToOneField',
    'many2many': 'openerp.base.search.ManyToManyField'
});
openerp.base.search.Invalid = Class.extend(
    /** @lends openerp.base.search.Invalid# */{
    /**
     * Exception thrown by search widgets when they hold invalid values,
     * which they can not return when asked.
     *
     * @constructs
     * @param field the name of the field holding an invalid value
     * @param value the invalid value
     * @param message validation failure message
     */
    init: function (field, value, message) {
        this.field = field;
        this.value = value;
        this.message = message;
    },
    toString: function () {
        return ('Incorrect value for field ' + this.field +
                ': [' + this.value + '] is ' + this.message);
    }
});
openerp.base.search.Widget = openerp.base.Controller.extend(
    /** @lends openerp.base.search.Widget# */{
    template: null,
    /**
     * Root class of all search widgets
     *
     * @constructs
     * @extends openerp.base.Controller
     *
     * @param view the ancestor view of this widget
     */
    init: function (view) {
        this.view = view;
    },
    /**
     * Sets and returns a globally unique identifier for the widget.
     *
     * If a prefix is specified, the identifier will be appended to it.
     *
     * @params prefix prefix sections, empty/falsy sections will be removed
     */
    make_id: function () {
        this.element_id = _.uniqueId(
            ['search'].concat(
                _.compact(_.toArray(arguments)),
                ['']).join('_'));
        return this.element_id;
    },
    /**
     * "Starts" the widgets. Called at the end of the rendering, this allows
     * widgets to hook themselves to their view sections.
     *
     * On widgets, if they kept a reference to a view and have an element_id,
     * will fetch and set their root element on $element.
     */
    start: function () {
        this._super();
        if (this.view && this.element_id) {
            // id is unique, and no getElementById on elements
            this.$element = $(document.getElementById(
                this.element_id));
        }
    },
    /**
     * "Stops" the widgets. Called when the view destroys itself, this
     * lets the widgets clean up after themselves.
     */
    stop: function () {
        delete this.view;
        this._super();
    },
    render: function (defaults) {
        return QWeb.render(
            this.template, _.extend(this, {
                defaults: defaults
        }));
    }
});
openerp.base.search.FilterGroup = openerp.base.search.Widget.extend({
    template: 'SearchView.filters',
    init: function (filters, view) {
        this._super(view);
        this.filters = filters;
    },
    start: function () {
        this._super();
        _.each(this.filters, function (filter) {
            filter.start();
        });
    }
});
openerp.base.search.add_expand_listener = function($root) {
    $root.find('a.searchview_group_string').click(function (e) {
        $root.toggleClass('folded expanded');
        e.stopPropagation();
        e.preventDefault();
    });
};
openerp.base.search.Group = openerp.base.search.Widget.extend({
    template: 'SearchView.group',
    // TODO: contain stuff
    // TODO: @expand
    init: function (view_section, view, fields) {
        this._super(view);
        this.attrs = view_section.attrs;
        this.lines = view.make_widgets(
            view_section.children, fields);
        this.make_id('group');
    },
    start: function () {
        this._super();
        _(this.lines)
            .chain()
            .flatten()
            .each(function (widget) { widget.start(); });
        openerp.base.search.add_expand_listener(this.$element);
    }
});

openerp.base.search.ExtendedSearch = openerp.base.BaseWidget.extend({
    template: 'SearchView.extended_search',
    identifier_prefix: 'extended-search',
    init: function (parent, fields) {
        this._super(parent);
        this.fields = fields;
    },
    add_group: function() {
        var group = new openerp.base.search.ExtendedSearchGroup(this, this.fields);
        var render = group.render({});
        this.$element.find('.searchview_extended_groups_list').append(render);
        group.start();
    },
    start: function () {
        this._super();
        var _this = this;
        openerp.base.search.add_expand_listener(this.$element);
        this.add_group();
        this.$element.find('.searchview_extended_add_group').click(function (e) {
            _this.add_group();
        });
    },
    get_context: function() {
        return null;
    },
    get_domain: function() {
        if(this.$element.hasClass("folded")) {
            return null;
        }
        return _.reduce(this.children,
            function(mem, x) { return mem.concat(x.get_domain());}, []);
    }
});

openerp.base.search.ExtendedSearchGroup = openerp.base.BaseWidget.extend({
    template: 'SearchView.extended_search.group',
    identifier_prefix: 'extended-search-group',
    init: function (parent, fields) {
        this._super(parent);
        this.fields = fields;
    },
    add_prop: function() {
        var prop = new openerp.base.search.ExtendedSearchProposition(this, this.fields);
        var render = prop.render({});
        this.$element.find('.searchview_extended_propositions_list').append(render);
        prop.start();
    },
    start: function () {
        this._super();
        var _this = this;
        this.add_prop();
        this.$element.find('.searchview_extended_add_proposition').click(function (e) {
            _this.add_prop();
        });
        var delete_btn = this.$element.find('.searchview_extended_delete_group');
        delete_btn.click(function (e) {
            _this.stop();
        });
    },
    get_domain: function() {
        var props = _(this.children).chain().map(function(x) {
            return x.get_proposition();
        }).compact().value();
        var choice = this.$element.find(".searchview_extended_group_choice").val();
        var op = choice == "all" ? "&" : "|";
        return [].concat(choice == "none" ? ['!'] : [],
            _.map(_.range(_.max([0,props.length - 1])), function() { return op; }),
            props);
    }
});

openerp.base.search.Input = openerp.base.search.Widget.extend(
    /** @lends openerp.base.search.Input# */{
    /**
     * @constructs
     * @extends openerp.base.search.Widget
     *
     * @param view
     */
    init: function (view) {
        this._super(view);
        this.view.inputs.push(this);
    },
    get_context: function () {
        throw new Error(
            "get_context not implemented for widget " + this.attrs.type);
    },
    get_domain: function () {
        throw new Error(
            "get_domain not implemented for widget " + this.attrs.type);
    }
});
openerp.base.search.Filter = openerp.base.search.Input.extend({
    template: 'SearchView.filter',
    // TODO: force rendering
    init: function (node, view) {
        this._super(view);
        this.attrs = node.attrs;
        this.classes = [this.attrs.string ? 'filter_label' : 'filter_icon'];
        this.make_id('filter', this.attrs.name);
    },
    start: function () {
        this._super();
        var self = this;
        this.$element.click(function (e) {
            $(this).toggleClass('enabled');
            self.view.do_toggle_filter(self);
        });
    },
    /**
     * Returns whether the filter is currently enabled (in use) or not.
     *
     * @returns a boolean
     */
    is_enabled:function () {
        return this.$element.hasClass('enabled');
    },
    /**
     * If the filter is present in the defaults (and has a truthy value),
     * enable the filter.
     *
     * @param {Object} defaults the search view's default values
     */
    render: function (defaults) {
        if (this.attrs.name && defaults[this.attrs.name]) {
            this.classes.push('enabled');
            this.view.do_toggle_filter(this, true);
        }
        return this._super(defaults);
    },
    get_context: function () {
        if (!this.is_enabled()) {
            return;
        }
        return this.attrs.context;
    },
    get_domain: function () {
        if (!this.is_enabled()) {
            return;
        }
        return this.attrs.domain;
    }
});
openerp.base.search.Field = openerp.base.search.Input.extend(
    /** @lends openerp.base.search.Field# */ {
    template: 'SearchView.field',
    default_operator: '=',
    // TODO: set default values
    // TODO: get context, domain
    // TODO: holds Filters
    /**
     * @constructs
     * @extends openerp.base.search.Input
     *
     * @param view_section
     * @param field
     * @param view
     */
    init: function (view_section, field, view) {
        this._super(view);
        this.attrs = _.extend({}, field, view_section.attrs);
        this.filters = new openerp.base.search.FilterGroup(_.map(
            view_section.children, function (filter_node) {
                return new openerp.base.search.Filter(
                    filter_node, view);
        }), view);
        this.make_id('input', field.type, this.attrs.name);
    },
    start: function () {
        this._super();
        this.filters.start();
    },
    get_context: function () {
        var val = this.get_value();
        // A field needs a value to be "active", and a context to send when
        // active
        var has_value = (val !== null && val !== '');
        var context = this.attrs.context;
        if (!(has_value && context)) {
            return;
        }
        return _.extend(
            {}, context,
            {own_values: {self: val}});
    },
    get_domain: function () {
        var val = this.get_value();

        var has_value = (val !== null && val !== '');
        if(!has_value) {
            return;
        }

        var domain = this.attrs['filter_domain'];
        if (!domain) {
            return [[
                this.attrs.name,
                this.attrs.operator || this.default_operator,
                this.get_value()
            ]];
        }
        return _.extend(
            {}, domain,
            {own_values: {self: val}});
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
 * @extends openerp.base.search.Field
 */
openerp.base.search.CharField = openerp.base.search.Field.extend(
    /** @lends openerp.base.search.CharField# */ {
    default_operator: 'ilike',
    get_value: function () {
        return this.$element.val();
    }
});
openerp.base.search.BooleanField = openerp.base.search.Field.extend({
    template: 'SearchView.field.selection',
    init: function () {
        this._super.apply(this, arguments);
        this.attrs.selection = [
            ['true', 'Yes'],
            ['false', 'No']
        ];
    },
    /**
     * Search defaults likely to be boolean values (for a boolean field).
     *
     * In the HTML, we only get strings, and our strings here are
     * <code>'true'</code> and <code>'false'</code>, so ensure we get only
     * those by truth-testing the default value.
     *
     * @param {Object} defaults default values for this search view
     */
    render: function (defaults) {
        var name = this.attrs.name;
        if (name in defaults) {
            defaults[name] = defaults[name] ? "true" : "false";
        }
        return this._super(defaults);
    },
    get_value: function () {
        switch (this.$element.val()) {
            case 'false': return false;
            case 'true': return true;
            default: return null;
        }
    }
});
openerp.base.search.IntegerField = openerp.base.search.Field.extend({
    get_value: function () {
        if (!this.$element.val()) {
            return null;
        }
        var val = parseInt(this.$element.val());
        var check = Number(this.$element.val());
        if (isNaN(check) || val !== check) {
            this.$element.addClass('error');
            throw new openerp.base.search.Invalid(
                this.attrs.name, this.$element.val(), "not a valid integer");
        }
        this.$element.removeClass('error');
        return val;
    }
});
openerp.base.search.FloatField = openerp.base.search.Field.extend({
    get_value: function () {
        var val = Number(this.$element.val());
        if (isNaN(val)) {
            this.$element.addClass('error');
            throw new openerp.base.search.Invalid(
                this.attrs.name, this.$element.val(), "not a valid number");
        }
        this.$element.removeClass('error');
        return val;
    }
});
openerp.base.search.SelectionField = openerp.base.search.Field.extend({
    template: 'SearchView.field.selection',
    get_value: function () {
        return this.$element.val();
    }
});
/**
 * @class
 * @extends openerp.base.search.Field
 */
openerp.base.search.DateField = openerp.base.search.Field.extend(
    /** @lends openerp.base.search.DateField# */{
    template: 'SearchView.fields.date',
    /**
     * enables date picker on the HTML widgets
     */
    start: function () {
        this._super();
        this.$element.find('input').datepicker({
            dateFormat: 'yy-mm-dd'
        });
    },
    stop: function () {
        this.$element.find('input').datepicker('destroy');
    },
    /**
     * Returns an object with two optional keys ``from`` and ``to`` providing
     * the values for resp. the from and to sections of the date widget.
     *
     * If a key is absent, then the corresponding field was not filled.
     *
     * @returns {Object}
     */
    get_values: function () {
        var values_array = this.$element.find('input').serializeArray();

        var from = values_array[0].value;
        var to = values_array[1].value;

        var field_values = {};
        if (from) {
            field_values.from = from;
        }
        if (to) {
            field_values.to = to;
        }
        return field_values;
    },
    get_context: function () {
        var values = this.get_values();
        if (!this.attrs.context || _.isEmpty(values)) {
            return null;
        }
        return _.extend(
            {}, this.attrs.context,
            {own_values: {self: values}});
    },
    get_domain: function () {
        var values = this.get_values();
        if (_.isEmpty(values)) {
            return null;
        }
        var domain = this.attrs['filter_domain'];
        if (!domain) {
            domain = [];
            if (values.from) {
                domain.push([this.attrs.name, '>=', values.from]);
            }
            if (values.to) {
                domain.push([this.attrs.name, '<=', values.to]);
            }
            return domain;
        }

        return _.extend(
                {}, domain,
                {own_values: {self: values}});
    }
});
openerp.base.search.DateTimeField = openerp.base.search.DateField.extend({
    // TODO: time?
});
openerp.base.search.OneToManyField = openerp.base.search.IntegerField.extend({
    // TODO: .relation, .context, .domain
});
openerp.base.search.ManyToOneField = openerp.base.search.IntegerField.extend({
    // TODO: @widget
    // TODO: .relation, .selection, .context, .domain
});
openerp.base.search.ManyToManyField = openerp.base.search.IntegerField.extend({
    // TODO: .related_columns (Array), .context, .domain
});

openerp.base.search.custom_filters = new openerp.base.Registry({
    'char': 'openerp.base.search.ExtendedSearchProposition.Char',
    'datetime': 'openerp.base.search.ExtendedSearchProposition.DateTime'
});

openerp.base.search.ExtendedSearchProposition = openerp.base.BaseWidget.extend({
    template: 'SearchView.extended_search.proposition',
    identifier_prefix: 'extended-search-proposition',
    init: function (parent, fields) {
        this._super(parent);
        this.fields = _(fields).chain()
            .map(function(val, key) { return _.extend({}, val, {'name': key}); })
            .sortBy(function(field) {return field.string;})
            .value();
        this.attrs = {_: _, fields: this.fields, selected: null};
        this.value = null;
    },
    start: function () {
        this._super();
        this.select_field(this.fields.length > 0 ? this.fields[0] : null);
        var _this = this;
        this.$element.find(".searchview_extended_prop_field").change(function() {
            _this.changed();
        });
        var delete_btn = this.$element.find('.searchview_extended_delete_prop');
        delete_btn.click(function (e) {
            _this.stop();
        });
    },
    changed: function() {
        var nval = this.$element.find(".searchview_extended_prop_field").val();
        if(this.attrs.selected == null || nval != this.attrs.selected.name) {
            this.select_field(_.detect(this.fields, function(x) {return x.name == nval;}));
        }
    },
    /**
     * Selects the provided field object
     *
     * @param field a field descriptor object (as returned by fields_get, augmented by the field name)
     */
    select_field: function(field) {
        var _this = this;
        if(this.attrs.selected != null) {
            this.value.stop();
            this.value = null;
            this.$element.find('.searchview_extended_prop_op').html('');
        }
        this.attrs.selected = field;
        if(field == null) {
            return;
        }

        try {
            this.value = new (openerp.base.search.custom_filters.get_object(field.type))
                              (this);
            _.each(this.value.operators, function(operator) {
                var option = jQuery('<option>', {value: operator.value})
                    .text(operator.text)
                    .appendTo(_this.$element.find('.searchview_extended_prop_op'));
            });
            this.$element.find('.searchview_extended_prop_value').html(
                this.value.render({}));
            this.value.start();
        } catch (e) {
            if (! e instanceof openerp.base.KeyNotFound) {
                throw e;
            }
            this.attrs.selected = null;
            this.log('Unknow field type ' + e.key);
        }
    },
    get_proposition: function() {
        if ( this.attrs.selected == null)
            return null;
        var field = this.attrs.selected.name;
        var op =  this.$element.find('.searchview_extended_prop_op').val();
        var value = this.value.get_value();
        return [field, op, value];
    }
});

openerp.base.search.ExtendedSearchProposition.Char = openerp.base.BaseWidget.extend({
    template: 'SearchView.extended_search.proposition.char',
    identifier_prefix: 'extended-search-proposition-char',
    operators: [
        {value: "ilike", text: "contains"},
        {value: "not ilike", text: "doesn't contain"},
        {value: "=", text: "is equal to"},
        {value: "!=", text: "is not equal to"},
        {value: ">", text: "greater than"},
        {value: "<", text: "less than"},
        {value: ">=", text: "greater or equal than"},
        {value: "<=", text: "less or equal than"}
    ],
    get_value: function() {
        return this.$element.val();
    }
});
openerp.base.search.ExtendedSearchProposition.DateTime = openerp.base.BaseWidget.extend({
    template: 'SearchView.extended_search.proposition.char',
    identifier_prefix: 'extended-search-proposition-datetime',
    operators: [
        {value: "=", text: "is equal to"},
        {value: "!=", text: "is not equal to"},
        {value: ">", text: "greater than"},
        {value: "<", text: "less than"},
        {value: ">=", text: "greater or equal than"},
        {value: "<=", text: "less or equal than"}
    ],
    get_value: function() {
        return this.$element.val();
    }
});

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
