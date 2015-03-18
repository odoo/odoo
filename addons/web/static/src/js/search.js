
(function() {

var instance = openerp;
openerp.web.search = {};

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
        this.values.on('add remove change reset', function (_, options) {
            this.trigger('change', this, options);
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

            this.remove(facet, {silent: true});
        }, this);
    },
    add: function (values, options) {
        options = options || {};

        if (!values) {
            values = [];
        } else if (!(values instanceof Array)) {
            values = [values];
        }

        _(values).each(function (value) {
            var model = this._prepareModel(value, options);
            var previous = this.detect(function (facet) {
                return facet.get('category') === model.get('category')
                    && facet.get('field') === model.get('field');
            });
            if (previous) {
                previous.values.add(model.get('values'), _.omit(options, 'at', 'merge'));
                return;
            }
            B.Collection.prototype.add.call(this, model, options);
        }, this);
        // warning: in backbone 1.0+ add is supposed to return the added models,
        // but here toggle may delegate to add and return its value directly.
        // return value of neither seems actually used but should be tested
        // before change, probably
        return this;
    },
    toggle: function (value, options) {
        options = options || {};

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
    events: {
        focus: function () { this.trigger('focused', this); },
        blur: function () { this.$el.text(''); this.trigger('blurred', this); },
        keydown: 'onKeydown',
        paste: 'onPaste',
    },
    getSelection: function () {
        this.el.normalize();
        // get Text node
        var root = this.el.childNodes[0];
        if (!root || !root.textContent) {
            // if input does not have a child node, or the child node is an
            // empty string, then the selection can only be (0, 0)
            return {start: 0, end: 0};
        }
        var range = window.getSelection().getRangeAt(0);
        // In Firefox, depending on the way text is selected (drag, double- or
        // triple-click) the range may start or end on the parent of the
        // selected text node‽ Check for this condition and fixup the range
        // note: apparently with C-a this can go even higher?
        if (range.startContainer === this.el && range.startOffset === 0) {
            range.setStart(root, 0);
        }
        if (range.endContainer === this.el && range.endOffset === 1) {
            range.setEnd(root, root.length);
        }
        assert(range.startContainer === root,
               "selection should be in the input view");
        assert(range.endContainer === root,
               "selection should be in the input view");
        return {
            start: range.startOffset,
            end: range.endOffset
        };
    },
    onKeydown: function (e) {
        this.el.normalize();
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
            var len = this.$el.text().length;
            if (sel.start !== len || sel.start !== sel.end) {
                e.stopPropagation();
            }
            break;
        }
    },
    setCursorAtEnd: function () {
        this.el.normalize();
        var sel = window.getSelection();
        sel.removeAllRanges();
        var range = document.createRange();
        // in theory, range.selectNodeContents should work here. In practice,
        // MSIE9 has issues from time to time, instead of selecting the inner
        // text node it would select the reference node instead (e.g. in demo
        // data, company news, copy across the "Company News" link + the title,
        // from about half the link to half the text, paste in search box then
        // hit the left arrow key, getSelection would blow up).
        //
        // Explicitly selecting only the inner text node (only child node
        // since we've normalized the parent) avoids the issue
        range.selectNode(this.el.childNodes[0]);
        range.collapse(false);
        sel.addRange(range);
    },
    onPaste: function () {
        this.el.normalize();
        // In MSIE and Webkit, it is possible to get various representations of
        // the clipboard data at this point e.g.
        // window.clipboardData.getData('Text') and
        // event.clipboardData.getData('text/plain') to ensure we have a plain
        // text representation of the object (and probably ensure the object is
        // pastable as well, so nobody puts an image in the search view)
        // (nb: since it's not possible to alter the content of the clipboard
        // — at least in Webkit — to ensure only textual content is available,
        // using this would require 1. getting the text data; 2. manually
        // inserting the text data into the content; and 3. cancelling the
        // paste event)
        //
        // But Firefox doesn't support the clipboard API (as of FF18)
        // although it correctly triggers the paste event (Opera does not even
        // do that) => implement lowest-denominator system where onPaste
        // triggers a followup "cleanup" pass after the data has been pasted
        setTimeout(function () {
            // Read text content (ignore pasted HTML)
            var data = this.$el.text();
            if (!data)
                return; 
            // paste raw text back in
            this.$el.empty().text(data);
            this.el.normalize();
            // Set the cursor at the end of the text, so the cursor is not lost
            // in some kind of error-spawning limbo.
            this.setCursorAtEnd();
        }.bind(this), 0);
    }
});
my.FacetView = instance.web.Widget.extend({
    template: 'SearchView.FacetView',
    events: {
        'focus': function () { this.trigger('focused', this); },
        'blur': function () { this.trigger('blurred', this); },
        'click': function (e) {
            if ($(e.target).is('.oe_facet_remove')) {
                this.model.destroy();
                return false;
            }
            this.$el.focus();
            e.stopPropagation();
        },
        'keydown': function (e) {
            var keys = $.ui.keyCode;
            switch (e.which) {
            case keys.BACKSPACE:
            case keys.DELETE:
                this.model.destroy();
                return false;
            }
        }
    },
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
        var $e = this.$('> span:last-child');
        return $.when(this._super()).then(function () {
            return $.when.apply(null, self.model.values.map(function (value) {
                return new my.FacetValueView(self, value).appendTo($e);
            }));
        });
    },
    model_changed: function () {
        this.$el.text(this.$el.text() + '*');
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
        this.$el.text(this.$el.text() + '*');
    }
});

instance.web.SearchView = instance.web.Widget.extend(/** @lends instance.web.SearchView# */{
    template: "SearchView",
    events: {
        // focus last input if view itself is clicked
        'click': function (e) {
            if (e.target === this.$('.oe_searchview_facets')[0]) {
                this.$('.oe_searchview_input:last').focus();
            }
        },
        // search button
        'click button.oe_searchview_search': function (e) {
            e.stopImmediatePropagation();
            this.do_search();
        },
        'click .oe_searchview_clear': function (e) {
            e.stopImmediatePropagation();
            this.query.reset();
        },
        'click .oe_searchview_unfold_drawer': function (e) {
            e.stopImmediatePropagation();
            if (this.drawer) 
                this.drawer.toggle();
        },
        'keydown .oe_searchview_input, .oe_searchview_facet': function (e) {
            switch(e.which) {
            case $.ui.keyCode.LEFT:
                this.focusPreceding(e.target);
                e.preventDefault();
                break;
            case $.ui.keyCode.RIGHT:
                if (!this.autocomplete.is_expandable()) {
                    this.focusFollowing(e.target);
                }
                e.preventDefault();
                break;
            }
        },
        'autocompleteopen': function () {
            this.$el.autocomplete('widget').css('z-index', 9999);
        },
    },
    /**
     * @constructs instance.web.SearchView
     * @extends instance.web.Widget
     *
     * @param parent
     * @param dataset
     * @param view_id
     * @param defaults
     * @param {Object} [options]
     * @param {Boolean} [options.hidden=false] hide the search view
     * @param {Boolean} [options.disable_custom_filters=false] do not load custom filters from ir.filters
     */
    init: function(parent, dataset, view_id, defaults, options) {
        this.options = _.defaults(options || {}, {
            hidden: false,
            disable_custom_filters: false,
        });
        this._super(parent);
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;

        this.defaults = defaults || {};
        this.has_defaults = !_.isEmpty(this.defaults);

        this.headless = this.options.hidden && !this.has_defaults;

        this.input_subviews = [];
        this.view_manager = null;
        this.$view_manager_header = null;

        this.ready = $.Deferred();
        this.drawer_ready = $.Deferred();
        this.fields_view_get = $.Deferred();
        this.drawer = new instance.web.SearchViewDrawer(parent, this);

    },
    start: function() {
        var self = this;
        var p = this._super();

        this.$view_manager_header = this.$el.parents(".oe_view_manager_header").first();

        this.setup_global_completion();
        this.query = new my.SearchQuery()
                .on('add change reset remove', this.proxy('do_search'))
                .on('change', this.proxy('renderChangedFacets'))
                .on('add reset remove', this.proxy('renderFacets'));

        if (this.options.hidden) {
            this.$el.hide();
        }
        if (this.headless) {
            this.ready.resolve();
        } else {
            var load_view = instance.web.fields_view_get({
                model: this.dataset._model,
                view_id: this.view_id,
                view_type: 'search',
                context: this.dataset.get_context(),
            });

            this.alive($.when(load_view)).then(function (r) {
                self.fields_view_get.resolve(r);
                return self.search_view_loaded(r);
            }).fail(function () {
                self.ready.reject.apply(null, arguments);
            });
        }

        var view_manager = this.getParent();
        while (!(view_manager instanceof instance.web.ViewManager) &&
                view_manager && view_manager.getParent) {
            view_manager = view_manager.getParent();
        }

        if (view_manager) {
            this.view_manager = view_manager;
            view_manager.on('switch_mode', this, function (e) {
                self.drawer.toggle(e === 'graph');
            });
        }
        return $.when(p, this.ready);
    },

    set_drawer: function (drawer) {
        this.drawer = drawer;
    },

    show: function () {
        this.$el.show();
    },
    hide: function () {
        this.$el.hide();
    },

    subviewForRoot: function (subview_root) {
        return _(this.input_subviews).detect(function (subview) {
            return subview.$el[0] === subview_root;
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
                .$el.focus();
    },
    focusFollowing: function (subview_root) {
        return this.siblingSubview(
            this.subviewForRoot(subview_root), +1, true)
                .$el.focus();
    },

    /**
     * Sets up search view's view-wide auto-completion widget
     */
    setup_global_completion: function () {
        var self = this;
        this.autocomplete = new instance.web.search.AutoComplete(this, {
            source: this.proxy('complete_global_search'),
            select: this.proxy('select_completion'),
            get_search_string: function () {
                return self.$('div.oe_searchview_input').text();
            },
            width: this.$el.width(),
        });
        this.autocomplete.appendTo(this.$el);
    },
    /**
     * Provide auto-completion result for req.term (an array to `resp`)
     *
     * @param {Object} req request to complete
     * @param {String} req.term searched term to complete
     * @param {Function} resp response callback
     */
    complete_global_search:  function (req, resp) {
        $.when.apply(null, _(this.drawer.inputs).chain()
            .filter(function (input) { return input.visible(); })
            .invoke('complete', req.term)
            .value()).then(function () {
                resp(_(arguments).chain()
                    .compact()
                    .flatten(true)
                    .value());
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
                this.$('div.oe_searchview_input:focus')[0]));
        this.query.add(ui.item.facet, {at: input_index / 2});
    },
    childFocused: function () {
        this.$el.addClass('oe_focused');
    },
    childBlurred: function () {
        var val = this.$el.val();
        this.$el.val('');
        this.$el.removeClass('oe_focused')
                     .trigger('blur');
        this.autocomplete.close();
    },
    /**
     * Call the renderFacets method with the correct arguments.
     * This is due to the fact that change events are called with two arguments
     * (model, options) while add, reset and remove events are called with
     * (collection, model, options) as arguments
     */
    renderChangedFacets: function (model, options) {
        this.renderFacets(undefined, model, options);
    },
    /**
     * @param {openerp.web.search.SearchQuery | undefined} Undefined if event is change
     * @param {openerp.web.search.Facet} 
     * @param {Object} [options]
     */
    renderFacets: function (collection, model, options) {
        var self = this;
        var started = [];
        var $e = this.$('div.oe_searchview_facets');
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
            if (options && options.focus_input === false) return;
            var input_to_focus;
            // options.at: facet inserted at given index, focus next input
            // otherwise just focus last input
            if (!options || typeof options.at !== 'number') {
                input_to_focus = _.last(self.input_subviews);
            } else {
                input_to_focus = self.input_subviews[(options.at + 1) * 2];
            }
            input_to_focus.$el.focus();
        });
    },

    search_view_loaded: function(data) {
        var self = this;
        this.fields_view = data;
        this.view_id = this.view_id || data.view_id;
        if (data.type !== 'search' ||
            data.arch.tag !== 'search') {
                throw new Error(_.str.sprintf(
                    "Got non-search view after asking for a search view: type %s, arch root %s",
                    data.type, data.arch.tag));
        }

        return this.drawer_ready
            .then(this.proxy('setup_default_query'))
            .then(function () { 
                self.trigger("search_view_loaded", data);
                self.ready.resolve();
            });
    },
    setup_default_query: function () {
        // Hacky implementation of CustomFilters#facet_for_defaults ensure
        // CustomFilters will be ready (and CustomFilters#filters will be
        // correctly filled) by the time this method executes.
        var custom_filters = this.drawer.custom_filters.filters;
        if (!this.options.disable_custom_filters && !_(custom_filters).isEmpty()) {
            // Check for any is_default custom filter
            var personal_filter = _(custom_filters).find(function (filter) {
                return filter.user_id && filter.is_default;
            });
            if (personal_filter) {
                this.drawer.custom_filters.toggle_filter(personal_filter, true);
                return;
            }

            var global_filter = _(custom_filters).find(function (filter) {
                return !filter.user_id && filter.is_default;
            });
            if (global_filter) {
                this.drawer.custom_filters.toggle_filter(global_filter, true);
                return;
            }
        }
        // No custom filter, or no is_default custom filter, apply view defaults
        this.query.reset(_(arguments).compact(), {preventSearch: true});
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
     * @param [_query]
     * @param {Object} [options]
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
        this.trigger('search_data', search.domains, search.contexts, search.groupbys);
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
        this.trigger('invalid_search', errors);
    },

    // The method appendTo is overwrited to be able to insert the drawer anywhere
    appendTo: function ($searchview_parent, $searchview_drawer_node) {
        var $searchview_drawer_node = $searchview_drawer_node || $searchview_parent;

        return $.when(
            this._super($searchview_parent),
            this.drawer.appendTo($searchview_drawer_node)
        );
    },

    destroy: function () {
        this.drawer.destroy();
        this.getParent().destroy.call(this);
    }
});

instance.web.SearchViewDrawer = instance.web.Widget.extend({
    template: "SearchViewDrawer",

    init: function(parent, searchview) {
        this._super(parent);
        this.searchview = searchview;
        this.searchview.set_drawer(this);
        this.ready = searchview.drawer_ready;
        this.controls = [];
        this.inputs = [];
    },

    toggle: function (visibility) {
        this.$el.toggle(visibility);
        var $view_manager_body = this.$el.closest('.oe_view_manager_body');
        if ($view_manager_body.length) {
            $view_manager_body.scrollTop(0);
        }
    },

    start: function() {
        var self = this;
        if (this.searchview.headless) return $.when(this._super(), this.searchview.ready);
        var filters_ready = this.searchview.fields_view_get
                                .then(this.proxy('prepare_filters'));
        return $.when(this._super(), filters_ready).then(function () {
            var defaults = arguments[1][0];
            self.ready.resolve.apply(null, defaults);
        });
    },
    prepare_filters: function (data) {
        this.make_widgets(
            data['arch'].children,
            data.fields);

        this.add_common_inputs();

        // build drawer
        var in_drawer = this.select_for_drawer();

        var $first_col = this.$(".col-md-7"),
            $snd_col = this.$(".col-md-5");

        var add_custom_filters = in_drawer[0].appendTo($first_col),
            add_filters = in_drawer[1].appendTo($first_col),
            add_rest = $.when.apply(null, _(in_drawer.slice(2)).invoke('appendTo', $snd_col)),
            defaults_fetched = $.when.apply(null, _(this.inputs).invoke(
                'facet_for_defaults', this.searchview.defaults));

        return $.when(defaults_fetched, add_custom_filters, add_filters, add_rest);
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
     * Builds a list of widget rows (each row is an array of widgets)
     *
     * @param {Array} items a list of nodes to convert to widgets
     * @param {Object} fields a mapping of field names to (ORM) field attributes
     * @param {Object} [group] group to put the new controls in
     */
    make_widgets: function (items, fields, group) {
        if (!group) {
            group = new instance.web.search.Group(
                this, 'q', {attrs: {string: _t("Filters")}});
        }
        var self = this;
        var filters = [];
        _.each(items, function (item) {
            if (filters.length && item.tag !== 'filter') {
                group.push(new instance.web.search.FilterGroup(filters, group));
                filters = [];
            }

            switch (item.tag) {
            case 'separator': case 'newline':
                break;
            case 'filter':
                filters.push(new instance.web.search.Filter(item, group));
                break;
            case 'group':
                self.add_separator();
                self.make_widgets(item.children, fields,
                    new instance.web.search.Group(group, 'w', item));
                self.add_separator();
                break;
            case 'field':
                var field = this.make_field(
                    item, fields[item['attrs'].name], group);
                group.push(field);
                // filters
                self.make_widgets(item.children, fields, group);
                break;
            }
        }, this);

        if (filters.length) {
            group.push(new instance.web.search.FilterGroup(filters, this));
        }
    },

    add_separator: function () {
        if (!(_.last(this.inputs) instanceof instance.web.search.Separator))
            new instance.web.search.Separator(this);
    },
    /**
     * Creates a field for the provided field descriptor item (which comes
     * from fields_view_get)
     *
     * @param {Object} item fields_view_get node for the field
     * @param {Object} field fields_get result for the field
     * @param {Object} [parent]
     * @returns instance.web.search.Field
     */
    make_field: function (item, field, parent) {
        // M2O combined with selection widget is pointless and broken in search views,
        // but has been used in the past for unsupported hacks -> ignore it
        if (field.type === "many2one" && item.attrs.widget === "selection"){
            item.attrs.widget = undefined;
        }
        var obj = instance.web.search.fields.get_any( [item.attrs.widget, field.type]);
        if(obj) {
            return new (obj) (item, field, parent || this);
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
        // add custom filters to this.inputs
        this.custom_filters = new instance.web.search.CustomFilters(this);
        // add Filters to this.inputs, need view.controls filled
        (new instance.web.search.Filters(this));
        (new instance.web.search.SaveFilter(this, this.custom_filters));
        // add Advanced to this.inputs
        (new instance.web.search.Advanced(this));
    },

});

/**
 * Registry of search fields, called by :js:class:`instance.web.SearchView` to
 * find and instantiate its field widgets.
 */
instance.web.search.fields = new instance.web.Registry({
    'char': 'instance.web.search.CharField',
    'text': 'instance.web.search.CharField',
    'html': 'instance.web.search.CharField',
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
     * @param parent parent of this widget
     */
    init: function (parent) {
        this._super(parent);
        var ancestor = parent;
        do {
            this.drawer = ancestor;
        } while (!(ancestor instanceof instance.web.SearchViewDrawer)
               && (ancestor = (ancestor.getParent && ancestor.getParent())));
        this.view = this.drawer.searchview || this.drawer;
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
    init: function (parent, icon, node) {
        this._super(parent);
        var attrs = node.attrs;
        this.modifiers = attrs.modifiers =
            attrs.modifiers ? JSON.parse(attrs.modifiers) : {};
        this.attrs = attrs;
        this.icon = icon;
        this.name = attrs.string;
        this.children = [];

        this.drawer.controls.push(this);
    },
    push: function (input) {
        this.children.push(input);
    },
    visible: function () {
        return !this.modifiers.invisible;
    },
});

instance.web.search.Input = instance.web.search.Widget.extend( /** @lends instance.web.search.Input# */{
    _in_drawer: false,
    /**
     * @constructs instance.web.search.Input
     * @extends instance.web.search.Widget
     *
     * @param parent
     */
    init: function (parent) {
        this._super(parent);
        this.load_attrs({});
        this.drawer.inputs.push(this);
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
        attrs.modifiers = attrs.modifiers ? JSON.parse(attrs.modifiers) : {};
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
        if (this.attrs.modifiers.invisible) {
            return false;
        }
        var parent = this;
        while ((parent = parent.getParent()) &&
               (   (parent instanceof instance.web.search.Group)
                || (parent instanceof instance.web.search.Input))) {
            if (!parent.visible()) {
                return false;
            }
        }
        return true;
    },
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
     * @param {instance.web.SearchView} parent parent in which the filters are contained
     */
    init: function (filters, parent) {
        // If all filters are group_by and we're not initializing a GroupbyGroup,
        // create a GroupbyGroup instead of the current FilterGroup
        if (!(this instanceof instance.web.search.GroupbyGroup) &&
              _(filters).all(function (f) {
                  if (!f.attrs.context) { return false; }
                  var c = instance.web.pyeval.eval('context', f.attrs.context);
                  return !_.isEmpty(c.group_by);})) {
            return new instance.web.search.GroupbyGroup(filters, parent);
        }
        this._super(parent);
        this.filters = filters;
        this.view.query.on('add remove change reset', this.proxy('search_change'));
    },
    start: function () {
        this.$el.on('click', 'li', this.proxy('toggle_filter'));
        return $.when(null);
    },
    /**
     * Handles change of the search query: any of the group's filter which is
     * in the search query should be visually checked in the drawer
     */
    search_change: function () {
        var self = this;
        var $filters = this.$('> li').removeClass('badge');
        var facet = this.view.query.find(_.bind(this.match_facet, this));
        if (!facet) { return; }
        facet.values.each(function (v) {
            var i = _(self.filters).indexOf(v.get('value'));
            if (i === -1) { return; }
            $filters.filter(function () {
                return Number($(this).data('index')) === i;
            }).addClass('badge');
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
        return _.extend(new instance.web.CompoundContext(), {
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
            .without('{}')
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
            .without('[]')
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
        this.toggle(this.filters[Number($(e.target).data('index'))]);
    },
    toggle: function (filter) {
        this.view.query.toggle(this.make_facet([this.make_value(filter)]));
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
    }
});
instance.web.search.GroupbyGroup = instance.web.search.FilterGroup.extend({
    icon: 'w',
    completion_label: _lt("Group by: %s"),
    init: function (filters, parent) {
        this._super(filters, parent);
        // Not flanders: facet unicity is handled through the
        // (category, field) pair of facet attributes. This is all well and
        // good for regular filter groups where a group matches a facet, but for
        // groupby we want a single facet. So cheat: add an attribute on the
        // view which proxies to the first GroupbyGroup, so it can be used
        // for every GroupbyGroup and still provides the various methods needed
        // by the search view. Use weirdo name to avoid risks of conflicts
        if (!this.view._s_groupby) {
            this.view._s_groupby = {
                help: "See GroupbyGroup#init",
                get_context: this.proxy('get_context'),
                get_domain: this.proxy('get_domain'),
                get_groupby: this.proxy('get_groupby')
            };
        }
    },
    match_facet: function (facet) {
        return facet.get('field') === this.view._s_groupby;
    },
    make_facet: function (values) {
        return {
            category: _t("GroupBy"),
            icon: this.icon,
            values: values,
            field: this.view._s_groupby
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

instance.web.search.Separator = instance.web.search.Input.extend({
    _in_drawer: false,

    complete: function () {
        return {is_separator: true};
    }
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
            return new instance.web.CompoundContext(context)
                .set_eval_context({self: self.value_from(facetValue)});
        });

        if (contexts.length === 1) { return contexts[0]; }

        return _.extend(new instance.web.CompoundContext(), {
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

        return _.extend(new instance.web.CompoundDomain(), {
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
instance.web.search.NumberField = instance.web.search.Field.extend(/** @lends instance.web.search.NumberField# */{
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
        var d;
        try {
            var t = (this.attrs && this.attrs.type === 'datetime') ? 'datetime' : 'date';
            var v = instance.web.parse_value(needle, {'widget': t});
            if (t === 'datetime'){
                d = instance.web.str_to_datetime(v);
            }
            else{
                d = instance.web.str_to_date(v);
            }
        } catch (e) {
            // pass
        }
        if (!d) { return $.when(null); }
        var date_string = instance.web.format_value(d, this.attrs);
        var label = _.str.sprintf(_.str.escapeHTML(
            _t("Search %(field)s at: %(value)s")), {
                field: '<em>' + _.escape(this.attrs.string) + '</em>',
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
    init: function (view_section, field, parent) {
        this._super(view_section, field, parent);
        this.model = new instance.web.Model(this.attrs.relation);
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
        var context = instance.web.pyeval.eval(
            'contexts', [this.view.dataset.get_context()]);
        return this.model.call('name_search', [], {
            name: needle,
            args: (typeof this.attrs.domain === 'string') ? [] : this.attrs.domain,
            limit: 8,
            context: context
        }).then(function (results) {
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
            assert(value.length <= 1,
                   _t("M2O search fields do not currently handle multiple default values"));
            // there are many cases of {search_default_$m2ofield: [id]}, need
            // to handle this as if it were a single value.
            value = value[0];
        }
        return this.model.call('name_get', [value]).then(function (names) {
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

instance.web.search.CustomFilters = instance.web.search.Input.extend({
    template: 'SearchView.Custom',
    _in_drawer: true,
    init: function () {
        this.is_ready = $.Deferred();
        this._super.apply(this,arguments);
    },
    start: function () {
        var self = this;
        this.model = new instance.web.Model('ir.filters');
        this.filters = {};
        this.$filters = {};
        this.view.query
            .on('remove', function (facet) {
                if (!facet.get('is_custom_filter')) {
                    return;
                }
                self.clear_selection();
            })
            .on('reset', this.proxy('clear_selection'));
        return this.model.call('get_filters', [this.view.model, this.get_action_id()])
            .then(this.proxy('set_filters'))
            .done(function () { self.is_ready.resolve(); })
            .fail(function () { self.is_ready.reject.apply(self.is_ready, arguments); });
    },
    get_action_id: function(){
        var action = instance.client.action_manager.inner_action;
        if (action) return action.id;
    },
    /**
     * Special implementation delaying defaults until CustomFilters is loaded
     */
    facet_for_defaults: function () {
        return this.is_ready;
    },
    /**
     * Generates a mapping key (in the filters and $filter mappings) for the
     * filter descriptor object provided (as returned by ``get_filters``).
     *
     * The mapping key is guaranteed to be unique for a given (user_id, name)
     * pair.
     *
     * @param {Object} filter
     * @param {String} filter.name
     * @param {Number|Pair<Number, String>} [filter.user_id]
     * @return {String} mapping key corresponding to the filter
     */
    key_for: function (filter) {
        var user_id = filter.user_id,
            action_id = filter.action_id;
        var uid = (user_id instanceof Array) ? user_id[0] : user_id;
        var act_id = (action_id instanceof Array) ? action_id[0] : action_id;
        return _.str.sprintf('(%s)(%s)%s', uid, act_id, filter.name);
    },
    /**
     * Generates a :js:class:`~instance.web.search.Facet` descriptor from a
     * filter descriptor
     *
     * @param {Object} filter
     * @param {String} filter.name
     * @param {Object} [filter.context]
     * @param {Array} [filter.domain]
     * @return {Object}
     */
    facet_for: function (filter) {
        return {
            category: _t("Custom Filter"),
            icon: 'M',
            field: {
                get_context: function () { return filter.context; },
                get_groupby: function () { return [filter.context]; },
                get_domain: function () { return filter.domain; }
            },
            _id: filter['id'],
            is_custom_filter: true,
            values: [{label: filter.name, value: null}]
        };
    },
    clear_selection: function () {
        this.$('span.badge').removeClass('badge');
    },
    append_filter: function (filter) {
        var self = this;
        var key = this.key_for(filter);
        var warning = _t("This filter is global and will be removed for everybody if you continue.");

        var $filter;
        if (key in this.$filters) {
            $filter = this.$filters[key];
        } else {
            var id = filter.id;
            this.filters[key] = filter;
            $filter = $('<li></li>')
                .appendTo(this.$('.oe_searchview_custom_list'))
                .toggleClass('oe_searchview_custom_default', filter.is_default)
                .append(this.$filters[key] = $('<span>').text(filter.name));

            this.$filters[key].addClass(filter.user_id ? 'oe_searchview_custom_private'
                                         : 'oe_searchview_custom_public')

            $('<a class="oe_searchview_custom_delete">x</a>')
                .click(function (e) {
                    e.stopPropagation();
                    if (!(filter.user_id || confirm(warning))) {
                        return;
                    }
                    self.model.call('unlink', [id]).done(function () {
                        $filter.remove();
                        delete self.$filters[key];
                        delete self.filters[key];
                        if (_.isEmpty(self.filters)) {
                            self.hide();
                        }
                    });
                })
                .appendTo($filter);
        }

        this.$filters[key].unbind('click').click(function () {
            self.toggle_filter(filter);
        });
        this.show();
    },
    toggle_filter: function (filter, preventSearch) {
        var current = this.view.query.find(function (facet) {
            return facet.get('_id') === filter.id;
        });
        if (current) {
            this.view.query.remove(current);
            this.$filters[this.key_for(filter)].removeClass('badge');
            return;
        }
        this.view.query.reset([this.facet_for(filter)], {
            preventSearch: preventSearch || false});
        this.$filters[this.key_for(filter)].addClass('badge');
    },
    set_filters: function (filters) {
        _(filters).map(_.bind(this.append_filter, this));
        if (!filters.length) {
            this.hide();
        }
    },
    hide: function () {
        this.$el.hide();
    },
    show: function () {
        this.$el.show();
    },
});

instance.web.search.SaveFilter = instance.web.search.Input.extend({
    template: 'SearchView.SaveFilter',
    _in_drawer: true,
    init: function (parent, custom_filters) {
        this._super(parent);
        this.custom_filters = custom_filters;
    },
    start: function () {
        var self = this;
        this.model = new instance.web.Model('ir.filters');
        this.$el.on('submit', 'form', this.proxy('save_current'));
        this.$el.on('click', 'input[type=checkbox]', function() {
            $(this).siblings('input[type=checkbox]').prop('checked', false);
        });
        this.$el.on('click', 'h4', function () {
            self.$el.toggleClass('oe_opened');
        });
    },
    save_current: function () {
        var self = this;
        var $name = this.$('input:first');
        var private_filter = !this.$('#oe_searchview_custom_public').prop('checked');
        var set_as_default = this.$('#oe_searchview_custom_default').prop('checked');
        if (_.isEmpty($name.val())){
            this.do_warn(_t("Error"), _t("Filter name is required."));
            return false;
        }
        var search = this.view.build_search_data();
        instance.web.pyeval.eval_domains_and_contexts({
            domains: search.domains,
            contexts: search.contexts,
            group_by_seq: search.groupbys || []
        }).done(function (results) {
            if (!_.isEmpty(results.group_by)) {
                results.context.group_by = results.group_by;
            }
            // Don't save user_context keys in the custom filter, otherwise end
            // up with e.g. wrong uid or lang stored *and used in subsequent
            // reqs*
            var ctx = results.context;
            _(_.keys(instance.session.user_context)).each(function (key) {
                delete ctx[key];
            });
            var filter = {
                name: $name.val(),
                user_id: private_filter ? instance.session.uid : false,
                model_id: self.view.model,
                context: results.context,
                domain: results.domain,
                is_default: set_as_default,
                action_id: self.custom_filters.get_action_id()
            };
            // FIXME: current context?
            return self.model.call('create_or_replace', [filter]).done(function (id) {
                filter.id = id;
                if (self.custom_filters) {
                    self.custom_filters.append_filter(filter);
                }
                self.$el
                    .removeClass('oe_opened')
                    .find('form')[0].reset();
            });
        });
        return false;
    },
});

instance.web.search.Filters = instance.web.search.Input.extend({
    template: 'SearchView.Filters',
    _in_drawer: true,
    start: function () {
        var self = this;
        var is_group = function (i) { return i instanceof instance.web.search.FilterGroup; };
        var visible_filters = _(this.drawer.controls).chain().reject(function (group) {
            return _(_(group.children).filter(is_group)).isEmpty()
                || group.modifiers.invisible;
        });

        var groups = visible_filters.map(function (group) {
                var filters = _(group.children).filter(is_group);
                return {
                    name: _.str.sprintf("<span class='oe_i'>%s</span> %s",
                            group.icon, group.name),
                    filters: filters,
                    length: _(filters).chain().map(function (i) {
                        return i.filters.length; }).sum().value()
                };
            }).value();

        var $dl = $('<dl class="dl-horizontal">').appendTo(this.$el);

        var rendered_lines = _.map(groups, function (group) {
            $('<dt>').html(group.name).appendTo($dl);
            var $dd = $('<dd>').appendTo($dl);
            return $.when.apply(null, _(group.filters).invoke('appendTo', $dd));
        });

        return $.when.apply(this, rendered_lines);
    },
});

instance.web.search.Advanced = instance.web.search.Input.extend({
    template: 'SearchView.advanced',
    _in_drawer: true,
    start: function () {
        var self = this;
        this.$el
            .on('keypress keydown keyup', function (e) { e.stopPropagation(); })
            .on('click', 'h4', function () {
                self.$el.toggleClass('oe_opened');
            }).on('click', 'button.oe_add_condition', function () {
                self.append_proposition();
            }).on('submit', 'form', function (e) {
                e.preventDefault();
                self.commit_search();
            });
        return $.when(
            this._super(),
            new instance.web.Model(this.view.model).call('fields_get', {
                    context: this.view.dataset.context
                }).done(function(data) {
                    self.fields = {
                        id: { string: 'ID', type: 'id', searchable: true }
                    };
                    _.each(data, function(field_def, field_name) {
                        if (field_def.selectable !== false && field_name != 'id') {
                            self.fields[field_name] = field_def;
                        }
                    });
        })).done(function () {
            self.append_proposition();
        });
    },
    append_proposition: function () {
        var self = this;
        return (new instance.web.search.ExtendedSearchProposition(this, this.fields))
            .appendTo(this.$('ul')).done(function () {
                self.$('button.oe_apply').prop('disabled', false);
            });
    },
    remove_proposition: function (prop) {
        // removing last proposition, disable apply button
        if (this.getChildren().length <= 1) {
            this.$('button.oe_apply').prop('disabled', true);
        }
        prop.destroy();
    },
    commit_search: function () {
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
        this.view.$el.removeClass('oe_searchview_open_drawer');
    }
});

instance.web.search.ExtendedSearchProposition = instance.web.Widget.extend(/** @lends instance.web.search.ExtendedSearchProposition# */{
    template: 'SearchView.extended_search.proposition',
    events: {
        'change .searchview_extended_prop_field': 'changed',
        'change .searchview_extended_prop_op': 'operator_changed',
        'click .searchview_extended_delete_prop': function (e) {
            e.stopPropagation();
            this.getParent().remove_proposition(this);
        }
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
        var nval = this.$(".searchview_extended_prop_field").val();
        if(this.attrs.selected === null || this.attrs.selected === undefined || nval != this.attrs.selected.name) {
            this.select_field(_.detect(this.fields, function(x) {return x.name == nval;}));
        }
    },
    operator_changed: function (e) {
        var $value = this.$('.searchview_extended_prop_value');
        switch ($(e.target).val()) {
        case '∃':
        case '∄':
            $value.hide();
            break;
        default:
            $value.show();
        }
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
            this.$('.searchview_extended_prop_op').html('');
        }
        this.attrs.selected = field;
        if(field === null || field === undefined) {
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
                .appendTo(self.$('.searchview_extended_prop_op'));
        });
        var $value_loc = this.$('.searchview_extended_prop_value').show().empty();
        this.value.appendTo($value_loc);

    },
    get_proposition: function() {
        if (this.attrs.selected === null || this.attrs.selected === undefined)
            return null;
        var field = this.attrs.selected;
        var op_select = this.$('.searchview_extended_prop_op')[0];
        var operator = op_select.options[op_select.selectedIndex];

        return {
            label: this.value.get_label(field, operator),
            value: this.value.get_domain(field, operator),
        };
    }
});

instance.web.search.ExtendedSearchProposition.Field = instance.web.Widget.extend({
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
        case '∃': return this.make_domain(field.name, '!=', false);
        case '∄': return this.make_domain(field.name, '=', false);
        default: return this.make_domain(
            field.name, operator.value, this.get_value());
        }
    },
    make_domain: function (field, operator, value) {
        return [field, operator, value];
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
        {value: "!=", text: _lt("is not equal to")},
        {value: "∃", text: _lt("is set")},
        {value: "∄", text: _lt("is not set")}
    ],
    get_value: function() {
        return this.$el.val();
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
        {value: "<=", text: _lt("less or equal than")},
        {value: "∃", text: _lt("is set")},
        {value: "∄", text: _lt("is not set")}
    ],
    /**
     * Date widgets live in view_form which is not yet loaded when this is
     * initialized -_-
     */
    widget: function () { return instance.web.DateTimeWidget; },
    get_value: function() {
        return this.datewidget.get_value();
    },
    toString: function () {
        return instance.web.format_value(this.get_value(), { type:"datetime" });
    },
    start: function() {
        var ready = this._super();
        this.datewidget = new (this.widget())(this);
        this.datewidget.appendTo(this.$el);
        return ready;
    }
});
instance.web.search.ExtendedSearchProposition.Date = instance.web.search.ExtendedSearchProposition.DateTime.extend({
    widget: function () { return instance.web.DateWidget; },
    toString: function () {
        return instance.web.format_value(this.get_value(), { type:"date" });
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
        {value: "<=", text: _lt("less or equal than")},
        {value: "∃", text: _lt("is set")},
        {value: "∄", text: _lt("is not set")}
    ],
    toString: function () {
        return this.$el.val();
    },
    get_value: function() {
        try {
            var val =this.$el.val();
            return instance.web.parse_value(val === "" ? 0 : val, {'widget': 'integer'});
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
        {value: "<=", text: _lt("less or equal than")},
        {value: "∃", text: _lt("is set")},
        {value: "∄", text: _lt("is not set")}
    ],
    toString: function () {
        return this.$el.val();
    },
    get_value: function() {
        try {
            var val =this.$el.val();
            return instance.web.parse_value(val === "" ? 0.0 : val, {'widget': 'float'});
        } catch (e) {
            return "";
        }
    }
});
instance.web.search.ExtendedSearchProposition.Selection = instance.web.search.ExtendedSearchProposition.Field.extend({
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
instance.web.search.ExtendedSearchProposition.Boolean = instance.web.search.ExtendedSearchProposition.Field.extend({
    template: 'SearchView.extended_search.proposition.empty',
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

instance.web.search.AutoComplete = instance.web.Widget.extend({
    template: "SearchView.autocomplete",

    // Parameters for autocomplete constructor:
    //
    // parent: this is used to detect keyboard events
    //
    // options.source: function ({term:query}, callback).  This function will be called to
    //      obtain the search results corresponding to the query string.  It is assumed that
    //      options.source will call callback with the results.
    // options.select: function (ev, {item: {facet:facet}}).  Autocomplete widget will call
    //      that function when a selection is made by the user
    // options.get_search_string: function ().  This function will be called by autocomplete
    //      to obtain the current search string.
    init: function (parent, options) {
        this._super(parent);
        this.$input = parent.$el;
        this.source = options.source;
        this.select = options.select;
        this.get_search_string = options.get_search_string;
        this.width = options.width || 400;

        this.current_result = null;

        this.searching = true;
        this.search_string = '';
        this.current_search = null;
    },
    start: function () {
        var self = this;
        this.$el.width(this.width);
        this.$input.on('keyup', function (ev) {
            if (ev.which === $.ui.keyCode.RIGHT) {
                self.searching = true;
                ev.preventDefault();
                return;
            }
            if (ev.which === $.ui.keyCode.ENTER) {
                if (self.search_string.length) {
                    self.select_item(ev);
                }
                return;
            }
            var search_string = self.get_search_string();
            if (self.search_string !== search_string) {
                if (search_string.length) {
                    self.search_string = search_string;
                    self.initiate_search(search_string);
                } else {
                    self.close();
                }
            }
        });
        this.$input.on('keypress', function (ev) {
            self.search_string = self.search_string + String.fromCharCode(ev.which);
            if (self.search_string.length) {
                self.searching = true;
                var search_string = self.search_string;
                self.initiate_search(search_string);
            } else {
                self.close();
            }
        });
        this.$input.on('keydown', function (ev) {
            switch (ev.which) {
                case $.ui.keyCode.ENTER:

                // TAB and direction keys are handled at KeyDown because KeyUp
                // is not guaranteed to fire.
                // See e.g. https://github.com/aef-/jquery.masterblaster/issues/13
                case $.ui.keyCode.TAB:
                    if (self.search_string.length) {
                        self.select_item(ev);
                    }
                    break;
                case $.ui.keyCode.DOWN:
                    self.move('down');
                    self.searching = false;
                    ev.preventDefault();
                    break;
                case $.ui.keyCode.UP:
                    self.move('up');
                    self.searching = false;
                    ev.preventDefault();
                    break;
                case $.ui.keyCode.RIGHT:
                    self.searching = false;
                    var current = self.current_result
                    if (current && current.expand && !current.expanded) {
                        self.expand();
                        self.searching = true;
                    }
                    ev.preventDefault();
                    break;
                case $.ui.keyCode.ESCAPE:
                    self.close();
                    self.searching = false;
                    break;
            }
        });
    },
    initiate_search: function (query) {
        if (query === this.search_string && query !== this.current_search) {
            this.search(query);
        }
    },
    search: function (query) {
        var self = this;
        this.current_search = query;
        this.source({term:query}, function (results) {
            if (results.length) {
                self.render_search_results(results);
                self.focus_element(self.$('li:first-child'));
            } else {
                self.close();
            }
        });
    },
    render_search_results: function (results) {
        var self = this;
        var $list = this.$('ul');
        $list.empty();
        var render_separator = false;
        results.forEach(function (result) {
            if (result.is_separator) {
                if (render_separator)
                    $list.append($('<li>').addClass('oe-separator'));
                render_separator = false;
            } else {
                var $item = self.make_list_item(result).appendTo($list);
                result.$el = $item;
                render_separator = true;
            }
        });
        this.show();
    },
    make_list_item: function (result) {
        var self = this;
        var $li = $('<li>')
            .hover(function (ev) {self.focus_element($li);})
            .mousedown(function (ev) {
                if (ev.button === 0) { // left button
                    self.select(ev, {item: {facet: result.facet}});
                    self.close();
                } else {
                    ev.preventDefault();
                }
            })
            .data('result', result);
        if (result.expand) {
            var $expand = $('<span class="oe-expand">').text('▶').appendTo($li);
            $expand.mousedown(function (ev) {
                ev.preventDefault();
                ev.stopPropagation();
                if (result.expanded)
                    self.fold();
                else
                    self.expand();
            });
            result.expanded = false;
        }
        if (result.indent) $li.addClass('oe-indent');
        $li.append($('<span>').html(result.label));
        return $li;
    },
    expand: function () {
        var self = this;
        this.current_result.expand(this.get_search_string()).then(function (results) {
            (results || [{label: '(no result)'}]).reverse().forEach(function (result) {
                result.indent = true;
                var $li = self.make_list_item(result);
                self.current_result.$el.after($li);
            });
            self.current_result.expanded = true;
            self.current_result.$el.find('span.oe-expand').html('▼');
        });
    },
    fold: function () {
        var $next = this.current_result.$el.next();
        while ($next.hasClass('oe-indent')) {
            $next.remove();
            $next = this.current_result.$el.next();
        }
        this.current_result.expanded = false;
        this.current_result.$el.find('span.oe-expand').html('▶');
    },
    focus_element: function ($li) {
        this.$('li').removeClass('oe-selection-focus');
        $li.addClass('oe-selection-focus');
        this.current_result = $li.data('result');
    },
    select_item: function (ev) {
        if (this.current_result.facet) {
            this.select(ev, {item: {facet: this.current_result.facet}});
            this.close();
        }
    },
    show: function () {
        this.$el.show();
    },
    close: function () {
        this.current_search = null;
        this.search_string = '';
        this.searching = true;
        this.$el.hide();
    },
    move: function (direction) {
        var $next;
        if (direction === 'down') {
            $next = this.$('li.oe-selection-focus').nextAll(':not(.oe-separator)').first();
            if (!$next.length) $next = this.$('li:first-child');
        } else {
            $next = this.$('li.oe-selection-focus').prevAll(':not(.oe-separator)').first();
            if (!$next.length) $next = this.$('li:not(.oe-separator)').last();
        }
        this.focus_element($next);
    },
    is_expandable: function () {
        return !!this.$('.oe-selection-focus .oe-expand').length;
    },
});

})();

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
