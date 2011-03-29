/*---------------------------------------------------------
 * OpenERP base library
 *---------------------------------------------------------*/

openerp.base$views = function(openerp) {

// process all kind of actions
openerp.base.ActionManager = openerp.base.Controller.extend({
    init: function(session, element_id) {
        this._super(session, element_id);
        this.action = null;
        this.viewmanager = null;
    },
    /**
     * Process an action
     * Supported actions: act_window
     */
    do_action: function(action) {
        // instantiate the right controllers by understanding the action
        this.action = action;
        if(action.type == "ir.actions.act_window") {
            this.viewmanager = new openerp.base.ViewManager(this.session,this.element_id);
            this.viewmanager.do_action_window(action);
            this.viewmanager.start();
        }
    }
});

// This will be ViewManager Abstract/Common
openerp.base.ViewManager =  openerp.base.Controller.extend({
    init: function(session, element_id) {
        this._super(session, element_id);
        this.action = null;
        this.dataset = null;
        this.searchview_id = false;
        this.searchview = null;
        this.search_visible = true;
        // this.views = { "list": { "view_id":1234, "controller": instance} }
        this.views = {};
    },
    start: function() {
    },
    on_mode_switch: function(view_type) {
        for (var i in this.views) {
           this.views[i].controller.$element.toggle(i === view_type);
        }
    },
    /**
     * Extract search view defaults from the current action's context.
     *
     * These defaults are of the form {search_default_*: value}
     *
     * @returns {Object} a clean defaults mapping of {field_name: value}
     */
    search_defaults: function () {
        var defaults = {};
        _.each(this.action.context, function (value, key) {
            var match = /^search_default_(.*)$/.exec(key);
            if (match) {
                defaults[match[1]] = value;
            }
        });
        return defaults;
    },
    do_action_window: function(action) {
        var self = this;
        var prefix_id = "#" + this.element_id;
        this.action = action;
        this.dataset = new openerp.base.DataSet(this.session, action.res_model);
        this.dataset.start();

        this.$element.html(QWeb.render("ViewManager", {"prefix": this.element_id, views: action.views}));

        this.searchview_id = false;
        if(this.search_visible && action.search_view_id) {
            this.searchview_id = action.search_view_id[0];
            var searchview = this.searchview = new openerp.base.SearchView(
                    this.session, this.element_id + "_search",
                    this.dataset, this.searchview_id,
                    this.search_defaults());
            searchview.on_search.add(this.do_search);
            searchview.start();

            if (action['auto_search']) {
                searchview.on_loaded.add_last(
                    searchview.do_search);
            }
        }
        for(var i = 0; i < action.views.length; i++)  {
            var view_id, controller;
            view_id = action.views[i][0];
            if(action.views[i][1] == "tree") {
                controller = new openerp.base.ListView(this.session, this.element_id + "_view_tree", this.dataset, view_id);
                controller.start();
                this.views.tree = { view_id: view_id, controller: controller };
                this.$element.find(prefix_id + "_button_tree").bind('click',function(){
                    self.on_mode_switch("tree");
                });
            } else if(action.views[i][1] == "form") {
                controller = new openerp.base.FormView(this.session, this.element_id + "_view_form", this.dataset, view_id);
                controller.start();
                this.views.form = { view_id: view_id, controller: controller };
                this.$element.find(prefix_id + "_button_form").bind('click',function(){
                   self.on_mode_switch("form");
                });
            }
        }
        // switch to the first one in sequence
        this.on_mode_switch("tree");
    },
    // create when root, also add to parent when o2m
    on_create: function() {
    },
    on_remove: function() {
    },
    on_edit: function() {
    },
    do_search: function (domains, contexts, groupbys) {
        var self = this;
        this.rpc('/base/session/eval_domain_and_context', {
            domains: domains,
            contexts: contexts,
            group_by_seq: groupbys
        }, function (results) {
            // TODO: handle non-empty results.group_by with read_group
            self.dataset.set({
                context: results.context,
                domain: results.domain
            }).fetch(0, self.action.limit);
        });
    }
});

// Extends view manager
openerp.base.ViewManagerRoot = openerp.base.Controller.extend({
});

// Extends view manager
openerp.base.ViewManagerUsedAsAMany2One = openerp.base.Controller.extend({
});

/**
 * Management interface between views and the collection of selected OpenERP
 * records (represents the view's state?)
 */
openerp.base.DataSet =  openerp.base.Controller.extend({
    init: function(session, model) {
        this._super(session);
        this.model = model;

        this._fields = null;

        this._ids = [];
        this._active_ids = null;
        this._active_id_index = 0;

        this._sort = [];
        this._domain = [];
        this._context = {};
    },
    start: function() {
        // TODO: fields_view_get fields selection?
        this.rpc("/base/dataset/fields", {"model":this.model}, this.on_fields);
    },
    on_fields: function(result) {
        this._fields = result._fields;
        this.on_ready();
    },

    /**
     * Fetch all the records selected by this DataSet, based on its domain
     * and context.
     *
     * Fires the on_ids event.
     *
     * @param {Number} [offset=0] The index from which selected records should be returned
     * @param {Number} [limit=null] The maximum number of records to return
     * @returns itself
     */
    fetch: function (offset, limit) {
        offset = offset || 0;
        limit = limit || null;
        this.rpc('/base/dataset/find', {
            model: this.model,
            fields: this._fields,
            domain: this._domain,
            context: this._context,
            sort: this._sort,
            offset: offset,
            limit: limit
        }, _.bind(function (records) {
            var data_records = _.map(
                records, function (record) {
                    return new openerp.base.DataRecord(
                        this.session, this.model,
                        this._fields, record);
                }, this);

            this.on_fetch(data_records, {
                offset: offset,
                limit: limit,
                domain: this._domain,
                context: this._context,
                sort: this._sort
            });
        }, this));
        return this;
    },
    /**
     * @event
     *
     * Fires after the DataSet fetched the records matching its internal ids selection
     * 
     * @param {Array} records An array of the DataRecord fetched
     * @param event The on_fetch event object
     * @param {Number} event.offset the offset with which the original DataSet#fetch call was performed
     * @param {Number} event.limit the limit set on the original DataSet#fetch call
     * @param {Array} event.domain the domain set on the DataSet before DataSet#fetch was called
     * @param {Object} event.context the context set on the DataSet before DataSet#fetch was called
     * @param {Array} event.sort the sorting criteria used to get the ids
     */
    on_fetch: function (records, event) { },

    /**
     * Fetch all the currently active records for this DataSet (records selected via DataSet#select)
     *
     * @returns itself
     */
    active_ids: function () {
        this.rpc('/base/dataset/get', {
            ids: this.get_active_ids(),
            model: this.model
        }, _.bind(function (records) {
            this.on_active_ids(_.map(
                records, function (record) {
                    return new openerp.base.DataRecord(
                        this.session, this.model,
                        this._fields, record);
                }, this));
        }, this));
        return this;
    },
    /**
     * @event
     *
     * Fires after the DataSet fetched the records matching its internal active ids selection
     *
     * @param {Array} records An array of the DataRecord fetched
     */
    on_active_ids: function (records) { },

    /**
     * Fetches the current active record for this DataSet
     *
     * @returns itself
     */
    active_id: function () {
        this.rpc('/base/dataset/get', {
            ids: [this.get_active_id()],
            model: this.model
        }, _.bind(function (records) {
            var record = records[0];
            this.on_active_id(
                record && new openerp.base.DataRecord(
                        this.session, this.model,
                        this._fields, record));
        }, this));
        return this;
    },
    /**
     * Fires after the DataSet fetched the record matching the current active record
     *
     * @param record the record matching the provided id, or null if there is no record for this id
     */
    on_active_id: function (record) {

    },

    /**
     * Configures the DataSet
     * 
     * @param options DataSet options
     * @param {Array} options.domain the domain to assign to this DataSet for filtering
     * @param {Object} options.context the context this DataSet should use during its calls
     * @param {Array} options.sort the sorting criteria for this DataSet
     * @returns itself
     */
    set: function (options) {
        if (options.domain) {
            this._domain = _.clone(options.domain);
        }
        if (options.context) {
            this._context = _.clone(options.context);
        }
        if (options.sort) {
            this._sort = _.clone(options.sort);
        }
        return this;
    },

    /**
     * Activates the previous id in the active sequence. If there is no previous id, wraps around to the last one
     * @returns itself
     */
    prev: function () {
        this._active_id_index -= 1;
        if (this._active_id_index < 0) {
            this._active_id_index = this._active_ids.length - 1;
        }
        return this;
    },
    /**
     * Activates the next id in the active sequence. If there is no next id, wraps around to the first one
     * @returns itself
     */
    next: function () {
        this._active_id_index += 1;
        if (this._active_id_index >= this._active_ids.length) {
            this._active_id_index = 0;
        }
        return this;
    },

    /**
     * Sets active_ids by value:
     *
     * * Activates all ids part of the current selection
     * * Sets active_id to be the first id of the selection
     *
     * @param {Array} ids the list of ids to activate
     * @returns itself
     */
    select: function (ids) {
        this._active_ids = ids;
        this._active_id_index = 0;
        return this;
    },
    /**
     * Fetches the ids of the currently selected records, if any.
     */
    get_active_ids: function () {
        return this._active_ids;
    },
    /**
     * Sets the current active_id by value
     *
     * If there are no active_ids selected, selects the provided id as the sole active_id
     *
     * If there are ids selected and the provided id is not in them, raise an error
     *
     * @param {Object} id the id to activate
     * @returns itself
     */
    activate: function (id) {
        if(!this._active_ids) {
            this._active_ids = [id];
            this._active_id_index = 0;
        } else {
            var index = _.indexOf(this._active_ids, id);
            if (index == -1) {
                throw new Error(
                    "Could not find id " + id +
                    " in array [" + this._active_ids.join(', ') + "]");
            }
            this._active_id_index = index;
        }
        return this;
    },
    /**
     * Fetches the id of the current active record, if any.
     *
     * @returns record? record id or <code>null</code>
     */
    get_active_id: function () {
        if (!this._active_ids) {
            return null;
        }
        return this._active_ids[this._active_id_index];
    }
});

openerp.base.DataRecord =  openerp.base.Controller.extend({
    init: function(session, model, fields, values) {
        this._super(session, null);
        this.model = model;
        this.id = values.id || null;
        this.fields = fields;
        this.values = values;
    },
    on_change: function() {
    },
    on_reload: function() {
    }
});

/**
 * Base class for widgets. Handle rendering (based on a QWeb template), identifier
 * generation, parenting and destruction of the widget.
 */
openerp.base.BaseWidget = openerp.base.Controller.extend({
	/**
	 * The name of the QWeb template that will be used for rendering. Must be redifined
	 * in subclasses or the render() method can not be used.
	 * 
	 * @type string
	 */
    template: null,
    /**
     * The prefix used to generate an id automatically. Should be redifined in subclasses.
     * If it is not defined, the make_id() method must be explicitly called.
     * 
     * @type string
     */
    identifier_prefix: null,
    /**
     * Contructor.
     * 
     * @params {openerp.base.search.BaseWidget} parent The parent widget.
     */
    init: function (parent) {
		this.children = [];
        this.parent = parent;
        if(parent != null) {
        	parent.children.push(this);
        }
        if(this.identifier_prefix != null) {
        	this.make_id(this.identifier_prefix);
        }
    },
    /**
     * Sets and returns a globally unique identifier for the widget.
     *
     * If a prefix is appended, the identifier will be appended to it.
     *
     * @params sections prefix sections, empty/falsy sections will be removed
     */
    make_id: function () {
        this.element_id = _.uniqueId(_.toArray(arguments).join('_'));
        return this.element_id;
    },
    /**
     * "Starts" the widgets. Called at the end of the rendering, this allows
     * to get a jQuery object referring to the DOM ($element attribute).
     */
    start: function () {
        this._super();
        if (this.element_id) {
            this.$element = $(document.getElementById(
                this.element_id));
        }
    },
    /**
     * "Stops" the widgets. Called when the view destroys itself, this
     * lets the widgets clean up after themselves.
     */
    stop: function () {
    	var tmp_children = this.children;
    	this.children = [];
    	_.each(tmp_children, function(x) {
    		x.stop();
    	});
    	if(this.$element != null) {
    		this.$element.remove();
    	}
    	if(this.parent != null) {
    		var _this = this;
    		this.parent.children = _.reject(this.parent.children, function(x) { return x === _this;});
            this.parent = null;
    	}
        this._super();
    },
    /**
     * Render the widget. This.template must be defined.
     * The content of the current object is passed as context to the template.
     * 
     * @param {object} additional Additional context arguments to pass to the template.
     */
    render: function (additional) {
        return QWeb.render(this.template, _.extend({}, this,
        		additional != null ? additional : {}));
    }
});

openerp.base.SearchView = openerp.base.Controller.extend({
    init: function(session, element_id, dataset, view_id, defaults) {
        this._super(session, element_id);
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;

        this.defaults = defaults || {};

        this.inputs = [];
        this.enabled_filters = [];
    },
    start: function() {
        //this.log('Starting SearchView '+this.model+this.view_id)
        this.rpc("/base/searchview/load", {"model": this.model, "view_id":this.view_id}, this.on_loaded);
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
        // TODO: should fetch from an actual registry
        // TODO: register fields in self?
        switch (field.type) {
            case 'char':
            case 'text':
                return new openerp.base.search.CharField(
                    item, field, this);
            case 'boolean':
                return new openerp.base.search.BooleanField(
                    item, field, this);
            case 'integer':
                return new openerp.base.search.IntegerField(
                    item, field, this);
            case 'float':
                return new openerp.base.search.FloatField(
                    item, field, this);
            case 'selection':
                return new openerp.base.search.SelectionField(
                    item, field, this);
            case 'datetime':
                return new openerp.base.search.DateTimeField(
                    item, field, this);
            case 'date':
                return new openerp.base.search.DateField(
                    item, field, this);
            case 'one2many':
                return new openerp.base.search.OneToManyField(
                    item, field, this);
            case 'many2one':
                return new openerp.base.search.ManyToOneField(
                    item, field, this);
            case 'many2many':
                return new openerp.base.search.ManyToManyField(
                    item, field, this);
            default:
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
        lines.push([new openerp.base.search.ExtendedSearch(null, data.fields_view.fields)]);
        
        var render = QWeb.render("SearchView", {
            'view': data.fields_view['arch'],
            'lines': lines,
            'defaults': this.defaults
        });
        this.$element.html(render);

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
    on_search: function (domains, contexts, groupbys) { },
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
    on_invalid: function (errors) { },
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

openerp.base.search = {};
openerp.base.search.Invalid = Class.extend({
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
openerp.base.search.Widget = openerp.base.Controller.extend({
    template: null,
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
	add_group: function(group) {
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
            e.stopPropagation();
            e.preventDefault();
        });
        // TODO: remove test
        this.$element.find('.test_get_domain').click(function (e) {
        	_this.$element.find('.test_domain').text(JSON.stringify(_this.get_domain()));
            e.stopPropagation();
            e.preventDefault();
        });
	},
	get_domain: function() {
		var domain = _.reduce(this.children,
				function(mem, x) { return mem.concat(x.get_domain());}, []);
		return domain;
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
            e.stopPropagation();
            e.preventDefault();
        });
        var delete_btn = this.$element.find('.searchview_extended_delete_group');
        delete_btn.click(function (e) {
        	_this.stop();
            e.stopPropagation();
            e.preventDefault();
        });
	},
	get_domain: function() {
		var props = _(this.children).chain().map(function(x) {
			return x.get_proposition();
		}).compact().value();
		var choice = this.$element.find(".searchview_extended_group_choice").val();
		var op = choice == "all" ? "&" : "|";
		var domain = [].concat(choice == "none" ? ['!'] : [],
				_.map(_.range(_.max([0,props.length - 1])), function(x) { return op; }),
				props);
		return domain;
	}
});

openerp.base.search.extended_filters_types = {
	char: {
		operators: [
		            {value: "ilike", text: "contains"},
		            {value: "not like", text: "doesn't contain"},
		            {value: "=", text: "is equal to"},
		            {value: "!=", text: "is not equal to"},
		            {value: ">", text: "greater than"},
		            {value: "<", text: "less than"},
		            {value: ">=", text: "greater or equal than"},
		            {value: "<=", text: "less or equal than"},
		],
		build_component: function(parent) {
			return new openerp.base.search.ExtendedSearchProposition.Char(parent);
		}
	}
};

openerp.base.search.ExtendedSearchProposition = openerp.base.BaseWidget.extend({
    template: 'SearchView.extended_search.proposition',
    identifier_prefix: 'extended-search-proposition',
    init: function (parent, fields) {
	    this._super(parent);
	    this.fields = _(fields).chain()
	    	.map(function(val,key) {return {name:key, obj:val};})
	    	.sortBy(function(x) {return x.obj.string;}).value();
	    this.attrs = {_: _, fields: this.fields, selected: null};
	    this.value_component = null;
	},
    start: function () {
        this._super();
	    this.set_selected(this.fields.length > 0 ? this.fields[0] : null);
	    var _this = this;
	    this.$element.find(".searchview_extended_prop_field").change(function(e) {
	    	_this.changed();
            e.stopPropagation();
            e.preventDefault();
	    });
	    var delete_btn = this.$element.find('.searchview_extended_delete_prop');
	    delete_btn.click(function (e) {
        	_this.stop();
            e.stopPropagation();
            e.preventDefault();
        });
	},
	changed: function() {
		var nval = this.$element.find(".searchview_extended_prop_field").val();
		if(this.attrs.selected == null || nval != this.attrs.selected.name) {
			this.set_selected(_.detect(this.fields, function(x) {return x.name == nval;}));
		}
	},
	set_selected: function(selected) {
		var _this = this;
		if(this.attrs.selected != null) {
			this.value_component.stop();
			this.value_component = null;
			this.$element.find('.searchview_extended_prop_op').html('');
		}
		this.attrs.selected = selected;
		if(selected == null) {
			return;
		}
		var type = selected.obj.type;
		var extended_filters_types = openerp.base.search.extended_filters_types;
		type = type in extended_filters_types ? type : "char";
		_.each(extended_filters_types[type].operators, function(operator) {
			option = jQuery('<option/>');
			option.attr('value', operator.value);
			option.text(operator.text);
			option.appendTo(_this.$element.find('.searchview_extended_prop_op'));
		});
		this.value_component = extended_filters_types[type].build_component(this);
		var render = this.value_component.render({});
		this.$element.find('.searchview_extended_prop_value').html(render);
		this.value_component.start();
	},
	get_proposition: function() {
		if ( this.attrs.selected == null)
			return null;
		var field = this.attrs.selected.name;
		var op =  this.$element.find('.searchview_extended_prop_op').val();
		var value = this.value_component.get_value();
		return [field, op, value];
	}
});

openerp.base.search.ExtendedSearchProposition.Char = openerp.base.BaseWidget.extend({
    template: 'SearchView.extended_search.proposition.char',
    identifier_prefix: 'extended-search-proposition-char',
    
    get_value: function() {
		var val = this.$element.val();
		return val;
	}
});

openerp.base.search.Input = openerp.base.search.Widget.extend({
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
        this.$element.click(function () {
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
openerp.base.search.Field = openerp.base.search.Input.extend({
    template: 'SearchView.field',
    default_operator: '=',
    // TODO: set default values
    // TODO: get context, domain
    // TODO: holds Filters
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
openerp.base.search.CharField = openerp.base.search.Field.extend({
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
openerp.base.search.DateTimeField = openerp.base.search.Field.extend({
    get_value: function () {
        return this.$element.val();
    }
});
openerp.base.search.DateField = openerp.base.search.Field.extend({
    get_value: function () {
        return this.$element.val();
    }
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

openerp.base.FormView =  openerp.base.Controller.extend({
    init: function(session, element_id, dataset, view_id) {
        this._super(session, element_id);
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;
        this.fields_views = {};
        this.widgets = {};
        this.widgets_counter = 0;
        this.fields = {};
        this.datarecord = {};
    },
    start: function() {
        //this.log('Starting FormView '+this.model+this.view_id)
        this.rpc("/base/formview/load", {"model": this.model, "view_id": this.view_id}, this.on_loaded);
    },
    on_loaded: function(data) {
        this.fields_view = data.fields_view;
        //this.log(this.fields_view);

        var frame = new openerp.base.WidgetFrame(this, this.fields_view.arch);

        this.$element.html(QWeb.render("FormView", { "frame": frame, "view": this }));
        for (var i in this.widgets) {
            this.widgets[i].start();
        }
        // bind to all wdigets that have onchange ??

        this.dataset.on_active_id.add(this.on_record_loaded);
    },
    on_record_loaded: function(record) {
        this.datarecord = record;
        for (var f in this.fields) {
            this.fields[f].set_value(this.datarecord.values[f]);
        }
    }
});

openerp.base.ListView = openerp.base.Controller.extend({
    init: function(session, element_id, dataset, view_id) {
        this._super(session, element_id);
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;
        this.name = "";

        this.cols = [];

        this.$table = null;
        this.colnames = [];
        this.colmodel = [];

        this.event_loading = false; // TODO in the future prevent abusive click by masking
    },
    start: function() {
        //this.log('Starting ListView '+this.model+this.view_id)
        this.rpc("/base/listview/load", {"model": this.model, "view_id":this.view_id}, this.on_loaded);
    },
    on_loaded: function(data) {
        this.fields_view = data.fields_view;
        //this.log(this.fields_view);
        this.name = "" + this.fields_view.arch.attrs.string;
        this.$element.html(QWeb.render("ListView", {"fields_view": this.fields_view}));
        this.$table = this.$element.find("table");
        this.cols = [];
        this.colnames = [];
        this.colmodel = [];
        // TODO uss a object for each col, fill it with view and fallback to dataset.model_field
        var tree = this.fields_view.arch.children;
        for(var i = 0; i < tree.length; i++)  {
            var col = tree[i];
            if(col.tag == "field") {
                this.cols.push(col.attrs.name);
                this.colnames.push(col.attrs.name);
                this.colmodel.push({ name: col.attrs.name, index: col.attrs.name });
            }
        }
        this.dataset.fields = this.cols;
        this.dataset.on_fetch.add(this.do_fill_table);
        
        var width = this.$element.width();
        this.$table.jqGrid({
            datatype: "local",
            height: "100%",
            rowNum: 100,
            //rowList: [10,20,30],
            colNames: this.colnames,
            colModel: this.colmodel,
            //pager: "#plist47",
            viewrecords: true,
            caption: this.name
        }).setGridWidth(width);

        var self = this;
        $(window).bind('resize', function() {
            self.$element.children().hide();
            self.$table.setGridWidth(self.$element.width());
            self.$element.children().show();
        }).trigger('resize');
    },
    do_fill_table: function(records) {
        this.log("do_fill_table");

        this.$table
            .clearGridData()
            .addRowData('id', _.map(records, function (record) {
                return record.values;
            }));

    }
});

openerp.base.TreeView = openerp.base.Controller.extend({
});



openerp.base.Widget = openerp.base.Controller.extend({
    // TODO Change this to init: function(view, node) { and use view.session and a new element_id for the super
    // it means that widgets are special controllers
    init: function(view, node) {
        this.view = view;
        this.node = node;
        this.type = this.type || node.tag;
        this.element_name = this.element_name || this.type;
        this.element_id = [this.view.element_id, this.element_name, this.view.widgets_counter++].join("_");

        this._super(this.view.session, this.element_id);

        this.view.widgets[this.element_id] = this;
        this.children = node.children;
        this.colspan = parseInt(node.attrs.colspan || 1);
        this.template = "Widget";

        this.string = this.string || node.attrs.string;
        this.help = this.help || node.attrs.help;
        this.invisible = (node.attrs.invisible == '1');
    },
    start: function() {
        this.$element = $('#' + this.element_id);
    },
    render: function() {
        var template = this.template;
        return QWeb.render(template, { "widget": this });
    }
});

openerp.base.WidgetFrame = openerp.base.Widget.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "WidgetFrame";
        this.columns = node.attrs.col || 4;
        this.x = 0;
        this.y = 0;
        this.table = [];
        this.add_row();
        for (var i = 0; i < node.children.length; i++) {
            var n = node.children[i];
            if (n.tag == "newline") {
                this.add_row();
            } else {
                this.handle_node(n);
            }
        }
        this.set_row_cells_with(this.table[this.table.length - 1]);
    },
    add_row: function(){
        if (this.table.length) {
            this.set_row_cells_with(this.table[this.table.length - 1]);
        }
        var row = [];
        this.table.push(row);
        this.x = 0;
        this.y += 1;
        return row;
    },
    set_row_cells_with: function(row) {
        for (var i = 0; i < row.length; i++) {
            var w = row[i];
            if (w.is_field_label) {
                w.width = "1%";
                if (row[i + 1]) {
                    row[i + 1].width = Math.round((100 / this.columns) * (w.colspan + 1) - 1) + '%';
                }
            } else if (w.width === undefined) {
                w.width = Math.round((100 / this.columns) * w.colspan) + '%';
            }
        }
    },
    handle_node: function(n) {
        var type = this.view.fields_view.fields[n.attrs.name] || {};
        var widget_type = n.attrs.widget || type.type || n.tag;
        if (openerp.base.widgets[widget_type]) {
            var widget = new openerp.base.widgets[widget_type](this.view, n);
            if (n.tag == 'field' && n.attrs.nolabel != '1') {
                var label = new openerp.base.widgets['label'](this.view, n);
                label["for"] = widget;
                this.add_widget(label);
            }
            this.add_widget(widget);
        } else {
            this.log("Unhandled widget type : " + widget_type, n);
        }
    },
    add_widget: function(w) {
        if (!w.invisible) {
            var current_row = this.table[this.table.length - 1];
            if (current_row.length && (this.x + w.colspan) > this.columns) {
                current_row = this.add_row();
            }
            current_row.push(w);
            this.x += w.colspan;
        }
        return w;
    }
});

openerp.base.WidgetNotebook = openerp.base.Widget.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "WidgetNotebook";
        this.pages = [];
        for (var i = 0; i < node.children.length; i++) {
            var n = node.children[i];
            if (n.tag == "page") {
                var page = new openerp.base.WidgetFrame(this.view, n);
                this.pages.push(page);
            }
        }
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$element.tabs();
    }
});

openerp.base.WidgetSeparator = openerp.base.Widget.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "WidgetSeparator";
    }
});

openerp.base.WidgetButton = openerp.base.Widget.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "WidgetButton";
    }
});

openerp.base.WidgetLabel = openerp.base.Widget.extend({
    init: function(view, node) {
        this.is_field_label = true;
        this.element_name = 'label_' + node.attrs.name;

        this._super(view, node);

        this.template = "WidgetLabel";
        this.colspan = 1;
    },
    render: function () {
        if (this['for'] && this.type !== 'label') {
            return QWeb.render(this.template, {widget: this['for']});
        }
        // Actual label widgets should not have a false and have type label
        return QWeb.render(this.template, {widget: this});
    }
});

openerp.base.Field = openerp.base.Widget.extend({
    init: function(view, node) {
        this.name = node.attrs.name;
        view.fields[this.name] = this;
        this.type = node.attrs.widget || view.fields_view.fields[node.attrs.name].type;
        this.element_name = "field_" + this.name + "_" + this.type;
        this.original_value;

        this._super(view, node);

        if (node.attrs.nolabel != '1' && this.colspan > 1) {
            this.colspan--;
        }
        // this.datarecord = this.view.datarecord ??
        this.field = view.fields_view.fields[node.attrs.name];
        this.string = node.attrs.string || this.field.string;
        this.help = node.attrs.help || this.field.help;
        this.nolabel = (node.attrs.nolabel == '1');
    },
    set_value: function(value) {
        this.original_value = value;
    }
});

openerp.base.FieldChar = openerp.base.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldChar";
    },
    start: function() {
        this._super.apply(this, arguments);
        // this.$element.bind('change',)  ... blur, focus, ...
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        if (value != null && value !== false) {
            this.$element.find('input').val(this.to_string(value));
        }
    },
    get_value: function() {
        return this.from_string(this.$element.find('input').val());
    },
    to_string: function(value) {
        return value.toString();
    },
    from_string: function(value) {
        return value.toString();
    },
    on_change: function() {
        //this.view.update_field(this.name,value);
    }
});

openerp.base.FieldEmail = openerp.base.FieldChar.extend({
});

openerp.base.FieldUrl = openerp.base.FieldChar.extend({
});

openerp.base.FieldFloat = openerp.base.FieldChar.extend({
    to_string: function(value) {
        return value.toFixed(2);
    }
});

openerp.base.FieldText = openerp.base.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldText";
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        if (value != null && value !== false) {
            this.$element.find('textarea').val(value);
        }
    },
    get_value: function() {
        return this.$element.find('textarea').val();
    }
});

openerp.base.FieldBoolean = openerp.base.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldBoolean";
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        this.$element.find('input')[0].checked = value;
    },
    get_value: function() {
        this.$element.find('input')[0].checked;
    }
});

openerp.base.FieldDate = openerp.base.FieldChar.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldDate";
    }
});

openerp.base.FieldDatetime = openerp.base.FieldChar.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldDatetime";
    }
});

openerp.base.FieldTextXml = openerp.base.Field.extend({
// to replace view editor
});

openerp.base.FieldSelection = openerp.base.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldSelection";
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        if (value != null && value !== false) {
            this.$element.find('select').val(value);
        }
    },
    get_value: function() {
        return this.$element.find('select').val();
    }
});

openerp.base.FieldMany2One = openerp.base.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldMany2One";
    }
});

openerp.base.FieldOne2Many = openerp.base.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldOne2Many";
    }
});

openerp.base.FieldMany2Many = openerp.base.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldMany2Many";
    }
});

openerp.base.FieldReference = openerp.base.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldReference";
    }
});

openerp.base.widgets = {
    'group' : openerp.base.WidgetFrame,
    'notebook' : openerp.base.WidgetNotebook,
    'separator' : openerp.base.WidgetSeparator,
    'label' : openerp.base.WidgetLabel,
    'char' : openerp.base.FieldChar,
    'email' : openerp.base.FieldEmail,
    'url' : openerp.base.FieldUrl,
    'text' : openerp.base.FieldText,
    'date' : openerp.base.FieldDate,
    'datetime' : openerp.base.FieldDatetime,
    'selection' : openerp.base.FieldSelection,
    'many2one' : openerp.base.FieldMany2One,
    'many2many' : openerp.base.FieldMany2Many,
    'one2many' : openerp.base.FieldOne2Many,
    'one2many_list' : openerp.base.FieldOne2Many,
    'reference' : openerp.base.FieldReference,
    'boolean' : openerp.base.FieldBoolean,
    'float' : openerp.base.FieldFloat,
    'button' : openerp.base.WidgetButton
};

openerp.base.CalendarView = openerp.base.Controller.extend({
// Dhtmlx scheduler ?
});

openerp.base.GanttView = openerp.base.Controller.extend({
// Dhtmlx gantt ?
});

openerp.base.DiagramView = openerp.base.Controller.extend({
// 
});

openerp.base.GraphView = openerp.base.Controller.extend({
});

openerp.base.ProcessView = openerp.base.Controller.extend({
});

openerp.base.HelpView = openerp.base.Controller.extend({
});

};

// DEBUG_RPC:rpc.request:('execute', 'addons-dsh-l10n_us', 1, '*', ('ir.filters', 'get_filters', u'res.partner'))
// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
