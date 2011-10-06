openerp.web.search = function(openerp) {
var QWeb = openerp.web.qweb;

openerp.web.SearchView = openerp.web.Widget.extend(/** @lends openerp.web.SearchView# */{
    template: "EmptyComponent",
    /**
     * @constructs openerp.web.SearchView
     * @extends openerp.web.Widget
     * 
     * @param parent
     * @param element_id
     * @param dataset
     * @param view_id
     * @param defaults
     */
    init: function(parent, dataset, view_id, defaults, hidden) {
        this._super(parent);
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;

        this.defaults = defaults || {};
        this.has_defaults = !_.isEmpty(this.defaults);

        this.inputs = [];
        this.enabled_filters = [];

        this.has_focus = false;

        this.hidden = !!hidden;
        this.headless = this.hidden && !this.has_defaults;

        this.ready = $.Deferred();
    },
    start: function() {
        this._super();
        if (this.hidden) {
            this.$element.hide();
        }
        if (this.headless) {
            this.ready.resolve();
        } else {
            this.rpc("/web/searchview/load", {"model": this.model, "view_id":this.view_id}, this.on_loaded);
        }
        return this.ready.promise();
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
                    new openerp.web.search.FilterGroup(
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
                    new openerp.web.search.Filter(
                        item, this));
            } else if (item.tag === 'separator') {
                // a separator is a no-op
            } else {
                if (item.tag === 'group') {
                    // TODO: group and field should be fetched from registries, maybe even filters
                    row.push(
                        new openerp.web.search.Group(
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
            row.push(new openerp.web.search.FilterGroup(filters, this));
        }

        return rows;
    },
    /**
     * Creates a field for the provided field descriptor item (which comes
     * from fields_view_get)
     *
     * @param {Object} item fields_view_get node for the field
     * @param {Object} field fields_get result for the field
     * @returns openerp.web.search.Field
     */
    make_field: function (item, field) {
        try {
            return new (openerp.web.search.fields.get_any(
                    [item.attrs.widget, field.type]))
                (item, field, this);
        } catch (e) {
            if (! e instanceof openerp.web.KeyNotFound) {
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
        var self = this,
           lines = this.make_widgets(
                data.fields_view['arch'].children,
                data.fields_view.fields);

        // for extended search view
        var ext = new openerp.web.search.ExtendedSearch(this, this.model);
        lines.push([ext]);
        this.inputs.push(ext);
        
        var render = QWeb.render("SearchView", {
            'view': data.fields_view['arch'],
            'lines': lines,
            'defaults': this.defaults
        });

        this.$element.html(render);
        this.$element.find(".oe_search-view-custom-filter-btn").click(ext.on_activate);

        var f = this.$element.find('form');
        this.$element.find('form')
                .submit(this.do_search)
                .bind('reset', this.do_clear);
        // start() all the widgets
        var widget_starts = _(lines).chain().flatten().map(function (widget) {
            return widget.start();
        }).value();

        $.when.apply(null, widget_starts).then(function () {
            self.ready.resolve();
        });
        
        this.reload_managed_filters();
    },
    reload_managed_filters: function() {
        var self = this;
        return this.rpc('/web/searchview/get_filters', {
            model: this.dataset.model
        }).then(function(result) {
            self.managed_filters = result;
            var filters = self.$element.find(".oe_search-view-filters-management");
            filters.html(QWeb.render("SearchView.managed-filters", {filters: result}));
            filters.change(self.on_filters_management);
        });
    },
    /**
     * Handle event when the user make a selection in the filters management select box.
     */
    on_filters_management: function(e) {
        var self = this;
        var select = this.$element.find(".oe_search-view-filters-management");
        var val = select.val();
        
        if (val.slice(0,1) == "_") { // useless action
            select.val("_filters");
            return;
        }
        if (val.slice(0, "get:".length) == "get:") {
            val = val.slice("get:".length);
            val = parseInt(val);
            var filter = this.managed_filters[val];
            this.on_search([filter.domain], [filter.context], []);
        } else if (val == "save_filter") {
            select.val("_filters");
            var data = this.build_search_data();
            var context = new openerp.web.CompoundContext();
            _.each(data.contexts, function(x) {
                context.add(x);
            });
            var domain = new openerp.web.CompoundDomain();
            _.each(data.domains, function(x) {
                domain.add(x);
            });
            var dial_html = QWeb.render("SearchView.managed-filters.add");
            var $dial = $(dial_html);
            $dial.dialog({
                modal: true,
                title: "Filter Entry",
                buttons: {
                    Cancel: function() {
                        $(this).dialog("close");
                    },
                    OK: function() {
                        $(this).dialog("close");
                        var name = $(this).find("input").val();
                        self.rpc('/web/searchview/save_filter', {
                            model: self.dataset.model,
                            context_to_save: context,
                            domain: domain,
                            name: name
                        }).then(function() {
                            self.reload_managed_filters();
                        });
                    }
                }
            });
        } else { // manage_filters
            select.val("_filters");
            this.do_action({
                res_model: 'ir.filters',
                views: [[false, 'list'], [false, 'form']],
                type: 'ir.actions.act_window',
                context: {"search_default_user_id": this.session.uid,
                "search_default_model_id": this.dataset.model},
                target: "current",
                limit : 80,
                auto_search : true
            });
        }
    },
    /**
     * Performs the search view collection of widget data.
     *
     * If the collection went well (all fields are valid), then triggers
     * :js:func:`openerp.web.SearchView.on_search`.
     *
     * If at least one field failed its validation, triggers
     * :js:func:`openerp.web.SearchView.on_invalid` instead.
     *
     * @param e jQuery event object coming from the "Search" button
     */
    do_search: function (e) {
        if (this.headless && !this.has_defaults) {
            return this.on_search([], [], []);
        }
        // reset filters management
        var select = this.$element.find(".oe_search-view-filters-management");
        select.val("_filters");

        if (e && e.preventDefault) { e.preventDefault(); }

        var data = this.build_search_data();

        if (data.errors.length) {
            this.on_invalid(data.errors);
            return;
        }

        this.on_search(data.domains, data.contexts, data.groupbys);
    },
    build_search_data: function() {
        var domains = [],
           contexts = [],
             errors = [];

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
                if (e instanceof openerp.web.search.Invalid) {
                    errors.push(e);
                } else {
                    throw e;
                }
            }
        });

        // TODO: do we need to handle *fields* with group_by in their context?
        var groupbys = _(this.enabled_filters)
                .chain()
                .map(function (filter) { return filter.get_context();})
                .compact()
                .value();
        return {domains: domains, contexts: contexts, errors: errors, groupbys: groupbys};
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
    do_clear: function () {
        this.$element.find('.filter_label, .filter_icon').removeClass('enabled');
        this.enabled_filters.splice(0);
        var string = $('a.searchview_group_string');
        _.each(string, function(str){
            $(str).closest('div.searchview_group').removeClass("expanded").addClass('folded');
         });
        this.$element.find('table:last').hide();

        $('.searchview_extended_groups_list').empty();
        setTimeout(this.on_clear);
    },
    /**
     * Triggered when the search view gets cleared
     *
     * @event
     */
    on_clear: function () {
        this.do_search();
    },
    /**
     * Called by a filter propagating its state changes
     *
     * @param {openerp.web.search.Filter} filter a filter which got toggled
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
openerp.web.search = {};
/**
 * Registry of search fields, called by :js:class:`openerp.web.SearchView` to
 * find and instantiate its field widgets.
 */
openerp.web.search.fields = new openerp.web.Registry({
    'char': 'openerp.web.search.CharField',
    'text': 'openerp.web.search.CharField',
    'boolean': 'openerp.web.search.BooleanField',
    'integer': 'openerp.web.search.IntegerField',
    'float': 'openerp.web.search.FloatField',
    'selection': 'openerp.web.search.SelectionField',
    'datetime': 'openerp.web.search.DateTimeField',
    'date': 'openerp.web.search.DateField',
    'many2one': 'openerp.web.search.ManyToOneField',
    'many2many': 'openerp.web.search.CharField',
    'one2many': 'openerp.web.search.CharField'
});
openerp.web.search.Invalid = openerp.web.Class.extend( /** @lends openerp.web.search.Invalid# */{
    /**
     * Exception thrown by search widgets when they hold invalid values,
     * which they can not return when asked.
     *
     * @constructs openerp.web.search.Invalid
     * @extends openerp.web.Class
     *
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
openerp.web.search.Widget = openerp.web.Widget.extend( /** @lends openerp.web.search.Widget# */{
    template: null,
    /**
     * Root class of all search widgets
     *
     * @constructs openerp.web.search.Widget
     * @extends openerp.web.Widget
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
openerp.web.search.add_expand_listener = function($root) {
    $root.find('a.searchview_group_string').click(function (e) {
        $root.toggleClass('folded expanded');
        e.stopPropagation();
        e.preventDefault();
    });
};
openerp.web.search.Group = openerp.web.search.Widget.extend({
    template: 'SearchView.group',
    init: function (view_section, view, fields) {
        this._super(view);
        this.attrs = view_section.attrs;
        this.lines = view.make_widgets(
            view_section.children, fields);
        this.make_id('group');
    },
    start: function () {
        this._super();
        openerp.web.search.add_expand_listener(this.$element);
        var widget_starts = _(this.lines).chain().flatten()
                .map(function (widget) { return widget.start(); })
            .value();
        return $.when.apply(null, widget_starts);
    }
});

openerp.web.search.Input = openerp.web.search.Widget.extend( /** @lends openerp.web.search.Input# */{
    /**
     * @constructs openerp.web.search.Input
     * @extends openerp.web.search.Widget
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
openerp.web.search.FilterGroup = openerp.web.search.Input.extend(/** @lends openerp.web.search.FilterGroup# */{
    template: 'SearchView.filters',
    /**
     * Inclusive group of filters, creates a continuous "button" with clickable
     * sections (the normal display for filters is to be a self-contained button)
     *
     * @constructs openerp.web.search.FilterGroup
     * @extends openerp.web.search.Input
     *
     * @param {Array<openerp.web.search.Filter>} filters elements of the group
     * @param {openerp.web.SearchView} view view in which the filters are contained
     */
    init: function (filters, view) {
        this._super(view);
        this.filters = filters;
        this.length = filters.length;
    },
    start: function () {
        this._super();
        _.each(this.filters, function (filter) {
            filter.start();
        });
    },
    get_context: function () { },
    /**
     * Handles domains-fetching for all the filters within it: groups them.
     */
    get_domain: function () {
        var domains = _(this.filters).chain()
            .filter(function (filter) { return filter.is_enabled(); })
            .map(function (filter) { return filter.attrs.domain; })
            .reject(_.isEmpty)
            .value();

        if (!domains.length) { return; }
        if (domains.length === 1) { return domains[0]; }
        for (var i=domains.length; --i;) {
            domains.unshift(['|']);
        }
        return _.extend(new openerp.web.CompoundDomain(), {
            __domains: domains
        });
    }
});
openerp.web.search.Filter = openerp.web.search.Input.extend(/** @lends openerp.web.search.Filter# */{
    template: 'SearchView.filter',
    /**
     * Implementation of the OpenERP filters (button with a context and/or
     * a domain sent as-is to the search view)
     *
     * @constructs openerp.web.search.Filter
     * @extends openerp.web.search.Input
     *
     * @param node
     * @param view
     */
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
    /**
     * Does not return anything: filter domain is handled at the FilterGroup
     * level
     */
    get_domain: function () { }
});
openerp.web.search.Field = openerp.web.search.Input.extend( /** @lends openerp.web.search.Field# */ {
    template: 'SearchView.field',
    default_operator: '=',
    /**
     * @constructs openerp.web.search.Field
     * @extends openerp.web.search.Input
     *
     * @param view_section
     * @param field
     * @param view
     */
    init: function (view_section, field, view) {
        this._super(view);
        this.attrs = _.extend({}, field, view_section.attrs);
        this.filters = new openerp.web.search.FilterGroup(_.map(
            view_section.children, function (filter_node) {
                return new openerp.web.search.Filter(
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
    /**
     * Function creating the returned domain for the field, override this
     * methods in children if you only need to customize the field's domain
     * without more complex alterations or tests (and without the need to
     * change override the handling of filter_domain)
     *
     * @param {String} name the field's name
     * @param {String} operator the field's operator (either attribute-specified or default operator for the field
     * @param {Number|String} value parsed value for the field
     * @returns {Array<Array>} domain to include in the resulting search
     */
    make_domain: function (name, operator, value) {
        return [[name, operator, value]];
    },
    get_domain: function () {
        var val = this.get_value();
        if (val === null || val === '') {
            return;
        }

        var domain = this.attrs['filter_domain'];
        if (!domain) {
            return this.make_domain(
                this.attrs.name,
                this.attrs.operator || this.default_operator,
                val);
        }
        return _.extend({}, domain, {own_values: {self: val}});
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
 * @extends openerp.web.search.Field
 */
openerp.web.search.CharField = openerp.web.search.Field.extend( /** @lends openerp.web.search.CharField# */ {
    default_operator: 'ilike',
    get_value: function () {
        return this.$element.val();
    }
});
openerp.web.search.NumberField = openerp.web.search.Field.extend(/** @lends openerp.web.search.NumberField# */{
    get_value: function () {
        if (!this.$element.val()) {
            return null;
        }
        var val = this.parse(this.$element.val()),
          check = Number(this.$element.val());
        if (isNaN(val) || val !== check) {
            this.$element.addClass('error');
            throw new openerp.web.search.Invalid(
                this.attrs.name, this.$element.val(), this.error_message);
        }
        this.$element.removeClass('error');
        return val;
    }
});
/**
 * @class
 * @extends openerp.web.search.NumberField
 */
openerp.web.search.IntegerField = openerp.web.search.NumberField.extend(/** @lends openerp.web.search.IntegerField# */{
    error_message: "not a valid integer",
    parse: function (value) {
        try {
            return openerp.web.parse_value(value, {'widget': 'integer'});
        } catch (e) {
            return NaN;
        }
    }
});
/**
 * @class
 * @extends openerp.web.search.NumberField
 */
openerp.web.search.FloatField = openerp.web.search.NumberField.extend(/** @lends openerp.web.search.FloatField# */{
    error_message: "not a valid number",
    parse: function (value) {
        try {
            return openerp.web.parse_value(value, {'widget': 'float'});
        } catch (e) {
            return NaN;
        }
    }
});
/**
 * @class
 * @extends openerp.web.search.Field
 */
openerp.web.search.SelectionField = openerp.web.search.Field.extend(/** @lends openerp.web.search.SelectionField# */{
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
    get_value: function () {
        var index = parseInt(this.$element.val(), 10);
        if (isNaN(index)) { return null; }
        var value = this.attrs.selection[index][0];
        if (value === false) { return null; }
        return value;
    }
});
openerp.web.search.BooleanField = openerp.web.search.SelectionField.extend(/** @lends openerp.web.search.BooleanField# */{
    /**
     * @constructs openerp.web.search.BooleanField
     * @extends openerp.web.search.BooleanField
     */
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
     * In the HTML, we only want/get strings, and our strings here are ``true``
     * and ``false``, so ensure we use precisely those by truth-testing the
     * default value (iif there is one in the view's defaults).
     *
     * @param {Object} defaults default values for this search view
     * @returns {String} rendered boolean field
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
/**
 * @class
 * @extends openerp.web.search.DateField
 */
openerp.web.search.DateField = openerp.web.search.Field.extend(/** @lends openerp.web.search.DateField# */{
    template: "SearchView.date",
    start: function () {
        this._super();
        this.datewidget = new openerp.web.DateWidget(this);
        this.datewidget.prependTo(this.$element);
        this.datewidget.$element.find("input").attr("size", 15);
        this.datewidget.$element.find("input").attr("autofocus",
            this.attrs.default_focus === '1' ? 'autofocus' : undefined);
        this.datewidget.set_value(this.defaults[this.attrs.name] || false);
    },
    get_value: function () {
        return this.datewidget.get_value() || null;
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
 * @extends openerp.web.DateField
 */
openerp.web.search.DateTimeField = openerp.web.search.DateField.extend(/** @lends openerp.web.search.DateTimeField# */{
    make_domain: function (name, operator, value) {
        return ['&', [name, '>=', value + ' 00:00:00'],
                     [name, '<=', value + ' 23:59:59']];
    }
});
openerp.web.search.ManyToOneField = openerp.web.search.CharField.extend({
    init: function (view_section, field, view) {
        this._super(view_section, field, view);
        var self = this;
        this.got_name = $.Deferred().then(function () {
            self.$element.val(self.name);
        });
        this.dataset = new openerp.web.DataSet(
                this.view, this.attrs['relation']);
    },
    start: function () {
        this._super();
        this.setup_autocomplete();
        var started = $.Deferred();
        this.got_name.then(function () { started.resolve();},
                           function () { started.resolve(); });
        return started.promise();
    },
    setup_autocomplete: function () {
        var self = this;
        this.$element.autocomplete({
            source: function (req, resp) {
                self.dataset.name_search(
                    req.term, self.attrs.domain, 'ilike', 8, function (data) {
                        resp(_.map(data, function (result) {
                            return {id: result[0], label: result[1]}
                        }));
                });
            },
            select: function (event, ui) {
                self.id = ui.item.id;
                self.name = ui.item.label;
            },
            delay: 0
        })
    },
    on_name_get: function (name_get) {
        if (!name_get.length) {
            delete this.id;
            this.got_name.reject();
            return;
        }
        this.name = name_get[0][1];
        this.got_name.resolve();
    },
    render: function (defaults) {
        if (defaults[this.attrs.name]) {
            this.id = defaults[this.attrs.name];
            if (this.id instanceof Array)
                this.id = this.id[0];
            // TODO: maybe this should not be completely removed
            delete defaults[this.attrs.name];
            this.dataset.name_get([this.id], $.proxy(this, 'on_name_get'));
        } else {
            this.got_name.reject();
        }
        return this._super(defaults);
    },
    make_domain: function (name, operator, value) {
        if (this.id && this.name) {
            if (value === this.name) {
                return [[name, '=', this.id]];
            } else {
                delete this.id;
                delete this.name;
            }
        }
        return this._super(name, operator, value);
    }
});

openerp.web.search.ExtendedSearch = openerp.web.OldWidget.extend({
    template: 'SearchView.extended_search',
    identifier_prefix: 'extended-search',
    init: function (parent, model) {
        this._super(parent);
        this.model = model;
    },
    add_group: function() {
        var group = new openerp.web.search.ExtendedSearchGroup(this, this.fields);
        group.appendTo(this.$element.find('.searchview_extended_groups_list'));
        this.check_last_element();
    },
    start: function () {
        this._super();
        if (!this.$element) {
            return; // not a logical state but sometimes it happens
        }
        this.$element.closest("table.oe-searchview-render-line").css("display", "none");
        var self = this;
        this.rpc("/web/searchview/fields_get",
            {"model": this.model}, function(data) {
            self.fields = data.fields;
            openerp.web.search.add_expand_listener(self.$element);
            self.$element.find('.searchview_extended_add_group').click(function (e) {
                self.add_group();
            });
        });
    },
    get_context: function() {
        return null;
    },
    get_domain: function() {
        if (!this.$element) {
            return null; // not a logical state but sometimes it happens
        }
        if(this.$element.closest("table.oe-searchview-render-line").css("display") == "none") {
            return null;
        }
        return _.reduce(this.widget_children,
            function(mem, x) { return mem.concat(x.get_domain());}, []);
    },
    on_activate: function() {
        this.add_group();
        var table = this.$element.closest("table.oe-searchview-render-line");
        table.css("display", "");
        if(this.$element.hasClass("folded")) {
            this.$element.toggleClass("folded expanded");
        }
    },
    hide: function() {
        var table = this.$element.closest("table.oe-searchview-render-line");
        table.css("display", "none");
        if(this.$element.hasClass("expanded")) {
            this.$element.toggleClass("folded expanded");
        }
    },
    check_last_element: function() {
        _.each(this.widget_children, function(x) {x.set_last_group(false);});
        if (this.widget_children.length >= 1) {
            this.widget_children[this.widget_children.length - 1].set_last_group(true);
        }
    }
});

openerp.web.search.ExtendedSearchGroup = openerp.web.OldWidget.extend({
    template: 'SearchView.extended_search.group',
    identifier_prefix: 'extended-search-group',
    init: function (parent, fields) {
        this._super(parent);
        this.fields = fields;
    },
    add_prop: function() {
        var prop = new openerp.web.search.ExtendedSearchProposition(this, this.fields);
        var render = prop.render({'index': this.widget_children.length - 1});
        this.$element.find('.searchview_extended_propositions_list').append(render);
        prop.start();
    },
    start: function () {
        this._super();
        var _this = this;
        this.add_prop();
        this.$element.find('.searchview_extended_add_proposition').click(function () {
            _this.add_prop();
        });
        this.$element.find('.searchview_extended_delete_group').click(function () {
            _this.stop();
        });
    },
    get_domain: function() {
        var props = _(this.widget_children).chain().map(function(x) {
            return x.get_proposition();
        }).compact().value();
        var choice = this.$element.find(".searchview_extended_group_choice").val();
        var op = choice == "all" ? "&" : "|";
        return choice == "none" ? ['!'] : [].concat(
            _.map(_.range(_.max([0,props.length - 1])), function() { return op; }),
            props);
    },
    stop: function() {
        var parent = this.widget_parent;
        if (this.widget_parent.widget_children.length == 1)
            this.widget_parent.hide();
        this._super();
        parent.check_last_element();
    },
    set_last_group: function(is_last) {
        this.$element.toggleClass('last_group', is_last);
    }
});

openerp.web.search.ExtendedSearchProposition = openerp.web.OldWidget.extend(/** @lends openerp.web.search.ExtendedSearchProposition# */{
    template: 'SearchView.extended_search.proposition',
    identifier_prefix: 'extended-search-proposition',
    /**
     * @constructs openerp.web.search.ExtendedSearchProposition
     * @extends openerp.web.OldWidget
     *
     * @param parent
     * @param fields
     */
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
        this.$element.find('.searchview_extended_delete_prop').click(function () {
            _this.stop();
        });
    },
    stop: function() {
        var parent;
        if (this.widget_parent.widget_children.length == 1)
            parent = this.widget_parent;
        this._super();
        if (parent)
            parent.stop();
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

        var type = field.type;
        try {
            openerp.web.search.custom_filters.get_object(type);
        } catch (e) {
            if (! e instanceof openerp.web.KeyNotFound) {
                throw e;
            }
            type = "char";
            console.log('Unknow field type ' + e.key);
        }
        this.value = new (openerp.web.search.custom_filters.get_object(type))
                          (this);
        if(this.value.set_field) {
            this.value.set_field(field);
        }
        _.each(this.value.operators, function(operator) {
            var option = jQuery('<option>', {value: operator.value})
                .text(operator.text)
                .appendTo(_this.$element.find('.searchview_extended_prop_op'));
        });
        this.$element.find('.searchview_extended_prop_value').html(
            this.value.render({}));
        this.value.start();
        
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

openerp.web.search.ExtendedSearchProposition.Char = openerp.web.OldWidget.extend({
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
openerp.web.search.ExtendedSearchProposition.DateTime = openerp.web.OldWidget.extend({
    template: 'SearchView.extended_search.proposition.empty',
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
        return this.datewidget.get_value();
    },
    start: function() {
        this._super();
        this.datewidget = new openerp.web.DateTimeWidget(this);
        this.datewidget.prependTo(this.$element);
    }
});
openerp.web.search.ExtendedSearchProposition.Date = openerp.web.OldWidget.extend({
    template: 'SearchView.extended_search.proposition.empty',
    identifier_prefix: 'extended-search-proposition-date',
    operators: [
        {value: "=", text: "is equal to"},
        {value: "!=", text: "is not equal to"},
        {value: ">", text: "greater than"},
        {value: "<", text: "less than"},
        {value: ">=", text: "greater or equal than"},
        {value: "<=", text: "less or equal than"}
    ],
    get_value: function() {
        return this.datewidget.get_value();
    },
    start: function() {
        this._super();
        this.datewidget = new openerp.web.DateWidget(this);
        this.datewidget.prependTo(this.$element);
    }
});
openerp.web.search.ExtendedSearchProposition.Integer = openerp.web.OldWidget.extend({
    template: 'SearchView.extended_search.proposition.integer',
    identifier_prefix: 'extended-search-proposition-integer',
    operators: [
        {value: "=", text: "is equal to"},
        {value: "!=", text: "is not equal to"},
        {value: ">", text: "greater than"},
        {value: "<", text: "less than"},
        {value: ">=", text: "greater or equal than"},
        {value: "<=", text: "less or equal than"}
    ],
    get_value: function() {
        try {
            return openerp.web.parse_value(this.$element.val(), {'widget': 'integer'});
        } catch (e) {
            return "";
        }
    }
});
openerp.web.search.ExtendedSearchProposition.Float = openerp.web.OldWidget.extend({
    template: 'SearchView.extended_search.proposition.float',
    identifier_prefix: 'extended-search-proposition-float',
    operators: [
        {value: "=", text: "is equal to"},
        {value: "!=", text: "is not equal to"},
        {value: ">", text: "greater than"},
        {value: "<", text: "less than"},
        {value: ">=", text: "greater or equal than"},
        {value: "<=", text: "less or equal than"}
    ],
    get_value: function() {
        try {
            return openerp.web.parse_value(this.$element.val(), {'widget': 'float'});
        } catch (e) {
            return "";
        }
    }
});
openerp.web.search.ExtendedSearchProposition.Selection = openerp.web.OldWidget.extend({
    template: 'SearchView.extended_search.proposition.selection',
    identifier_prefix: 'extended-search-proposition-selection',
    operators: [
        {value: "=", text: "is"},
        {value: "!=", text: "is not"}
    ],
    set_field: function(field) {
        this.field = field;
    },
    get_value: function() {
        return this.$element.val();
    }
});
openerp.web.search.ExtendedSearchProposition.Boolean = openerp.web.OldWidget.extend({
    template: 'SearchView.extended_search.proposition.boolean',
    identifier_prefix: 'extended-search-proposition-boolean',
    operators: [
        {value: "=", text: "is true"},
        {value: "!=", text: "is false"}
    ],
    get_value: function() {
        return true;
    }
});

openerp.web.search.custom_filters = new openerp.web.Registry({
    'char': 'openerp.web.search.ExtendedSearchProposition.Char',
    'text': 'openerp.web.search.ExtendedSearchProposition.Char',
    'one2many': 'openerp.web.search.ExtendedSearchProposition.Char',
    'many2one': 'openerp.web.search.ExtendedSearchProposition.Char',
    'many2many': 'openerp.web.search.ExtendedSearchProposition.Char',
    
    'datetime': 'openerp.web.search.ExtendedSearchProposition.DateTime',
    'date': 'openerp.web.search.ExtendedSearchProposition.Date',
    'integer': 'openerp.web.search.ExtendedSearchProposition.Integer',
    'float': 'openerp.web.search.ExtendedSearchProposition.Float',
    'boolean': 'openerp.web.search.ExtendedSearchProposition.Boolean',
    'selection': 'openerp.web.search.ExtendedSearchProposition.Selection'
});

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
