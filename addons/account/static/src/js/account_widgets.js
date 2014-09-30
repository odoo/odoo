/*global _:false */
/*global openerp:false */

openerp.account = function (instance) {
    'use strict';

    openerp.account.quickadd(instance);
    var _t = instance.web._t,
        _lt = instance.web._lt;
    var QWeb = instance.web.qweb;
    
    instance.web.account = instance.web.account || {};

    /*

    ABOUT
    
    In this closure, you'll find two abstract widgets : one that represent a single reconciliation (abstractReconciliationLine)
    and one that serves as container and parent for the former (abstractReconciliation), displaying title, progress, etc.
    
    Those widgets are implemented for the bank statement reconciliation and the manual reconciliation.
    
    "Implementation classes" must declare a this.children_widget = instance.web.account.implementationOfAbstractReconciliationLine
    property so abstractReconciliation can instanciate new reconciliations.
    
    They may specify a template_prefix property (ex : methods in the abstract widget that renders templates will try
    template_prefix_some_template before to try some_template)

    When a method's body in an abstract widget is left empty, it means it should be defined by implementation classes
    

    TODO

    Reconciliation widgets' instanciation performances can be improved by generating the "createForm" once in the parent
    then cloning it for each new child.
    
    */

    instance.web.account.abstractReconciliation = instance.web.Widget.extend({
        className: 'oe_reconciliation',

        events: {},
    
        init: function(parent, context) {
            this._super(parent);
            this.max_reconciliations_displayed = 10;
    
            // Only for statistical purposes
            this.lines_reconciled_with_ctrl_enter = 0;
            this.time_widget_loaded = Date.now();
    
            // Stuff used by the children reconciliationLine
            this.crash_manager = new instance.web.CrashManager();
            this.formatCurrencies; // Method that formats the currency ; loaded from the server
            this.model_res_users = new instance.web.Model("res.users");
            this.model_tax = new instance.web.Model("account.tax");
            this.max_move_lines_displayed = 5;
            this.animation_speed = 100; // "Blocking" animations
            this.aestetic_animation_speed = 300; // eye candy
            this.map_tax_id_amount = {};
            // We'll need to get the code of an account selected in a many2one field (which returns the id)
            this.map_account_id_code = {};
            // NB : for presets to work correctly, a field id must be the same string as a preset field
            this.presets = {};
            // Description of the fields to initialize in the "create new line" form
            this.create_form_fields = {
                account_id: {
                    id: "account_id",
                    index: 0, // position in the form
                    corresponding_property: "account_id", // a account.move field name
                    label: _t("Account"),
                    required: true,
                    tabindex: 10,
                    constructor: instance.web.form.FieldMany2One,
                    field_properties: {
                        relation: "account.account",
                        string: _t("Account"),
                        type: "many2one",
                        domain: [['type','not in',['view', 'closed', 'consolidation']]],
                    },
                },
                label: {
                    id: "label",
                    index: 5,
                    corresponding_property: "label",
                    label: _t("Label"),
                    required: true,
                    tabindex: 15,
                    constructor: instance.web.form.FieldChar,
                    field_properties: {
                        string: _t("Label"),
                        type: "char",
                    },
                },
                tax_id: {
                    id: "tax_id",
                    index: 10,
                    corresponding_property: "tax_id",
                    label: _t("Tax"),
                    required: false,
                    tabindex: 20,
                    constructor: instance.web.form.FieldMany2One,
                    field_properties: {
                        relation: "account.tax",
                        string: _t("Tax"),
                        type: "many2one",
                        domain: [['type_tax_use','in',['purchase', 'all']], ['parent_id', '=', false]],
                    },
                },
                amount: {
                    id: "amount",
                    index: 15,
                    corresponding_property: "amount",
                    label: _t("Amount"),
                    required: true,
                    tabindex: 25,
                    constructor: instance.web.form.FieldFloat,
                    field_properties: {
                        string: _t("Amount"),
                        type: "float",
                    },
                },
                analytic_account_id: {
                    id: "analytic_account_id",
                    index: 20,
                    corresponding_property: "analytic_account_id",
                    label: _t("Analytic Acc."),
                    required: false,
                    tabindex: 30,
                    group:"analytic.group_analytic_accounting",
                    constructor: instance.web.form.FieldMany2One,
                    field_properties: {
                        relation: "account.analytic.account",
                        string: _t("Analytic Acc."),
                        type: "many2one",
                    },
                },
            };
        },
    
        start: function() {
            var self = this;
            return $.when(this._super()).then(function(){
                var deferred_promises = [];

                // Create a dict account id -> account code for display facilities
                deferred_promises.push(new instance.web.Model("account.account")
                    .query(['id', 'code'])
                    .all().then(function(data) {
                        _.each(data, function(o) { self.map_account_id_code[o.id] = o.code });
                    })
                );

                // Create a dict tax id -> amount
                deferred_promises.push(new instance.web.Model("account.tax")
                    .query(['id', 'amount'])
                    .all().then(function(data) {
                        _.each(data, function(o) { self.map_tax_id_amount[o.id] = o.amount });
                    })
                );

                // Get operation templates
                deferred_promises.push(new instance.web.Model("account.operation.template")
                    .query(['id','name',
                        'account_id','journal_id','label','amount_type','amount','tax_id','analytic_account_id',
                        'has_second_line',
                        'second_account_id','second_journal_id','second_label','second_amount_type','second_amount','second_tax_id','second_analytic_account_id'])
                    .all().then(function (data) {
                        _(data).each(function(datum){
                            var preset = {
                                id: datum.id,
                                name: datum.name,
                                lines: [{
                                    account_id: datum.account_id,
                                    journal_id: datum.journal_id,
                                    label: datum.label,
                                    amount_type: datum.amount_type,
                                    amount: datum.amount,
                                    tax_id: datum.tax_id,
                                    analytic_account_id: datum.analytic_account_id
                                }]
                            };
                            if (datum.has_second_line) {
                                preset.lines.push({
                                    account_id: datum.second_account_id,
                                    journal_id: datum.second_journal_id,
                                    label: datum.second_label,
                                    amount_type: datum.second_amount_type,
                                    amount: datum.second_amount,
                                    tax_id: datum.second_tax_id,
                                    analytic_account_id: datum.second_analytic_account_id
                                });
                            }
                            self.presets[datum.id] = preset;
                        });
                    })
                );

                // Get the function to format currencies
                deferred_promises.push(new instance.web.Model("res.currency")
                    .call("get_format_currencies_js_function")
                    .then(function(data) {
                        self.formatCurrencies = new Function("amount, currency_id", data);
                    })
                );
                
                // Bind keyboard events
                instance.web.bus.on("keypress", "body", function(e) {
                    self.keyboardShortcutsHandler(e);
                });

                return $.when.apply($, deferred_promises);
            });
        },
    
        keyboardShortcutsHandler: function(e) {
            var self = this;
            if ((e.which === 13 || e.which === 10) && (e.ctrlKey || e.metaKey)) {
                self.processReconciliations(_.filter(self.getChildren(), function(o) { return o.is_valid; }));
            }
        },

        processReconciliations: function(reconciliations) {},

        displayReconciliation: function() {},
    
        childValidated: function(child) {},
    
        displayDoneMessage: function() {},
    
        updateProgressbar: function() {},

        // adds fields, prefixed with q_, to the move line for qweb rendering
        decorateMoveLine: function(line) {
            line.partial_reconcile = false;
            line.propose_partial_reconcile = false;
            line.q_due_date = (line.date_maturity === false ? line.date : line.date_maturity);
            line.q_amount = (line.debit !== 0 ? "- "+line.q_debit : "") + (line.credit !== 0 ? line.q_credit : "");
            line.q_label = line.name;
            var template_name = (QWeb.has_template(this.template_prefix+"reconciliation_move_line_details") ? this.template_prefix : "") + "reconciliation_move_line_details";
            line.q_popover = QWeb.render(template_name, {line: line});
            if (line.ref && line.ref !== line.name)
                line.q_label += " : " + line.ref;
        },
    });
    
    instance.web.account.abstractReconciliationLine = instance.web.Widget.extend({
        className: 'oe_reconciliation_line',
        
        events: {
            "click .mv_line": "moveLineClickHandler",
            "click .created_line": "createdLineClickHandler",
            "click .pager_control_left:not(.disabled)": "pagerControlLeftHandler",
            "click .pager_control_right:not(.disabled)": "pagerControlRightHandler",
            "keyup .filter": "filterHandler",
            "click .add_line": "addLineBeingEdited",
            "click .preset": "presetClickHandler",
            "click .line_info_button": function(e){e.stopPropagation()},
            // Prevent non natively focusable elements from gaining focus on click
            "mousedown *[tabindex='0']": function(e){e.preventDefault()},
        },

        init: function(parent, context) {
            this._super(parent);
            var self = this;

            this.decorateMoveLine = this.getParent().decorateMoveLine;
            this.formatCurrencies = this.getParent().formatCurrencies;

            // TODO : ?
            if (context.initial_data_provided) {
                // Process data
                _.each(context.reconciliation_proposition, function(line) {
                    self.decorateMoveLine(line);
                }, this);
                this.set("mv_lines_selected", context.reconciliation_proposition);
                this.partner_id = context.line.partner_id;
            } else {
                this.set("mv_lines_selected", []);
            }

            this.context = context;
            this.max_move_lines_displayed = this.getParent().max_move_lines_displayed;
            this.animation_speed = this.getParent().animation_speed;
            this.aestetic_animation_speed = this.getParent().aestetic_animation_speed;
            this.model_res_users = this.getParent().model_res_users;
            this.model_tax = this.getParent().model_tax;
            this.map_tax_id_amount = this.getParent().map_tax_id_amount;
            this.map_account_id_code = this.getParent().map_account_id_code;
            this.is_valid = true;
            this.is_consistent = true; // Used to prevent bad server requests
            this.can_fetch_more_move_lines; // Tell if we can show more move lines
            this.filter = "";

            // Kind of a hack. Let's say : set("prop"), on("change:prop", dostuff), dostuff(){ return $.Deferred() }
            // If you set("prop", value), you don't get the deferred back. So this is for the cases where you want
            // to wait until move lines (in the "match" pannel) are loaded after you set("mode", "match") for instance.
            this.finishedLoadingMoveLines;
        
            this.set("mode", undefined);
            this.on("change:mode", this, this.modeChanged);
            this.set("balance", undefined); // Debit is +, credit is -
            this.on("change:balance", this, this.balanceChanged);
            this.set("pager_index", 0);
            this.on("change:pager_index", this, this.pagerChanged);
            // NB : mv_lines represent the counterpart that will be created to reconcile existing move lines, so debit and credit are inverted
            this.set("mv_lines", []);
            this.on("change:mv_lines", this, this.mvLinesChanged);
            this.mv_lines_deselected = []; // deselected lines are displayed on top of the match table
            this.on("change:mv_lines_selected", this, this.mvLinesSelectedChanged);

            this.set("lines_created", []);
            this.set("line_created_being_edited", [{'id': 0}]);
            this.on("change:lines_created", this, this.createdLinesChanged);
            this.on("change:line_created_being_edited", this, this.createdLinesChanged);
        },
    
        start: function() {
            var self = this;
            return self._super().then(function() {

                // no animation while loading
                self.animation_speed = 0;
                self.aestetic_animation_speed = 0;
    
                self.is_consistent = false;
                if (self.context.animate_entrance) {
                    self.$el.fadeOut(0);
                    self.$el.slideUp(0);
                }
                return $.when(self.loadData()).then(function(){
                    return $.when(self.render()).then(function(){
                        self.is_consistent = true;
                        // Make an entrance
                        self.animation_speed = self.getParent().animation_speed;
                        self.aestetic_animation_speed = self.getParent().aestetic_animation_speed;
                        if (self.context.animate_entrance) {
                            return self.$el.stop(true, true).fadeIn({ duration: self.aestetic_animation_speed, queue: false }).css('display', 'none').slideDown(self.aestetic_animation_speed); 
                        }
                    });
                });
            });
        },

        loadData: function() {},

        render: function() {},

        /* create form widgets, append them to the dom and bind their events handlers */
        createFormWidgets: function() {
            var self = this;
            var create_form_fields = self.getParent().create_form_fields;
            var create_form_fields_arr = [];
            for (var key in create_form_fields)
                if (create_form_fields.hasOwnProperty(key))
                    create_form_fields_arr.push(create_form_fields[key]);
            create_form_fields_arr.sort(function(a, b){ return b.index - a.index });
        
            // field_manager
            var dataset = new instance.web.DataSet(this, "account.account", self.context);
            dataset.ids = [];
            dataset.arch = {
                attrs: { string: "Stéphanie de Monaco", version: "7.0", class: "oe_form_container" },
                children: [],
                tag: "form"
            };
        
            self.field_manager = new instance.web.FormView (
                this, dataset, false, {
                    initial_mode: 'edit',
                    disable_autofocus: false,
                    $buttons: $(),
                    $pager: $()
            });
        
            self.field_manager.load_form(dataset);
        
            // fields default properties
            var Default_field = function() {
                this.context = {};
                this.domain = [];
                this.help = "";
                this.readonly = false;
                this.required = true;
                this.selectable = true;
                this.states = {};
                this.views = {};
            };
            var Default_node = function(field_name) {
                this.tag = "field";
                this.children = [];
                this.required = true;
                this.attrs = {
                    invisible: "False",
                    modifiers: '{"required":true}',
                    name: field_name,
                    nolabel: "True",
                };
            };
        
            // Append fields to the field_manager
            self.field_manager.fields_view.fields = {};
            for (var i=0; i<create_form_fields_arr.length; i++) {
                self.field_manager.fields_view.fields[create_form_fields_arr[i].id] = _.extend(new Default_field(), create_form_fields_arr[i].field_properties);
            }
        
            // Returns a function that serves as a xhr response handler
            var hideGroupResponseClosureFactory = function(field_widget, $container, obj_key){
                return function(has_group){
                    if (has_group) $container.show();
                    else {
                        field_widget.destroy();
                        $container.remove();
                        delete self[obj_key];
                    }
                };
            };
        
            // generate the create "form"
            self.create_form = [];
            for (var i=0; i<create_form_fields_arr.length; i++) {
                var field_data = create_form_fields_arr[i];
        
                // create widgets
                var node = new Default_node(field_data.id);
                if (! field_data.required) node.attrs.modifiers = "";
                var field = new field_data.constructor(self.field_manager, node);
                self[field_data.id+"_field"] = field;
                self.create_form.push(field);
        
                // on update : change the last created line
                field.corresponding_property = field_data.corresponding_property;
                field.on("change:value", self, self.formCreateInputChanged);
        
                // append to DOM
                var $field_container = $(QWeb.render("form_create_field", {id: field_data.id, label: field_data.label}));
                field.appendTo($field_container.find("td"));
                self.$(".create_form").prepend($field_container);
        
                // now that widget's dom has been created (appendTo does that), bind events and adds tabindex
                if (field_data.field_properties.type != "many2one") {
                    // Triggers change:value TODO : moche bind ?
                    field.$el.find("input").keyup(function(e, field){ field.commit_value(); }.bind(null, null, field));
                }
                field.$el.find("input").attr("tabindex", field_data.tabindex);
        
                // Hide the field if group not OK
                if (field_data.group !== undefined) {
                    var target = $field_container;
                    target.hide();
                    self.model_res_users
                        .call("has_group", [field_data.group])
                        .then(hideGroupResponseClosureFactory(field, target, (field_data.id+"_field")));
                }
            }
            self.field_manager.do_show();
        },

    
        /** Utils */
    
        bindPopoverTo: function(el) {
            var self = this;
            $(el).addClass("bootstrap_popover");
            el.popover({
                'placement': 'left',
                'container': self.el,
                'html': true,
                'trigger': 'hover',
                'animation': false,
                'toggle': 'popover'
            });
        },

        islineCreatedBeingEditedValid: function() {
            var line = this.get("line_created_being_edited")[0];
            return line.amount // must be defined and not 0
                && line.account_id // must be defined (and will never be 0)
                && line.label; // must be defined and not empty
        },
        
        /* returns the created lines, plus the ones being edited if valid */
        getCreatedLines: function() {
            var self = this;
            var created_lines = self.get("lines_created").slice();
            if (self.islineCreatedBeingEditedValid())
                return created_lines.concat(self.get("line_created_being_edited"));
            else
                return created_lines;
        },

    
        /** Matching */
    
        moveLineClickHandler: function(e) {
            var self = this;
            if (e.currentTarget.dataset.selected === "true") self.deselectMoveLine(e.currentTarget);
            else self.selectMoveLine(e.currentTarget);
        },

        selectMoveLine: function(mv_line) {
            var self = this;
            var line_id = mv_line.dataset.lineid;

            // find the line in mv_lines or mv_lines_deselected
            var line = _.find(self.get("mv_lines"), function(o){ return o.id == line_id});
            if (! line) {
                line = _.find(self.mv_lines_deselected, function(o){ return o.id == line_id });
                self.mv_lines_deselected = _.filter(self.mv_lines_deselected, function(o) { return o.id != line_id });
            }
            if (! line) return; // If no line found, we've got a syncing problem (let's turn a deaf ear)
            
            // Let inheriting function do the rest
            return line;
        },

        deselectMoveLine: function(mv_line) {
            var self = this;
            var line_id = mv_line.dataset.lineid;
            var line = _.find(self.get("mv_lines_selected"), function(o){ return o.id == line_id});
            if (! line) return; // If no line found, we've got a syncing problem (let's turn a deaf ear)

            $(mv_line).attr('data-selected','false');
            self.mv_lines_deselected.unshift(line);
            self.set("mv_lines_selected",_.filter(self.get("mv_lines_selected"), function(o) { return o.id != line_id }));
            self.$el.removeClass("no_match");
            self.set("mode", "match");

            return line;
        },
    

        /** Matches pagination */
    
        pagerControlLeftHandler: function() {
            var self = this;
            if (self.$(".pager_control_left").hasClass("disabled")) { return; /* shouldn't happen, anyway*/ }
            if (self.get("pager_index") === 0) { return; }
            self.set("pager_index", self.get("pager_index")-1 );
        },
        
        pagerControlRightHandler: function() {
            var self = this;
            var new_index = self.get("pager_index")+1;
            if (self.$(".pager_control_right").hasClass("disabled")) { return; /* shouldn't happen, anyway*/ }
            if (! self.can_fetch_more_move_lines) { return; }
            self.set("pager_index", new_index );
        },

        filterHandler: function() {
            var self = this;
            self.set("pager_index", 0);
            self.filter = self.$(".filter").val();
            window.clearTimeout(self.apply_filter_timeout);
            self.apply_filter_timeout = window.setTimeout(self.proxy('updateMatches'), 200);
        },


        /** Creating */
        
        initializeCreateForm: function() {
            var self = this;

            _.each(self.create_form, function(field) {
                field.set("value", false);
            });
            self.amount_field.set("value", -1*self.get("balance"));
            self.account_id_field.focus();
        },
        
        addLineBeingEdited: function() {
            var self = this;
            if (! self.islineCreatedBeingEditedValid()) return;
            
            self.set("lines_created", self.get("lines_created").concat(self.get("line_created_being_edited")));
            // Add empty created line
            var new_id = self.get("line_created_being_edited")[0].id + 1;
            self.set("line_created_being_edited", [{'id': new_id}]);
        
            self.initializeCreateForm();
        },

        createdLineClickHandler: function(e) {
            this.removeLine($(e.currentTarget));
        },
        
        removeLine: function($line) {
            var self = this;
            var line_id = $line.data("lineid");
        
            // if deleting the created line that is being edited, validate it before
            if (line_id === self.get("line_created_being_edited")[0].id) {
                self.addLineBeingEdited();
            }
            self.set("lines_created", _.filter(self.get("lines_created"), function(o) { return o.id != line_id }));
            self.amount_field.set("value", -1*self.get("balance"));
        },

        presetClickHandler: function(e) {
            var self = this;
            var preset = this.presets[e.currentTarget.dataset.presetid];
            for (var i=0; i<preset.lines.length; i++) {
                self.addLineBeingEdited();
                self.applyPresetLine(preset.lines[i]);
            }
        },

        applyPresetLine: function(preset_line) {
            var self = this;
            self.initializeCreateForm();
            // Hack : set_value of a field calls a handler that returns a deferred because it could make a RPC call
            // to compute the tax before it updates the line being edited. Unfortunately this deferred is lost.
            // Hence this ugly hack to avoid concurrency problem that arose when setting amount (in initializeCreateForm), then tax, then another amount
            if (preset_line.tax && self.tax_field) self.tax_field.set_value(false);
            if (preset_line.amount && self.amount_field) self.amount_field.set_value(false);

            for (var key in preset_line) {
                if (! preset_line.hasOwnProperty(key) || key === "amount") continue;
                if (preset_line[key] && self.hasOwnProperty(key+"_field"))
                    self[key+"_field"].set_value(preset_line[key]);
            }
            if (preset_line.amount && self.amount_field) {
                if (preset_line.amount_type === "fixed")
                    self.amount_field.set_value(preset_line.amount);
                else if (preset_line.amount_type === "percentage") {
                    self.amount_field.set_value(0);
                    self.updateBalance();
                    self.amount_field.set_value(-1 * self.get("balance") * preset_line.amount / 100);
                }
            }
        },
    
    
        /** Views updating */
    
        updateAccountingViewMatchedLines: function() {
            var self = this;
            $.each(self.$(".tbody_matched_lines .bootstrap_popover"), function(){ $(this).popover('destroy') });
            self.$(".tbody_matched_lines").empty();
            
            var template_name = (QWeb.has_template(this.template_prefix+"reconciliation_move_line") ? this.template_prefix : "") + "reconciliation_move_line";
            _(self.get("mv_lines_selected")).each(function(line){
                var $line = $(QWeb.render(template_name, {line: line, selected: true}));
                self.bindPopoverTo($line.find(".line_info_button"));
                if (line.propose_partial_reconcile) self.bindPopoverTo($line.find(".do_partial_reconcile_button"));
                if (line.partial_reconcile) self.bindPopoverTo($line.find(".undo_partial_reconcile_button"));
                self.$(".tbody_matched_lines").append($line);
            });
        },

        updateAccountingViewCreatedLines: function() {
            var self = this;
            $.each(self.$(".tbody_created_lines .bootstrap_popover"), function(){ $(this).popover('destroy') });
            self.$(".tbody_created_lines").empty();
            
            var template_name = (QWeb.has_template(this.template_prefix+"reconciliation_created_line") ? this.template_prefix : "") + "reconciliation_created_line";
            _(self.getCreatedLines()).each(function(line){
                var $line = $(QWeb.render(template_name, {line: line}));
                self.$(".tbody_created_lines").append($line);
                if (line.no_remove_action) {
                    // Then the previous line's remove button deletes this line too
                    $line.hover(function(){ $(this).prev().addClass("active") },function(){ $(this).prev().removeClass("active") });
                }
            });
        },
    
        updateMatchView: function() {
            var self = this;
            var table = self.$(".match table");
            var nothing_displayed = true;
        
            // Display move lines
            $.each(self.$(".match table .bootstrap_popover"), function(){ $(this).popover('destroy') });
            table.empty();
            var slice_start = self.get("pager_index") * self.max_move_lines_displayed;
            var slice_end = (self.get("pager_index")+1) * self.max_move_lines_displayed;
            _( _.filter(self.mv_lines_deselected, function(o){
                    var floatFromFilter = false;
                    try { floatFromFilter = instance.web.parse_value(self.filter, {type: 'float'}); } catch(e){}
                    return o.name.indexOf(self.filter) !== -1
                    || (o.ref && o.ref.indexOf(self.filter) !== -1)
                    || (isFinite(floatFromFilter) && (o.debit === floatFromFilter || o.credit === floatFromFilter) )})
                .slice(slice_start, slice_end)).each(function(line){
                var $line = $(QWeb.render("reconciliation_move_line", {line: line, selected: false}));
                self.bindPopoverTo($line.find(".line_info_button"));
                table.append($line);
                nothing_displayed = false;
            });
            _(self.get("mv_lines")).each(function(line){
                var $line = $(QWeb.render("reconciliation_move_line", {line: line, selected: false}));
                self.bindPopoverTo($line.find(".line_info_button"));
                table.append($line);
                nothing_displayed = false;
            });
            if (nothing_displayed && this.filter !== "")
                table.append(QWeb.render("filter_no_match", {filter_str: self.filter}));
        },
        
        updatePagerControls: function() {
            var self = this;
        
            if (self.get("pager_index") === 0)
                self.$(".pager_control_left").addClass("disabled");
            else
                self.$(".pager_control_left").removeClass("disabled");
            if (! self.can_fetch_more_move_lines)
                self.$(".pager_control_right").addClass("disabled");
            else
                self.$(".pager_control_right").removeClass("disabled");
        },


        /** Display */

        lineOpenBalanceClickHandler: function() {
            var self = this;
            if (self.get("mode") === "create") {
                self.set("mode", "match");
            } else {
                self.set("mode", "create");
            }
        },
    
    
        /** Properties changed */
    
        // Updates the validation button and the "open balance" line
        balanceChanged: function() {},
    
        modeChanged: function(o, val) {
            var self = this;

            self.$(".action_pane.active").removeClass("active");

            if (val.oldValue === "create")
                self.addLineBeingEdited();
            
            if (self.get("mode") === "inactive") {
                self.$(".match").slideUp(self.animation_speed);
                self.$(".create").slideUp(self.animation_speed);
                self.el.dataset.mode = "inactive";
                if (self.finishedLoadingMoveLines) self.finishedLoadingMoveLines.resolve();
            
            } else if (self.get("mode") === "match") {
                self.updateMatches().then(function() {
                    if (self.$el.hasClass("no_match")) {
                        self.$(".create").stop(true, false); // Visual hack
                        self.set("mode", "create");
                        return;
                    }
                    self.$(".match").slideDown(self.animation_speed);
                    self.$(".create").slideUp(self.animation_speed);
                    self.el.dataset.mode = "match";
                    if (self.finishedLoadingMoveLines) self.finishedLoadingMoveLines.resolve();
                });
            
            } else if (self.get("mode") === "create") {
                self.initializeCreateForm();
                self.$(".match").slideUp(self.animation_speed);
                self.$(".create").slideDown(self.animation_speed);
                self.el.dataset.mode = "create";
                if (self.finishedLoadingMoveLines) self.finishedLoadingMoveLines.resolve();
            }
        },
    
        pagerChanged: function() {
            this.updateMatches();
        },
    
        mvLinesChanged: function() {
            var self = this;
            // If pager_index is out of range, set it to display the last page
            if (self.get("pager_index") !== 0 && self.get("mv_lines").length === 0 && ! self.can_fetch_more_move_lines) {
                self.set("pager_index", 0);
            }
        
            // If there is no match to display, disable match view and pass in mode inactive
            if (self.get("mv_lines").length + self.mv_lines_deselected.length === 0 && !self.can_fetch_more_move_lines && self.filter === "") {
                self.$el.addClass("no_match");
                if (self.get("mode") === "match") {
                    self.set("mode", "inactive");
                }
            } else {
                self.$el.removeClass("no_match");
            }
        
            self.updateMatchView();
            self.updatePagerControls();
        },

    
        mvLinesSelectedChanged: function(elt, val) {
            var self = this;
            $.when(self.updateMatches()).then(function() {
                self.updateAccountingViewMatchedLines();
                self.updateBalance();
            });
        },
    
    
        /** Model */
        
        // Loads move lines according to the widget's state
        updateMatches: function() {
            var self = this;
            var deselected_lines_num = self.mv_lines_deselected.length;
            var offset = self.get("pager_index") * self.max_move_lines_displayed - deselected_lines_num;
            if (offset < 0) offset = 0;
            var limit = (self.get("pager_index")+1) * self.max_move_lines_displayed - deselected_lines_num;
            if (limit > self.max_move_lines_displayed) limit = self.max_move_lines_displayed;
            var excluded_ids = _.collect(self.get("mv_lines_selected").concat(self.mv_lines_deselected), function(o) { return o.id; });
            
            limit += 1; // To see if there's more move lines than we display
            if (limit > 0)
                return self.updateMatchesGetMvLines(excluded_ids, offset, limit, function(move_lines) {
                    self.can_fetch_more_move_lines = (move_lines.length === limit);
                    self.set("mv_lines", move_lines.slice(0, limit-1));
                });
            else
                self.set("mv_lines", []);
        },

        updateMatchesGetMvLines: function(excluded_ids, offset, limit, callback) {},

        // Generic function for updating the line_created_being_edited
        formCreateInputChanged: function(elt, val) {
            var self = this;
            var line_created_being_edited = self.get("line_created_being_edited");
            line_created_being_edited[0][elt.corresponding_property] = val.newValue;
        
            // Specific cases
            if (elt === self.account_id_field)
                line_created_being_edited[0].account_num = self.map_account_id_code[elt.get("value")];
        
            // Update tax line
            var deferred_tax = new $.Deferred();
            if (elt === self.tax_id_field || elt === self.amount_field) {
                var amount = self.amount_field.get("value");
                var tax = self.map_tax_id_amount[self.tax_id_field.get("value")];
                if (amount && tax) {
                    deferred_tax = self.model_tax
                        .call("compute_for_bank_reconciliation", [self.tax_id_field.get("value"), amount])
                        .then(function(data){
                            line_created_being_edited[0].amount_with_tax = line_created_being_edited[0].amount;
                            line_created_being_edited[0].amount = (data.total.toFixed(3) === amount.toFixed(3) ? amount : data.total);
                            var current_line_cursor = 1;
                            $.each(data.taxes, function(index, tax){
                                if (tax.amount !== 0.0) {
                                    var tax_account_id = (amount > 0 ? tax.account_collected_id : tax.account_paid_id);
                                    tax_account_id = tax_account_id !== false ? tax_account_id: line_created_being_edited[0].account_id;
                                    line_created_being_edited[current_line_cursor] = {
                                        id: line_created_being_edited[0].id,
                                        account_id: tax_account_id,
                                        account_num: self.map_account_id_code[tax_account_id],
                                        label: tax.name,
                                        amount: tax.amount,
                                        no_remove_action: true,
                                        is_tax_line: true
                                    };
                                    current_line_cursor = current_line_cursor + 1;
                                }
                            });
                        }
                    );
                } else {
                    line_created_being_edited[0].amount = amount;
                    line_created_being_edited.length = 1;
                    deferred_tax.resolve();
                }
            } else { deferred_tax.resolve(); }
        
            return deferred_tax.then(function(){
                // Format amounts
                $.each(line_created_being_edited, function(index, val) {
                    if (val.amount)
                        line_created_being_edited[index].amount_str = self.formatCurrencies(Math.abs(val.amount), self.currency_id);
                });
                self.set("line_created_being_edited", line_created_being_edited);
                self.createdLinesChanged(); // TODO For some reason, previous line doesn't trigger change handler
            });
        },
        
        createdLinesChanged: function() {
            var self = this;
            self.updateAccountingViewCreatedLines();
            self.updateBalance();
        
            if (self.islineCreatedBeingEditedValid()) self.$(".add_line").show();
            else self.$(".add_line").hide();
        },

        updateBalance: function() {
            var self = this;
            var balance = 0;
            var mv_lines_selected = self.get("mv_lines_selected");
            _.each(mv_lines_selected, function(o) {
                balance = balance - o.debit + o.credit;
            });
            _.each(self.getCreatedLines(), function(o) {
                balance += o.amount;
            });
            // Should work as long as currency's rounding factor is > 0.001 (ie: don't use gold kilos as a currency)
            balance = Math.round(balance*1000)/1000;
            self.set("balance", balance);
        },

        // Returns an object that can be passed to process_reconciliation()
        prepareCreatedMoveLineForPersisting: function(line) {
            var dict = {
                account_id: line.account_id,
                name: line.label
            };
            var amount = line.tax_id ? line.amount_with_tax: line.amount;
            if (amount > 0) dict['credit'] = amount;
            if (amount < 0) dict['debit'] = -1 * amount;
            if (line.tax_id) dict['account_tax_id'] = line.tax_id;
            if (line.is_tax_line) dict['is_tax_line'] = line.is_tax_line;
            if (line.analytic_account_id) dict['analytic_account_id'] = line.analytic_account_id;
            return dict;
        },

        bowOut: function(speed, doPostMortemProcess) {
            speed = speed === undefined ? this.animation_speed : speed;
            if (doPostMortemProcess)
                var postMortemProcess = this.getPostMortemProcess();
            var self = this;
            var height = self.$el.outerHeight();
            var container = $("<div />");
            container.css("height", height)
                     .css("marginTop", self.$el.css("marginTop"))
                     .css("marginBottom", self.$el.css("marginBottom"));
            self.$el.wrap(container);
            return $.when(self.$el.parent().animate({height: 0, marginBottom: 0}, speed*height/150)).then(function() {
                $.each(self.$(".bootstrap_popover"), function(){ $(this).popover('destroy') });
                _.each(self.getChildren(), function(o){ o.destroy() });
                self.$el.parent().remove();
                return $.when(self.destroy()).then(function(){
                    if (doPostMortemProcess)
                        postMortemProcess.call(self);
                });
            });
        },

        // Returns the post mortem process function. We need a closure to keep some data after this.destroy()
        getPostMortemProcess: function() {},
    });

    instance.web.client_actions.add('bank_statement_reconciliation_view', 'instance.web.account.bankStatementReconciliation');
    instance.web.account.bankStatementReconciliation = instance.web.account.abstractReconciliation.extend({
        className: instance.web.account.abstractReconciliation.prototype.className + ' oe_bank_statement_reconciliation',

        events: _.defaults({
            "click .statement_name span": "statementNameClickHandler",
            "keyup .change_statement_name_field": "changeStatementNameFieldHandler",
            "click .change_statement_name_button": "changeStatementButtonClickHandler",
        }, instance.web.account.abstractReconciliation.prototype.events),

        init: function(parent, context) {
            this._super(parent, context);
            this.children_widget = instance.web.account.bankStatementReconciliationLine;
            this.template_prefix = "bank_statement_";

            if (context.context.statement_id) this.statement_ids = [context.context.statement_id];
            if (context.context.statement_ids) this.statement_ids = context.context.statement_ids;
            this.single_statement = this.statement_ids !== undefined && this.statement_ids.length === 1;
            this.multiple_statements = this.statement_ids !== undefined && this.statement_ids.length > 1;
            this.title = context.context.title || _t("Reconciliation");
            this.import_feedback = context.context.import_feedback;
            this.lines = []; // list of reconciliations identifiers to instantiate children widgets
            this.last_displayed_reconciliation_index = undefined; // Flow control
            this.reconciled_lines = 0; // idem
            this.already_reconciled_lines = 0; // Number of lines of the statement which were already reconciled
            this.model_bank_statement = new instance.web.Model("account.bank.statement");
            this.model_bank_statement_line = new instance.web.Model("account.bank.statement.line");
            this.reconciliation_menu_id = false; // Used to update the needaction badge
            // The same move line cannot be selected for multiple resolutions
            this.excluded_move_lines_ids = {};
        },
    
        start: function() {
            var self = this;
            return $.when(this._super()).then(function(){
                // Retreive statement infos and reconciliation data from the model
                var lines_filter = [['journal_entry_id', '=', false], ['account_id', '=', false]];
                var deferred_promises = [];
                
                // Working on specified statement(s)
                if (self.statement_ids) {
                    lines_filter.push(['statement_id', 'in', self.statement_ids]);

                    // If only one statement, display its name as title and allow to modify it
                    if (self.single_statement) {
                        deferred_promises.push(self.model_bank_statement
                            .query(["name"])
                            .filter([['id', '=', self.statement_ids[0]]])
                            .first()
                            .then(function(title){
                                self.title = title.name;
                            })
                        );
                    }

                    // Anyway, find out how many statement lines are reconciled (for the progressbar)
                    deferred_promises.push(self.model_bank_statement
                        .call("number_of_lines_reconciled", [self.statement_ids])
                        .then(function(num) {
                            self.already_reconciled_lines = num;
                        })
                    );
                }

                // Get the id of the menuitem
                deferred_promises.push(new instance.web.Model("ir.model.data")
                    .call("xmlid_to_res_id", ["account.menu_bank_reconcile_bank_statements"])
                    .then(function(data) {
                        self.reconciliation_menu_id = data;
                        self.doReloadMenuReconciliation();
                    })
                );

                // Get statement lines
                deferred_promises.push(self.model_bank_statement_line
                    .query(['id'])
                    .filter(lines_filter)
                    .order_by('statement_id, id')
                    .all().then(function (data) {
                        self.lines = _(data).map(function(o){ return o.id });
                    })
                );
        
                // When queries are done, render template and reconciliation lines
                return $.when.apply($, deferred_promises).then(function(){
        
                    // If there is no statement line to reconcile, stop here
                    if (self.lines.length === 0) {
                        self.$el.prepend(QWeb.render("bank_statement_nothing_to_reconcile"));
                        if (self.import_feedback) {
                            self.displayImportFeedback(self.import_feedback);
                        }
                        return;
                    }
        
                    // Render and display
                    self.$el.prepend(QWeb.render("reconciliation", {
                        title: self.title,
                        single_statement: self.single_statement,
                        total_lines: self.already_reconciled_lines+self.lines.length
                    }));
                    self.updateProgressbar();
                    var reconciliations_to_show = self.lines.slice(0, self.max_reconciliations_displayed);
                    self.last_displayed_reconciliation_index = reconciliations_to_show.length;
                    self.$(".reconciliation_lines_container").css("opacity", 0);
        
                    // Display the reconciliations
                    return self.model_bank_statement_line
                        .call("get_data_for_reconciliations", [reconciliations_to_show])
                        .then(function (data) {
                            var child_promises = [];
                            var datum = data.shift();
                            if (datum !== undefined)
                                child_promises.push(self.displayReconciliation(datum.st_line.id, 'match', false, true, datum.st_line, datum.reconciliation_proposition));
                            while ((datum = data.shift()) !== undefined)
                                child_promises.push(self.displayReconciliation(datum.st_line.id, 'inactive', false, true, datum.st_line, datum.reconciliation_proposition));
                            
                            // When reconciliations are instanciated, make an entrance
                            $.when.apply($, child_promises).then(function(){
                                self.$(".reconciliation_lines_container").animate({opacity: 1}, self.aestetic_animation_speed, function() {
                                    if (self.import_feedback) {
                                        self.displayImportFeedback(self.import_feedback);
                                    }
                                });
                            });
                        });
                });
            });
        },

        displayImportFeedback: function(feedback) {
            var self = this;
            var notification = $("<div class='import_feedback alert alert-info' role='alert'>"+feedback+"</div>").hide();
            notification.appendTo(this.$(".notification_area")).slideDown(this.aestetic_animation_speed);
            this.$(".notification_area").css("cursor", "pointer").click(function() {
                $(this).slideUp(self.aestetic_animation_speed, function() {
                    $(this).remove();
                });
            });
        },

        statementNameClickHandler: function() {
            if (! this.single_statement) return;
            this.$(".statement_name span").hide();
            this.$(".change_statement_name_field").attr("value", this.title);
            this.$(".change_statement_name_container").show();
            this.$(".change_statement_name_field").focus();
        },
        
        changeStatementNameFieldHandler: function(e) {
            var name = this.$(".change_statement_name_field").val();
            if (name === "") this.$(".change_statement_name_button").attr("disabled", "disabled");
            else this.$(".change_statement_name_button").removeAttr("disabled");
            
            if (name !== "" && e.which === 13) // Enter
                this.$(".change_statement_name_button").trigger("click");
            if (e.which === 27) { // Escape
                this.$(".statement_name span").show();
                this.$(".change_statement_name_container").hide();
            }
        },
        
        changeStatementButtonClickHandler: function() {
            var self = this;
            if (! self.single_statement) return;
            var name = self.$(".change_statement_name_field").val();
            if (name === "") return;
            return self.model_bank_statement
                .call("write", [[self.statement_ids[0]], {'name': name}])
                .then(function () {
                    self.title = name;
                    self.$(".statement_name span").text(name).show();
                    self.$(".change_statement_name_container").hide();
                });
        },

        updateProgressbar: function() {
            var self = this;
            var done = self.already_reconciled_lines + self.reconciled_lines;
            var total = self.already_reconciled_lines + self.lines.length;
            var prog_bar = self.$(".progress .progress-bar");
            prog_bar.attr("aria-valuenow", done);
            prog_bar.css("width", (done/total*100)+"%");
            self.$(".progress .progress-text .valuenow").text(done);
        },

        processReconciliations: function(reconciliations) {
            if (reconciliations.length === 0) return;
            var self = this;
            var data = _.collect(reconciliations, function(o) {
                return [o.st_line_id, o.makeMoveLineDicts()];
            });
            var deferred_animation = self.$(".reconciliation_lines_container").fadeOut(self.aestetic_animation_speed);
            var deferred_rpc = self.model_bank_statement_line.call("process_reconciliations", [data]);
            return $.when(deferred_animation, deferred_rpc)
                .done(function() {
                    // Remove children
                    for (var i=0; i<reconciliations.length; i++)
                        reconciliations[i].bowOut(0, false);
                    // Update interface
                    self.lines_reconciled_with_ctrl_enter += reconciliations.length;
                    self.reconciled_lines += reconciliations.length;
                    self.updateProgressbar();
                    self.doReloadMenuReconciliation();

                    // Display new line if there are left
                    if (self.last_displayed_reconciliation_index < self.lines.length) {
                        var begin = self.last_displayed_reconciliation_index;
                        var end = Math.min((begin+self.max_reconciliations_displayed), self.lines.length);
                        var reconciliations_to_show = self.lines.slice(begin, end);

                        return self.model_bank_statement_line
                            .call("get_data_for_reconciliations", [reconciliations_to_show])
                            .then(function (data) {
                                var child_promises = [];
                                var datum;
                                while ((datum = data.shift()) !== undefined)
                                    child_promises.push(self.displayReconciliation(datum.st_line.id, 'inactive', false, true, datum.st_line, datum.reconciliation_proposition));
                                self.last_displayed_reconciliation_index += reconciliations_to_show.length;
                                return $.when.apply($, child_promises).then(function() {
                                    // Put the first line in match mode
                                    if (self.reconciled_lines !== self.lines.length) {
                                        var first_child = self.getChildren()[0];
                                        if (first_child.get("mode") === "inactive") {
                                            first_child.set("mode", "match");
                                        }
                                    }
                                    self.$(".reconciliation_lines_container").fadeIn(self.aestetic_animation_speed);
                                });
                            });
                    } else if (self.reconciled_lines === self.lines.length) {
                        // Congratulate the user if the work is done
                        self.displayDoneMessage();
                    } else {
                        // Some lines weren't persisted because they were't valid
                        self.$(".reconciliation_lines_container").fadeIn(self.aestetic_animation_speed);
                    }
                }).fail(function() {
                    self.$(".reconciliation_lines_container").fadeIn(self.aestetic_animation_speed);
                });
        },
    
        displayReconciliation: function(line_id, mode, animate_entrance, initial_data_provided, line, reconciliation_proposition) {
            var self = this;
            animate_entrance = (animate_entrance === undefined ? true : animate_entrance);
            initial_data_provided = (initial_data_provided === undefined ? false : initial_data_provided);
        
            var context = {
                line_id: line_id,
                mode: mode,
                animate_entrance: animate_entrance,
                initial_data_provided: initial_data_provided,
                line: initial_data_provided ? line : undefined,
                reconciliation_proposition: initial_data_provided ? reconciliation_proposition : undefined,
            };
            var widget = new self.children_widget(self, context);
            return widget.appendTo(self.$(".reconciliation_lines_container"));
        },

        // Adds move line ids to the list of move lines not to fetch for a given partner
        // This is required because the same move line cannot be selected for multiple reconciliation
        // and because for a partial reconciliation only one line can be fetched)
        excludeMoveLines: function(source_child, partner_id, lines) {
            var self = this;
            var line_ids = _.collect(lines, function(o) { return o.id });
        
            var excluded_ids = this.excluded_move_lines_ids[partner_id];
            var excluded_move_lines_changed = false;
            _.each(line_ids, function(line_id){
                if (excluded_ids.indexOf(line_id) === -1) {
                    excluded_ids.push(line_id);
                    excluded_move_lines_changed = true;
                }
            });
            if (! excluded_move_lines_changed)
                return;
        
            // Function that finds if an array of line objects contains at least a line identified by its id
            var contains_lines = function(lines_array, line_ids) {
                for (var i = 0; i < lines_array.length; i++)
                    for (var j = 0; j < line_ids.length; j++)
                        if (lines_array[i].id === line_ids[j])
                            return true;
                return false;
            };
        
            // Update children if needed
            _.each(self.getChildren(), function(child){
                if (child.st_line === undefined) {
                    console.error("[Warning] Calling excludeMoveLines when a reconciliation hasn't finished fetching its data from the server.");
                } else if ((child.partner_id === partner_id || child.st_line.has_no_partner) && child !== source_child) {
                    if (contains_lines(child.get("mv_lines_selected"), line_ids)) {
                        child.set("mv_lines_selected", _.filter(child.get("mv_lines_selected"), function(o){ return line_ids.indexOf(o.id) === -1 }));
                    } else if (contains_lines(child.mv_lines_deselected, line_ids)) {
                        child.mv_lines_deselected = _.filter(child.mv_lines_deselected, function(o){ return line_ids.indexOf(o.id) === -1 });
                        child.updateMatches();
                    } else if (contains_lines(child.get("mv_lines"), line_ids) || child.get("mode") === "match") {
                        child.updateMatches();
                    }
                }
            });
        },
        
        unexcludeMoveLines: function(source_child, partner_id, lines) {
            var self = this;
            var line_ids = _.collect(lines, function(o) { return o.id });

            var initial_excluded_lines_num = this.excluded_move_lines_ids[partner_id].length;
            this.excluded_move_lines_ids[partner_id] = _.difference(this.excluded_move_lines_ids[partner_id], line_ids);
            if (this.excluded_move_lines_ids[partner_id].length === initial_excluded_lines_num)
                return;
        
            // Update children if needed
            _.each(self.getChildren(), function(child){
                if (child.partner_id === partner_id && child !== source_child && (child.get("mode") === "match" || child.$el.hasClass("no_match")))
                    child.updateMatches();
                if (child.st_line.has_no_partner && child.get("mode") === "match" || child.$el.hasClass("no_match"))
                    child.updateMatches();
            });
        },

        childValidated: function() {
            var self = this;
            
            self.reconciled_lines++;
            self.updateProgressbar();
            self.doReloadMenuReconciliation();
            
            // Display new line if there are left
            if (self.last_displayed_reconciliation_index < self.lines.length) {
                self.displayReconciliation(self.lines[self.last_displayed_reconciliation_index++], 'inactive');
            }
            // Congratulate the user if the work is done
            if (self.reconciled_lines === self.lines.length) {
                self.displayDoneMessage();
            }
        
            // Put the first line in match mode
            if (self.reconciled_lines !== self.lines.length) {
                var first_child = self.getChildren()[0];
                if (first_child.get("mode") === "inactive") {
                    first_child.set("mode", "match");
                }
            }
        },

        decorateMoveLine: function(line) {
            line['credit'] = [line['debit'], line['debit'] = line['credit']][0];
            this._super(line);
        },

        /* reloads the needaction badge */
        doReloadMenuReconciliation: function () {
            var menu = instance.webclient.menu;
            if (!menu || !this.reconciliation_menu_id) {
                return $.when();
            }
            return menu.rpc("/web/menu/load_needaction", {'menu_ids': [this.reconciliation_menu_id]}).done(function(r) {
                menu.on_needaction_loaded(r);
            }).then(function () {
                menu.trigger("need_action_reloaded");
            });
        },

        goBackToStatementsTreeView: function() {
            var self = this;
            new instance.web.Model("ir.model.data")
                .call("get_object_reference", ['account', 'action_bank_statement_tree'])
                .then(function (result) {
                    var action_id = result[1];
                    // Warning : altough I don't see why this widget wouldn't be directly instanciated by the
                    // action manager, if it wasn't, this code wouldn't work. You'd have to do something like :
                    // var action_manager = self;
                    // while (! action_manager instanceof ActionManager)
                    //    action_manager = action_manager.getParent();
                    var action_manager = self.getParent();
                    var breadcrumbs = action_manager.breadcrumbs;
                    var found = false;
                    for (var i=breadcrumbs.length-1; i>=0; i--) {
                        if (breadcrumbs[i].action && breadcrumbs[i].action.id === action_id) {
                            var title = breadcrumbs[i].get_title();
                            action_manager.select_breadcrumb(i, _.isArray(title) ? i : undefined);
                            found = true;
                        }
                    }
                    if (!found)
                        instance.web.Home(self);
                });
        },
    
        displayDoneMessage: function() {
            var self = this;
            
            var sec_taken = Math.round((Date.now()-self.time_widget_loaded)/1000);
            var sec_per_item = Math.round(sec_taken/self.reconciled_lines);
            var achievements = [];
    
            var time_taken;
            if (sec_taken/60 >= 1) time_taken = Math.floor(sec_taken/60) +"' "+ sec_taken%60 +"''";
            else time_taken = sec_taken%60 +" seconds";
    
            var title;
            if (sec_per_item < 5) title = _t("Whew, that was fast !") + " <i class='fa fa-trophy congrats_icon'></i>";
            else title = _t("Congrats, you're all done !") + " <i class='fa fa-thumbs-o-up congrats_icon'></i>";
    
            if (self.lines_reconciled_with_ctrl_enter === self.reconciled_lines)
                achievements.push({
                    title: _t("Efficiency at its finest"),
                    desc: _t("Only use the ctrl-enter shortcut to validate reconciliations."),
                    icon: "fa-keyboard-o"}
                );
    
            if (sec_per_item < 5)
                achievements.push({
                    title: _t("Fast reconciler"),
                    desc: _t("Take on average less than 5 seconds to reconcile a transaction."),
                    icon: "fa-bolt"}
                );
    
            // Render it
            self.$(".protip").hide();
            self.$(".oe_form_sheet").append(QWeb.render("bank_statement_reconciliation_done_message", {
                title: title,
                time_taken: time_taken,
                sec_per_item: sec_per_item,
                transactions_done: self.reconciled_lines,
                done_with_ctrl_enter: self.lines_reconciled_with_ctrl_enter,
                achievements: achievements,
                single_statement: self.single_statement,
                multiple_statements: self.multiple_statements,
            }));
    
            // Animate it
            var container = $("<div style='overflow: hidden;' />");
            self.$(".done_message").wrap(container).css("opacity", 0).css("position", "relative").css("left", "-50%");
            self.$(".done_message").animate({opacity: 1, left: 0}, self.aestetic_animation_speed*2, "easeOutCubic");
            self.$(".done_message").animate({opacity: 1}, self.aestetic_animation_speed*3, "easeOutCubic");
    
            // Make it interactive
            self.$(".achievement").popover({'placement': 'top', 'container': self.el, 'trigger': 'hover'});
            
            if (self.$(".button_back_to_statement").length !== 0) {
                self.$(".button_back_to_statement").click(function() {
                    self.goBackToStatementsTreeView();
                });
            }

            if (self.$(".button_close_statement").length !== 0) {
                self.$(".button_close_statement").hide();
                self.model_bank_statement
                    .query(["balance_end_real", "balance_end"])
                    .filter([['id', 'in', self.statement_ids]])
                    .all()
                    .then(function(data){
                        if (_.all(data, function(o) { return o.balance_end_real === o.balance_end })) {
                            self.$(".button_close_statement").show();
                            self.$(".button_close_statement").click(function() {
                                self.$(".button_close_statement").attr("disabled", "disabled");
                                self.model_bank_statement
                                    .call("button_confirm_bank", [self.statement_ids])
                                    .then(
                                        function() { self.goBackToStatementsTreeView(); },
                                        function() { self.$(".button_close_statement").removeAttr("disabled"); }
                                    );
                            });
                        }
                    });
            }
        },
    });
    
    instance.web.account.bankStatementReconciliationLine = instance.web.account.abstractReconciliationLine.extend({
        className: instance.web.account.abstractReconciliationLine.prototype.className + ' oe_bank_statement_reconciliation_line',

        events: _.defaults({
            "click .change_partner": "changePartnerClickHandler",
            "click .button_ok": "persistAndBowOut",
            "click .initial_line": "initialLineClickHandler",
            "click .line_open_balance": "lineOpenBalanceClickHandler",
            "click .do_partial_reconcile_button": "doPartialReconcileButtonClickHandler",
            "click .undo_partial_reconcile_button": "undoPartialReconcileButtonClickHandler",
        }, instance.web.account.abstractReconciliationLine.prototype.events),
        
        init: function(parent, context) {
            this._super(parent, context);
            this.template_prefix = this.getParent().template_prefix;
    
            if (context.initial_data_provided) {
                // Process data
                this.st_line = context.line;
                this.decorateStatementLine(this.st_line);
                this.currency_id = this.st_line.currency_id;
    
                // Exclude selected move lines
                if (this.getParent().excluded_move_lines_ids[this.partner_id] === undefined)
                    this.getParent().excluded_move_lines_ids[this.partner_id] = [];
                this.getParent().excludeMoveLines(this, this.partner_id, context.reconciliation_proposition);
            } else {
                this.st_line = undefined;
                this.partner_id = undefined;
            }

            this.st_line_id = context.line_id;
            this.model_bank_statement_line = this.getParent().model_bank_statement_line;
            this.presets = this.getParent().presets;
        },

        loadData: function() {
            var self = this;
            if (self.context.initial_data_provided)
                return;

            // Get ids of selected move lines (to exclude them from reconciliation proposition)
            var excluded_move_lines_ids = [];
            _.each(self.getParent().excluded_move_lines_ids, function(o){
                excluded_move_lines_ids = excluded_move_lines_ids.concat(o);
            });
            
            // Load statement line
            return self.model_bank_statement_line
                .call("get_data_for_reconciliations", [[self.st_line_id], excluded_move_lines_ids])
                .then(function (data) {
                    self.st_line = data[0].st_line;
                    self.decorateStatementLine(self.st_line);
                    self.currency_id = self.st_line.currency_id;
                    self.partner_id = data[0].st_line.partner_id;
                    if (self.getParent().excluded_move_lines_ids[self.partner_id] === undefined)
                        self.getParent().excluded_move_lines_ids[self.partner_id] = [];
                    var mv_lines = [];
                    _.each(data[0].reconciliation_proposition, function(line) {
                        self.decorateMoveLine(line);
                        mv_lines.push(line);
                    }, self);
                    self.set("mv_lines_selected", self.get("mv_lines_selected").concat(mv_lines));
                });
        },

        render: function() {
            var self = this;
            var presets_array = [];
            for (var id in self.presets)
                if (self.presets.hasOwnProperty(id))
                    presets_array.push(self.presets[id]);
            self.$el.prepend(QWeb.render("bank_statement_reconciliation_line", {
                line: self.st_line,
                presets: presets_array
            }));
            
            // Stuff that require the template to be rendered
            self.$(".match").slideUp(0);
            self.$(".create").slideUp(0);
            if (self.st_line.no_match) self.$el.addClass("no_match");
            self.bindPopoverTo(self.$(".line_info_button"));
            self.createFormWidgets();
            // Special case hack : no identified partner
            if (self.st_line.has_no_partner) {
                self.updateBalance();
                self.$(".change_partner_container").show(0);
                self.$el.addClass("no_partner");
            }
            
            self.finishedLoadingMoveLines = $.Deferred();
            self.set("mode", self.context.mode);
            return $.when(self.finishedLoadingMoveLines).then(function(){
                // Make sure the display is OK
                self.balanceChanged();
                self.createdLinesChanged();
                self.updateAccountingViewMatchedLines();
            });
        },
    
        restart: function(mode) {
            var self = this;
            mode = (mode === undefined ? 'inactive' : mode);
            self.context.animate_entrance = false;
            self.$el.css("height", self.$el.outerHeight());
            // Destroy everything
            _.each(self.getChildren(), function(o){ o.destroy() });
            self.is_consistent = false;
            return $.when(self.$el.animate({opacity: 0}, self.animation_speed)).then(function() {
                self.getParent().unexcludeMoveLines(self, self.partner_id, self.get("mv_lines_selected"));
                $.each(self.$(".bootstrap_popover"), function(){ $(this).popover('destroy') });
                self.$el.empty();
                self.$el.removeClass("no_partner");
                self.context.mode = mode;
                self.context.initial_data_provided = false;
                self.is_valid = true;
                self.is_consistent = true;
                self.filter = "";
                self.set("balance", undefined, {silent: true});
                self.set("mode", undefined, {silent: true});
                self.set("pager_index", 0, {silent: true});
                self.set("mv_lines", [], {silent: true});
                self.set("mv_lines_selected", [], {silent: true});
                self.mv_lines_deselected = [];
                self.set("lines_created", [], {silent: true});
                self.set("line_created_being_edited", [{'id': 0}], {silent: true});
                // Rebirth
                return $.when(self.start()).then(function() {
                    self.$el.css("height", "auto");
                    self.is_consistent = true;
                    self.$el.animate({opacity: 1}, self.animation_speed);
                });
            });
        },
    
        /* create form widgets, append them to the dom and bind their events handlers */
        createFormWidgets: function() {
            var self = this;
            this._super();

            // generate the change partner "form"
            var change_partner_field = {
                relation: "res.partner",
                string: _t("Partner"),
                type: "many2one",
                domain: [['parent_id','=',false], '|', ['customer','=',true], ['supplier','=',true]],
                help: "",
                readonly: false,
                required: true,
                selectable: true,
                states: {},
                views: {},
                context: {},
            };
            var change_partner_node = {
                tag: "field",
                children: [],
                required: true,
                attrs: {
                    invisible: "False",
                    modifiers: '',
                    name: "change_partner",
                    nolabel: "True",
                }
            };
            self.field_manager.fields_view.fields["change_partner"] = change_partner_field;
            self.change_partner_field = new instance.web.form.FieldMany2One(self.field_manager, change_partner_node);
            self.change_partner_field.appendTo(self.$(".change_partner_container"));
            self.change_partner_field.on("change:value", self.change_partner_field, function() {
                self.changePartner(this.get_value());
            });
            self.change_partner_field.$el.find("input").attr("placeholder", self.st_line.communication_partner_name || _t("Select Partner"));
        },
    
        /** Utils */
    
        /* TODO : if t-call for attr, all in qweb */
        decorateStatementLine: function(line){
            line.q_popover = QWeb.render("bank_statement_reconciliation_statement_line_details", {line: line});
        },


        /** Creating */

        initializeCreateForm: function() {
            this.label_field.set("value", this.st_line.name);
            this._super();
        },

    
        /** Matching */
    
        selectMoveLine: function(mv_line) {
            var self = this;
            var line = self._super(mv_line);
            if (!line) return;

            // Warn the user if he's selecting lines from both a payable and a receivable account
            var last_selected_line = _.last(self.get("mv_lines_selected"));
            if (last_selected_line && last_selected_line.account_type != line.account_type) {
                self.getParent().crash_manager.show_warning({data: {
                    exception_type: "Chair-To-Keyboard Interface",
                    message: _.str.sprintf(_t("You are selecting transactions from both a payable and a receivable account.\n\nIn order to proceed, you first need to deselect the %s transactions."), last_selected_line.account_type)
                }});
                return;
            }

            $(mv_line).attr('data-selected','true');
            self.set("mv_lines_selected", self.get("mv_lines_selected").concat(line));
        },

        deselectMoveLine: function(mv_line) {
            var self = this;
            var line = self._super(mv_line);
            if (!line) return;

            // remove partial reconciliation stuff if necessary
            var need_redraw = false;
            if (line.partial_reconcile === true) {
                self.unpartialReconcileLine(line);
                need_redraw = true;
            }
            if (line.propose_partial_reconcile === true) {
                line.propose_partial_reconcile = false;
                need_redraw = true;
            }
            if (need_redraw) self.deselectMoveLine(mv_line);
        },

    
        /** Display */
    
        initialLineClickHandler: function() {
            var self = this;
            if (self.get("mode") !== "inactive") {
                self.set("mode", "inactive");
            } else {
                self.set("mode", "match");
            }
        },
    
        changePartnerClickHandler: function() {
            var self = this;
            self.$(".change_partner_container").find("input").attr("placeholder", self.st_line.partner_name);
            self.$(".change_partner_container").show();
            self.$(".partner_name").hide();
            self.change_partner_field.$drop_down.trigger("click");
        },
    
    
        /** Properties changed */
    
        // Updates the validation button and the "open balance" line
        balanceChanged: function() {
            var self = this;
            var balance = self.get("balance");
            self.$(".tbody_open_balance").empty();
            // Special case hack : no identified partner
            if (self.st_line.has_no_partner) {
                if (Math.abs(balance).toFixed(3) === "0.000") {
                    self.$(".button_ok").addClass("oe_highlight");
                    self.$(".button_ok").removeAttr("disabled");
                    self.$(".button_ok").text("OK");
                    self.is_valid = true;
                } else {
                    self.$(".button_ok").removeClass("oe_highlight");
                    self.$(".button_ok").attr("disabled", "disabled");
                    self.$(".button_ok").text("OK");
                    self.is_valid = false;
                    var debit = (balance > 0 ? self.formatCurrencies(balance, self.currency_id) : "");
                    var credit = (balance < 0 ? self.formatCurrencies(-1*balance, self.currency_id) : "");
                    var $line = $(QWeb.render("reconciliation_line_open_balance", {
                        debit: debit,
                        credit: credit,
                        account_code: self.map_account_id_code[self.st_line.open_balance_account_id],
                        label: "Choose counterpart"
                    }));
                    self.$(".tbody_open_balance").append($line);
                }
                return;
            }
    
            if (Math.abs(balance).toFixed(3) === "0.000") {
                self.$(".button_ok").addClass("oe_highlight");
                self.$(".button_ok").text("OK");
            } else {
                self.$(".button_ok").removeClass("oe_highlight");
                self.$(".button_ok").text("Keep open");
                var debit = (balance > 0 ? self.formatCurrencies(balance, self.currency_id) : "");
                var credit = (balance < 0 ? self.formatCurrencies(-1*balance, self.currency_id) : "");
                var $line = $(QWeb.render("reconciliation_line_open_balance", {
                    debit: debit,
                    credit: credit,
                    account_code: self.map_account_id_code[self.st_line.open_balance_account_id],
                    label: "Open balance"
                }));
                self.$(".tbody_open_balance").append($line);
            }
        },
        
        mvLinesChanged: function(elt, val) {
            var self = this;
            this._super(elt, val);
            _.each(self.get("mv_lines"), function(line) {
                if (line.partial_reconciliation_siblings.length > 0) {
                    self.getParent().excludeMoveLines(self, self.partner_id, line.partial_reconciliation_siblings);
                }
            });
        },

        mvLinesSelectedChanged: function(elt, val) {
            var self = this;

            var added_lines = _.difference(val.newValue, val.oldValue);
            var removed_lines = _.difference(val.oldValue, val.newValue);

            self.getParent().excludeMoveLines(self, self.partner_id, added_lines);
            self.getParent().unexcludeMoveLines(self, self.partner_id, removed_lines);
            
            self._super(elt, val);
        },
    
        /** Model */

        doPartialReconcileButtonClickHandler: function(e) {
            var self = this;
    
            var line_id = $(e.currentTarget).closest("tr").data("lineid");
            var line = _.find(self.get("mv_lines_selected"), function(o) { return o.id == line_id });
            self.partialReconcileLine(line);
    
            $(e.currentTarget).popover('destroy');
            self.updateAccountingViewMatchedLines();
            self.updateBalance();
            e.stopPropagation();
        },
    
        partialReconcileLine: function(line) {
            var self = this;
            var balance = self.get("balance");
            line.initial_amount = line.debit !== 0 ? line.debit : -1 * line.credit;
            if (balance < 0) {
                line.debit += balance;
                line.amount_str = self.formatCurrencies(line.debit, self.currency_id);
            } else {
                line.credit -= balance;
                line.amount_str = self.formatCurrencies(line.credit, self.currency_id);
            }
            line.propose_partial_reconcile = false;
            line.partial_reconcile = true;
        },
    
        undoPartialReconcileButtonClickHandler: function(e) {
            var self = this;
    
            var line_id = $(e.currentTarget).closest("tr").data("lineid");
            var line = _.find(self.get("mv_lines_selected"), function(o) { return o.id == line_id });
            self.unpartialReconcileLine(line);
    
            $(e.currentTarget).popover('destroy');
            self.updateAccountingViewMatchedLines();
            self.updateBalance();
            e.stopPropagation();
        },
    
        unpartialReconcileLine: function(line) {
            var self = this;
            if (line.initial_amount > 0) {
                line.debit = line.initial_amount;
                line.amount_str = self.formatCurrencies(line.debit, self.currency_id);
            } else {
                line.credit = -1 * line.initial_amount;
                line.amount_str = self.formatCurrencies(line.credit, self.currency_id);
            }
            line.propose_partial_reconcile = true;
            line.partial_reconcile = false;
        },
    
        updateBalance: function() {
            var self = this;
            var mv_lines_selected = self.get("mv_lines_selected");
            var lines_selected_num = mv_lines_selected.length;

            // Undo partial reconciliation if necessary
            if (lines_selected_num !== 1) {
                _.each(mv_lines_selected, function(line) {
                    if (line.partial_reconcile === true) self.unpartialReconcileLine(line);
                    if (line.propose_partial_reconcile === true) line.propose_partial_reconcile = false;
                });
                self.updateAccountingViewMatchedLines();
            }

            // Compute balance
            var balance = 0;
            balance -= self.st_line.amount;
            _.each(mv_lines_selected, function(o) {
                balance = balance - o.debit + o.credit;
            });
            _.each(self.getCreatedLines(), function(o) {
                balance += o.amount;
            });
            // Dealing with floating-point
            balance = Math.round(balance*1000)/1000;
            self.set("balance", balance);
            
            // Propose partial reconciliation if necessary
            if (lines_selected_num === 1 &&
                self.st_line.amount * balance > 0 &&
                self.st_line.amount * (mv_lines_selected[0].debit - mv_lines_selected[0].credit) < 0 &&
                ! mv_lines_selected[0].partial_reconcile) {
                
                mv_lines_selected[0].propose_partial_reconcile = true;
                self.updateAccountingViewMatchedLines();
            } else if (lines_selected_num === 1) {
                mv_lines_selected[0].propose_partial_reconcile = false;
                self.updateAccountingViewMatchedLines();
            }
        },

        updateMatchesGetMvLines: function(excluded_ids, offset, limit, callback) {
            var self = this;
            var globally_excluded_ids = [];
            if (self.st_line.has_no_partner)
                _.each(self.getParent().excluded_move_lines_ids, function(o) { globally_excluded_ids = globally_excluded_ids.concat(o) });
            else
                globally_excluded_ids = self.getParent().excluded_move_lines_ids[self.partner_id];
            for (var i=0; i<globally_excluded_ids.length; i++)
                if (excluded_ids.indexOf(globally_excluded_ids[i]) === -1)
                    excluded_ids.push(globally_excluded_ids[i]);
            return self.model_bank_statement_line
                .call("get_move_lines_for_bank_reconciliation_by_statement_line_id", [self.st_line.id, excluded_ids, self.filter, offset, limit])
                .then(function (lines) {
                    _.each(lines, function(line) { self.decorateMoveLine(line) }, self);
                    return callback.call(self, lines);
                });
        },

        // Changes the partner_id of the statement_line in the DB and reloads the widget
        changePartner: function(partner_id, callback) {
            var self = this;
            self.is_consistent = false;
            return self.model_bank_statement_line
                // Update model
                .call("write", [[self.st_line_id], {'partner_id': partner_id}])
                .then(function () {
                    return $.when(self.restart("match")).then(function(){
                        self.is_consistent = true;
                        if (callback) callback();
                    });
                });
        },

        // Returns an object that can be passed to process_reconciliation()
        prepareSelectedMoveLineForPersisting: function(line) {
            return {
                name: line.name,
                debit: line.debit,
                credit: line.credit,
                counterpart_move_line_id: line.id,
            };
        },
    
        // idem
        prepareOpenBalanceForPersisting: function() {
            var balance = this.get("balance");
            var dict = {};
    
            dict['account_id'] = this.st_line.open_balance_account_id;
            dict['name'] = _t("Open balance");
            if (balance > 0) dict['debit'] = balance;
            if (balance < 0) dict['credit'] = -1*balance;
    
            return dict;
        },

        makeMoveLineDicts: function() {
            var self = this;
            var mv_line_dicts = [];
            _.each(self.get("mv_lines_selected"), function(o) { mv_line_dicts.push(self.prepareSelectedMoveLineForPersisting(o)) });
            _.each(self.getCreatedLines(), function(o) { mv_line_dicts.push(self.prepareCreatedMoveLineForPersisting(o)) });
            if (Math.abs(self.get("balance")).toFixed(3) !== "0.000") mv_line_dicts.push(self.prepareOpenBalanceForPersisting());
            return mv_line_dicts;
        },
    
        // Persist data, notify parent view and terminate widget
        persistAndBowOut: function() {
            var self = this;
            if (! this.is_consistent) return;
            this.model_bank_statement_line.call("process_reconciliation", [this.st_line_id, this.makeMoveLineDicts()]).then(function() {
                self.bowOut(self.animation_speed, true);
            });
        },

        getPostMortemProcess: function() {
            var parent = this.getParent();
            var partner_id = this.partner_id;
            var mv_lines_selected = this.get("mv_lines_selected");
            return function() {
                parent.unexcludeMoveLines(undefined, partner_id, mv_lines_selected);
                parent.childValidated();
            };
        },
    });
    
    instance.web.client_actions.add('manual_reconciliation_view', 'instance.web.account.manualReconciliation');
    instance.web.account.manualReconciliation = instance.web.account.abstractReconciliation.extend({
        className: instance.web.account.abstractReconciliation.prototype.className + ' oe_manual_reconciliation',

        events: _.defaults({
            "change input[name='show_reconciliations_type']": "showReconciliationsTypeHandler",
        }, instance.web.account.abstractReconciliation.prototype.events),

        init: function(parent, context) {
            this._super(parent, context);
            this.children_widget = instance.web.account.manualReconciliationLine;
            this.template_prefix = "manual_";
            this.model_aml = new instance.web.Model("account.move.line");
            this.model_partner = new instance.web.Model("res.partner");
            this.model_account = new instance.web.Model("account.account");
            this.title = _t("Journal Items to Reconcile");
            this.max_reconciliations_displayed = 10;
            this.max_move_lines_displayed = 20;
            this.partner_id = context.context.partner_id;
            this.account_id = context.context.account_id;
            this.working_on_a_given_item = this.partner_id || this.account_id;
            this.partners_data = {
                show: true,
                items: [],
                num_total: undefined,
                num_done: 0,
            };
            this.accounts_data = {
                show: true,
                items: [],
                num_total: undefined,
                num_done: 0,
            };
            this.create_form_fields = _.defaults({
                journal_id: {
                    id: "journal_id",
                    index: 2,
                    corresponding_property: "journal_id", // a account.move field name
                    label: _t("Journal"),
                    required: true,
                    tabindex: 11,
                    constructor: instance.web.form.FieldMany2One,
                    field_properties: {
                        relation: "account.journal",
                        string: _t("Journal"),
                        type: "many2one",
                        domain: [['type','not in',['view', 'closed', 'consolidation']]],
                    },
                }
            }, this.create_form_fields);
        },
    
        start: function() {
            var self = this;
            return $.when(this._super()).then(function(){
                // Get data for a partner, an account or all partners/accounts that can be reconciled
                var deferred_partner, deferred_account;
                if (self.partner_id !== undefined)
                    deferred_partner = self.model_aml.call("get_partner_data_for_manual_reconciliation", [self.partner_id]);
                if (self.account_id !== undefined)
                    deferred_account = self.model_aml.call("get_account_data_for_manual_reconciliation", [self.account_id]);
                if (self.partner_id === undefined && self.account_id === undefined) {
                    deferred_partner = self.model_aml.call("get_partner_data_for_manual_reconciliation");
                    deferred_account = self.model_aml.call("get_account_data_for_manual_reconciliation");
                }

                return $.when(deferred_partner, deferred_account).then(function(data_partner, data_account){
                    var data_partner_len = data_partner ? data_partner.length : 0;
                    var data_account_len = data_account ? data_account.length : 0;

                    // If nothing to reconcile, stop here
                    if (data_partner_len + data_account_len === 0) {
                        self.$el.prepend(QWeb.render("manual_reconciliation_nothing_to_reconcile"));
                        return;
                    }

                    // If reconciling a specified account/partner, adapt title to the use case
                    if (self.partner_id !== undefined)
                        self.title = _t("Reconciling ")+data_partner[0].partner_name;
                    if (self.account_id !== undefined)
                        self.title = _t("Reconciling ")+data_account[0].account_code;

                    // Display interface
                    self.$el.prepend(QWeb.render("manual_reconciliation", {
                        title: self.title,
                        total_lines: 0,
                        hide_progress: self.working_on_a_given_item,
                        show_partners: self.partners_data.show,
                        show_accounts: self.accounts_data.show,
                        show_accounts_type_controller: data_partner_len !== 0 && data_account_len !== 0
                    }));
                    
                    // Process data
                    self.partners_data.num_total = data_partner_len;
                    self.accounts_data.num_total = data_account_len;
                    self.partners_data.items = _.collect(data_partner, function(datum) {
                        self.prepareReconciliationData(datum);
                        datum.reconciliation_type = 'partner';
                        return datum;
                    });
                    self.accounts_data.items = _.collect(data_account, function(datum) {
                        self.prepareReconciliationData(datum);
                        datum.reconciliation_type = 'account';
                        return datum;
                    });

                    // Instanciate reconciliations
                    self.$(".reconciliation_lines_container").css("opacity", 0);
                    return $.when(self.updateProgress(false)).then(function(){
                        return self.$(".reconciliation_lines_container").animate({opacity: 1}, self.aestetic_animation_speed);
                    });
                });
            });
        },

        processReconciliations: function(reconciliations) {
            if (reconciliations.length === 0) return;
            var self = this;
            var reconciliations_type_count = _.countBy(reconciliations, function(rec) { return rec.data.reconciliation_type; });
            var data = _.collect(reconciliations, function(rec) {
                return {
                    id: rec.data.reconciliation_type === 'partner' ? rec.data.partner_id : rec.data.account_id,
                    type: rec.data.reconciliation_type,
                    mv_line_ids: _.collect(rec.get("mv_lines_selected"), function(o){ return o.id }),
                    new_mv_line_dicts: _.collect(rec.getCreatedLines(), function(o){ return rec.prepareCreatedMoveLineForPersisting(o) }),
                };
            });
            var deferred_animation = self.$(".reconciliation_lines_container").fadeOut(self.aestetic_animation_speed);
            var deferred_rpc = self.model_aml.call("process_reconciliations", [data]);
            return $.when(deferred_animation, deferred_rpc)
                .done(function() {
                    // Remove children
                    for (var i=0; i<reconciliations.length; i++)
                        reconciliations[i].bowOut(0, false);
                    // Update interface
                    self.lines_reconciled_with_ctrl_enter += reconciliations.length;
                    self.partners_data.num_done += reconciliations_type_count.partner || 0;
                    self.accounts_data.num_done += reconciliations_type_count.account || 0;
                    self.updateProgress();
                }).always(function() {
                    self.$(".reconciliation_lines_container").fadeIn(self.aestetic_animation_speed);
                });
        },

        displayReconciliation: function(data, animate_entrance) {
            var widget = new this.children_widget(this, {data: data, animate_entrance: animate_entrance});
            data.displayed = true;
            return widget.appendTo(this.$(".reconciliation_lines_container"));
        },

        showReconciliationsTypeHandler: function(e) {
            var self = this;
            var val = $(e.target).attr("val");
            self.partners_data.show = true;
            self.accounts_data.show = true;
            if (val === 'partners')
                self.accounts_data.show = false;
            else if (val === 'accounts')
                self.partners_data.show = false;
            self.updateProgress();
        },

        updateProgress: function(animate_entrance) {
            animate_entrance = (animate_entrance === undefined ? true : animate_entrance);
            var self = this;

            self.updateProgressbar();

            // Remove children that should not be displayed
            _.each(self.getChildren(), function(child) {
                var hide = (!self.partners_data.show && child.data.reconciliation_type === 'partner')
                        || (!self.accounts_data.show && child.data.reconciliation_type === 'account');
                if (hide) {
                    child.$el.slideUp(self.aestetic_animation_speed, function(){ child.destroy() });
                    child.data.displayed = false;
                }
            });
            
            // show next reconciliation(s)
            var children_promises = [];
            var items_to_display = _.filter(self.partners_data.items.concat(self.accounts_data.items), function(item) {
                if (!self.partners_data.show && item.reconciliation_type === 'partner') return false;
                if (!self.accounts_data.show && item.reconciliation_type === 'account') return false;
                return item.displayed === false;
            }).slice(0, self.max_reconciliations_displayed - self.getChildren().length);
            _.each(items_to_display, function(item){
                children_promises.push(self.displayReconciliation(item, animate_entrance));
            });

            // show or hide done message
            var reconciliations_left = (self.partners_data.show ? self.partners_data.num_total - self.partners_data.num_done : 0) + (self.accounts_data.show ? self.accounts_data.num_total - self.accounts_data.num_done : 0);
            if (reconciliations_left === 0 && self.$(".done_message").length === 0)
                self.showDoneMessage();
            if (reconciliations_left !== 0 && self.$(".done_message").length !== 0)
                self.hideDoneMessage();

            return $.when.apply($, children_promises);
        },

        updateProgressbar: function() {
            var done = (this.partners_data.show ? this.partners_data.num_done : 0) + (this.accounts_data.show ? this.accounts_data.num_done : 0);
            var total = (this.partners_data.show ? this.partners_data.num_total : 0) + (this.accounts_data.show ? this.accounts_data.num_total : 0);
            var prog_bar = this.$(".progress .progress-bar");
            prog_bar.attr("aria-valuenow", done);
            prog_bar.css("width", (done/total*100)+"%");
            this.$(".progress .progress-text .valuenow").text(done);
            this.$(".progress .progress-text .valuemax").text(total);
        },

        showDoneMessage: function() {
            this.$(".oe_form_sheet").append(QWeb.render("manual_reconciliation_done_message"));
            var container = $("<div style='overflow: hidden;' />");
            this.$(".done_message").wrap(container).css("opacity", 0).css("position", "relative").css("left", "-50%");
            this.$(".done_message").animate({opacity: 1, left: 0}, this.aestetic_animation_speed*2, "easeOutCubic");
            this.$(".done_message").animate({opacity: 1}, this.aestetic_animation_speed*3, "easeOutCubic");
        },

        hideDoneMessage: function() {
            this.$(".done_message").remove();
        },

        prepareReconciliationData: function(data) {
            data.displayed = false;
        },

        childValidated: function(reconciliation_type) {
            if (reconciliation_type === "partner")
                this.partners_data.num_done++;
            else if (reconciliation_type === "account")
                this.accounts_data.num_done++;
            this.updateProgress();
        },
    });
    
    instance.web.account.manualReconciliationLine = instance.web.account.abstractReconciliationLine.extend({
        className: instance.web.account.abstractReconciliationLine.prototype.className + ' oe_manual_reconciliation_line',

        events: _.defaults({
            "click .accounting_view thead": "headerClickHandler",
            "click .line_open_balance": "lineOpenBalanceClickHandler",
            "click .button_reconcile": "buttonReconcileClickHandler",
        }, instance.web.account.abstractReconciliationLine.prototype.events),
    
        init: function(parent, context) {
            this._super(parent, context);
            this.working_on_a_given_item = this.getParent().working_on_a_given_item;
            this.template_prefix = this.getParent().template_prefix;
            this.model_aml = this.getParent().model_aml;
            this.data = context.data;
            this.currency_id = context.data.currency_id;
            this.presets = this.getParent().presets;
            // Make sure a partial reconciliation will appear only once by excluding siblings of a selected partially reconciled move line
            this.excluded_move_lines_ids = [];
        },

        render: function() {
            var self = this;
            var presets_array = [];
            for (var id in self.presets)
                if (self.presets.hasOwnProperty(id))
                    presets_array.push(self.presets[id]);
            self.$el.prepend(QWeb.render("manual_reconciliation_line", {
                data: self.data,
                presets: presets_array,
            }));
            self.$(".match").slideUp(0);
            self.$(".create").slideUp(0);
            self.createFormWidgets();
            self.updateBalance();
            self.updateAccountingViewMatchedLines();
            self.finishedLoadingMoveLines = $.Deferred();
            self.set("mode", "match");
            return self.finishedLoadingMoveLines;
        },

        islineCreatedBeingEditedValid: function() {
            return this._super() && this.get("line_created_being_edited")[0].journal_id;
        },

        selectMoveLine: function(mv_line) {
            var self = this;
            var line = self._super(mv_line);
            if (!line) return;

            $(mv_line).attr('data-selected','true');
            self.set("mv_lines_selected", self.get("mv_lines_selected").concat(line));
        },

        mvLinesChanged: function() {
            var self = this;
            self._super();

            // If we're not reconciling a specific account/partner, we're displaying all remaining
            // move lines and there's not at least a debit and a credit, consider that the reconciliation is done
            if (!self.working_on_a_given_item && self.get("pager_index") === 0 && !self.can_fetch_more_move_lines && self.get("mv_lines_selected").length === 0 && self.filter === '') {
                var mkay, mmkay = false;
                var lines = self.get("mv_lines").concat(self.mv_lines_deselected);
                for (var i=0; i<lines.length; i++) {
                    if (lines[i].credit !== 0) mkay = true;
                    if (lines[i].debit !== 0) mmkay = true;
                    if (mkay && mmkay) break;
                }
                if (!(mkay && mmkay)) {
                    self.markAsReconciled();
                }
            }

            // Make sure to display only one "summary line" per partial reconciliation
            _.each(self.get("mv_lines"), function(line) {
                for (var i=0; i<line.partial_reconciliation_siblings.length; i++)
                    if (self.excluded_move_lines_ids.indexOf(line.partial_reconciliation_siblings[i].id) === -1)
                        self.excluded_move_lines_ids.push(line.partial_reconciliation_siblings[i].id);
            });
        },

        headerClickHandler: function() {
            if (this.get("mode") !== "match")
                this.set("mode", "match");
        },

        buttonReconcileClickHandler: function() {
            if (this.persist_action === "reconcile")
                this.processReconciliation();
            else if (this.persist_action === "mark_as_reconciled")
                this.markAsReconciled();
        },

        // Make sure there's at least one (empty) line in the accounting view so the T appears
        // Should be done in CSS with sth like elt:empty:before { content: "HTML"; }
        // Unfortunately, "Generated content does not alter the document tree"
        preventAccountingViewCollapse: function() {
            if (this.$(".tbody_matched_lines > *").length + this.$(".tbody_created_lines > *").length === 0)
                this.$(".tbody_matched_lines").append('<tr class="filler_line"><td class="cell_action"></td><td class="cell_due_date"></td><td class="cell_label"></td><td class="cell_debit"></td><td class="cell_credit"></td><td class="cell_info_popover"></td></tr>');
        },

        updateAccountingViewMatchedLines: function() {
            this._super();
            this.preventAccountingViewCollapse();
        },

        updateAccountingViewCreatedLines: function() {
            this._super();
            this.preventAccountingViewCollapse();
        },

        balanceChanged: function() {
            var self = this;
            var balance = self.get("balance");

            self.$(".button_reconcile").removeClass("oe_highlight");
            self.$(".button_reconcile").text(_t("Reconcile"));
            self.persist_action = "reconcile";
            if (self.get("mv_lines_selected").length < 2) {
                self.$(".button_reconcile").text(_t("Done"));
                self.persist_action = "mark_as_reconciled";
            } else if (Math.abs(balance).toFixed(3) === "0.000") {
                self.$(".button_reconcile").addClass("oe_highlight");
            }

            self.$(".tbody_open_balance").empty();
            if (Math.abs(balance).toFixed(3) !== "0.000" && self.get("mv_lines_selected").length > 1) {
                var debit = (balance > 0 ? self.formatCurrencies(balance, self.currency_id) : "");
                var credit = (balance < 0 ? self.formatCurrencies(-1*balance, self.currency_id) : "");
                var $line = $(QWeb.render("manual_reconciliation_line_open_balance", {
                    debit: debit,
                    credit: credit,
                    label: _t("Create writeoff")
                }));
                self.$(".tbody_open_balance").append($line);
            }
        },


        /* Model */

        updateMatchesGetMvLines: function(excluded_ids, offset, limit, callback) {
            var self = this;
            excluded_ids = excluded_ids.concat(self.excluded_move_lines_ids);
            return self.model_aml
                .call("get_move_lines_for_manual_reconciliation", [self.data.account_id, self.data.partner_id || undefined, excluded_ids, self.filter, offset, limit])
                .then(function (lines) {
                    _.each(lines, function(line) { self.decorateMoveLine(line) }, self);
                    callback.call(self, lines);
                });
        },

        prepareCreatedMoveLineForPersisting: function(line) {
            var dict = this._super(line);
            dict['journal_id'] = line.journal_id;
            return dict;
        },

        processReconciliation: function() {
            var self = this;
            if (! self.is_consistent) return $.Deferred().rejectWith({reason: "Reconciliation widget is not in a consistent state."});
            var mv_line_ids = _.collect(self.get("mv_lines_selected"), function(o){ return o.id });
            var new_mv_line_dicts = _.collect(self.getCreatedLines(), function(o){ return self.prepareCreatedMoveLineForPersisting(o) });
            return self.model_aml.call("process_reconciliation", [mv_line_ids, new_mv_line_dicts]).then(function() {
                self.initializeCreateForm();
                self.set("mv_lines_selected", []);
                self.set("lines_created", []);
                self.set("mode", "match");
                self.balanceChanged();
            });
        },

        markAsReconciled: function() {
            var self = this;
            if (! self.is_consistent) return $.Deferred().rejectWith({reason: "Reconciliation widget is not in a consistent state."});
            var type = this.data.reconciliation_type;
            var id = (type === "partner" ? this.data.partner_id : this.data.account_id);
            var model = (type === "partner" ? this.getParent().model_partner : this.getParent().model_account);
            model.call("mark_as_reconciled", [[id]]).then(function() {
                self.bowOut(self.animation_speed, true);
            });
        },

        getPostMortemProcess: function() {
            var reconciliation_type = this.data.reconciliation_type;
            var parent = this.getParent();
            return function() {
                if (parent)
                    parent.childValidated(reconciliation_type);
            };
        },
    });
};
