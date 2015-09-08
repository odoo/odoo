odoo.define('web.SearchView', function (require) {
"use strict";

var AutoComplete = require('web.AutoComplete');
var core = require('web.core');
var FavoriteMenu = require('web.FavoriteMenu');
var FilterMenu = require('web.FilterMenu');
var GroupByMenu = require('web.GroupByMenu');
var Model = require('web.DataModel');
var pyeval = require('web.pyeval');
var search_inputs = require('web.search_inputs');
var utils = require('web.utils');
var Widget = require('web.Widget');

var Backbone = window.Backbone;

var FacetValue = Backbone.Model.extend({});

var FacetValues = Backbone.Collection.extend({
    model: FacetValue
});

var Facet = Backbone.Model.extend({
    initialize: function (attrs) {
        var values = attrs.values;
        delete attrs.values;

        Backbone.Model.prototype.initialize.apply(this, arguments);

        this.values = new FacetValues(values || []);
        this.values.on('add remove change reset', function (_, options) {
            this.trigger('change', this, options);
        }, this);
    },
    get: function (key) {
        if (key !== 'values') {
            return Backbone.Model.prototype.get.call(this, key);
        }
        return this.values.toJSON();
    },
    set: function (key, value) {
        if (key !== 'values') {
            return Backbone.Model.prototype.set.call(this, key, value);
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

var SearchQuery = Backbone.Collection.extend({
    model: Facet,
    initialize: function () {
        Backbone.Collection.prototype.initialize.apply(
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
                return facet.get('category') === model.get('category') &&
                       facet.get('field') === model.get('field');
            });
            if (previous) {
                previous.values.add(model.get('values'), _.omit(options, 'at', 'merge'));
                return;
            }
            Backbone.Collection.prototype.add.call(this, model, options);
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

var InputView = Widget.extend({
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
        utils.assert(range.startContainer === root,
               "selection should be in the input view");
        utils.assert(range.endContainer === root,
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
                if (preceding && (preceding instanceof FacetView)) {
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

var FacetView = Widget.extend({
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
                return new FacetValueView(self, value).appendTo($e);
            }));
        });
    },
    model_changed: function () {
        this.$el.text(this.$el.text() + '*');
    }
});

var FacetValueView = Widget.extend({
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

var SearchView = Widget.extend(/** @lends instance.web.SearchView# */{
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
            disable_filters: false,
            disable_groupby: false,
            disable_favorites: false,
            disable_custom_filters: false,
        });
        this._super(parent);
        this.query = undefined;
        this.dataset = dataset;
        this.view_id = view_id;
        this.title = options.action && options.action.name;
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
        this.favorite_menu = undefined;
        this.action_id = this.options && this.options.action && this.options.action.id;
    },    
    start: function() {
        if (this.headless) {
            this.do_hide();
        }
        this.toggle_visibility(false);
        this.$facets_container = this.$('div.oe_searchview_facets');
        this.setup_global_completion();
        this.query = new SearchQuery()
                .on('add change reset remove', this.proxy('do_search'))
                .on('change', this.proxy('renderChangedFacets'))
                .on('add reset remove', this.proxy('renderFacets'));
        var load_view = this.dataset._model.fields_view_get({
            view_id: this.view_id,
            view_type: 'search',
            context: this.dataset.get_context(),
        });
        this.$('.oe_searchview_unfold_drawer')
            .toggleClass('fa-caret-down', !this.visible_filters)
            .toggleClass('fa-caret-up', this.visible_filters);
        return this.alive($.when(this._super(), this.alive(load_view).then(this.view_loaded.bind(this))));
    },
    get_title: function() {
        return this.title;
    },
    view_loaded: function (r) {
        var menu_defs = [];
        this.fields_view_get = r;
        this.view_id = this.view_id || r.view_id;
        this.prepare_search_inputs();
        if (this.$buttons) {
            var fields_def = new Model(this.dataset.model).call('fields_get', {
                    context: this.dataset.get_context()
                });

            if (!this.options.disable_filters) {
                this.filter_menu = new FilterMenu(this, this.filters, fields_def);
                menu_defs.push(this.filter_menu.appendTo(this.$buttons));
            }
            if (!this.options.disable_groupby) {
                this.groupby_menu = new GroupByMenu(this, this.groupbys, fields_def);
                menu_defs.push(this.groupby_menu.appendTo(this.$buttons));
            }
            if (!this.options.disable_favorites) {
                this.favorite_menu = new FavoriteMenu(this, this.query, this.dataset.model, this.action_id);
                menu_defs.push(this.favorite_menu.appendTo(this.$buttons));
            }
        }
        return $.when.apply($, menu_defs).then(this.proxy('set_default_filters'));
    },
    set_default_filters: function () {
        var self = this,
            default_custom_filter = this.$buttons && this.favorite_menu.get_default_filter();
        if (!self.options.disable_custom_filters && default_custom_filter) {
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
        this.do_toggle(!this.headless && is_visible);
        if (this.$buttons) {
            this.$buttons.toggle(!this.headless && is_visible && this.visible_filters);
        }
        if (!this.headless && is_visible) {
            this.$('div.oe_searchview_input').last().focus();
        }
    },
    toggle_buttons: function (is_visible) {
        this.visible_filters = is_visible || !this.visible_filters;
        if (this.$buttons)  {
            this.$buttons.toggle(this.visible_filters);
        }
    },
    /**
     * Sets up search view's view-wide auto-completion widget
     */
    setup_global_completion: function () {
        var self = this;
        this.autocomplete = new AutoComplete(this, {
            source: this.proxy('complete_global_search'),
            select: this.proxy('select_completion'),
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

        var i = new InputView(this);
        started.push(i.appendTo(this.$facets_container));
        this.input_subviews.push(i);
        this.query.each(function (facet) {
            var f = new FacetView(this, facet);
            started.push(f.appendTo(self.$facets_container));
            self.input_subviews.push(f);

            var i = new InputView(this);
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
                    var context = pyeval.eval('context', item.attrs.context);
                    if (context.group_by) {
                        category = 'group_by';
                    }
                } catch (e) {}
            }
            return {
                item: item,
                category: category,
            };
        }
        var current_group = [],
            current_category = 'filters',
            categories = {filters: this.filters, group_by: this.groupbys};

        _.each(filters.concat({category:'filters', item: 'separator'}), function (filter) {
            if (filter.item.tag === 'filter' && filter.category === current_category) {
                return current_group.push(new search_inputs.Filter(filter.item, self));
            }
            if (current_group.length) {
                var group = new search_inputs.FilterGroup(current_group, self);
                categories[current_category].push(group);
                current_group = [];
            }
            if (filter.item.tag === 'field') {
                var attrs = filter.item.attrs;
                var field = self.fields_view_get.fields[attrs.name];

                // M2O combined with selection widget is pointless and broken in search views,
                // but has been used in the past for unsupported hacks -> ignore it
                if (field.type === "many2one" && attrs.widget === "selection") {
                    attrs.widget = undefined;
                }

                var Obj = core.search_widgets_registry.get_any([attrs.widget, field.type]);
                if (Obj) {
                    self.search_fields.push(new (Obj) (filter.item, field, self));
                }
            }
            if (filter.item.tag === 'filter') {
                current_group.push(new search_inputs.Filter(filter.item, self));
            }
            current_category = filter.category;
        });
    },
});

_.extend(SearchView, {
    SearchQuery: SearchQuery,
    Facet: Facet,
});

return SearchView;

});

odoo.define('web.AutoComplete', function (require) {
"use strict";

var Widget = require('web.Widget');

return Widget.extend({
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

        this.current_result = null;

        this.searching = true;
        this.search_string = '';
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
                    var current = self.current_result;
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
            .hover(function () {self.focus_element($li);})
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
        var current_result = this.current_result;
        current_result.expand(this.get_search_string()).then(function (results) {
            (results || [{label: '(no result)'}]).reverse().forEach(function (result) {
                result.indent = true;
                var $li = self.make_list_item(result);
                current_result.$el.after($li);
            });
            current_result.expanded = true;
            current_result.$el.find('span.oe-expand').html('▼');
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
});
