openerp.web.search = function(instance) {
var QWeb = instance.web.qweb,
      _t =  instance.web._t,
     _lt = instance.web._lt;
_.mixin({
    sum: function (obj) { return _.reduce(obj, function (a, b) { return a + b; }, 0); }
});

/** @namespace */
var my = instance.web.search = {};

var B = Backbone;
my.FacetValue = B.Model.extend({

});
my.FacetValues = B.Collection.extend({
    model: my.FacetValue
});
my.Facet = B.Model.extend({
    initialize: function (attrs) {
        var values = attrs.values;
        delete attrs.values;

        B.Model.prototype.initialize.apply(this, arguments);

        this.values = new my.FacetValues(values || []);
        this.values.on('add remove change reset', function () {
            this.trigger('change', this);
        }, this);
    },
    get: function (key) {
        if (key !== 'values') {
            return B.Model.prototype.get.call(this, key);
        }
        return this.values.toJSON();
    },
    set: function (key, value) {
        if (key !== 'values') {
            return B.Model.prototype.set.call(this, key, value);
        }
        this.values.reset(value);
    },
    toJSON: function () {
        var out = {};
        var attrs = this.attributes;
        for(var att in attrs) {
            if (!attrs.hasOwnProperty(att) || att === 'field') {
                continue;
            }
            out[att] = attrs[att];
        }
        out.values = this.values.toJSON();
        return out;
    }
});
my.SearchQuery = B.Collection.extend({
    model: my.Facet,
    initialize: function () {
        B.Collection.prototype.initialize.apply(
            this, arguments);
        this.on('change', function (facet) {
            if(!facet.values.isEmpty()) { return; }

            this.remove(facet);
        }, this);
    },
    add: function (values, options) {
        options || (options = {});
        if (!(values instanceof Array)) {
            values = [values];
        }

        _(values).each(function (value) {
            var model = this._prepareModel(value, options);
            var previous = this.detect(function (facet) {
                return facet.get('category') === model.get('category')
                    && facet.get('field') === model.get('field');
            });
            if (previous) {
                previous.values.add(model.get('values'));
                return;
            }
            B.Collection.prototype.add.call(this, model, options);
        }, this);
        return this;
    },
    toggle: function (value, options) {
        options || (options = {});

        var facet = this.detect(function (facet) {
            return facet.get('category') === value.category
                && facet.get('field') === value.field;
        });
        if (!facet) {
            return this.add(value, options);
        }

        var changed = false;
        _(value.values).each(function (val) {
            var already_value = facet.values.detect(function (v) {
                return v.get('value') === val.value
                    && v.get('label') === val.label;
            });
            // toggle value
            if (already_value) {
                facet.values.remove(already_value, {silent: true});
            } else {
                facet.values.add(val, {silent: true});
            }
            changed = true;
        });
        // "Commit" changes to values array as a single call, so observers of
        // change event don't get misled by intermediate incomplete toggling
        // states
        facet.trigger('change', facet);
        return this;
    }
});

my.InputView = instance.web.Widget.extend({
    template: 'SearchView.InputView',
    start: function () {
        var self = this;
        var p = this._super.apply(this, arguments);
        this.$element.on('focus', this.proxy('onFocus'));
        this.$element.on('blur', this.proxy('onBlur'));
        return p;
    },
    onFocus: function () {
        this.$element.siblings().trigger('deselect');
        this.getParent().$element.trigger('focus');
    },
    onBlur: function () {
        this.$element.text('');
        this.getParent().$element.trigger('blur');
    }
});
my.FacetView = instance.web.Widget.extend({
    template: 'SearchView.FacetView',
    init: function (parent, model) {
        this._super(parent);
        this.model = model;
        this.model.on('change', this.model_changed, this);
    },
    destroy: function () {
        this.model.off('change', this.model_changed, this);
        this._super();
    },
    start: function () {
        var self = this;
        this.$element.on('deselect', function () {
            self.$element.removeClass('oe_selected');
        });
        this.$element.on('click', function (e) {
            if ($(e.target).is('.oe_facet_remove')) {
                return;
            }
            e.stopPropagation();
            self.$element.siblings().trigger('deselect');
            self.$element.addClass('oe_selected');
        });
        var $e = self.$element.find('> span:last-child');
        var q = $.when(this._super());
        return q.pipe(function () {
            var values = self.model.values.map(function (value) {
                return new my.FacetValueView(self, value).appendTo($e);
            });

            return $.when.apply(null, values);
        });
    },
    model_changed: function () {
        this.$element.text(this.$element.text() + '*');
    }
});
my.FacetValueView = instance.web.Widget.extend({
    template: 'SearchView.FacetView.Value',
    init: function (parent, model) {
        this._super(parent);
        this.model = model;
        this.model.on('change', this.model_changed, this);
    },
    destroy: function () {
        this.model.off('change', this.model_changed, this);
        this._super();
    },
    model_changed: function () {
        this.$element.text(this.$element.text() + '*');
    }
});

instance.web.SearchView = instance.web.Widget.extend(/** @lends instance.web.SearchView# */{
    template: "SearchView",
    /**
     * @constructs instance.web.SearchView
     * @extends instance.web.Widget
     *
     * @param parent
     * @param dataset
     * @param view_id
     * @param defaults
     * @param hidden
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

        this.input_subviews = [];

        this.ready = $.Deferred();
    },
    start: function() {
        var self = this;
        var p = this._super();

        this.setup_global_completion();
        this.query = new my.SearchQuery()
                .on('add change reset', this.proxy('do_search'))
                .on('add change reset', this.proxy('renderFacets'))
                .on('remove', function (record, collection, options) {
            self.renderFacets();
            if (options.trigger_search) {
                self.do_search();
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
                .pipe(this.on_loaded)
                .fail(function () {
                    self.ready.reject.apply(null, arguments);
                });
        }

        this.$element.on('click', '.oe_searchview_unfold_drawer', function (e) {
            e.stopImmediatePropagation();
            self.$element.toggleClass('oe_searchview_open_drawer');
        });
        this.$element.on('click', '.oe_facet_remove', function (e) {
            e.stopImmediatePropagation();
            // get index of clicked facet: number of preceding facet siblings
            var index = $(this).closest('.oe_searchview_facet')
                   .prevAll('.oe_searchview_facet')
                   .length;
            self.query.remove(
                self.query.at(index), {trigger_search: true});
        });
        // Focus last input if the view itself is clicked
        this.$element.on('click', function (e) {
            if (e.target === self.$element[0]) {
                self.$element.find('.oe_searchview_input:last').focus();
            }
        });
        // focusing class on whole searchview, :focus is not transitive
        this.$element.on('focus', function () {
            self.$element.addClass('oe_focused');
        });
        this.$element.on('blur', function () {
            self.$element.removeClass('oe_focused');
        });
        // when the completion list opens/refreshes, automatically select the
        // first completion item so if the user just hits [RETURN] or [TAB] it
        // automatically selects it
        this.$element.on('autocompleteopen', function () {
            var menu = self.$element.data('autocomplete').menu;
            menu.activate(
                $.Event({ type: "mouseenter" }),
                menu.element.children().first());
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
    select_for_drawer: function () {
        return _(this.inputs).filter(function (input) {
            return input.in_drawer();
        });
    },
    /**
     * Sets up search view's view-wide auto-completion widget
     */
    setup_global_completion: function () {
        var self = this;

        // autocomplete only correctly handles being initialized on the actual
        // editable element (and only an element with a @value in 1.8 e.g.
        // input or textarea), cheat by setting val() on $element
        this.$element.on('keydown', function () {
            // keydown is triggered *before* the element's value is set, so
            // delay this. Pray that setTimeout are executed in FIFO (if they
            // have the same delay) as autocomplete uses the exact same trick.
            // FIXME: brittle as fuck
            setTimeout(function () {
                self.$element.val(self.currentInputValue());
            }, 0);

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

            if (item.facet !== undefined) {
                // regular completion item
                return $item.append(
                    (item.label)
                        ? $('<a>').html(item.label)
                        : $('<a>').text(item.value));
            }
            return $item.text(item.label)
                .css({
                    borderTop: '1px solid #cccccc',
                    margin: 0,
                    padding: 0,
                    zoom: 1,
                    'float': 'left',
                    clear: 'left',
                    width: '100%'
                });
        };
    },
    /**
     * Gets value out of the currently focused "input" (a
     * div[contenteditable].oe_searchview_input)
     */
    currentInputValue: function () {
        return this.$element.find('div.oe_searchview_input:focus').text();
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

        this.query.add(ui.item.facet);
    },
    renderFacets: function () {
        var self = this;
        var $e = this.$element.find('div.oe_searchview_facets');
        _.invoke(this.input_subviews, 'destroy');
        this.input_subviews = [];

        var i = new my.InputView(this);
        i.appendTo($e);
        this.input_subviews.push(i);
        this.query.each(function (facet) {
            var f = new my.FacetView(this, facet);
            f.appendTo($e);
            self.input_subviews.push(f);

            var i = new my.InputView(this);
            i.appendTo($e);
            self.input_subviews.push(i);
        }, this);
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
                group.push(new instance.web.search.FilterGroup(filters, this));
                filters = [];
            }

            switch (item.tag) {
            case 'separator': case 'newline':
                break;
            case 'filter':
                filters.push(new instance.web.search.Filter(item, this));
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
            group.push(new instance.web.search.FilterGroup(filters, this));
        }
    },
    /**
     * Creates a field for the provided field descriptor item (which comes
     * from fields_view_get)
     *
     * @param {Object} item fields_view_get node for the field
     * @param {Object} field fields_get result for the field
     * @returns instance.web.search.Field
     */
    make_field: function (item, field) {
        var obj = instance.web.search.fields.get_any( [item.attrs.widget, field.type]);
        if(obj) {
            return new (obj) (item, field, this);
        } else {
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

        // add Filters to this.inputs, need view.controls filled
        var filters = new instance.web.search.Filters(this);
        // add Advanced to this.inputs
        var advanced = new instance.web.search.Advanced(this);

        // build drawer
        var drawer_started = $.when.apply(
            null, _(this.select_for_drawer()).invoke(
                'appendTo', this.$element.find('.oe_searchview_drawer')));

        // load defaults
        var defaults_fetched = $.when.apply(null, _(this.inputs).invoke(
            'facet_for_defaults', this.defaults)).then(function () {
                self.query.reset(_(arguments).compact(), {silent: true});
                self.renderFacets();
            });

        return $.when(drawer_started, defaults_fetched)
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
            var context = new instance.web.CompoundContext();
            _.each(data.contexts, function(x) {
                context.add(x);
            });
            var domain = new instance.web.CompoundDomain();
            _.each(data.domains, function(x) {
                domain.add(x);
            });
            var groupbys = _.pluck(data.groupbys, "group_by").join();
            context.add({"group_by": groupbys});
            var dial_html = QWeb.render("SearchView.managed-filters.add");
            var $dial = $(dial_html);
            instance.web.dialog($dial, {
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
            menu = instance.webclient.menu,
            $dialog = $(QWeb.render("SearchView.add_to_dashboard", {
                dashboards : menu.data.data.children,
                selected_menu_id : menu.$element.find('a.active').data('menu')
            }));
        $dialog.find('input').val(this.fields_view.name);
        instance.web.dialog($dialog, {
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
                        context = new instance.web.CompoundContext(),
                        domain = new instance.web.CompoundDomain();
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
     * :js:func:`instance.web.SearchView.on_search`.
     *
     * If at least one field failed its validation, triggers
     * :js:func:`instance.web.SearchView.on_invalid` instead.
     *
     * @param e jQuery event object coming from the "Search" button
     */
    do_search: function () {
        var domains = [], contexts = [], groupbys = [], errors = [];

        return this.on_search([], [], []);
        this.query.each(function (facet) {
            var field = facet.get('field');
            try {
                var domain = field.get_domain(facet);
                if (domain) {
                    domains.push(domain);
                }
                var context = field.get_context(facet);
                if (context) {
                    contexts.push(context);
                }
                var group_by = field.get_groupby(facet);
                if (group_by) {
                    groupbys.push.apply(groupbys, group_by);
                }
            } catch (e) {
                if (e instanceof instance.web.search.Invalid) {
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

/**
 * Registry of search fields, called by :js:class:`instance.web.SearchView` to
 * find and instantiate its field widgets.
 */
instance.web.search.fields = new instance.web.Registry({
    'char': 'instance.web.search.CharField',
    'text': 'instance.web.search.CharField',
    'boolean': 'instance.web.search.BooleanField',
    'integer': 'instance.web.search.IntegerField',
    'id': 'instance.web.search.IntegerField',
    'float': 'instance.web.search.FloatField',
    'selection': 'instance.web.search.SelectionField',
    'datetime': 'instance.web.search.DateTimeField',
    'date': 'instance.web.search.DateField',
    'many2one': 'instance.web.search.ManyToOneField',
    'many2many': 'instance.web.search.CharField',
    'one2many': 'instance.web.search.CharField'
});
instance.web.search.Invalid = instance.web.Class.extend( /** @lends instance.web.search.Invalid# */{
    /**
     * Exception thrown by search widgets when they hold invalid values,
     * which they can not return when asked.
     *
     * @constructs instance.web.search.Invalid
     * @extends instance.web.Class
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
instance.web.search.Widget = instance.web.OldWidget.extend( /** @lends instance.web.search.Widget# */{
    template: null,
    /**
     * Root class of all search widgets
     *
     * @constructs instance.web.search.Widget
     * @extends instance.web.OldWidget
     *
     * @param view the ancestor view of this widget
     */
    init: function (view) {
        this._super(view);
        this.view = view;
    }
});
instance.web.search.add_expand_listener = function($root) {
    $root.find('a.searchview_group_string').click(function (e) {
        $root.toggleClass('folded expanded');
        e.stopPropagation();
        e.preventDefault();
    });
};
instance.web.search.Group = instance.web.search.Widget.extend({
    template: 'SearchView.group',
    init: function (view_section, view, fields) {
        this._super(view);
        this.attrs = view_section.attrs;
        this.lines = view.make_widgets(
            view_section.children, fields);
    }
});

instance.web.search.Input = instance.web.search.Widget.extend( /** @lends instance.web.search.Input# */{
    _in_drawer: false,
    /**
     * @constructs instance.web.search.Input
     * @extends instance.web.search.Widget
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
    in_drawer: function () {
        return !!this._in_drawer;
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
instance.web.search.FilterGroup = instance.web.search.Input.extend(/** @lends instance.web.search.FilterGroup# */{
    template: 'SearchView.filters',
    /**
     * Inclusive group of filters, creates a continuous "button" with clickable
     * sections (the normal display for filters is to be a self-contained button)
     *
     * @constructs instance.web.search.FilterGroup
     * @extends instance.web.search.Input
     *
     * @param {Array<instance.web.search.Filter>} filters elements of the group
     * @param {instance.web.SearchView} view view in which the filters are contained
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
        var fs = _(this.filters).chain()
            .filter(function (f) {
                return f.attrs && f.attrs.name && !!defaults[f.attrs.name];
            }).map(function (f) {
                return {label: f.attrs.string || f.attrs.name,
                        value: f};
            }).value();
        if (_.isEmpty(fs)) { return $.when(null); }
        return $.when({
            category: _t("Filter"),
            values: fs,
            field: this
        });
    },
    /**
     * Fetches contexts for all enabled filters in the group
     *
     * @param {VS.model.SearchFacet} facet
     * @return {*} combined contexts of the enabled filters in this group
     */
    get_context: function (facet) {
        var contexts = _(facet.get('values')).chain()
            .map(function (filter) { return filter.attrs.context; })
            .reject(_.isEmpty)
            .value();

        if (!contexts.length) { return; }
        if (contexts.length === 1) { return contexts[0]; }
        return _.extend(new instance.web.CompoundContext, {
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
        return  _(facet.get('values')).chain()
            .map(function (filter) { return filter.attrs.context; })
            .reject(_.isEmpty)
            .value();
    },
    /**
     * Handles domains-fetching for all the filters within it: groups them.
     *
     * @param {VS.model.SearchFacet} facet
     * @return {*} combined domains of the enabled filters in this group
     */
    get_domain: function (facet) {
        var domains = _(facet.get('values')).chain()
            .map(function (filter) { return filter.attrs.domain; })
            .reject(_.isEmpty)
            .value();

        if (!domains.length) { return; }
        if (domains.length === 1) { return domains[0]; }
        for (var i=domains.length; --i;) {
            domains.unshift(['|']);
        }
        return _.extend(new instance.web.CompoundDomain(), {
            __domains: domains
        });
    },
    toggle_filter: function (e) {
        this.toggle(this.filters[$(e.target).index()]);
    },
    toggle: function (filter) {
        this.view.query.toggle({
            category: _t("Filter"),
            field: this,
            values: [{
                label: filter.attrs.string || filter.attrs.name,
                value: filter
            }]
        });
    }
});
instance.web.search.Filter = instance.web.search.Input.extend(/** @lends instance.web.search.Filter# */{
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
     * @param view
     */
    init: function (node, view) {
        this._super(view);
        this.load_attrs(node.attrs);
    },
    facet_for: function () { return $.when(null); },
    get_context: function () { },
    get_domain: function () { },
});
instance.web.search.Field = instance.web.search.Input.extend( /** @lends instance.web.search.Field# */ {
    template: 'SearchView.field',
    default_operator: '=',
    /**
     * @constructs instance.web.search.Field
     * @extends instance.web.search.Input
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
        return $.when({
            field: this,
            category: this.attrs.string || this.attrs.name,
            values: [{label: String(value), value: value}]
        });
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
        return new instance.web.CompoundContext(context)
                .set_eval_context({self: val});
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
        return new instance.web.CompoundDomain(domain)
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
 * @extends instance.web.search.Field
 */
instance.web.search.CharField = instance.web.search.Field.extend( /** @lends instance.web.search.CharField# */ {
    default_operator: 'ilike',
    complete: function (value) {
        if (_.isEmpty(value)) { return $.when(null); }
        var label = _.str.sprintf(_.str.escapeHTML(
            _t("Search %(field)s for: %(value)s")), {
                field: '<em>' + this.attrs.string + '</em>',
                value: '<strong>' + _.str.escapeHTML(value) + '</strong>'});
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
instance.web.search.NumberField = instance.web.search.Field.extend(/** @lends instance.web.search.NumberField# */{
    get_value: function () {
        if (!this.$element.val()) {
            return null;
        }
        var val = this.parse(this.$element.val()),
          check = Number(this.$element.val());
        if (isNaN(val) || val !== check) {
            this.$element.addClass('error');
            throw new instance.web.search.Invalid(
                this.attrs.name, this.$element.val(), this.error_message);
        }
        this.$element.removeClass('error');
        return val;
    }
});
/**
 * @class
 * @extends instance.web.search.NumberField
 */
instance.web.search.IntegerField = instance.web.search.NumberField.extend(/** @lends instance.web.search.IntegerField# */{
    error_message: _t("not a valid integer"),
    parse: function (value) {
        try {
            return instance.web.parse_value(value, {'widget': 'integer'});
        } catch (e) {
            return NaN;
        }
    }
});
/**
 * @class
 * @extends instance.web.search.NumberField
 */
instance.web.search.FloatField = instance.web.search.NumberField.extend(/** @lends instance.web.search.FloatField# */{
    error_message: _t("not a valid number"),
    parse: function (value) {
        try {
            return instance.web.parse_value(value, {'widget': 'float'});
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
        category: field['attrs'].string,
        values: [{label: pair[1], value: pair[0]}]
    };
}

/**
 * @class
 * @extends instance.web.search.Field
 */
instance.web.search.SelectionField = instance.web.search.Field.extend(/** @lends instance.web.search.SelectionField# */{
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
                    label: sel[1],
                    facet: facet_from(self, sel)
                };
            }).value();
        if (_.isEmpty(results)) { return $.when(null); }
        return $.when.call(null, [{
            label: this.attrs.string
        }].concat(results));
    },
    facet_for: function (value) {
        var match = _(this.attrs.selection).detect(function (sel) {
            return sel[0] === value;
        });
        if (!match) { return $.when(null); }
        return $.when(facet_from(this, match));
    },
    get_value: function (facet) {
        return facet.get('values');
    }
});
instance.web.search.BooleanField = instance.web.search.SelectionField.extend(/** @lends instance.web.search.BooleanField# */{
    /**
     * @constructs instance.web.search.BooleanField
     * @extends instance.web.search.BooleanField
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
 * @extends instance.web.search.DateField
 */
instance.web.search.DateField = instance.web.search.Field.extend(/** @lends instance.web.search.DateField# */{
    get_value: function (facet) {
        return openerp.web.date_to_str(facet.get('values'));
    },
    complete: function (needle) {
        var d = Date.parse(needle);
        if (!d) { return $.when(null); }
        var date_string = instance.web.format_value(d, this.attrs);
        var label = _.str.sprintf(_.str.escapeHTML(
            _t("Search %(field)s at: %(value)s")), {
                field: '<em>' + this.attrs.string + '</em>',
                value: '<strong>' + date_string + '</strong>'});
        return $.when([{
            label: label,
            facet: {
                category: this.attrs.string,
                field: this,
                values: [{label: date_string, value: d}]
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
instance.web.search.DateTimeField = instance.web.search.DateField.extend(/** @lends instance.web.search.DateTimeField# */{
    get_value: function (facet) {
        return openerp.web.datetime_to_str(facet.get('values'));
    }
});
instance.web.search.ManyToOneField = instance.web.search.CharField.extend({
    init: function (view_section, field, view) {
        this._super(view_section, field, view);
        this.model = new instance.web.Model(this.attrs.relation);
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
            return [{label: self.attrs.string}].concat(
                _(results).map(function (result) {
                    return {
                        label: result[1],
                        facet: facet_from(self, result)
                    };
                }));
        });
    },
    facet_for: function (value) {
        var self = this;
        if (value instanceof Array) {
            return $.when(facet_from(this, value));
        }
        return this.model.call('name_get', [value], {}).pipe(function (names) {
            if (_(names).isEmpty()) { return null; }
            return facet_from(self, names[0]);
        })
    },
    make_domain: function (name, operator, facet) {
        // ``json`` -> actual auto-completed id
        if (facet.get('values')) {
            return [[name, '=', facet.get('values')]];
        }

        return this._super(name, operator, facet);
    }
});

instance.web.search.Filters = instance.web.search.Input.extend({
    template: 'SearchView.Filters',
    _in_drawer: true,
    start: function () {
        var self = this;
        var running_count = 0;
        // get total filters count
        var is_group = function (i) { return i instanceof instance.web.search.FilterGroup; };
        var filters_count = _(this.view.controls).chain()
            .flatten()
            .filter(is_group)
            .map(function (i) { return i.filters.length; })
            .sum()
            .value();

        var col1 = [], col2 = _(this.view.controls).map(function (inputs, group) {
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
        (col1.length <= col2.length ? col1 : col2).push({
            name: _t("Custom Filters"),
            filters: _.map(this.view.custom_filters, function (filter) {
                // FIXME: handling of ``disabled`` being set
                var f = new instance.web.search.Filter({attrs: {
                    string: filter.name,
                    context: filter.context,
                    domain: filter.domain
                }}, self.view);
                return new instance.web.search.FilterGroup([f], self.view);
            }),
            length: this.view.custom_filters.length
        });
        return $.when(
            this.render_column(col1, $('<div>').appendTo(this.$element)),
            this.render_column(col2, $('<div>').appendTo(this.$element)));
    },
    render_column: function (column, $el) {
        return $.when.apply(null, _(column).map(function (group) {
            $('<h3>').text(group.name).appendTo($el);
            return $.when.apply(null,
                _(group.filters).invoke('appendTo', $el));
        }));
    }
});
instance.web.search.Advanced = instance.web.search.Input.extend({
    template: 'SearchView.advanced',
    _in_drawer: true,
    start: function () {
        var self = this;
        this.$element
            .on('keypress keydown keyup', function (e) { e.stopPropagation(); })
            .on('click', 'h4', function () {
                self.$element.toggleClass('oe_opened');
            }).on('click', 'button.oe_add_condition', function () {
                self.append_proposition();
            }).on('submit', 'form', function (e) {
                e.preventDefault();
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
        return (new instance.web.search.ExtendedSearchProposition(this, this.fields))
            .appendTo(this.$element.find('ul'));
    },
    commit_search: function () {
        var self = this;
        // Get domain sections from all propositions
        var children = this.getChildren(),
            domain = _.invoke(children, 'get_proposition');
        var filters = _(domain).map(function (section) {
            return new instance.web.search.Filter({attrs: {
                string: _.str.sprintf('%s(%s)%s',
                    section[0], section[1], section[2]),
                domain: [section]
            }}, self.view);
        });
        // Create Filter (& FilterGroup around it) with that domain
        var f = new instance.web.search.FilterGroup(filters, this.view);
        // add group to query
        this.query.add({
            category: _t("Advanced"),
            values: filters,
            field: f
        });
        // remove all propositions
        _.invoke(children, 'destroy');
        // add new empty proposition
        this.append_proposition();
        // TODO: API on searchview
        this.view.$element.removeClass('oe_searchview_open_drawer');
    }
});

instance.web.search.ExtendedSearchProposition = instance.web.OldWidget.extend(/** @lends instance.web.search.ExtendedSearchProposition# */{
    template: 'SearchView.extended_search.proposition',
    /**
     * @constructs instance.web.search.ExtendedSearchProposition
     * @extends instance.web.OldWidget
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
        var _this = this;
        this.$element.find(".searchview_extended_prop_field").change(function() {
            _this.changed();
        });
        this.$element.find('.searchview_extended_delete_prop').click(function () {
            _this.destroy();
        });
        this.changed();
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
        var obj = instance.web.search.custom_filters.get_object(type);
        if(obj === null) {
            obj = instance.web.search.custom_filters.get_object("char");
        }
        this.value = new (obj) (this);
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

instance.web.search.ExtendedSearchProposition.Field = instance.web.OldWidget.extend({
    start: function () {
        this.$element = $("#" + this.element_id);
    }
});
instance.web.search.ExtendedSearchProposition.Char = instance.web.search.ExtendedSearchProposition.Field.extend({
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
instance.web.search.ExtendedSearchProposition.DateTime = instance.web.search.ExtendedSearchProposition.Field.extend({
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
        this.datewidget = new instance.web.DateTimeWidget(this);
        this.datewidget.prependTo(this.$element);
    }
});
instance.web.search.ExtendedSearchProposition.Date = instance.web.search.ExtendedSearchProposition.Field.extend({
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
        this.datewidget = new instance.web.DateWidget(this);
        this.datewidget.prependTo(this.$element);
    }
});
instance.web.search.ExtendedSearchProposition.Integer = instance.web.search.ExtendedSearchProposition.Field.extend({
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
            return instance.web.parse_value(this.$element.val(), {'widget': 'integer'});
        } catch (e) {
            return "";
        }
    }
});
instance.web.search.ExtendedSearchProposition.Id = instance.web.search.ExtendedSearchProposition.Integer.extend({
    operators: [{value: "=", text: _lt("is")}]
});
instance.web.search.ExtendedSearchProposition.Float = instance.web.search.ExtendedSearchProposition.Field.extend({
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
            return instance.web.parse_value(this.$element.val(), {'widget': 'float'});
        } catch (e) {
            return "";
        }
    }
});
instance.web.search.ExtendedSearchProposition.Selection = instance.web.search.ExtendedSearchProposition.Field.extend({
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
instance.web.search.ExtendedSearchProposition.Boolean = instance.web.search.ExtendedSearchProposition.Field.extend({
    template: 'SearchView.extended_search.proposition.boolean',
    operators: [
        {value: "=", text: _lt("is true")},
        {value: "!=", text: _lt("is false")}
    ],
    get_value: function() {
        return true;
    }
});

instance.web.search.custom_filters = new instance.web.Registry({
    'char': 'instance.web.search.ExtendedSearchProposition.Char',
    'text': 'instance.web.search.ExtendedSearchProposition.Char',
    'one2many': 'instance.web.search.ExtendedSearchProposition.Char',
    'many2one': 'instance.web.search.ExtendedSearchProposition.Char',
    'many2many': 'instance.web.search.ExtendedSearchProposition.Char',

    'datetime': 'instance.web.search.ExtendedSearchProposition.DateTime',
    'date': 'instance.web.search.ExtendedSearchProposition.Date',
    'integer': 'instance.web.search.ExtendedSearchProposition.Integer',
    'float': 'instance.web.search.ExtendedSearchProposition.Float',
    'boolean': 'instance.web.search.ExtendedSearchProposition.Boolean',
    'selection': 'instance.web.search.ExtendedSearchProposition.Selection',

    'id': 'instance.web.search.ExtendedSearchProposition.Id'
});

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
