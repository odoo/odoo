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

function assert(condition, message) {
    if(!condition) {
        throw new Error(message);
    }
}
my.InputView = instance.web.Widget.extend({
    template: 'SearchView.InputView',
    start: function () {
        var p = this._super.apply(this, arguments);
        this.$element.on('focus', this.proxy('onFocus'));
        this.$element.on('blur', this.proxy('onBlur'));
        this.$element.on('keydown', this.proxy('onKeydown'));
        return p;
    },
    onFocus: function () {
        this.trigger('focused', this);
    },
    onBlur: function () {
        this.$element.text('');
        this.trigger('blurred', this);
    },
    getSelection: function () {
        // get Text node
        var root = this.$element[0].childNodes[0];
        if (!root || !root.textContent) {
            // if input does not have a child node, or the child node is an
            // empty string, then the selection can only be (0, 0)
            return {start: 0, end: 0};
        }
        if (window.getSelection) {
            var domRange = window.getSelection().getRangeAt(0);
            assert(domRange.startContainer === root,
                   "selection should be in the input view");
            assert(domRange.endContainer === root,
                   "selection should be in the input view");
            return {
                start: domRange.startOffset,
                end: domRange.endOffset
            }
        } else if (document.selection) {
            var ieRange = document.selection.createRange();
            var rangeParent = ieRange.parentElement();
            assert(rangeParent === root,
                   "selection should be in the input view");
            var offsetRange = document.body.createTextRange();
            offsetRange = offsetRange.moveToElementText(rangeParent);
            offsetRange.setEndPoint("EndToStart", ieRange);
            var start = offsetRange.text.length;
            return {
                start: start,
                end: start + ieRange.text.length
            }
        }
        throw new Error("Could not get caret position");
    },
    onKeydown: function (e) {
        var sel;
        switch (e.which) {
        // Do not insert newline, but let it bubble so searchview can use it
        case $.ui.keyCode.ENTER:
            e.preventDefault();
            break;

        // FIXME: may forget content if non-empty but caret at index 0, ok?
        case $.ui.keyCode.BACKSPACE:
            sel = this.getSelection();
            if (sel.start === 0 && sel.start === sel.end) {
                e.preventDefault();
                var preceding = this.getParent().siblingSubview(this, -1);
                if (preceding && (preceding instanceof my.FacetView)) {
                    preceding.model.destroy();
                }
            }
            break;

        // let left/right events propagate to view if caret is at input border
        // and not a selection
        case $.ui.keyCode.LEFT:
            sel = this.getSelection();
            if (sel.start !== 0 || sel.start !== sel.end) {
                e.stopPropagation();
            }
            break;
        case $.ui.keyCode.RIGHT:
            sel = this.getSelection();
            var len = this.$element.text().length;
            if (sel.start !== len || sel.start !== sel.end) {
                e.stopPropagation();
            }
            break;
        }
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
        this.$element.on('focus', function () { self.trigger('focused', self); });
        this.$element.on('blur', function () { self.trigger('blurred', self); });
        this.$element.on('click', function (e) {
            if ($(e.target).is('.oe_facet_remove')) {
                self.model.destroy();
                return false;
            }
            self.$element.focus();
            e.stopPropagation();
        });
        this.$element.on('keydown', function (e) {
            var keys = $.ui.keyCode;
            switch (e.which) {
            case keys.BACKSPACE:
            case keys.DELETE:
                self.model.destroy();
                return false;
            }
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

        this.input_subviews = [];

        this.ready = $.Deferred();
    },
    start: function() {
        var self = this;
        var p = this._super();

        this.setup_global_completion();
        this.query = new my.SearchQuery()
                .on('add change reset remove', this.proxy('do_search'))
                .on('add change reset remove', this.proxy('renderFacets'));

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

            $.when(load_view)
                .pipe(this.on_loaded)
                .fail(function () {
                    self.ready.reject.apply(null, arguments);
                });
        }

        // Launch a search on clicking the oe_searchview_search button
        this.$element.on('click', 'button.oe_searchview_search', function (e) {
            e.stopImmediatePropagation();
            self.do_search();
        });

        this.$element.on('keydown',
                '.oe_searchview_input, .oe_searchview_facet', function (e) {
            switch(e.which) {
            case $.ui.keyCode.LEFT:
                self.focusPreceding(this);
                e.preventDefault();
                break;
            case $.ui.keyCode.RIGHT:
                self.focusFollowing(this);
                e.preventDefault();
                break;
            }
        });

        this.$element.on('click', '.oe_searchview_clear', function (e) {
            e.stopImmediatePropagation();
            self.query.reset();
        });
        this.$element.on('click', '.oe_searchview_unfold_drawer', function (e) {
            e.stopImmediatePropagation();
            self.$element.toggleClass('oe_searchview_open_drawer');
        });
        instance.web.bus.on('click', this, function(ev) {
            if ($(ev.target).parents('.oe_searchview').length === 0) {
                self.$element.removeClass('oe_searchview_open_drawer');
            }
        });
        // Focus last input if the view itself is clicked (empty section of
        // facets element)
        this.$element.on('click', function (e) {
            if (e.target === self.$element.find('.oe_searchview_facets')[0]) {
                self.$element.find('.oe_searchview_input:last').focus();
            }
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

    subviewForRoot: function (subview_root) {
        return _(this.input_subviews).detect(function (subview) {
            return subview.$element[0] === subview_root;
        });
    },
    siblingSubview: function (subview, direction, wrap_around) {
        var index = _(this.input_subviews).indexOf(subview) + direction;
        if (wrap_around && index < 0) {
            index = this.input_subviews.length - 1;
        } else if (wrap_around && index >= this.input_subviews.length) {
            index = 0;
        }
        return this.input_subviews[index];
    },
    focusPreceding: function (subview_root) {
        return this.siblingSubview(
            this.subviewForRoot(subview_root), -1, true)
                .$element.focus();
    },
    focusFollowing: function (subview_root) {
        return this.siblingSubview(
            this.subviewForRoot(subview_root), +1, true)
                .$element.focus();
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
            minLength: 1,
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

        var input_index = _(this.input_subviews).indexOf(
            this.subviewForRoot(
                this.$element.find('div.oe_searchview_input:focus')[0]));
        this.query.add(ui.item.facet, {at: input_index / 2});
    },
    childFocused: function () {
        this.$element.addClass('oe_focused');
    },
    childBlurred: function () {
        var val = this.$element.val();
        this.$element.val('');
        var complete = this.$element.data('autocomplete');
        if ((val && complete.term === undefined) || complete.previous !== undefined) {
            throw new Error("new jquery.ui version altering implementation" +
                            " details relied on");
        }
        delete complete.term;
        this.$element.removeClass('oe_focused')
                     .trigger('blur');
    },
    /**
     *
     * @param {openerp.web.search.SearchQuery | openerp.web.search.Facet} _1
     * @param {openerp.web.search.Facet} [_2]
     * @param {Object} [options]
     */
    renderFacets: function (_1, _2, options) {
        // _1: model if event=change, otherwise collection
        // _2: undefined if event=change, otherwise model
        var self = this;
        var started = [];
        var $e = this.$element.find('div.oe_searchview_facets');
        _.invoke(this.input_subviews, 'destroy');
        this.input_subviews = [];

        var i = new my.InputView(this);
        started.push(i.appendTo($e));
        this.input_subviews.push(i);
        this.query.each(function (facet) {
            var f = new my.FacetView(this, facet);
            started.push(f.appendTo($e));
            self.input_subviews.push(f);

            var i = new my.InputView(this);
            started.push(i.appendTo($e));
            self.input_subviews.push(i);
        }, this);
        _.each(this.input_subviews, function (childView) {
            childView.on('focused', self, self.proxy('childFocused'));
            childView.on('blurred', self, self.proxy('childBlurred'));
        });

        $.when.apply(null, started).then(function () {
            var input_to_focus;
            // options.at: facet inserted at given index, focus next input
            // otherwise just focus last input
            if (!options || typeof options.at !== 'number') {
                input_to_focus = _.last(self.input_subviews);
            } else {
                input_to_focus = self.input_subviews[(options.at + 1) * 2];
            }

            input_to_focus.$element.focus();
        });
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

    add_common_inputs: function() {
        // add Filters to this.inputs, need view.controls filled
        (new instance.web.search.Filters(this));
        // add custom filters to this.inputs
        (new instance.web.search.CustomFilters(this));
        // add Advanced to this.inputs
        (new instance.web.search.Advanced(this));
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

        this.add_common_inputs();

        // build drawer
        var drawer_started = $.when.apply(
            null, _(this.select_for_drawer()).invoke(
                'appendTo', this.$element.find('.oe_searchview_drawer')));
        
        // load defaults
        var defaults_fetched = $.when.apply(null, _(this.inputs).invoke(
            'facet_for_defaults', this.defaults)).then(function () {
                self.query.reset(_(arguments).compact(), {preventSearch: true});
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
    /**
     * Extract search data from the view's facets.
     *
     * Result is an object with 4 (own) properties:
     *
     * errors
     *     An array of any error generated during data validation and
     *     extraction, contains the validation error objects
     * domains
     *     Array of domains
     * contexts
     *     Array of contexts
     * groupbys
     *     Array of domains, in groupby order rather than view order
     *
     * @return {Object}
     */
    build_search_data: function () {
        var domains = [], contexts = [], groupbys = [], errors = [];

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
        return {
            domains: domains,
            contexts: contexts,
            groupbys: groupbys,
            errors: errors
        };
    }, /**
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
    do_search: function (_query, options) {
        if (options && options.preventSearch) {
            return;
        }
        var search = this.build_search_data();
        if (!_.isEmpty(search.errors)) {
            this.on_invalid(search.errors);
            return;
        }
        return this.on_search(search.domains, search.contexts, search.groupbys);
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
instance.web.search.Widget = instance.web.Widget.extend( /** @lends instance.web.search.Widget# */{
    template: null,
    /**
     * Root class of all search widgets
     *
     * @constructs instance.web.search.Widget
     * @extends instance.web.Widget
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
    icon: 'q',
    completion_label: _lt("Filter on: %s"),
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
        // If all filters are group_by and we're not initializing a GroupbyGroup,
        // create a GroupbyGroup instead of the current FilterGroup
        if (!(this instanceof instance.web.search.GroupbyGroup) &&
              _(filters).all(function (f) {
                  return f.attrs.context && f.attrs.context.group_by; })) {
            return new instance.web.search.GroupbyGroup(filters, view);
        }
        this._super(view);
        this.filters = filters;
        this.view.query.on('add remove change reset', this.proxy('search_change'));
    },
    start: function () {
        this.$element.on('click', 'li', this.proxy('toggle_filter'));
        return $.when(null);
    },
    /**
     * Handles change of the search query: any of the group's filter which is
     * in the search query should be visually checked in the drawer
     */
    search_change: function () {
        var self = this;
        var $filters = this.$element.find('> li').removeClass('oe_selected');
        var facet = this.view.query.find(_.bind(this.match_facet, this));
        if (!facet) { return; }
        facet.values.each(function (v) {
            var i = _(self.filters).indexOf(v.get('value'));
            if (i === -1) { return; }
            $filters.eq(i).addClass('oe_selected');
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
            category: _t("Filter"),
            icon: this.icon,
            values: values,
            field: this
        }
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
        return  facet.values.chain()
            .map(function (f) { return f.get('value').attrs.context; })
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
        var domains = facet.values.chain()
            .map(function (f) { return f.get('value').attrs.domain; })
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
        this.view.query.toggle(this.make_facet([this.make_value(filter)]));
    },
    complete: function (item) {
        var self = this;
        item = item.toLowerCase();
        var facet_values = _(this.filters).chain()
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
                                     facet_value.label),
                facet: self.make_facet([facet_value])
            }
        }));
    }
});
instance.web.search.GroupbyGroup = instance.web.search.FilterGroup.extend({
    icon: 'w',
    completion_label: _lt("Group by: %s"),
    init: function (filters, view) {
        this._super(filters, view);
        // Not flanders: facet unicity is handled through the
        // (category, field) pair of facet attributes. This is all well and
        // good for regular filter groups where a group matches a facet, but for
        // groupby we want a single facet. So cheat: add an attribute on the
        // view which proxies to the first GroupbyGroup, so it can be used
        // for every GroupbyGroup and still provides the various methods needed
        // by the search view. Use weirdo name to avoid risks of conflicts
        if (!this.getParent()._s_groupby) {
            this.getParent()._s_groupby = {
                help: "See GroupbyGroup#init",
                get_context: this.proxy('get_context'),
                get_domain: this.proxy('get_domain'),
                get_groupby: this.proxy('get_groupby')
            }
        }
    },
    match_facet: function (facet) {
        return facet.get('field') === this.getParent()._s_groupby;
    },
    make_facet: function (values) {
        return {
            category: _t("GroupBy"),
            icon: this.icon,
            values: values,
            field: this.getParent()._s_groupby
        };
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
            return new instance.web.CompoundContext(context)
                .set_eval_context({self: self.value_from(facetValue)});
        });

        if (contexts.length === 1) { return contexts[0]; }

        return _.extend(new instance.web.CompoundContext, {
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
     * @param {Number|String} value parsed value for the field
     * @returns {Array<Array>} domain to include in the resulting search
     */
    make_domain: function (name, operator, facet) {
        return [[name, operator, this.value_from(facet)]];
    },
    get_domain: function (facet) {
        if (!facet.values.length) { return; }

        var value_to_domain;
        var self = this;
        var domain = this.attrs['filter_domain'];
        if (domain) {
            value_to_domain = function (facetValue) {
                return new instance.web.CompoundDomain(domain)
                    .set_eval_context({self: self.value_from(facetValue)});
            };
        } else {
            value_to_domain = function (facetValue) {
                return self.make_domain(
                    self.attrs.name,
                    self.attrs.operator || self.default_operator,
                    facetValue);
            };
        }
        var domains = facet.values.map(value_to_domain);

        if (domains.length === 1) { return domains[0]; }
        for (var i = domains.length; --i;) {
            domains.unshift(['|']);
        }

        return _.extend(new instance.web.CompoundDomain, {
            __domains: domains
        });
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
    value_from: function () {
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
            [true, _t("Yes")],
            [false, _t("No")]
        ];
    }
});
/**
 * @class
 * @extends instance.web.search.DateField
 */
instance.web.search.DateField = instance.web.search.Field.extend(/** @lends instance.web.search.DateField# */{
    value_from: function (facetValue) {
        return instance.web.date_to_str(facetValue.get('value'));
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
    value_from: function (facetValue) {
        return instance.web.datetime_to_str(facetValue.get('value'));
    }
});
instance.web.search.ManyToOneField = instance.web.search.CharField.extend({
    default_operator: {},
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
            if (value.length === 2 && _.isString(value[1])) {
                return $.when(facet_from(this, value));
            }
            if (value.length > 1) {
                // more than one search_default m2o id? Should we OR them?
                throw new Error(
                    _("M2O search fields do not currently handle multiple default values"));
            }
            // there are many cases of {search_default_$m2ofield: [id]}, need
            // to handle this as if it were a single value.
            value = value[0];
        }
        return this.model.call('name_get', [value], {}).pipe(function (names) {
            if (_(names).isEmpty()) { return null; }
            return facet_from(self, names[0]);
        })
    },
    value_from: function (facetValue) {
        return facetValue.get('label');
    },
    make_domain: function (name, operator, facetValue) {
        if (operator === this.default_operator) {
            return [[name, '=', facetValue.get('value')]];
        }
        return this._super(name, operator, facetValue);
    },
    get_context: function (facet) {
        var values = facet.values;
        if (_.isEmpty(this.attrs.context) && values.length === 1) {
            var c = {};
            c['default_' + this.attrs.name] = values.at(0).get('value');
            return c;
        }
        return this._super(facet);
    }
});

instance.web.search.CustomFilters = instance.web.search.Input.extend({
    template: 'SearchView.CustomFilters',
    _in_drawer: true,
    start: function () {
        var self = this;
        this.model = new instance.web.Model('ir.filters');
        this.filters = {};
        this.view.query
            .on('remove', function (facet) {
                if (!facet.get('is_custom_filter')) {
                    return;
                }
                self.clear_selection();
            })
            .on('reset', this.proxy('clear_selection'));
        this.$element.on('submit', 'form', this.proxy('save_current'));
        this.$element.on('click', 'h4', function () {
            self.$element.toggleClass('oe_opened');
        });
        // FIXME: local eval of domain and context to get rid of special endpoint
        return this.rpc('/web/searchview/get_filters', {
            model: this.view.model
        }).pipe(this.proxy('set_filters'));
    },
    clear_selection: function () {
        this.$element.find('li.oe_selected').removeClass('oe_selected');
    },
    append_filter: function (filter) {
        var self = this;
        var key = _.str.sprintf('(%s)%s', filter.user_id, filter.name);

        var $filter;
        if (key in this.filters) {
            $filter = this.filters[key];
        } else {
            var id = filter.id;
            $filter = this.filters[key] = $('<li></li>')
                .appendTo(this.$element.find('.oe_searchview_custom_list'))
                .addClass(filter.user_id ? 'oe_searchview_custom_private'
                                         : 'oe_searchview_custom_public')
                .text(filter.name);

            $('<a class="oe_searchview_custom_delete">x</a>')
                .click(function (e) {
                    e.stopPropagation();
                    self.model.call('unlink', [id]).then(function () {
                        $filter.remove();
                    });
                })
                .appendTo($filter);
        }

        $filter.unbind('click').click(function () {
            self.view.query.reset([{
                category: _("Custom Filter"),
                icon: 'M',
                field: {
                    get_context: function () { return filter.context; },
                    get_groupby: function () { return [filter.context]; },
                    get_domain: function () { return filter.domain; }
                },
                is_custom_filter: true,
                values: [{label: filter.name, value: null}]
            }]);
            $filter.addClass('oe_selected');
        });
    },
    set_filters: function (filters) {
        _(filters).map(_.bind(this.append_filter, this));
    },
    save_current: function () {
        var self = this;
        var $name = this.$element.find('input:first');
        var private_filter = !this.$element.find('input:last').prop('checked');

        var search = this.view.build_search_data();
        this.rpc('/web/session/eval_domain_and_context', {
            domains: search.domains,
            contexts: search.contexts,
            group_by_seq: search.groupbys || []
        }).then(function (results) {
            if (!_.isEmpty(results.group_by)) {
                results.context.group_by = results.group_by;
            }
            var filter = {
                name: $name.val(),
                user_id: private_filter ? instance.session.uid : false,
                model_id: self.view.model,
                context: results.context,
                domain: results.domain
            };
            // FIXME: current context?
            return self.model.call('create_or_replace', [filter]).then(function (id) {
                filter.id = id;
                self.append_filter(filter);
                self.$element
                    .removeClass('oe_opened')
                    .find('form')[0].reset();
            });
        });
        return false;
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
                name: group === 'null' ? "<span class='oe_i'>q</span> " + _t("Filters") : "<span class='oe_i'>w</span> " + group,
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

        return $.when(
            this.render_column(col1, $('<div>').appendTo(this.$element)),
            this.render_column(col2, $('<div>').appendTo(this.$element)));
    },
    render_column: function (column, $el) {
        return $.when.apply(null, _(column).map(function (group) {
            $('<h3>').html(group.name).appendTo($el);
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
        var children = this.getChildren();
        var propositions = _.invoke(children, 'get_proposition');
        var domain = _(propositions).pluck('value');
        for (var i = domain.length; --i;) {
            domain.unshift('|');
        }

        this.view.query.add({
            category: _t("Advanced"),
            values: propositions,
            field: {
                get_context: function () { },
                get_domain: function () { return domain;},
                get_groupby: function () { }
            }
        });

        // remove all propositions
        _.invoke(children, 'destroy');
        // add new empty proposition
        this.append_proposition();
        // TODO: API on searchview
        this.view.$element.removeClass('oe_searchview_open_drawer');
    }
});

instance.web.search.ExtendedSearchProposition = instance.web.Widget.extend(/** @lends instance.web.search.ExtendedSearchProposition# */{
    template: 'SearchView.extended_search.proposition',
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
        var Field = instance.web.search.custom_filters.get_object(type);
        if(!Field) {
            Field = instance.web.search.custom_filters.get_object("char");
        }
        this.value = new Field(this, field);
        _.each(this.value.operators, function(operator) {
            $('<option>', {value: operator.value})
                .text(String(operator.text))
                .appendTo(self.$element.find('.searchview_extended_prop_op'));
        });
        var $value_loc = this.$element.find('.searchview_extended_prop_value').empty();
        this.value.appendTo($value_loc);

    },
    get_proposition: function() {
        if ( this.attrs.selected == null)
            return null;
        var field = this.attrs.selected;
        var op = this.$element.find('.searchview_extended_prop_op')[0];
        var operator = op.options[op.selectedIndex];
        return {
            label: _.str.sprintf(_t('%(field)s %(operator)s "%(value)s"'), {
                field: field.string,
                // According to spec, HTMLOptionElement#label should return
                // HTMLOptionElement#text when not defined/empty, but it does
                // not in older Webkit (between Safari 5.1.5 and Chrome 17) and
                // Gecko (pre Firefox 7) browsers, so we need a manual fallback
                // for those
                operator: operator.label || operator.text,
                value: this.value}),
            value: [field.name, operator.value, this.value.get_value()]
        };
    }
});

instance.web.search.ExtendedSearchProposition.Field = instance.web.Widget.extend({
    init: function (parent, field) {
        this._super(parent);
        this.field = field;
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
    /**
     * Date widgets live in view_form which is not yet loaded when this is
     * initialized -_-
     */
    widget: function () { return instance.web.DateTimeWidget; },
    get_value: function() {
        return this.datewidget.get_value();
    },
    start: function() {
        var ready = this._super();
        this.datewidget = new (this.widget())(this);
        this.datewidget.appendTo(this.$element);
        return ready;
    }
});
instance.web.search.ExtendedSearchProposition.Date = instance.web.search.ExtendedSearchProposition.DateTime.extend({
    widget: function () { return instance.web.DateWidget; }
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
    toString: function () {
        return this.$element.val();
    },
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
    toString: function () {
        return this.$element.val();
    },
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
    toString: function () {
        var select = this.$element[0];
        var option = select.options[select.selectedIndex];
        return option.label || option.text;
    },
    get_value: function() {
        return this.$element.val();
    }
});
instance.web.search.ExtendedSearchProposition.Boolean = instance.web.search.ExtendedSearchProposition.Field.extend({
    template: 'SearchView.extended_search.proposition.empty',
    operators: [
        {value: "=", text: _lt("is true")},
        {value: "!=", text: _lt("is false")}
    ],
    toString: function () { return ''; },
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
