openerp.web.search = function(openerp) {
var QWeb = openerp.web.qweb,
      _t =  openerp.web._t,
     _lt = openerp.web._lt;

// Have SearchBox optionally use callback function to produce inputs and facets
// (views) set on callbacks.make_facet and callbacks.make_input keys when
// initializing VisualSearch
var SearchBox_renderFacet = function (facet, position) {
    var view = new (this.app.options.callbacks['make_facet'] || VS.ui.SearchFacet)({
      app   : this.app,
      model : facet,
      order : position
    });

    // Input first, facet second.
    this.renderSearchInput();
    this.facetViews.push(view);
    this.$('.VS-search-inner').children().eq(position*2).after(view.render().el);

    view.calculateSize();
    _.defer(_.bind(view.calculateSize, view));

    return view;
  }; // warning: will not match
// Ensure we're replacing the function we think
if (SearchBox_renderFacet.toString() !== VS.ui.SearchBox.prototype.renderFacet.toString().replace(/(VS\.ui\.SearchFacet)/, "(this.app.options.callbacks['make_facet'] || $1)")) {
    throw new Error(
        "Trying to replace wrong version of VS.ui.SearchBox#renderFacet. "
        + "Please fix replacement.");
}
var SearchBox_renderSearchInput = function () {
    var input = new (this.app.options.callbacks['make_input'] || VS.ui.SearchInput)({position: this.inputViews.length, app: this.app});
    this.$('.VS-search-inner').append(input.render().el);
    this.inputViews.push(input);
  };
// Ensure we're replacing the function we think
if (SearchBox_renderSearchInput.toString() !== VS.ui.SearchBox.prototype.renderSearchInput.toString().replace(/(VS\.ui\.SearchInput)/, "(this.app.options.callbacks['make_input'] || $1)")) {
    throw new Error(
        "Trying to replace wrong version of VS.ui.SearchBox#renderSearchInput. "
        + "Please fix replacement.");
}
var SearchBox_searchEvent = function (e) {
    var query = this.value();
    this.app.options.callbacks.search(query, this.app.searchQuery);
  };
if (SearchBox_searchEvent.toString() !== VS.ui.SearchBox.prototype.searchEvent.toString().replace(
        /this\.focusSearch\(e\);\n[ ]{4}this\.value\(query\);\n[ ]{4}/, '')) {
    throw new Error(
        "Trying to replace wrong version of VS.ui.SearchBox#searchEvent. "
        + "Please fix replacement.");
}
_.extend(VS.ui.SearchBox.prototype, {
    renderFacet: SearchBox_renderFacet,
    renderSearchInput: SearchBox_renderSearchInput,
    searchEvent: SearchBox_searchEvent
});
_.extend(VS.model.SearchFacet.prototype, {
    value: function () {
        if (this.has('json')) {
            return this.get('json');
        }
        return this.get('value');
    }
});

openerp.web.SearchView = openerp.web.Widget.extend(/** @lends openerp.web.SearchView# */{
    template: "SearchView",
    /**
     * @constructs openerp.web.SearchView
     * @extends openerp.web.OldWidget
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
        var p = this._super();

        this.setup_global_completion();
        this.vs = VS.init({
            container: this.$element,
            query: '',
            callbacks: {
                make_facet: this.proxy('make_visualsearch_facet'),
                make_input: this.proxy('make_visualsearch_input'),
                search: function (query, searchCollection) {
                    console.log(query, searchCollection);
                },
                facetMatches: function (callback) {
                },
                valueMatches : function(facet, searchTerm, callback) {
                }
            }
        });

        if (this.hidden) {
            this.$element.hide();
        }
        if (this.headless) {
            this.ready.resolve();
        } else {
            this.rpc("/web/searchview/load", {
                model: this.model,
                view_id: this.view_id,
                context: this.dataset.get_context()
            }, this.on_loaded);
        }
        return $.when(p, this.ready);
    },
    show: function () {
        this.$element.show();
    },
    hide: function () {
        this.$element.hide();
    },

    /**
     * Sets up search view's view-wide auto-completion widget
     */
    setup_global_completion: function () {
        var self = this;
        this.$element.autocomplete({
            source: this.proxy('complete_global_search'),
            select: this.proxy('select_completion'),
            focus: function (e) { e.preventDefault(); },
            html: true,
            minLength: 0,
            delay: 0
        }).data('autocomplete')._renderItem = function (ul, item) {
            // item of completion list
            var $item = $( "<li></li>" )
                .data( "item.autocomplete", item )
                .appendTo( ul );
            if (item.type === 'section') {
                $item.text(item.label)
                    .css({
                        borderTop: '1px solid #cccccc',
                        margin: 0,
                        padding: 0,
                        zoom: 1,
                        'float': 'left',
                        clear: 'left',
                        width: '100%'
                    });
            } else if (item.type === 'base') {
                // FIXME: translation
                $item.append("<a>Search for: \"<strong>" + item.value + "</strong>\"</a>");
            } else {
                $item.append($("<a>").text(item.label));
            }
            return $item;
        }
    },
    /**
     * Provide auto-completion result for req.term (an array to `resp`)
     *
     * @param {Object} req request to complete
     * @param {String} req.term searched term to complete
     * @param {Function} resp response callback
     */
    complete_global_search:  function (req, resp) {
        var completion = [{value: req.term, type: 'base'}];
        $.when.apply(null, _(this.inputs).chain()
            .invoke('complete', req.term)
            .value()).then(function () {
                var results = completion.concat.apply(
                        completion, _(arguments).compact());
                resp(results);
        });
    },

    /**
     * Action to perform in case of selection: create a facet (model)
     * and add it to the search collection
     *
     * @param {Object} e selection event, preventDefault to avoid setting value on object
     * @param {Object} ui selection information
     * @param {Object} ui.item selected completion item
     */
    select_completion: function (e, ui) {
        e.preventDefault();
        if (ui.item.type === 'base') {
            this.vs.searchQuery.add(new VS.model.SearchFacet({
                category: null,
                value: ui.item.value,
                app: this.vs
            }));
            return;
        }
        this.vs.searchQuery.add(new VS.model.SearchFacet({
            category: ui.item.category,
            value: ui.item.label,
            json: ui.item.value,
            app: this.vs
        }));
    },

    /**
     * Builds the right SearchFacet view based on the facet object to render
     * (e.g. readonly facets for filters)
     *
     * @param {Object} options
     * @param {VS.model.SearchFacet} options.model facet object to render
     */
    make_visualsearch_facet: function (options) {
        return new VS.ui.SearchFacet(options);
    },
    /**
     * Proxies searches on a SearchInput to the search view's global completion
     *
     * Also disables SearchInput.autocomplete#_move so search view's
     * autocomplete can get the corresponding events, or something.
     *
     * @param options
     */
    make_visualsearch_input: function (options) {
        var self = this, input = new VS.ui.SearchInput(options);
        input.setupAutocomplete = function () {
            this.box.autocomplete({
                minLength: 1,
                delay: 0,
                search: function () {
                    self.$element.autocomplete('search', input.box.val());
                    return false;
                }
            }).data('autocomplete')._move = function () {};
        };
        return input;
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
        var self = this;
        this.fields_view = data.fields_view;
        if (data.fields_view.type !== 'search' ||
            data.fields_view.arch.tag !== 'search') {
                throw new Error(_.str.sprintf(
                    "Got non-search view after asking for a search view: type %s, arch root %s",
                    data.fields_view.type, data.fields_view.arch.tag));
        }

        this.make_widgets(
                data.fields_view['arch'].children,
                data.fields_view.fields);

        // load defaults
        return $.when.apply(null, _(this.inputs).invoke('facet_for_defaults', this.defaults))
            .then(function () {
                self.vs.searchQuery.reset(_(arguments).compact());
                self.ready.resolve();
        });

        // for extended search view
        var ext = new openerp.web.search.ExtendedSearch(this, this.model);
        lines.push([ext]);
        this.extended_search = ext;

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
            filters.html(QWeb.render("SearchView.managed-filters", {
                filters: result,
                disabled_filter_message: _t('Filter disabled due to invalid syntax')
            }));
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
        switch(val) {
        case 'advanced_filter':
            this.extended_search.on_activate();
            break;
        case 'add_to_dashboard':
            this.on_add_to_dashboard();
            break;
        case 'manage_filters':
            this.do_action({
                res_model: 'ir.filters',
                views: [[false, 'list'], [false, 'form']],
                type: 'ir.actions.act_window',
                context: {"search_default_user_id": this.session.uid,
                "search_default_model_id": this.dataset.model},
                target: "current",
                limit : 80
            });
            break;
        case 'save_filter':
            var data = this.build_search_data();
            var context = new openerp.web.CompoundContext();
            _.each(data.contexts, function(x) {
                context.add(x);
            });
            var domain = new openerp.web.CompoundDomain();
            _.each(data.domains, function(x) {
                domain.add(x);
            });
            var groupbys = _.pluck(data.groupbys, "group_by").join();
            context.add({"group_by": groupbys});
            var dial_html = QWeb.render("SearchView.managed-filters.add");
            var $dial = $(dial_html);
            openerp.web.dialog($dial, {
                modal: true,
                title: _t("Filter Entry"),
                buttons: [
                    {text: _t("Cancel"), click: function() {
                        $(this).dialog("close");
                    }},
                    {text: _t("OK"), click: function() {
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
                    }}
                ]
            });
            break;
        case '':
            this.do_clear();
        }
        if (val.slice(0, 4) == "get:") {
            val = val.slice(4);
            val = parseInt(val, 10);
            var filter = this.managed_filters[val];
            this.do_clear(false).then(_.bind(function() {
                select.val('get:' + val);

                var groupbys = [];
                var group_by = filter.context.group_by;
                if (group_by) {
                    groupbys = _.map(
                        group_by instanceof Array ? group_by : group_by.split(','),
                        function (el) { return { group_by: el }; });
                }
                this.on_search([filter.domain], [filter.context], groupbys);
            }, this));
        } else {
            select.val('');
        }
    },
    on_add_to_dashboard: function() {
        this.$element.find(".oe_search-view-filters-management")[0].selectedIndex = 0;
        var self = this,
            menu = openerp.webclient.menu,
            $dialog = $(QWeb.render("SearchView.add_to_dashboard", {
                dashboards : menu.data.data.children,
                selected_menu_id : menu.$element.find('a.active').data('menu')
            }));
        $dialog.find('input').val(this.fields_view.name);
        openerp.web.dialog($dialog, {
            modal: true,
            title: _t("Add to Dashboard"),
            buttons: [
                {text: _t("Cancel"), click: function() {
                    $(this).dialog("close");
                }},
                {text: _t("OK"), click: function() {
                    $(this).dialog("close");
                    var menu_id = $(this).find("select").val(),
                        title = $(this).find("input").val(),
                        data = self.build_search_data(),
                        context = new openerp.web.CompoundContext(),
                        domain = new openerp.web.CompoundDomain();
                    _.each(data.contexts, function(x) {
                        context.add(x);
                    });
                    _.each(data.domains, function(x) {
                           domain.add(x);
                    });
                    self.rpc('/web/searchview/add_to_dashboard', {
                        menu_id: menu_id,
                        action_id: self.getParent().action.id,
                        context_to_save: context,
                        domain: domain,
                        view_mode: self.getParent().active_view,
                        name: title
                    }, function(r) {
                        if (r === false) {
                            self.do_warn("Could not add filter to dashboard");
                        } else {
                            self.do_notify("Filter added to dashboard", '');
                        }
                    });
                }}
            ]
        });
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
        console.log(this.vs.searchBox.value());
        console.log(this.vs.searchQuery.facets());
        return this.on_search([], [], []);

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
        this.do_notify(_t("Invalid Search"), _t("triggered from search view"));
    },
    /**
     * @param {Boolean} [reload_view=true]
     */
    do_clear: function (reload_view) {
        this.$element.find('.filter_label, .filter_icon').removeClass('enabled');
        this.enabled_filters.splice(0);
        var string = $('a.searchview_group_string');
        _.each(string, function(str){
            $(str).closest('div.searchview_group').removeClass("expanded").addClass('folded');
         });
        this.$element.find('table:last').hide();

        $('.searchview_extended_groups_list').empty();
        return $.async_when.apply(
            null, _(this.inputs).invoke('clear')).pipe(
                reload_view !== false ? this.on_clear : null);
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
    'id': 'openerp.web.search.IntegerField',
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
        return _.str.sprintf(
            _t("Incorrect value for field %(fieldname)s: [%(value)s] is %(message)s"),
            {fieldname: this.field, value: this.value, message: this.message}
        );
    }
});
openerp.web.search.Widget = openerp.web.OldWidget.extend( /** @lends openerp.web.search.Widget# */{
    template: null,
    /**
     * Root class of all search widgets
     *
     * @constructs openerp.web.search.Widget
     * @extends openerp.web.OldWidget
     *
     * @param view the ancestor view of this widget
     */
    init: function (view) {
        this._super(view);
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
    destroy: function () {
        delete this.view;
        this._super();
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
        this.style = undefined;
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
        return $.when(null)
    },
    /**
     * Returns a VS.model.SearchFacet instance for the provided defaults if
     * they apply to this widget, or null if they don't.
     *
     * This default implementation will try calling
     * :js:func:`openerp.web.search.Input#facet_for` if the widget's name
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
    get_domain: function () {
        throw new Error(
            "get_domain not implemented for widget " + this.attrs.type);
    },
    load_attrs: function (attrs) {
        if (attrs.modifiers) {
            attrs.modifiers = JSON.parse(attrs.modifiers);
            attrs.invisible = attrs.modifiers.invisible || false;
            if (attrs.invisible) {
                this.style = 'display: none;'
            }
        }
        this.attrs = attrs;
    },
    /**
     * Specific clearing operations, if any
     */
    clear: function () {}
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
        this.make_id('filters');
    },
    facet_for_defaults: function (defaults) {
        var fs = _(this.filters).filter(function (f) {
            return f.attrs && f.attrs.name && !!defaults[f.attrs.name];
        });
        if (_.isEmpty(fs)) { return $.when(null); }
        return $.when(new VS.model.SearchFacet({
            category: 'q',
            value: _(fs).map(function (f) {
                return f.attrs.string || f.attrs.name }).join(' | '),
            json: fs,
            field: this,
            app: this.view.vs
        }));

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
        this.load_attrs(node.attrs);
    },
    facet_for: function () { return $.when(null); },
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
        this.load_attrs(_.extend({}, field, view_section.attrs));
        this.filters = new openerp.web.search.FilterGroup(_.compact(_.map(
            view_section.children, function (filter_node) {
                if (filter_node.attrs.string &&
                        typeof console !== 'undefined' && console.debug) {
                    console.debug("Filter-in-field with a 'string' attribute "
                                + "in view", view);
                }
                delete filter_node.attrs.string;
                return new openerp.web.search.Filter(
                    filter_node, view);
        })), view);
        this.make_id('input', field.type, this.attrs.name);
    },
    facet_for: function (value) {
        return $.when(new VS.model.SearchFacet({
            category: this.attrs.string || this.attrs.name,
            value: String(value),
            json: value,
            field: this,
            app: this.view.vs
        }));
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
    complete: function (value) {
        // FIXME: formatting
        var label = _.str.sprintf(_t('Search "%s" for "%s"'),
                                  this.attrs.string, value);
        return $.when([
            {category: this.attrs.name, label: label, value:value}
        ]);
    },
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
    error_message: _t("not a valid integer"),
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
    error_message: _t("not a valid number"),
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
    complete: function (needle) {
        var self = this;
        var results = _(this.attrs.selection).chain()
            .filter(function (sel) {
                var value = sel[0], label = sel[1];
                if (!value) { return false; }
                return label.toLowerCase().indexOf(needle.toLowerCase()) !== -1;
            })
            .map(function (sel) {
                return {
                    category: self.attrs.name,
                    label: sel[1],
                    value: sel[0]
                };
            }).value();
        if (_.isEmpty(results)) { return $.when(null); }
        return $.when.apply(null,
            [{type: 'section', label: this.attrs.string}].concat(results));
    },
    facet_for: function (value) {
        var match = _(this.attrs.selection).detect(function (sel) {
            return sel[0] === value;
        });
        if (!match) { return $.when(null); }
        return $.when(new VS.model.SearchFacet({
            category: this.attrs.string || this.attrs.name,
            value: match[1],
            json: match[0],
            field: this,
            app: this.view.vs
        }));
    },
    get_value: function () {
        var index = parseInt(this.$element.val(), 10);
        if (isNaN(index)) { return null; }
        var value = this.attrs.selection[index][0];
        if (value === false) { return null; }
        return value;
    },
    clear: function () {
        var self = this, d = $.Deferred(), selection = this.attrs.selection;
        for(var index=0; index<selection.length; ++index) {
            var item = selection[index];
            if (!item[1]) {
                setTimeout(function () {
                    // won't override mutable, because we immediately bail out
                    //noinspection JSReferencingMutableVariableFromClosure
                    self.$element.val(index);
                    d.resolve();
                }, 0);
                return d.promise();
            }
        }
        return d.resolve().promise();
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
            ['true', _t("Yes")],
            ['false', _t("No")]
        ];
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
        // FIXME: this insanity puts a div inside a span
        this.datewidget = new openerp.web.DateWidget(this);
        this.datewidget.prependTo(this.$element);
        this.datewidget.$element.find("input")
            .attr("size", 15)
            .attr("autofocus", this.attrs.default_focus === '1' ? 'autofocus' : null)
            .removeAttr('style');
        this.datewidget.set_value(this.defaults[this.attrs.name] || false);
    },
    get_value: function () {
        return this.datewidget.get_value() || null;
    },
    clear: function () {
        this.datewidget.set_value(false);
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
    complete: function (needle) {
        var self = this;
        // TODO: context
        // FIXME: "concurrent" searches (multiple requests, mis-ordered responses)
        return new openerp.web.Model(this.attrs.relation).call('name_search', [], {
            name: needle,
            limit: 8,
            context: {}
        }).pipe(function (results) {
            if (_.isEmpty(results)) { return null; }
            return [{type: 'section', label: self.attrs.string}].concat(
                _(results).map(function (result) {
                    return {
                        category: self.attrs.name,
                        label: result[1],
                        value: result[0]
                    };
                }));
        });
    },
    facet_for: function (value) {
        var self = this;
        if (value instanceof Array) {
            return $.when(new VS.model.SearchFacet({
                category: this.attrs.string || this.attrs.name,
                value: value[1],
                json: value[0],
                field: this,
                app: this.view.vs
            }));
        }
        return new openerp.web.Model(this.attrs.relation)
            .call('name_get', [value], {}).pipe(function (names) {
                return new VS.model.SearchFacet({
                category: self.attrs.string || self.attrs.name,
                value: names[0][1],
                json: names[0][0],
                field: self,
                app: self.view.vs
            });
        })
    },
    start: function () {
        this._super();
        this.setup_autocomplete();
        var started = $.Deferred();
        this.got_name.then(function () { started.resolve();},
                           function () { started.resolve(); });
        return started.promise();
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

openerp.web.search.ExtendedSearch = openerp.web.search.Input.extend({
    template: 'SearchView.extended_search',
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
        this.$element.closest("table.oe-searchview-render-line").css("display", "none");
        var self = this;
        this.rpc("/web/searchview/fields_get",
            {"model": this.model}, function(data) {
            self.fields = data.fields;
            if (!('id' in self.fields)) {
                self.fields.id = {
                    string: 'ID',
                    type: 'id'
                }
            }
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
        return _.reduce(this.getChildren(),
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
        _.each(this.getChildren(), function(x) {x.set_last_group(false);});
        if (this.getChildren().length >= 1) {
            this.getChildren()[this.getChildren().length - 1].set_last_group(true);
        }
    }
});

openerp.web.search.ExtendedSearchGroup = openerp.web.OldWidget.extend({
    template: 'SearchView.extended_search.group',
    init: function (parent, fields) {
        this._super(parent);
        this.fields = fields;
    },
    add_prop: function() {
        var prop = new openerp.web.search.ExtendedSearchProposition(this, this.fields);
        var render = prop.render({'index': this.getChildren().length - 1});
        this.$element.find('.searchview_extended_propositions_list').append(render);
        prop.start();
    },
    start: function () {
        var _this = this;
        this.add_prop();
        this.$element.find('.searchview_extended_add_proposition').click(function () {
            _this.add_prop();
        });
        this.$element.find('.searchview_extended_delete_group').click(function () {
            _this.destroy();
        });
    },
    get_domain: function() {
        var props = _(this.getChildren()).chain().map(function(x) {
            return x.get_proposition();
        }).compact().value();
        var choice = this.$element.find(".searchview_extended_group_choice").val();
        var op = choice == "all" ? "&" : "|";
        return choice == "none" ? ['!'] : [].concat(
            _.map(_.range(_.max([0,props.length - 1])), function() { return op; }),
            props);
    },
    destroy: function() {
        var parent = this.getParent();
        if (this.getParent().getChildren().length == 1)
            this.getParent().hide();
        this._super();
        parent.check_last_element();
    },
    set_last_group: function(is_last) {
        this.$element.toggleClass('last_group', is_last);
    }
});

openerp.web.search.ExtendedSearchProposition = openerp.web.OldWidget.extend(/** @lends openerp.web.search.ExtendedSearchProposition# */{
    template: 'SearchView.extended_search.proposition',
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
        this.$element = $("#" + this.element_id);
        this.select_field(this.fields.length > 0 ? this.fields[0] : null);
        var _this = this;
        this.$element.find(".searchview_extended_prop_field").change(function() {
            _this.changed();
        });
        this.$element.find('.searchview_extended_delete_prop').click(function () {
            _this.destroy();
        });
    },
    destroy: function() {
        var parent;
        if (this.getParent().getChildren().length == 1)
            parent = this.getParent();
        this._super();
        if (parent)
            parent.destroy();
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
        var self = this;
        if(this.attrs.selected != null) {
            this.value.destroy();
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
            $('<option>', {value: operator.value})
                .text(String(operator.text))
                .appendTo(self.$element.find('.searchview_extended_prop_op'));
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

openerp.web.search.ExtendedSearchProposition.Field = openerp.web.OldWidget.extend({
    start: function () {
        this.$element = $("#" + this.element_id);
    }
});
openerp.web.search.ExtendedSearchProposition.Char = openerp.web.search.ExtendedSearchProposition.Field.extend({
    template: 'SearchView.extended_search.proposition.char',
    operators: [
        {value: "ilike", text: _lt("contains")},
        {value: "not ilike", text: _lt("doesn't contain")},
        {value: "=", text: _lt("is equal to")},
        {value: "!=", text: _lt("is not equal to")},
        {value: ">", text: _lt("greater than")},
        {value: "<", text: _lt("less than")},
        {value: ">=", text: _lt("greater or equal than")},
        {value: "<=", text: _lt("less or equal than")}
    ],
    get_value: function() {
        return this.$element.val();
    }
});
openerp.web.search.ExtendedSearchProposition.DateTime = openerp.web.search.ExtendedSearchProposition.Field.extend({
    template: 'SearchView.extended_search.proposition.empty',
    operators: [
        {value: "=", text: _lt("is equal to")},
        {value: "!=", text: _lt("is not equal to")},
        {value: ">", text: _lt("greater than")},
        {value: "<", text: _lt("less than")},
        {value: ">=", text: _lt("greater or equal than")},
        {value: "<=", text: _lt("less or equal than")}
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
openerp.web.search.ExtendedSearchProposition.Date = openerp.web.search.ExtendedSearchProposition.Field.extend({
    template: 'SearchView.extended_search.proposition.empty',
    operators: [
        {value: "=", text: _lt("is equal to")},
        {value: "!=", text: _lt("is not equal to")},
        {value: ">", text: _lt("greater than")},
        {value: "<", text: _lt("less than")},
        {value: ">=", text: _lt("greater or equal than")},
        {value: "<=", text: _lt("less or equal than")}
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
openerp.web.search.ExtendedSearchProposition.Integer = openerp.web.search.ExtendedSearchProposition.Field.extend({
    template: 'SearchView.extended_search.proposition.integer',
    operators: [
        {value: "=", text: _lt("is equal to")},
        {value: "!=", text: _lt("is not equal to")},
        {value: ">", text: _lt("greater than")},
        {value: "<", text: _lt("less than")},
        {value: ">=", text: _lt("greater or equal than")},
        {value: "<=", text: _lt("less or equal than")}
    ],
    get_value: function() {
        try {
            return openerp.web.parse_value(this.$element.val(), {'widget': 'integer'});
        } catch (e) {
            return "";
        }
    }
});
openerp.web.search.ExtendedSearchProposition.Id = openerp.web.search.ExtendedSearchProposition.Integer.extend({
    operators: [{value: "=", text: _lt("is")}]
});
openerp.web.search.ExtendedSearchProposition.Float = openerp.web.search.ExtendedSearchProposition.Field.extend({
    template: 'SearchView.extended_search.proposition.float',
    operators: [
        {value: "=", text: _lt("is equal to")},
        {value: "!=", text: _lt("is not equal to")},
        {value: ">", text: _lt("greater than")},
        {value: "<", text: _lt("less than")},
        {value: ">=", text: _lt("greater or equal than")},
        {value: "<=", text: _lt("less or equal than")}
    ],
    get_value: function() {
        try {
            return openerp.web.parse_value(this.$element.val(), {'widget': 'float'});
        } catch (e) {
            return "";
        }
    }
});
openerp.web.search.ExtendedSearchProposition.Selection = openerp.web.search.ExtendedSearchProposition.Field.extend({
    template: 'SearchView.extended_search.proposition.selection',
    operators: [
        {value: "=", text: _lt("is")},
        {value: "!=", text: _lt("is not")}
    ],
    set_field: function(field) {
        this.field = field;
    },
    get_value: function() {
        return this.$element.val();
    }
});
openerp.web.search.ExtendedSearchProposition.Boolean = openerp.web.search.ExtendedSearchProposition.Field.extend({
    template: 'SearchView.extended_search.proposition.boolean',
    operators: [
        {value: "=", text: _lt("is true")},
        {value: "!=", text: _lt("is false")}
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
    'selection': 'openerp.web.search.ExtendedSearchProposition.Selection',

    'id': 'openerp.web.search.ExtendedSearchProposition.Id'
});

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
