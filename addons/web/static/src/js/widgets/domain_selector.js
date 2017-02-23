odoo.define("web.DomainSelector", function (require) {
"use strict";

var core = require("web.core");
var datepicker = require("web.datepicker");
var Domain = require("web.Domain");
var field_utils = require ("web.field_utils");
var ModelFieldSelector = require("web.ModelFieldSelector");
var Widget = require("web.Widget");

var _t = core._t;
var _lt = core._lt;

// "child_of", "parent_of", "like", "not like", "=like", "=ilike"
// are only used if user entered them manually or if got from demo data
var operator_mapping = {
    "=": _lt("is equal to"),
    "!=": _lt("is not equal to"),
    ">": _lt("greater than"),
    "<": _lt("less than"),
    ">=": _lt("greater than or equal to"),
    "<=": _lt("less than or equal to"),
    "ilike": _lt("contains"),
    "not ilike": _lt("not contains"),
    "in": _lt("in"),
    "not in": _lt("not in"),

    "child_of": _lt("child of"),
    "parent_of": _lt("parent of"),
    "like": "like",
    "not like": "not like",
    "=like": "=like",
    "=ilike": "=ilike",

    // custom
    "set": _lt("is set"),
    "not set": _lt("is not set"),
};

/// The DomainNode Widget is an abstraction for widgets which can represent and allow
/// edition of a domain (part).
var DomainNode = Widget.extend({
    events: {
        /// If click on the node add or delete button, notify the parent and let it handle the addition/removal
        "click .o_domain_delete_node_button": function (e) {
            e.preventDefault();
            e.stopPropagation();
            this.trigger_up("delete_node_clicked", {child: this});
        },
        "click .o_domain_add_node_button": function (e) {
            e.preventDefault();
            e.stopPropagation();
            this.trigger_up("add_node_clicked", {newBranch: !!$(e.currentTarget).data("branch"), child: this});
        },
    },
    /// A DomainNode needs a model and domain to work. It can also receives a set of options
    /// @param model - a string with the model name
    /// @param domain - an array of the prefix representation of the domain (or a string which represents it)
    /// @param options - an object with possible values:
    ///                    - readonly, a boolean to indicate if the widget is readonly or not (default to true)
    ///                    - operators, a list of available operators (default to null, which indicates all of supported ones)
    ///                    - debugMode, a boolean which is true if the widget should be in debug mode (default to false)
    ///                    - @see ModelFieldSelector for other options
    init: function (parent, model, domain, options) {
        this._super.apply(this, arguments);

        this.model = model;
        this.options = _.extend({
            readonly: true,
            operators: null,
            debugMode: false,
        }, options || {});

        this.readonly = this.options.readonly;
        this.debug = this.options.debugMode;
    },
    /// The getDomain method is an abstract method which should returns the prefix domain
    /// the widget is currently representing (an array).
    getDomain: function () {},
});
/// The DomainTree is a DomainNode which can handle subdomains (a domain which is composed
/// of multiple parts). It thus will be composed of other DomainTree instances and/or leaf parts
/// of a domain (@see DomainLeaf).
var DomainTree = DomainNode.extend({
    template: "DomainTree",
    events: _.extend({}, DomainNode.prototype.events, {
        "click .o_domain_tree_operator_selector > ul > li > a": function (e) {
            e.preventDefault();
            e.stopPropagation();
            this.changeOperator($(e.target).data("operator"));
        },
    }),
    custom_events: {
        /// If a domain child sends a request to add a child or remove one, call the appropriate methods.
        /// Propagates the event until success.
        "delete_node_clicked": function (e) {
            e.stopped = this.removeChild(e.data.child);
        },
        "add_node_clicked": function (e) {
            var domain = [["id", "=", 1]];
            if (e.data.newBranch) {
                domain = [this.operator === "&" ? "|" : "&"].concat(domain).concat(domain);
            }
            e.stopped = this.addChild(domain, e.data.child);
        },
    },
    /// @see DomainNode.init
    /// The initialization of a DomainTree creates a "children" array attribute which will contain the
    /// the DomainNode children. It also deduces the operator from the domain (default to "&").
    /// @see DomainTree._addFlattenedChildren
    init: function (parent, model, domainStr, options) {
        this._super.apply(this, arguments);
        this._initialize(Domain.prototype.stringToArray(domainStr));
    },
    /// @see DomainTree.init
    _initialize: function (domain) {
        this.operator = domain[0];
        this.children = [];

        // Add flattened children by search the appropriate number of children in the rest
        // of the domain (after the operator)
        var nbLeafsToFind = 1;
        for (var i = 1 ; i < domain.length ; i++) {
            if (_.contains(["&", "|"], domain[i])) {
                nbLeafsToFind++;
            } else if (domain[i] !== "!") {
                nbLeafsToFind--;
            }

            if (!nbLeafsToFind) {
                var partLeft = domain.slice(1, i+1);
                var partRight = domain.slice(i+1);
                if (partLeft.length) {
                    this._addFlattenedChildren(partLeft);
                }
                if (partRight.length) {
                    this._addFlattenedChildren(partRight);
                }
                break;
            }
        }

        // Mark "!" tree children so that they do not allow to add other children around them
        if (this.operator === "!") {
            this.children[0].noControlPanel = true;
        }
    },
    start: function () {
        this._postRender();
        return $.when(this._super.apply(this, arguments), this._renderChildrenTo(this.$childrenContainer));
    },
    _postRender: function () {
        this.$childrenContainer = this.$("> .o_domain_node_children_container");
    },
    _renderChildrenTo: function ($to) {
        var $div = $("<div/>");
        return $.when.apply($, _.map(this.children, (function (child) {
            return child.appendTo($div);
        }).bind(this))).then((function () {
            _.each(this.children, function (child) {
                child.$el.appendTo($to); // Forced to do it this way so that the children are not misordered
            });
        }).bind(this));
    },
    getDomain: function () {
        var childDomains = [];
        var nbChildren = 0;
        _.each(this.children, function (child) {
            var childDomain = child.getDomain();
            if (childDomain.length) {
                nbChildren++;
                childDomains = childDomains.concat(child.getDomain());
            }
        });
        var nbChildRequired = this.operator === "!" ? 1 : 2;
        var operators = _.times(nbChildren - nbChildRequired + 1, _.constant(this.operator));
        return operators.concat(childDomains);
    },
    changeOperator: function (operator) {
        this.operator = operator;
        this.trigger_up("domain_changed", {child: this});
    },
    /// The addChild method adds a domain part to the widget.
    /// @param domain - an array of the prefix-like domain to build and add to the widget
    /// @param afterNode - the node after which the new domain part must be added (at the end if not given)
    /// @trigger_up domain_changed if the child is added
    /// @return true if the part was added, false otherwise (the afterNode was not found)
    addChild: function (domain, afterNode) {
        var i = afterNode ? _.indexOf(this.children, afterNode) : this.children.length;
        if (i < 0) return false;

        this.children.splice(i+1, 0, instantiateNode(this, this.model, domain, this.options));
        this.trigger_up("domain_changed", {child: this});
        return true;
    },
    /// The removeChild method removes a given child from the widget.
    /// @param oldChild - the child instance to remove
    /// @trigger_up domain_changed if the child is removed
    /// @return true if the child was removed, false otherwise (the widget does not own the child)
    removeChild: function (oldChild) {
        var i = _.indexOf(this.children, oldChild);
        if (i < 0) return false;

        this.children[i].destroy();
        this.children.splice(i, 1);
        this.trigger_up("domain_changed", {child: this});
        return true;
    },
    /// The private _addFlattenedChildren method adds a child which represents the given
    /// domain. If the child has children and that the child main domain operator is the
    /// same as the current widget one, the 2-children prefix hierarchy is then simplified
    /// by making the child children the widget own children.
    /// @param domain - the domain of the child to add and simplify
    _addFlattenedChildren: function (domain) {
        var node = instantiateNode(this, this.model, domain, this.options);
        if (node === null) {
            return;
        }
        if (!node.children || node.operator !== this.operator) {
            this.children.push(node);
            return;
        }
        _.each(node.children, (function (child) {
            child.setParent(this);
            this.children.push(child);
        }).bind(this));
        node.destroy();
    },
    /// This method is ugly but achieves the right behavior without flickering.
    /// It will be refactored alongside the new views/widget API.
    _redraw: function (domain) {
        var oldChildren = this.children.slice();
        this._initialize(domain || this.getDomain());
        return this._renderChildrenTo($("<div/>")).then((function () {
            this.renderElement();
            this._postRender();
            _.each(this.children, (function (child) { child.$el.appendTo(this.$childrenContainer); }).bind(this));
            _.each(oldChildren, function (child) { child.destroy(); });
        }).bind(this));
    },
});
/// The DomainSelector widget can be used to build prefix char domain. It is the DomainTree
/// specialization to use to have a fully working widget.
///
/// Known limitations:
///     - Some operators like "child_of", "parent_of", "like", "not like", "=like", "=ilike"
///       will come only if you use them from demo data or debug input.
///     - Some kind of domain can not be build right now e.g ("country_id", "in", [1,2,3,4])
///       but you can insert from debug input.
var DomainSelector = DomainTree.extend({
    template: "DomainSelector",
    events: _.extend({}, DomainTree.prototype.events, {
        "click .o_domain_add_first_node_button": function (e) {
            this.addChild([["id", "=", 1]]);
        },
        /// When the debug input changes, the string prefix domain is read. If it is syntax-valid
        /// the widget is re-rendered and notifies the parents. If not, a warning is shown to the
        /// user and the input is ignored.
        "change .o_domain_debug_input": function (e) {
            var currentDomain;
            try {
                currentDomain = Domain.prototype.stringToArray($(e.currentTarget).val());
            } catch (err) {
                this.do_warn(_t("Syntax error"), _t("The domain you entered is not properly formed"));
                return;
            }
            this._redraw(currentDomain).then((function () {
                this.trigger_up("domain_changed", {child: this, alreadyRedrawn: true});
            }).bind(this));
        },
    }),
    custom_events: _.extend({}, DomainTree.prototype.custom_events, {
        /// If a subdomain notifies that it underwent some modifications, the DomainSelector
        /// catches the message and performs a full re-rendering.
        "domain_changed": function (e) {
            e.stopped = false;
            if (!e.data.alreadyRedrawn) {
                this._redraw();
            }
        },
    }),
    _initialize: function (domain) {
        // Check if the domain starts with implicit "&" operators and make them
        // explicit. As the DomainSelector is a specialization of a DomainTree,
        // it is waiting for a tree and not a leaf. So [] and [A] will be made
        // explicit with ["&"], ["&", A] so that tree parsing is made correctly.
        // Note: the domain is considered to be a valid one
        if (domain.length <= 1) {
            return this._super(["&"].concat(domain));
        }
        var expected = 1;
        _.each(domain, function (item) {
            if (item === "&" || item === "|") {
                expected++;
            } else if (item !== "!") {
                expected--;
            }
        });
        if (expected < 0) {
            domain =  _.times(Math.abs(expected), _.constant("&")).concat(domain);
        }
        return this._super(domain);
    },
    _postRender: function () {
        this._super.apply(this, arguments);

        // Display technical domain if in debug mode
        this.$debugInput = this.$(".o_domain_debug_input");
        if (this.$debugInput.length) {
            this.$debugInput.val(Domain.prototype.arrayToString(this.getDomain()));
        }
    },
});
/// The DomainLeaf widget is a DomainNode which handles a domain which cannot be split in
/// another subdomains, i.e. composed of a field chain, an operator and a value.
var DomainLeaf = DomainNode.extend({
    template: "DomainLeaf",
    events: _.extend({}, DomainNode.prototype.events, {
        "change .o_domain_leaf_operator_select": function (e) {
            this.onOperatorChange($(e.currentTarget).val());
        },
        "change .o_domain_leaf_value_input": function (e) {
            if (e.currentTarget !== e.target) return;
            this.onValueChange($(e.currentTarget).val());
        },

        // Handle the tags widget part (TODO should be an independant widget)
        "click .o_domain_leaf_value_add_tag_button": "on_add_tag",
        "keyup .o_domain_leaf_value_tags input": "on_add_tag",
        "click .o_domain_leaf_value_remove_tag_button": "on_remove_tag",
    }),
    custom_events: {
        "field_chain_changed": function (e) {
            this.onChainChange(e.data.chain);
        },
    },
    /// @see DomainNode.init
    init: function (parent, model, domainStr, options) {
        this._super.apply(this, arguments);

        var currentDomain = Domain.prototype.stringToArray(domainStr);
        this.chain = currentDomain[0][0];
        this.operator = currentDomain[0][1];
        this.value = currentDomain[0][2];

        this.operator_mapping = operator_mapping;
    },
    willStart: function () {
        var defs = [this._super.apply(this, arguments)];

        if (!this.readonly) {
            // In edit mode, instantiate a field selector. This is done here in willStart and prepared by
            // appending it to a dummy element because the DomainLeaf rendering need some information which
            // cannot be computed before the ModelFieldSelector is fully rendered (TODO).
            this.fieldSelector = new ModelFieldSelector(this, this.model, this.chain, this.options);
            defs.push(this.fieldSelector.appendTo($("<div/>")).then((function () {
                var wDefs = [];

                // Set list of operators according to field type
                this.operators = this._getOperatorsFromType(this.fieldSelector.selectedField.type);
                if (_.contains(["child_of", "parent_of", "like", "not like", "=like", "=ilike"], this.operator)) {
                    // In case user entered manually or from demo data
                    this.operators[this.operator] = operator_mapping[this.operator];
                } else if (!this.operators[this.operator]) {
                    this.operators[this.operator] = "?"; // In case the domain uses an unsupported operator for the field type
                }

                // Set list of values according to field type
                this.selectionChoices = null;
                if (this.fieldSelector.selectedField.type === "boolean") {
                    this.selectionChoices = [["1", "set (true)"], ["0", "not set (false)"]];
                } else if (this.fieldSelector.selectedField.type === "selection") {
                    this.selectionChoices = this.fieldSelector.selectedField.selection;
                }

                // Adapt display value and operator for rendering
                this.displayValue = this.value;
                try {
                    var f = this.fieldSelector.selectedField;
                    if (!f.relation) { // TODO in this case, the value should be m2o input, etc...
                        this.displayValue = field_utils.format_field(this.value, this.fieldSelector.selectedField);
                    }
                } catch (err) {/**/}
                this.displayOperator = this.operator;
                if (this.fieldSelector.selectedField.type === "boolean") {
                    this.displayValue = this.value ? "1" : "0";
                } else if ((this.operator === "!=" || this.operator === "=") && this.value === false) {
                    this.displayOperator = this.operator === "!=" ? "set" : "not set";
                }

                // TODO the value could be a m2o input, etc...
                if (_.contains(["date", "datetime"], this.fieldSelector.selectedField.type)) {
                    this.valueWidget = new (this.fieldSelector.selectedField.type === "datetime" ? datepicker.DateTimeWidget : datepicker.DateWidget)(this);
                    wDefs.push(this.valueWidget.appendTo("<div/>").then((function () {
                        this.valueWidget.$el.addClass("o_domain_leaf_value_input");
                        this.valueWidget.set_value(this.value);
                        this.valueWidget.on("datetime_changed", this, function () {
                            this.onValueChange(this.valueWidget.get_value());
                        });
                    }).bind(this)));
                }

                return $.when.apply($, wDefs);
            }).bind(this)));
        }

        return $.when.apply($, defs);
    },
    start: function () {
        if (!this.readonly) { // In edit mode ...
            this.fieldSelector.$el.prependTo(this.$("> .o_domain_leaf_edition")); // ... place the field selector
            if (this.valueWidget) { // ... and place the value widget if any
                this.$(".o_domain_leaf_value_input").replaceWith(this.valueWidget.$el);
            }
        }
        return this._super.apply(this, arguments);
    },
    getDomain: function () {
        return [[this.chain, this.operator, this.value]];
    },
    /// The onChainChange method handles a field chain change in the domain. In that case, the operator
    /// should be adapted to a valid one for the new field and the value should also be adapted to the
    /// new field and/or operator.
    /// @param chain - the new field chain (string)
    /// @param silent - true if the method call should not trigger_up a domain_changed event
    /// @trigger_up domain_changed event to ask for a re-rendering
    onChainChange: function (chain, silent) {
        this.chain = chain;

        var operators = this._getOperatorsFromType(this.fieldSelector.selectedField.type);
        if (operators[this.operator] === undefined) {
            this.onOperatorChange("=", true);
        }

        this.onValueChange(this.value, true);

        if (!silent) this.trigger_up("domain_changed", {child: this});
    },
    /// The onOperatorChange method handles an operator change in the domain. In that case, the value
    /// should be adapted to a valid one for the new operator.
    /// @param operator - the new operator
    /// @param silent - true if the method call should not trigger_up a domain_changed event
    /// @trigger_up domain_changed event to ask for a re-rendering
    onOperatorChange: function (operator, silent) {
        this.operator = operator;

        if (_.contains(["set", "not set"], this.operator)) {
            this.operator = this.operator === "not set" ? "=" : "!=";
            this.value = false;
        } else if (_.contains(["in", "not in"], this.operator)) {
            this.value = _.isArray(this.value) ? this.value : this.value ? ("" + this.value).split(",") : [];
        } else {
            if (_.isArray(this.value)) {
                this.value = this.value.join(",");
            }
            this.onValueChange(this.value, true);
        }

        if (!silent) this.trigger_up("domain_changed", {child: this});
    },
    /// The onValueChange method handles a formatted value change in the domain. In that case, the value
    /// should be adapted to a valid technical one.
    /// @param value - the new formatted value
    /// @param silent - true if the method call should not trigger_up a domain_changed event
    /// @trigger_up domain_changed event to ask for a re-rendering
    onValueChange: function (value, silent) {
        var couldNotParse = false;
        try {
            this.value = field_utils.parse_field(value, this.fieldSelector.selectedField);
        } catch (err) {
            this.value = value;
            couldNotParse = true;
        }

        if (this.fieldSelector.selectedField.type === "boolean") {
            if (!_.isBoolean(this.value)) { // Convert boolean-like value to boolean
                this.value = !!parseFloat(this.value);
            }
        } else if (this.fieldSelector.selectedField.type === "selection") {
            if (!_.some(this.fieldSelector.selectedField.selection, (function (option) { return option[0] === this.value; }).bind(this))) {
                this.value = this.fieldSelector.selectedField.selection[0][0];
            }
        } else if (_.contains(["date", "datetime"], this.fieldSelector.selectedField.type)) {
            if (couldNotParse || _.isBoolean(this.value)) {
                this.value = field_utils.parse_field(field_utils.format_field(Date.now(), this.fieldSelector.selectedField), this.fieldSelector.selectedField);
            }
        } else {
            if (_.isBoolean(this.value)) { // Never display "true" or "false" strings from boolean value
                this.value = "";
            }
        }

        if (!silent) this.trigger_up("domain_changed", {child: this});
    },
    /// The private _getOperatorsFromType returns the mapping of "technical operator" to "display operator value"
    /// of the operators which are available for the given field type.
    _getOperatorsFromType: function (type) {
        var operators = {};

        switch (type) {
            case "boolean":
                operators = {
                    "=": _t("is"),
                    "!=": _t("is not"),
                };
                break;

            case "char":
            case "text":
            case "html":
                operators = _.pick(operator_mapping, "=", "!=", "ilike", "not ilike", "set", "not set", "in", "not in");
                break;

            case "many2many":
            case "one2many":
            case "many2one":
                operators = _.pick(operator_mapping, "=", "!=", "ilike", "not ilike", "set", "not set");
                break;

            case "integer":
            case "float":
            case "monetary":
                operators = _.pick(operator_mapping, "=", "!=", ">", "<", ">=", "<=", "ilike", "not ilike", "set", "not set");
                break;

            case "selection":
                operators = _.pick(operator_mapping, "=", "!=", "set", "not set");
                break;

            case "date":
            case "datetime":
                operators = _.pick(operator_mapping, "=", "!=", ">", "<", ">=", "<=", "set", "not set");
                break;

            default:
                operators = _.extend({}, operator_mapping);
                break;
        }

        if (this.options.operators) {
            operators = _.pick.apply(_, [operators].concat(this.options.operators));
        }

        return operators;
    },

    on_add_tag: function (e) {
        if (e.type === "keyup" && e.which !== $.ui.keyCode.ENTER) return;
        if (!_.contains(["not in", "in"], this.operator)) return;

        var values = _.isArray(this.value) ? this.value.slice() : [];

        var $input = this.$(".o_domain_leaf_value_tags input");
        var val = $input.val().trim();
        if (val && values.indexOf(val) < 0) {
            values.push(val);
            _.defer(this.onValueChange.bind(this, values));
            $input.focus();
        }
    },
    on_remove_tag: function (e) {
        var values = _.isArray(this.value) ? this.value.slice() : [];
        var val = this.$(e.currentTarget).data("value");

        var index = values.indexOf(val);
        if (index >= 0) {
            values.splice(index, 1);
            _.defer(this.onValueChange.bind(this, values));
        }
    },
});

/// The instantiateNode function instantiates a DomainTree if the given domain contains
/// several parts and a DomainLeaf if it only contains one part. Returns null otherwise.
function instantiateNode(parent, model, domain, options) {
    if (domain.length > 1) {
        return new DomainTree(parent, model, domain, options);
    } else if (domain.length === 1) {
        return new DomainLeaf(parent, model, domain, options);
    }
    return null;
}

return DomainSelector;
});
