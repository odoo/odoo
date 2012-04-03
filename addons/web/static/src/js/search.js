openerp.web.search = function(openerp) {
var QWeb = openerp.web.qweb,
      _t =  openerp.web._t,
     _lt = openerp.web._lt;
_.mixin({
    sum: function (obj) { return _.reduce(obj, function (a, b) { return a + b; }, 0); }
});

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
    var query = null;
    this.renderFacets();
    this.focusSearch(e);
    this.app.options.callbacks.search(query, this.app.searchQuery);
  };
if (SearchBox_searchEvent.toString() !== VS.ui.SearchBox.prototype.searchEvent.toString().replace(
        /this\.value\(\);\n[ ]{4}this\.focusSearch\(e\);\n[ ]{4}this\.value\(query\)/,
        'null;\n    this.renderFacets();\n    this.focusSearch(e)')) {
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
        this.controls = {};

        this.hidden = !!hidden;
        this.headless = this.hidden && !this.has_defaults;

        this.filter_data = {};

        this.ready = $.Deferred();
    },
    start: function() {
        var self = this;
        var p = this._super();

        this.setup_global_completion();
        this.vs = VS.init({
            container: this.$element,
            query: '',
            callbacks: {
                make_facet: this.proxy('make_visualsearch_facet'),
                make_input: this.proxy('make_visualsearch_input'),
                search: function (query, searchCollection) {
                    self.do_search();
                },
                facetMatches: function (callback) {
                },
                valueMatches : function(facet, searchTerm, callback) {
                }
            }
        });

        var search = function () { self.vs.searchBox.searchEvent({}); };
        // searchQuery operations
        this.vs.searchQuery
            .off('add').on('add', search)
            .off('change').on('change', search)
            .off('reset').on('reset', search)
            .off('remove').on('remove', function (record, collection, options) {
                if (options['trigger_search']) {
                    search();
                }
            });

        if (this.hidden) {
            this.$element.hide();
        }
        if (this.headless) {
            this.ready.resolve();
        } else {
            var load_view = this.rpc("/web/searchview/load", {
                model: this.model,
                view_id: this.view_id,
                context: this.dataset.get_context() });
            // FIXME: local eval of domain and context to get rid of special endpoint
            var filters = this.rpc('/web/searchview/get_filters', {
                model: this.model
            }).then(function (filters) { self.custom_filters = filters; });

            $.when(load_view, filters)
                .pipe(function (load) { return load[0]; })
                .then(this.on_loaded);
        }

        this.$element.on('click', '.oe_vs_unfold_drawer', function () {
            self.$element.toggleClass('oe_searchview_open_drawer');
        });

        return $.when(p, this.ready);
    },
    show: function () {
        this.$element.show();
    },
    hide: function () {
        this.$element.hide();
    },

    /**
     * Sets up thingie where all the mess is put?
     */
    setup_stuff_drawer: function () {
        var self = this;
        $('<div class="oe_vs_unfold_drawer">').appendTo(this.$element.find('.VS-search-box'));
        var $drawer = $('<div class="oe_searchview_drawer">').appendTo(this.$element);
        var $filters = $('<div class="oe_searchview_filters">').appendTo($drawer);

        var running_count = 0;
        // get total filters count
        var is_group = function (i) { return i instanceof openerp.web.search.FilterGroup; };
        var filters_count = _(this.controls).chain()
            .flatten()
            .filter(is_group)
            .map(function (i) { return i.filters.length; })
            .sum()
            .value();

        var col1 = [], col2 = _(this.controls).map(function (inputs, group) {
            var filters = _(inputs).filter(is_group);
            return {
                name: group === 'null' ? _t("Filters") : group,
                filters: filters,
                length: _(filters).chain().map(function (i) {
                    return i.filters.length; }).sum().value()
            };
        });

        while (col2.length) {
            // col1 + group should be smaller than col2 + group
            if ((running_count + col2[0].length) <= (filters_count - running_count)) {
                running_count += col2[0].length;
                col1.push(col2.shift());
            } else {
                break;
            }
        }

        // Create a Custom Filter FilterGroup for each custom filter read from
        // the db, add all of this as a group in the smallest column
        [].push.call(col1.length <= col2.length ? col1 : col2, {
            name: _t("Custom Filters"),
            filters: _.map(this.custom_filters, function (filter) {
                // FIXME: handling of ``disabled`` being set
                var f = new openerp.web.search.Filter({attrs: {
                    string: filter.name,
                    context: filter.context,
                    domain: filter.domain
                }}, self);
                return new openerp.web.search.FilterGroup([f], self);
            }),
            length: 3
        });

        return $.when(
            this.render_column(col1, $('<div>').appendTo($filters)),
            this.render_column(col2, $('<div>').appendTo($filters)),
            (new openerp.web.search.Advanced(this).appendTo($drawer)));
    },
    render_column: function (column, $el) {
        return $.when.apply(null, _(column).map(function (group) {
            $('<h3>').text(group.name).appendTo($el);
            return $.when.apply(null,
                _(group.filters).invoke('appendTo', $el));
        }));
    },
    /**
     * Sets up search view's view-wide auto-completion widget
     */
    setup_global_completion: function () {
        // Prevent keydown from within a facet's input from reaching the
        // auto-completion widget and opening the completion list
        this.$element.on('keydown', '.search_facet input', function (e) {
            e.stopImmediatePropagation();
        });

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

            if (item.value !== undefined) {
                // regular completion item
                return $item.append(
                    (item.label)
                        ? $('<a>').html(item.label)
                        : $('<a>').text(item.value));
            }
            return $item.text(item.category)
                .css({
                    borderTop: '1px solid #cccccc',
                    margin: 0,
                    padding: 0,
                    zoom: 1,
                    'float': 'left',
                    clear: 'left',
                    width: '100%'
                });
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
        $.when.apply(null, _(this.inputs).chain()
            .invoke('complete', req.term)
            .value()).then(function () {
                resp(_(_(arguments).compact()).flatten(true));
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
        this.vs.searchQuery.add(new VS.model.SearchFacet(_.extend(
            {app: this.vs}, ui.item)));
        this.vs.searchBox.searchEvent({});
    },

    /**
     * Builds the right SearchFacet view based on the facet object to render
     * (e.g. readonly facets for filters)
     *
     * @param {Object} options
     * @param {VS.model.SearchFacet} options.model facet object to render
     */
    make_visualsearch_facet: function (options) {
        if (options.model.get('field') instanceof openerp.web.search.FilterGroup) {
            return new openerp.web.search.FilterGroupFacet(options);
        }
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
            _.extend(this.box.autocomplete({
                minLength: 1,
                delay: 0,
                search: function () {
                    self.$element.autocomplete('search', input.box.val());
                    return false;
                }
            }).data('autocomplete'), {
                _move: function () {},
                close: function () { self.$element.autocomplete('close'); }
            });
        };
        return input;
    },

    /**
     * Builds a list of widget rows (each row is an array of widgets)
     *
     * @param {Array} items a list of nodes to convert to widgets
     * @param {Object} fields a mapping of field names to (ORM) field attributes
     * @param {String} [group_name] name of the group to put the new controls in
     */
    make_widgets: function (items, fields, group_name) {
        group_name = group_name || null;
        if (!(group_name in this.controls)) {
            this.controls[group_name] = [];
        }
        var self = this, group = this.controls[group_name];
        var filters = [];
        _.each(items, function (item) {
            if (filters.length && item.tag !== 'filter') {
                group.push(new openerp.web.search.FilterGroup(filters, this));
                filters = [];
            }

            switch (item.tag) {
            case 'separator': case 'newline':
                break;
            case 'filter':
                filters.push(new openerp.web.search.Filter(item, this));
                break;
            case 'group':
                self.make_widgets(item.children, fields, item.attrs.string);
                break;
            case 'field':
                group.push(this.make_field(item, fields[item['attrs'].name]));
                // filters
                self.make_widgets(item.children, fields, group_name);
                break;
            }
        }, this);

        if (filters.length) {
            group.push(new openerp.web.search.FilterGroup(filters, this));
        }
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
        return $.when(
                this.setup_stuff_drawer(),
                $.when.apply(null, _(this.inputs).invoke('facet_for_defaults', this.defaults))
                    .then(function () { self.vs.searchQuery.reset(_(arguments).compact()); }))
            .then(function () { self.ready.resolve(); })
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
                this.filter_data = {
                    domains: [filter.domain],
                    contexts: [filter.context],
                    groupbys: groupbys
                };
                this.do_search();
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
    do_search: function () {
        var domains = [], contexts = [], groupbys = [], errors = [];

        this.vs.searchQuery.each(function (facet) {
            var field = facet.get('field');
            try {
                var domain = field.get_domain(facet);
                if (domain) {
                    domains.push(domain);
                }
                var context = field.get_context(facet);
                if (context) {
                    contexts.push(context);
                    groupbys.push(context);
                }
            } catch (e) {
                if (e instanceof openerp.web.search.Invalid) {
                    errors.push(e);
                } else {
                    throw e;
                }
            }
        });

        if (!_.isEmpty(errors)) {
            this.on_invalid(errors);
            return;
        }
        return this.on_search(domains, contexts, groupbys);
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
    }
});

/** @namespace */
openerp.web.search = {};

openerp.web.search.FilterGroupFacet = VS.ui.SearchFacet.extend({
    events: _.extend({
        'click': 'selectFacet'
    }, VS.ui.SearchFacet.prototype.events),

    render: function () {
        this.setMode('not', 'editing');
        this.setMode('not', 'selected');

        var value = this.model.get('value');
        this.$el.html(QWeb.render('SearchView.filters.facet', {
            facet: this.model
        }));
        // virtual input so SearchFacet code has something to play with
        this.box = $('<input>').val(value);

        return this;
    },
    enableEdit: function () {
        this.selectFacet()
    },
    keydown: function (e) {
        var key = VS.app.hotkeys.key(e);
        if (key !== 'right') {
            return VS.ui.SearchFacet.prototype.keydown.call(this, e);
        }
        e.preventDefault();
        this.deselectFacet();
        this.options.app.searchBox.focusNextFacet(this, 1);
    }
});
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
    },
    start: function () {
        this.$element.on('click', 'li', this.proxy('toggle_filter'));
        return $.when(null);
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
    /**
     * Fetches contexts for all enabled filters in the group
     *
     * @param {VS.model.SearchFacet} facet
     * @return {*} combined contexts of the enabled filters in this group
     */
    get_context: function (facet) {
        var contexts = _(facet.get('json')).chain()
            .map(function (filter) { return filter.attrs.context; })
            .reject(_.isEmpty)
            .value();

        if (!contexts.length) { return; }
        if (contexts.length === 1) { return contexts[0]; }
        return _.extend(new openerp.web.CompoundContext, {
            __contexts: contexts
        });
    },
    /**
     * Handles domains-fetching for all the filters within it: groups them.
     *
     * @param {VS.model.SearchFacet} facet
     * @return {*} combined domains of the enabled filters in this group
     */
    get_domain: function (facet) {
        var domains = _(facet.get('json')).chain()
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
    },
    toggle_filter: function (e) {
        this.toggle(this.filters[$(e.target).index()]);
    },
    toggle: function (filter) {
        // FIXME: oh god, my eyes, they hurt
        var self = this, fs;
        var facet = this.view.vs.searchQuery.detect(function (f) {
            return f.get('field') === self; });
        if (facet) {
            fs = facet.get('json');

            if (_.include(fs, filter)) {
                fs = _.without(fs, filter);
            } else {
                fs.push(filter);
            }
            if (_(fs).isEmpty()) {
                this.view.vs.searchQuery.remove(facet, {trigger_search: true});
            } else {
                facet.set({
                    json: fs,
                    value: _(fs).map(function (f) {
                        return f.attrs.string || f.attrs.name }).join(' | ')
                });
            }
            return;
        } else {
            fs = [filter];
        }

        this.view.vs.searchQuery.add({
            category: 'q',
            value: _(fs).map(function (f) {
                return f.attrs.string || f.attrs.name }).join(' | '),
            json: fs,
            field: this,
            app: this.view.vs
        });
    }
});
openerp.web.search.Filter = openerp.web.search.Input.extend(/** @lends openerp.web.search.Filter# */{
    template: 'SearchView.filter',
    /**
     * Implementation of the OpenERP filters (button with a context and/or
     * a domain sent as-is to the search view)
     *
     * Filters are only attributes holder, the actual work (compositing
     * domains and contexts, converting between facets and filters) is
     * performed by the filter group.
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
    get_context: function () { },
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
    get_value: function (facet) {
        return facet.value();
    },
    get_context: function (facet) {
        var val = this.get_value(facet);
        // A field needs a value to be "active", and a context to send when
        // active
        var has_value = (val !== null && val !== '');
        var context = this.attrs.context;
        if (!(has_value && context)) {
            return;
        }
        return new openerp.web.CompoundContext(context)
                .set_eval_context({self: val});
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
    make_domain: function (name, operator, facet) {
        return [[name, operator, this.get_value(facet)]];
    },
    get_domain: function (facet) {
        var val = this.get_value(facet);
        if (val === null || val === '') {
            return;
        }

        var domain = this.attrs['filter_domain'];
        if (!domain) {
            return this.make_domain(
                this.attrs.name,
                this.attrs.operator || this.default_operator,
                facet);
        }
        return new openerp.web.CompoundDomain(domain)
                .set_eval_context({self: val});
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
        if (_.isEmpty(value)) { return $.when(null); }
        var label = _.str.sprintf(_.str.escapeHTML(
            _t("Search %(field)s for: %(value)s")), {
                field: '<em>' + this.attrs.string + '</em>',
                value: '<strong>' + _.str.escapeHTML(value) + '</strong>'});
        return $.when([{
            category: this.attrs.string,
            label: label,
            value: value,
            field: this
        }]);
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
                    category: self.attrs.string,
                    field: self,
                    value: sel[1],
                    json: sel[0]
                };
            }).value();
        if (_.isEmpty(results)) { return $.when(null); }
        return $.when.apply(null, [{
            category: this.attrs.string
        }].concat(results));
    },
    facet_for: function (value) {
        var match = _(this.attrs.selection).detect(function (sel) {
            return sel[0] === value;
        });
        if (!match) { return $.when(null); }
        return $.when(new VS.model.SearchFacet({
            category: this.attrs.string,
            value: match[1],
            json: match[0],
            field: this,
            app: this.view.app
        }));
    },
    get_value: function (facet) {
        return facet.get('json');
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
    get_value: function (facet) {
        switch (this._super(facet)) {
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
    get_value: function (facet) {
        return openerp.web.date_to_str(facet.get('json'));
    },
    complete: function (needle) {
        var d = Date.parse(needle);
        if (!d) { return $.when(null); }
        var value = openerp.web.format_value(d, this.attrs);
        var label = _.str.sprintf(_.str.escapeHTML(
            _t("Search %(field)s at: %(value)s")), {
                field: '<em>' + this.attrs.string + '</em>',
                value: '<strong>' + value + '</strong>'});
        return $.when([{
            category: this.attrs.string,
            label: label,
            value: value,
            json: d,
            field: this
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
 * @extends openerp.web.DateField
 */
openerp.web.search.DateTimeField = openerp.web.search.DateField.extend(/** @lends openerp.web.search.DateTimeField# */{
    get_value: function (facet) {
        return openerp.web.datetime_to_str(facet.get('json'));
    }
});
openerp.web.search.ManyToOneField = openerp.web.search.CharField.extend({
    init: function (view_section, field, view) {
        this._super(view_section, field, view);
        this.model = new openerp.web.Model(this.attrs.relation);
    },
    complete: function (needle) {
        var self = this;
        // TODO: context
        // FIXME: "concurrent" searches (multiple requests, mis-ordered responses)
        return this.model.call('name_search', [], {
            name: needle,
            limit: 8,
            context: {}
        }).pipe(function (results) {
            if (_.isEmpty(results)) { return null; }
            return [{category: self.attrs.string}].concat(
                _(results).map(function (result) {
                    return {
                        category: self.attrs.string,
                        value: result[1],
                        json: result[0],
                        field: self
                    };
                }));
        });
    },
    facet_for: function (value) {
        var self = this;
        if (value instanceof Array) {
            return $.when(new VS.model.SearchFacet({
                category: this.attrs.string,
                value: value[1],
                json: value[0],
                field: this,
                app: this.view.vs
            }));
        }
        return this.model.call('name_get', [value], {}).pipe(function (names) {
                return new VS.model.SearchFacet({
                category: self.attrs.string,
                value: names[0][1],
                json: names[0][0],
                field: self,
                app: self.view.vs
            });
        })
    },
    make_domain: function (name, operator, facet) {
        // ``json`` -> actual auto-completed id
        if (facet.get('json')) {
            return [[name, '=', facet.get('json')]];
        }

        return this._super(name, operator, facet);
    }
});

openerp.web.search.Advanced = openerp.web.search.Input.extend({
    template: 'SearchView.advanced',
    start: function () {
        var self = this;
        this.propositions = [];
        this.$element
            .on('keypress keydown keyup', function (e) { e.stopPropagation(); })
            .on('click', 'h4', function () {
                self.$element.toggleClass('oe_opened');
            }).on('click', 'button.oe_add_condition', function () {
                self.append_proposition();
            }).on('click', 'button.oe_apply', function () {
                self.commit_search();
            });
        return $.when(
            this._super(),
            this.rpc("/web/searchview/fields_get", {model: this.view.model}, function(data) {
                self.fields = _.extend({
                    id: { string: 'ID', type: 'id' }
                }, data.fields);
        })).then(function () {
            self.append_proposition();
        });
    },
    append_proposition: function () {
        return (new openerp.web.search.ExtendedSearchProposition(this, this.fields))
            .appendTo(this.$element.find('ul'));
    },
    commit_search: function () {
        var self = this;
        // Get domain sections from all propositions
        var children = this.getChildren(),
            domain = _.invoke(children, 'get_proposition');
        var filters = _(domain).map(function (section) {
            return new openerp.web.search.Filter({attrs: {
                string: _.str.sprintf('%s(%s)%s',
                    section[0], section[1], section[2]),
                domain: [section]
            }}, self.view);
        });
        // Create Filter (& FilterGroup around it) with that domain
        var f = new openerp.web.search.FilterGroup(filters, this.view);
        // add group to query
        this.view.vs.searchQuery.add({
            category: 'q',
            value: _(filters).map(function (f) {
                return f.attrs.string || f.attrs.name }).join(' | '),
            json: filters,
            field: f,
            app: this.view.vs
        });
        // remove all propositions
        _.invoke(children, 'destroy');
        // add new empty proposition
        this.append_proposition();
        // ? close drawer?
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
        this.select_field(this.fields.length > 0 ? this.fields[0] : null);
        var _this = this;
        this.$element.find(".searchview_extended_prop_field").change(function() {
            _this.changed();
        });
        this.$element.find('.searchview_extended_delete_prop').click(function () {
            _this.destroy();
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
        {value: "!=", text: _lt("is not equal to")}
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
