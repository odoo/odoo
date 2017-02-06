odoo.define("web.ModelFieldSelector", function (require) {
"use strict";

var core = require("web.core");
var Model = require("web.DataModel");
var Widget = require("web.Widget");

/// The ModelFieldSelector widget can be used to select a particular field chain from a given model.
var ModelFieldSelector = Widget.extend({
    template: "FieldSelector",
    events: {
        // Handle popover opening and closing
        "focusin": function () {
            clearTimeout(this._hidePopoverTimeout);
            this.showPopover();
        },
        "focusout": function () {
            this._hidePopoverTimeout = _.defer(this.hidePopover.bind(this));
        },
        "click .o_field_selector_close": "hidePopover",

        // Handle popover field navigation
        "click .o_field_selector_prev_page": "goToPrevPage",
        "click .o_field_selector_next_page": function (e) {
            e.stopPropagation();
            this.goToNextPage(this._getLastPageField($(e.currentTarget).data("name")));
        },
        "click li.o_field_selector_select_button": function (e) {
            this.selectField(this._getLastPageField($(e.currentTarget).data("name")));
        },

        // Handle a direct change in the debug input
        "change input": function() {
            this.setChain(this.$input.val());
            this.validate(true);
            this._prefill().then(this.displayPage.bind(this, ""));
            this.trigger_up("field_chain_changed", {chain: this.chain});
        },

        // Handle keyboard and mouse navigation to build the field chain
        "mouseover li.o_field_selector_item": function (e) {
            this.$("li.o_field_selector_item").removeClass("active");
            $(e.currentTarget).addClass("active");
        },
        "keydown": function (e) {
            if (!this.$popover.is(":visible")) return;
            var inputHasFocus = this.$input.is(":focus");

            switch (e.which) {
                case $.ui.keyCode.UP:
                case $.ui.keyCode.DOWN:
                    e.preventDefault();
                    var $active = this.$("li.o_field_selector_item.active");
                    var $to = $active[e.which === $.ui.keyCode.DOWN ? "next" : "prev"](".o_field_selector_item");
                    if ($to.length) {
                        $active.removeClass("active");
                        $to.addClass("active");
                        this.$popover.focus();

                        var $page = $to.closest(".o_field_selector_page");
                        var full_height = $page.height();
                        var el_position = $to.position().top;
                        var el_height = $to.outerHeight();
                        var current_scroll = $page.scrollTop();
                        if (el_position < 0) {
                            $page.scrollTop(current_scroll - el_height);
                        } else if (full_height < el_position + el_height) {
                            $page.scrollTop(current_scroll + el_height);
                        }
                    }
                    break;
                case $.ui.keyCode.RIGHT:
                    if (inputHasFocus) break;
                    e.preventDefault();
                    var name = this.$("li.o_field_selector_item.active").data("name");
                    if (name) {
                        var field = this._getLastPageField(name);
                        if (field.relation) {
                            this.goToNextPage(field);
                        }
                    }
                    break;
                case $.ui.keyCode.LEFT:
                    if (inputHasFocus) break;
                    e.preventDefault();
                    this.goToPrevPage();
                    break;
                case $.ui.keyCode.ESCAPE:
                    e.stopPropagation();
                    this.hidePopover();
                    break;
                case $.ui.keyCode.ENTER:
                    if (inputHasFocus) break;
                    e.preventDefault();
                    this.selectField(this._getLastPageField(this.$("li.o_field_selector_item.active").data("name")));
                    break;
            }
        },
    },
    /// The ModelFieldSelector requires a model and a initial field chain to work with.
    /// @param model - a string with the model name (e.g. "res.partner")
    /// @param chain - a string with the initial field chain (e.g. "company_id.name")
    /// @param options - an object with several options:
    ///                     - filters: an object which contains a series of filters to use
    ///                     - debugMode: a boolean which is true if the widget is in debug mode
    init: function (parent, model, chain, options) {
        this._super.apply(this, arguments);

        this.model = model;
        this.chain = chain;
        this.options = _.extend({
            filters: {},
            debugMode: false,
        }, options || {});

        this.pages = [];
        this.selectedField = false;
        this.isSelected = true;
        this.dirty = false;

        this.debug = this.options.debugMode;
    },
    willStart: function () {
        return $.when(
            this._super.apply(this, arguments),
            this._prefill()
        );
    },
    start: function () {
        this.$input = this.$("input");
        this.$popover = this.$(".o_field_selector_popover");
        this.displayPage();

        return this._super.apply(this, arguments);
    },
    /// The setChain method saves a new field chain string and displays it in the DOM input element.
    /// @param chain - the new field chain string
    setChain: function (chain) {
        this.chain = chain;
        this.$input.val(this.chain);
    },
    /// The addChainNode method adds a field name to the current field chain.
    /// @param fieldName - the new field name to add at the end of the current field chain
    addChainNode: function (fieldName) {
        this.dirty = true;
        if (this.isSelected) {
            this.removeChainNode();
            this.isSelected = false;
        }
        if (!this.valid) {
            this.setChain("");
            this.validate(true);
        }
        this.setChain((this.chain ? (this.chain + ".") : "") + fieldName);
    },
    /// The removeChainNode method removes the last field name at the end of the current field chain.
    removeChainNode: function () {
        this.dirty = true;
        this.setChain(this.chain.substring(0, this.chain.lastIndexOf(".")));
    },
    /// The validate method toggles the valid status of the widget and display the error message if it
    /// is not valid.
    /// @param valid - a boolean which is true if the widget is valid
    validate: function (valid) {
        this.$(".o_field_selector_warning").toggleClass("hidden", valid);
        this.valid = valid;
    },
    /// The showPopover method shows the popover to select the field chain. It prepares the popover pages
    /// before actually showing it. (if already open, does nothing)
    showPopover: function () {
        if (this._isOpen) return;
        this._isOpen = true;
        this._prefill().then((function () {
            this.displayPage();
            this.$popover.removeClass("hidden");
        }).bind(this));
    },
    /// The hidePopover method closes the popover and mark the field as selected. If the field chain changed,
    /// it notifies its parents. (if not open, does nothing)
    hidePopover: function () {
        if (!this._isOpen) return;
        this._isOpen = false;
        this.$popover.addClass("hidden");
        this.isSelected = true;
        if (this.dirty) {
            this.trigger_up("field_chain_changed", {chain: this.chain});
            this.dirty = false;
        }
    },
    /// The private _prefill method prepares the popover by filling its pages according to the current field chain.
    /// @return a deferred which is resolved once the last page is shown
    _prefill: function () {
        this.pages = [];
        return this._pushPageData(this.model).then((function() {
            return (this.chain ? processChain.call(this, this.chain.split(".").reverse()) : $.when());
        }).bind(this));

        function processChain(chain) {
            var field = this._getLastPageField(chain.pop());
            if (field && field.relation && chain.length > 0) { // Fetch next chain node if any and possible
                return this._pushPageData(field.relation).then(processChain.bind(this, chain));
            } else if (field && chain.length === 0) { // Last node fetched, save it
                this.selectedField = field;
                this.validate(true);
            } else { // Wrong node chain
                this.validate(false);
            }
            return $.when();
        }
    },
    /// The private _pushPageData method gets the field of a particular model and adds them for the new
    /// last popover page.
    /// @param model - the model name whose fields have to be fetched
    /// @return a deferred which is resolved once the fields have been added
    _pushPageData: function (model) {
        return fieldsCache.getFields(model, this.options.filters).then((function (fields) {
            this.pages.push(fields);
        }).bind(this));
    },
    /// The displayPage method shows the last page content of the popover. It also adapts the title according
    /// to the previous page.
    /// @param animation - an optional animation class to add to the page
    displayPage: function (animation) {
        this.$(".o_field_selector_prev_page").toggleClass("hidden", this.pages.length === 1);

        var page = _.last(this.pages);
        var title = "";
        if (this.pages.length > 1) {
            var chainParts = this.chain.split(".");
            var prevField = _.findWhere(this.pages[this.pages.length - 2], {
                name: this.isSelected ? chainParts[chainParts.length - 2] : _.last(chainParts),
            });
            if (prevField) title = prevField.string;
        }
        this.$(".o_field_selector_popover_header .o_field_selector_title").text(title);
        this.$(".o_field_selector_page").replaceWith(core.qweb.render("FieldSelector.page", {lines: page, animation: animation, debug: this.debug}));
    },
    /// The goToPrevPage method removes the last page, adapts the field chain and displays the new last page.
    goToPrevPage: function () {
        if (this.pages.length <= 1) return;
        this.pages.pop();
        this.removeChainNode();
        this.selectedField = this._getLastPageField(_.last(this.chain.split(".")));
        this.displayPage("o_animate_slide_left");
    },
    /// The goToNextPage method adds a new page to the popover following the given field relation and adapts
    /// the chain node according to this given field.
    /// @param field - the field to add to the chain node
    goToNextPage: function (field) {
        this.addChainNode(field.name);
        this.selectedField = field;
        this._pushPageData(field.relation).then(this.displayPage.bind(this, "o_animate_slide_right"));
    },
    /// The selectField method selects the given field and adapts the chain node according to it. It also closes
    /// the popover and thus notifies the parents about the change.
    /// @param field - the field to select
    selectField: function (field) {
        this.addChainNode(field.name);
        this.selectedField = field;
        this.hidePopover();
    },
    /// The private _getLastPageField search a field in the last page by its name.
    /// @return the field data (an object) found in the last popover page thanks to its name
    _getLastPageField: function (name) {
        return _.findWhere(_.last(this.pages), {
            name: name,
        });
    },
});

/// Field Selector Cache
///
/// * Stores fields per model used in field selector
/// * Apply filters on the fly
var fieldsCache = {
    cache: {},
    cacheDefs: {},
    getFields: function (model, filters) {
        return (this.cacheDefs[model] ? this.cacheDefs[model] : this.updateCache(model)).then((function () {
            return this.filter(model, filters);
        }).bind(this));
    },
    updateCache: function (model) {
        this.cacheDefs[model] = new Model(model).call("fields_get", [
            false,
            ["store", "searchable", "type", "string", "relation", "selection", "related"],
        ]).then((function (fields) {
            var field_data = [];
            _.each(_.sortBy(_.keys(fields), function (f) { return fields[f].string; }), function (key) {
                fields[key]["name"] = key;
                field_data.push(fields[key]);
            });
            this.cache[model] = field_data;
        }).bind(this));
        return this.cacheDefs[model];
    },
    filter: function (model, filters) {
        filters = _.defaults(filters || {}, {searchable: true});
        return _.filter(this.cache[model], function (f) {
            return !filters.searchable || f.searchable;
        });
    },
};

return ModelFieldSelector;
});
