
(function() {

var instance = openerp;
openerp.web.search = {};

var QWeb = instance.web.qweb,
      _t =  instance.web._t,
     _lt = instance.web._lt;

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
        'click div.oe_searchview_search': function (e) {
            e.stopImmediatePropagation();
            this.do_search();
        },
        'click .oe_searchview_unfold_drawer': function (e) {
            e.stopImmediatePropagation();
            $(e.target).toggleClass('fa-caret-down fa-caret-up');
            localStorage.visible_search_menu = (localStorage.visible_search_menu !== 'true');
            this.toggle_buttons();
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
        this.query = undefined;   
        this.dataset = dataset;
        this.view_id = view_id;
        this.search_fields = [];
        this.filters = [];
        this.groupbys = [];
        this.visible_filters = (localStorage.visible_search_menu === 'true');
        this.input_subviews = []; // for user input in searchbar
        this.defaults = defaults || {};
        this.headless = this.options.hidden &&  _.isEmpty(this.defaults);
        this.$buttons = this.options.$buttons;

        this.filter_menu = undefined;
        this.groupby_menu = undefined;
        this.favorite_menu = undefined
    },    
    start: function() {
        if (this.headless) {
            this.$el.hide();
        }
        this.toggle_visibility(false);
        this.$facets_container = this.$('div.oe_searchview_facets');
        this.setup_global_completion();
        this.query = new my.SearchQuery()
                .on('add change reset remove', this.proxy('do_search'))
                .on('change', this.proxy('renderChangedFacets'))
                .on('add reset remove', this.proxy('renderFacets'));
        var load_view = instance.web.fields_view_get({
            model: this.dataset._model,
            view_id: this.view_id,
            view_type: 'search',
            context: this.dataset.get_context(),
        });
        this.$('.oe_searchview_unfold_drawer')
            .toggleClass('fa-caret-down', !this.visible_filters)
            .toggleClass('fa-caret-up', this.visible_filters);
        return this.alive($.when(this._super(), load_view.then(this.view_loaded.bind(this))));
    },
    view_loaded: function (r) {
        var self = this;
        this.fields_view_get = r;
        this.prepare_search_inputs();
        if (this.$buttons) {

            var fields_def = new instance.web.Model(this.dataset.model).call('fields_get', {
                    context: this.dataset.context
                });

            this.groupby_menu = new my.GroupByMenu(this, this.groupbys, fields_def);
            this.filter_menu = new my.FilterMenu(this, this.filters, fields_def);
            this.favorite_menu = new my.FavoriteMenu(this, this.query, this.dataset.model);

            this.filter_menu.appendTo(this.$buttons);
            this.groupby_menu.appendTo(this.$buttons);
            var custom_filters_ready = this.favorite_menu.appendTo(this.$buttons);
        }
        return $.when(custom_filters_ready).then(this.proxy('set_default_filters'));
    },
    // it should parse the arch field of the view, instantiate the corresponding 
    // filters/fields, and put them in the correct variables:
    // * this.search_fields is a list of all the fields,
    // * this.filters: groups of filters
    // * this.group_by: group_bys
    prepare_search_inputs: function () {
        var self = this,
            arch = this.fields_view_get.arch;

        var filters = [].concat.apply([], _.map(arch.children, function (item) {
            return item.tag !== 'group' ? eval_item(item) : item.children.map(eval_item);
        }));
        function eval_item (item) {
            var category = 'filters';
            if (item.attrs.context) {
                try {
                    var context = instance.web.pyeval.eval('context', item.attrs.context);
                    if (context.group_by) {
                        category = 'group_by';
                    }                    
                } catch (e) {}
            }
            return {
                item: item,
                category: category,
            }
        }
        var current_group = [],
            current_category = 'filters',
            categories = {filters: this.filters, group_by: this.groupbys};

        _.each(filters.concat({category:'filters', item: 'separator'}), function (filter) {
            if (filter.item.tag === 'filter' && filter.category === current_category) {
                return current_group.push(new my.Filter(filter.item, self));
            }
            if (current_group.length) {
                var group = new my.FilterGroup(current_group, self);
                categories[current_category].push(group);
                current_group = [];
            }
            if (filter.item.tag === 'field') {
                var attrs = filter.item.attrs,
                    field = self.fields_view_get.fields[attrs.name],
                    Obj = my.fields.get_any([attrs.widget, field.type]);
                if (Obj) {
                    self.search_fields.push(new (Obj) (filter.item, field, self));
                }
            }
            if (filter.item.tag === 'filter') {
                current_group.push(new my.Filter(filter.item, self));
            }
            current_category = filter.category;
        });
    },
    set_default_filters: function () {
        var self = this,
            default_custom_filter = this.$buttons && this.favorite_menu.get_default_filter();
        if (default_custom_filter) {
            return this.favorite_menu.toggle_filter(default_custom_filter, true);
        }
        if (!_.isEmpty(this.defaults)) {
            var inputs = this.search_fields.concat(this.filters, this.groupbys),
                defaults = _.invoke(inputs, 'facet_for_defaults', this.defaults);
            return $.when.apply(null, defaults).then(function () {
                self.query.reset(_(arguments).compact(), {preventSearch: true});
            });
        } 
        this.query.reset([], {preventSearch: true});
        return $.when();
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
        this.trigger('search_data', search.domains, search.contexts, search.groupbys);
    },
    /**
     * Extract search data from the view's facets.
     *
     * Result is an object with 3 (own) properties:
     *
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
        var domains = [], contexts = [], groupbys = [];

        this.query.each(function (facet) {
            var field = facet.get('field');
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
        });
        return {
            domains: domains,
            contexts: contexts,
            groupbys: groupbys,
        };
    }, 
    toggle_visibility: function (is_visible) {
        this.$el.toggle(!this.headless && is_visible);
        this.$buttons && this.$buttons.toggle(!this.headless && is_visible && this.visible_filters);
    },
    toggle_buttons: function (is_visible) {
        this.visible_filters = is_visible || !this.visible_filters;
        this.$buttons && this.$buttons.toggle(this.visible_filters);
    },
    /**
     * Sets up search view's view-wide auto-completion widget
     */
    setup_global_completion: function () {
        var self = this;
        this.autocomplete = new my.AutoComplete(this, {
            source: this.proxy('complete_global_search'),
            select: this.proxy('select_completion'),
            delay: 0,
            get_search_string: function () {
                return self.$('div.oe_searchview_input').text();
            },
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
        var inputs = this.search_fields.concat(this.filters, this.groupbys);
        $.when.apply(null, _(inputs).chain()
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
     * @param {openerp.web.search.SearchQuery | undefined} Undefined if event is change
     * @param {openerp.web.search.Facet} 
     * @param {Object} [options]
     */
    renderFacets: function (collection, model, options) {
        var self = this;
        var started = [];
        _.invoke(this.input_subviews, 'destroy');
        this.input_subviews = [];

        var i = new my.InputView(this);
        started.push(i.appendTo(this.$facets_container));
        this.input_subviews.push(i);
        this.query.each(function (facet) {
            var f = new my.FacetView(this, facet);
            started.push(f.appendTo(self.$facets_container));
            self.input_subviews.push(f);

            var i = new my.InputView(this);
            started.push(i.appendTo(self.$facets_container));
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
    childFocused: function () {
        this.$el.addClass('active');
    },
    childBlurred: function () {
        this.$el.val('').removeClass('active').trigger('blur');
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

instance.web.search.Input = instance.web.Widget.extend( /** @lends instance.web.search.Input# */{
    /**
     * @constructs instance.web.search.Input
     * @extends instance.web.Widget
     *
     * @param parent
     */
    init: function (parent) {
        this._super(parent);
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
        return !this.attrs.modifiers.invisible;
    },
});
instance.web.search.FilterGroup = instance.web.search.Input.extend(/** @lends instance.web.search.FilterGroup# */{
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
        this.searchview = parent;
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
        var $filters = this.$el.removeClass('selected');
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
    }
});
instance.web.search.GroupbyGroup = instance.web.search.FilterGroup.extend({
    icon: 'fa-bars',
    completion_label: _lt("Group by: %s"),
    init: function (filters, parent) {
        this._super(filters, parent);
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
            category: _t("GroupBy"),
            icon: this.icon,
            values: values,
            field: this.searchview._s_groupby
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
        category: field.attrs.string,
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
                    label: _.escape(sel[1]),
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
        var d = Date.parse(needle);
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
        var context = instance.web.pyeval.eval(
            'contexts', [this.searchview.dataset.get_context()]);
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
            c['default_' + this.attrs.name] = values.at(0).get('value');
            return c;
        }
        return this._super(facet);
    }
});

instance.web.search.FilterMenu = instance.web.Widget.extend({
    template: 'SearchView.FilterMenu',
    events: {
        'click .oe-add-filter': function () {
            this.toggle_custom_filter_menu();
        },
        'click li': function (event) {event.stopImmediatePropagation();},
        'hidden.bs.dropdown': function () {
            this.toggle_custom_filter_menu(false);
        },
        'click .oe-add-condition': 'append_proposition',
        'click .oe-apply-filter': 'commit_search',
    },
    init: function (parent, filters, fields_def) {
        var self = this;
        this._super(parent);
        this.filters = filters || [];
        this.searchview = parent;
        this.propositions = [];
        this.fields_def = fields_def.then(function (data) {
            var fields = {
                id: { string: 'ID', type: 'id', searchable: true }
            };
            _.each(data, function(field_def, field_name) {
                if (field_def.selectable !== false && field_name !== 'id') {
                    fields[field_name] = field_def;
                }
            });
            return fields;
        });
    },
    start: function () {
        var self = this;
        this.$menu = this.$('.filters-menu');
        this.$add_filter = this.$('.oe-add-filter');
        this.$apply_filter = this.$('.oe-apply-filter');
        this.$add_filter_menu = this.$('.oe-add-filter-menu');
        _.each(this.filters, function (group) {
            if (group.is_visible()) {
                group.insertBefore(self.$add_filter);
                $('<li class="divider">').insertBefore(self.$add_filter);
            }
        });
        this.append_proposition().then(function (prop) {
            prop.$el.hide();
        });
    },
    toggle_custom_filter_menu: function (is_open) {
        this.$add_filter
            .toggleClass('closed-menu', !is_open)
            .toggleClass('open-menu', is_open);
        this.$add_filter_menu.toggle(is_open);
        if (this.$add_filter.hasClass('closed-menu') && (!this.propositions.length)) {
            this.append_proposition();
        }
        this.$('.oe-filter-condition').toggle(is_open);
    },
    append_proposition: function () {
        var self = this;
        return this.fields_def.then(function (fields) {
            var prop = new instance.web.search.ExtendedSearchProposition(self, fields);
            self.propositions.push(prop);
            prop.insertBefore(self.$add_filter_menu);
            self.$apply_filter.prop('disabled', false);
            return prop;
        });
    },
    remove_proposition: function (prop) {
        this.propositions = _.without(this.propositions, prop);
        if (!this.propositions.length) {
            this.$apply_filter.prop('disabled', true);
        }
        prop.destroy();
    },
    commit_search: function () {
        var filters = _.invoke(this.propositions, 'get_filter'),
            filters_widgets = _.map(filters, function (filter) {
                return new my.Filter(filter, this);
            }),
            filter_group = new my.FilterGroup(filters_widgets, this.searchview),
            facets = filters_widgets.map(function (filter) {
                return filter_group.make_facet([filter_group.make_value(filter)]);
            });
        filter_group.insertBefore(this.$add_filter);
        $('<li class="divider">').insertBefore(this.$add_filter);
        this.searchview.query.add(facets, {silent: true});
        this.searchview.query.trigger('reset');

        _.invoke(this.propositions, 'destroy');
        this.propositions = [];
        this.append_proposition();
        this.toggle_custom_filter_menu(false);
    },
});

instance.web.search.GroupByMenu = instance.web.Widget.extend({
    template: 'SearchView.GroupByMenu',
    events: {
        'click li': function (event) {
            event.stopImmediatePropagation();
        },
        'hidden.bs.dropdown': function () {
            this.toggle_add_menu(false);
        },
        'click .add-custom-group a': function () {
            this.toggle_add_menu();
        },
    },
    init: function (parent, groups, fields_def) {
        this._super(parent);
        this.groups = groups || [];
        this.groupable_fields = {};
        this.searchview = parent;
        this.fields_def = fields_def.then(this.proxy('get_groupable_fields'));
    },
    start: function () {
        var self = this;
        this.$menu = this.$('.group-by-menu');
        var divider = this.$menu.find('.divider');
        _.invoke(this.groups, 'insertBefore', divider);
        if (this.groups.length) {
            divider.show();
        }
        this.$add_group = this.$menu.find('.add-custom-group');
        this.fields_def.then(function () {
            self.$menu.append(QWeb.render('GroupByMenuSelector', self));
            self.$add_group_menu = self.$('.oe-add-group');
            self.$group_selector = self.$('.oe-group-selector');
            self.$('.oe-select-group').click(function (event) {
                self.toggle_add_menu(false);
                var field = self.$group_selector.find(':selected').data('name');
                self.add_groupby_to_menu(field);
            });            
        });
    },
    get_groupable_fields: function (fields) {
        var self = this,
            groupable_types = ['many2one', 'char', 'boolean', 'selection', 'date', 'datetime'];

        _.each(fields, function (field, name) {
            if (field.store && _.contains(groupable_types, field.type)) {
                self.groupable_fields[name] = field;
            }
        });
    },
    toggle_add_menu: function (is_open) {
        this.$add_group
            .toggleClass('closed-menu', !is_open)
            .toggleClass('open-menu', is_open);
        this.$add_group_menu.toggle(is_open);
        if (this.$add_group.hasClass('open-menu')) {
            this.$group_selector.focus();
        }
    },
    add_groupby_to_menu: function (field_name) {
        var filter = new my.Filter({attrs:{
            context:"{'group_by':'" + field_name + "''}",
            name: this.groupable_fields[field_name].string,
        }}, this.searchview);
        var group = new my.FilterGroup([filter], this.searchview),
            divider = this.$('.divider').show();
        group.insertBefore(divider);
        group.toggle(filter);
    },
});

instance.web.search.FavoriteMenu = instance.web.Widget.extend({
    template: 'SearchView.FavoriteMenu',
    events: {
        'click li': function (event) {
            event.stopImmediatePropagation();
        },
        'click .oe-save-search a': function () {
            this.toggle_save_menu();
        },
        'click .oe-save-name button': 'save_favorite',
        'hidden.bs.dropdown': function () {
            this.close_menus();
        },
    },
    init: function (parent, query, target_model) {
        this._super.apply(this,arguments);
        this.searchview = parent;
        this.query = query;
        this.target_model = target_model;
        this.model = new instance.web.Model('ir.filters');
        this.filters = {};
        this.$filters = {};
        var action = instance.client.action_manager.inner_action;
        this.action_id = action && action.id;
    },
    start: function () {
        var self = this;
        this.$save_search = this.$('.oe-save-search');
        this.$save_name = this.$('.oe-save-name');
        this.$inputs = this.$save_name.find('input');
        this.$divider = this.$('.divider');
        this.$inputs.eq(0).val(this.searchview.getParent().title);
        var $shared_filter = this.$inputs.eq(1),
            $default_filter = this.$inputs.eq(2);
        $shared_filter.click(function () {$default_filter.prop('checked', false)});
        $default_filter.click(function () {$shared_filter.prop('checked', false)});

        this.query
            .on('remove', function (facet) {
                if (facet.get('is_custom_filter')) {
                    self.clear_selection();
                }
            })
            .on('reset', this.proxy('clear_selection'));
        return this.model.call('get_filters', [this.target_model, this.action_id])
            .done(this.proxy('prepare_dropdown_menu'));
    },
    prepare_dropdown_menu: function (filters) {
        filters.map(this.append_filter.bind(this));
    },
    toggle_save_menu: function (is_open) {
        this.$save_search
            .toggleClass('closed-menu', !is_open)
            .toggleClass('open-menu', is_open);
        this.$save_name.toggle(is_open);
        if (this.$save_search.hasClass('open-menu')) {
            this.$save_name.find('input').first().focus();
        }
    },
    close_menus: function () {
        this.toggle_save_menu(false);
    },
    save_favorite: function () {
        var self = this,
            filter_name = this.$inputs[0].value,
            default_filter = this.$inputs[1].checked,
            shared_filter = this.$inputs[2].checked;
        if (!filter_name.length){
            this.do_warn(_t("Error"), _t("Filter name is required."));
            this.$inputs.first().focus();
            return;
        }
        var search = this.searchview.build_search_data(),
            results = instance.web.pyeval.sync_eval_domains_and_contexts({
                domains: search.domains,
                contexts: search.contexts,
                group_by_seq: search.groupbys || [],
            });
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
            name: filter_name,
            user_id: shared_filter ? false : instance.session.uid,
            model_id: this.searchview.dataset.model,
            context: results.context,
            domain: results.domain,
            is_default: default_filter,
            action_id: this.action_id,
        };
        return this.model.call('create_or_replace', [filter]).done(function (id) {
            filter.id = id;
            self.toggle_save_menu(false);
            self.$save_name.find('input').val('').prop('checked', false);
            self.append_filter(filter);
            self.toggle_filter(filter, true);
        });
    },
    get_default_filter: function () {
        var personal_filter = _.find(this.filters, function (filter) {
            return filter.user_id && filter.is_default;
        });
        if (personal_filter) {
            return personal_filter;
        }
        return _.find(this.filters, function (filter) {
            return !filter.user_id && filter.is_default;
        });
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
            action_id = filter.action_id,
            uid = (user_id instanceof Array) ? user_id[0] : user_id,
            act_id = (action_id instanceof Array) ? action_id[0] : action_id;
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
            icon: 'fa-star',
            field: {
                get_context: function () { return filter.context; },
                get_groupby: function () { return [filter.context]; },
                get_domain: function () { return filter.domain; }
            },
            _id: filter.id,
            is_custom_filter: true,
            values: [{label: filter.name, value: null}]
        };
    },
    clear_selection: function () {
        this.$('li.selected').removeClass('selected');
    },
    append_filter: function (filter) {
        var self = this,
            key = this.key_for(filter),
            $filter,
            warning = _t("This filter is global and will be removed for everybody if you continue.");

        this.$divider.show();
        if (key in this.$filters) {
            $filter = this.$filters[key];
        } else {
            this.filters[key] = filter;
            $filter = $('<li></li>')
                .insertBefore(this.$divider)
                .toggleClass('oe_searchview_custom_default', filter.is_default)
                .append($('<a>').text(filter.name));

            this.$filters[key] = $filter;
            this.$filters[key].addClass(filter.user_id ? 'oe_searchview_custom_private'
                                         : 'oe_searchview_custom_public')
            $('<span>')
                .addClass('fa fa-trash-o')
                .click(function (event) {
                    event.stopImmediatePropagation(); 
                    self.remove_filter(filter, $filter, key);
                })
                .appendTo($filter);
        }
        this.$filters[key].unbind('click').click(function () {
            self.toggle_filter(filter);
        });
    },
    toggle_filter: function (filter, preventSearch) {
        var current = this.query.find(function (facet) {
            return facet.get('_id') === filter.id;
        });
        if (current) {
            this.query.remove(current);
            this.$filters[this.key_for(filter)].removeClass('selected');
            return;
        }
        this.query.reset([this.facet_for(filter)], {
            preventSearch: preventSearch || false});
        this.$filters[this.key_for(filter)].addClass('selected');
    },
    remove_filter: function (filter, $filter, key) {
        var self = this;
        var warning = _t("This filter is global and will be removed for everybody if you continue.");
        if (!(filter.user_id || confirm(warning))) {
            return;
        }
        this.model.call('unlink', [filter.id]).done(function () {
            $filter.remove();
            delete self.$filters[key];
            delete self.filters[key];
            if (_.isEmpty(self.filters)) {
                self.$('li.divider').remove();
            }
        });        
    },
});

instance.web.search.ExtendedSearchProposition = instance.web.Widget.extend(/** @lends instance.web.search.ExtendedSearchProposition# */{
    template: 'SearchView.extended_search.proposition',
    events: {
        'change .searchview_extended_prop_field': 'changed',
        'change .searchview_extended_prop_op': 'operator_changed',
        'click .searchview_extended_delete_prop': function (e) {
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
    get_filter: function () {
        if (this.attrs.selected === null || this.attrs.selected === undefined)
            return null;
        var field = this.attrs.selected,
            op_select = this.$('.searchview_extended_prop_op')[0],
            operator = op_select.options[op_select.selectedIndex];

        return {
            attrs: {
                domain: [this.value.get_domain(field, operator)],
                string: this.value.get_label(field, operator),
            },
            children: [],
            tag: 'filter',
        };
    },
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
    // options.delay: delay in millisecond before calling source.  Useful if you don't want
    //      to make too many rpc calls
    // options.select: function (ev, {item: {facet:facet}}).  Autocomplete widget will call
    //      that function when a selection is made by the user
    // options.get_search_string: function ().  This function will be called by autocomplete
    //      to obtain the current search string.
    init: function (parent, options) {
        this._super(parent);
        this.$input = parent.$el;
        this.source = options.source;
        this.delay = options.delay;
        this.select = options.select,
        this.get_search_string = options.get_search_string;

        this.current_result = null;

        this.searching = true;
        this.search_string = null;
        this.current_search = null;
    },
    start: function () {
        var self = this;
        this.$input.on('keyup', function (ev) {
            if (ev.which === $.ui.keyCode.RIGHT) {
                self.searching = true;
                ev.preventDefault();
                return;
            }
            if (!self.searching) {
                self.searching = true;
                return;
            }
            self.search_string = self.get_search_string();
            if (self.search_string.length) {
                var search_string = self.search_string;
                setTimeout(function () { self.initiate_search(search_string);}, self.delay);
            } else {
                self.close();
            }
        });
        this.$input.on('keydown', function (ev) {
            switch (ev.which) {
                case $.ui.keyCode.TAB:
                case $.ui.keyCode.ENTER:
                    if (self.current_result && self.get_search_string().length) {
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
        this.search_string = null;
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
