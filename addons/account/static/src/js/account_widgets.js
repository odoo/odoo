openerp.account = function (instance) {
    openerp.account.quickadd(instance);
    var _t = instance.web._t,
        _lt = instance.web._lt;
    var QWeb = instance.web.qweb;
    
    instance.web.account = instance.web.account || {};
    
    instance.web.client_actions.add('bank_statement_reconciliation_view', 'instance.web.account.bankStatementReconciliation');
    instance.web.account.bankStatementReconciliation = instance.web.Widget.extend({
        className: 'oe_bank_statement_reconciliation',
    
        init: function(parent, context) {
            this._super(parent);
            this.max_reconciliations_displayed = 10;
            this.statement_id = context.context.statement_id;
            this.title = context.context.title || _t("Reconciliation");
            this.st_lines = [];
            this.last_displayed_reconciliation_index = undefined; // Flow control
            this.reconciled_lines = 0; // idem
            this.already_reconciled_lines = 0; // Number of lines of the statement which were already reconciled
            this.model_bank_statement = new instance.web.Model("account.bank.statement");
            this.model_bank_statement_line = new instance.web.Model("account.bank.statement.line");
            this.reconciliation_menu_id = false; // Used to update the needaction badge
            this.formatCurrency; // Method that formats the currency ; loaded from the server
    
            // Only for statistical purposes
            this.lines_reconciled_with_ctrl_enter = 0;
            this.time_widget_loaded = Date.now();
    
            // Stuff used by the children bankStatementReconciliationLine
            this.max_move_lines_displayed = 5;
            this.animation_speed = 100; // "Blocking" animations
            this.aestetic_animation_speed = 300; // eye candy
            this.map_tax_id_amount = {};
            this.presets = {};
            // We'll need to get the code of an account selected in a many2one (whose value is the id)
            this.map_account_id_code = {};
            // The same move line cannot be selected for multiple resolutions
            this.excluded_move_lines_ids = [];
            // Description of the fields to initialize in the "create new line" form
            // NB : for presets to work correctly, a field id must be the same string as a preset field
            this.create_form_fields = {
                account_id: {
                    id: "account_id",
                    index: 0,
                    corresponding_property: "account_id", // a account.move field name
                    label: _t("Account"),
                    required: true,
                    tabindex: 10,
                    constructor: instance.web.form.FieldMany2One,
                    field_properties: {
                        relation: "account.account",
                        string: _t("Account"),
                        type: "many2one",
                        domain: [['type','!=','view']],
                    },
                },
                label: {
                    id: "label",
                    index: 1,
                    corresponding_property: "label",
                    label: _t("Label"),
                    required: true,
                    tabindex: 11,
                    constructor: instance.web.form.FieldChar,
                    field_properties: {
                        string: _t("Label"),
                        type: "char",
                    },
                },
                tax_id: {
                    id: "tax_id",
                    index: 2,
                    corresponding_property: "tax_id",
                    label: _t("Tax"),
                    required: false,
                    tabindex: 12,
                    constructor: instance.web.form.FieldMany2One,
                    field_properties: {
                        relation: "account.tax",
                        string: _t("Tax"),
                        type: "many2one",
                    },
                },
                amount: {
                    id: "amount",
                    index: 3,
                    corresponding_property: "amount",
                    label: _t("Amount"),
                    required: true,
                    tabindex: 13,
                    constructor: instance.web.form.FieldFloat,
                    field_properties: {
                        string: _t("Amount"),
                        type: "float",
                    },
                },
                analytic_account_id: {
                    id: "analytic_account_id",
                    index: 4,
                    corresponding_property: "analytic_account_id",
                    label: _t("Analytic Acc."),
                    required: false,
                    tabindex: 14,
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
            this._super();
            var self = this;
    
            // Inject variable styles
            var style = document.createElement("style");
            style.appendChild(document.createTextNode(""));
            document.head.appendChild(style);
            var css_selector = ".oe_bank_statement_reconciliation_line .toggle_match, .oe_bank_statement_reconciliation_line .toggle_create,  .oe_bank_statement_reconciliation_line .initial_line > td";
            if(style.sheet.insertRule) {
                style.sheet.insertRule(css_selector + " { -webkit-transition-duration: "+self.aestetic_animation_speed+"ms; }", 0);
                style.sheet.insertRule(css_selector + " { -moz-transition-duration: "+self.aestetic_animation_speed+"ms; }", 0);
                style.sheet.insertRule(css_selector + " { -ms-transition-duration: "+self.aestetic_animation_speed+"ms; }", 0);
                style.sheet.insertRule(css_selector + " { -o-transition-duration: "+self.aestetic_animation_speed+"ms; }", 0);
                style.sheet.insertRule(css_selector + " { transition-duration: "+self.aestetic_animation_speed+"ms; }", 0);
            } else {
                style.sheet.addRule(css_selector, "-webkit-transition-duration: "+self.aestetic_animation_speed+"ms;");
                style.sheet.addRule(css_selector, "-moz-transition-duration: "+self.aestetic_animation_speed+"ms;");
                style.sheet.addRule(css_selector, "-ms-transition-duration: "+self.aestetic_animation_speed+"ms;");
                style.sheet.addRule(css_selector, "-o-transition-duration: "+self.aestetic_animation_speed+"ms;");
                style.sheet.addRule(css_selector, "-webkit-transition-duration: "+self.aestetic_animation_speed+"ms;");
            }
    
            // Retreive statement infos and reconciliation data from the model
            var lines_filter = [['journal_entry_id', '=', false]];
            var deferred_promises = [];
    
            if (self.statement_id) {
                lines_filter.push(['statement_id', '=', self.statement_id]);
                deferred_promises.push(self.model_bank_statement
                    .query(["name"])
                    .filter([['id', '=', self.statement_id]])
                    .first()
                    .then(function(title){
                        self.title = title.name;
                    })
                );
                deferred_promises.push(self.model_bank_statement
                    .call("number_of_lines_reconciled", [self.statement_id])
                    .then(function(num) {
                        self.already_reconciled_lines = num;
                    })
                );
            }
    
            deferred_promises.push(new instance.web.Model("account.statement.operation.template")
                .query(['id','name','account_id','label','amount_type','amount','tax_id','analytic_account_id'])
                .all().then(function (data) {
                    _(data).each(function(preset){
                        self.presets[preset.id] = preset;
                    });
                })
            );

            deferred_promises.push(self.model_bank_statement
                .call("get_format_currency_js_function", [self.statement_id])
                .then(function(data){
                    self.formatCurrency = new Function("amount, currency_id", data);
                })
            );
    
            deferred_promises.push(self.model_bank_statement_line
                .query(['id'])
                .filter(lines_filter)
                .order_by('id')
                .all().then(function (data) {
                    self.st_lines = _(data).map(function(o){ return o.id });
                })
            );
    
            // When queries are done, render template and reconciliation lines
            return $.when.apply($, deferred_promises).then(function(){
    
                // If there is no statement line to reconcile, stop here
                if (self.st_lines.length === 0) {
                    self.$el.prepend(QWeb.render("bank_statement_nothing_to_reconcile"));
                    return;
                }
    
                // Create a dict account id -> account code for display facilities
                new instance.web.Model("account.account")
                    .query(['id', 'code'])
                    .all().then(function(data) {
                        _.each(data, function(o) { self.map_account_id_code[o.id] = o.code });
                    });
    
                // Create a dict tax id -> amount
                new instance.web.Model("account.tax")
                    .query(['id', 'amount'])
                    .all().then(function(data) {
                        _.each(data, function(o) { self.map_tax_id_amount[o.id] = o.amount });
                    });
    
                new instance.web.Model("ir.model.data")
                    .call("xmlid_to_res_id", ["account.menu_bank_reconcile_bank_statements"])
                    .then(function(data) {
                        self.reconciliation_menu_id = data;
                        self.doReloadMenuReconciliation();
                    });
    
                // Bind keyboard events TODO : méthode standard ?
                $("body").on("keypress", function (e) {
                    self.keyboardShortcutsHandler(e);
                });
    
                // Render and display
                self.$el.prepend(QWeb.render("bank_statement_reconciliation", {title: self.title, total_lines: self.already_reconciled_lines+self.st_lines.length}));
                self.updateProgressbar();
                var reconciliations_to_show = self.st_lines.slice(0, self.max_reconciliations_displayed);
                self.last_displayed_reconciliation_index = reconciliations_to_show.length;
                self.$(".reconciliation_lines_container").css("opacity", 0);
    
                // Display the reconciliations
                return self.model_bank_statement_line
                    .call("get_data_for_reconciliations", [reconciliations_to_show])
                    .then(function (data) {
                        var child_promises = [];
                        _.each(reconciliations_to_show, function(st_line_id){
                            var datum = data.shift();
                            child_promises.push(self.displayReconciliation(st_line_id, 'inactive', false, true, datum.st_line, datum.reconciliation_proposition));
                        });
                        $.when.apply($, child_promises).then(function(){
                            self.getChildren()[0].set("mode", "match");
                            self.$(".reconciliation_lines_container").animate({opacity: 1}, self.aestetic_animation_speed);
                        });
                    });
            });
        },
    
        keyboardShortcutsHandler: function(e) {
            var self = this;
            if ((e.which === 13 || e.which === 10) && (e.ctrlKey || e.metaKey)) {
                $.each(self.getChildren(), function(i, o){
                    if (o.is_valid && o.persistAndDestroy()) {
                        self.lines_reconciled_with_ctrl_enter++;
                    }
                });
            }
        },

        excludeMoveLines: function(line_ids) {
            var self = this;
            _.each(line_ids, function(line_id){
                line_id = parseInt(line_id);
                if (self.excluded_move_lines_ids.indexOf(line_id) === -1) {
                    self.excluded_move_lines_ids.push(line_id);
                }
            });
            //update all children view
            _.each(self.getChildren(), function(child){
                child.render();
            });
        },

        unexcludeMoveLines: function(line_ids) {
            var self = this;
            var index = -1;
            _.each(line_ids, function(line_id){
                line_id = parseInt(line_id);
                index = self.excluded_move_lines_ids.indexOf(line_id);
                if (index > -1) {
                    self.excluded_move_lines_ids.splice(index,1);
                }
            });
            //update all children view
            _.each(self.getChildren(), function(child){
                child.render();
            });
        },
    
        displayReconciliation: function(st_line_id, mode, animate_entrance, initial_data_provided, st_line, reconciliation_proposition) {
            var self = this;
            animate_entrance = (animate_entrance === undefined ? true : animate_entrance);
            initial_data_provided = (initial_data_provided === undefined ? false : initial_data_provided);
    
            var context = {
                st_line_id: st_line_id,
                mode: mode,
                animate_entrance: animate_entrance,
                initial_data_provided: initial_data_provided,
                st_line: initial_data_provided ? st_line : undefined,
                reconciliation_proposition: initial_data_provided ? reconciliation_proposition : undefined,
            };
            var widget = new instance.web.account.bankStatementReconciliationLine(self, context);
            return widget.appendTo(self.$(".reconciliation_lines_container"));
        },
    
        childValidated: function(child) {
            var self = this;
    
            self.reconciled_lines++;
            self.updateProgressbar();
            self.doReloadMenuReconciliation();
    
            // Display new line if there are left
            if (self.last_displayed_reconciliation_index < self.st_lines.length) {
                self.displayReconciliation(self.st_lines[self.last_displayed_reconciliation_index++], 'inactive');
            }
            // Put the first line in match mode
            if (self.reconciled_lines !== self.st_lines.length) {
                var first_child = self.getChildren()[0];
                if (first_child.get("mode") === "inactive") {
                    first_child.set("mode", "match");
                }
            }
            // Congratulate the user if the work is done
            if (self.reconciled_lines === self.st_lines.length) {
                self.displayDoneMessage();
            }
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
                has_statement_id: self.statement_id !== undefined,
            }));
    
            // Animate it
            var container = $("<div style='overflow: hidden;' />");
            self.$(".done_message").wrap(container).css("opacity", 0).css("position", "relative").css("left", "-50%");
            self.$(".done_message").animate({opacity: 1, left: 0}, self.aestetic_animation_speed*2, "easeOutCubic");
            self.$(".done_message").animate({opacity: 1}, self.aestetic_animation_speed*3, "easeOutCubic");
    
            // Make it interactive
            self.$(".achievement").popover({'placement': 'top', 'container': self.el, 'trigger': 'hover'});
            
            self.$(".button_back_to_statement").click(function() {
                self.do_action({
                    type: 'ir.actions.client',
                    tag: 'history_back',
                });
            });

            if (self.$(".button_close_statement").length !== 0) {
                self.$(".button_close_statement").hide();
                self.model_bank_statement
                    .query(["balance_end_real", "balance_end"])
                    .filter([['id', '=', self.statement_id]])
                    .first()
                    .then(function(data){
                        if (data.balance_end_real === data.balance_end) {
                            self.$(".button_close_statement").show();
                            self.$(".button_close_statement").click(function() {
                                self.$(".button_close_statement").attr("disabled", "disabled");
                                self.model_bank_statement
                                    .call("button_confirm_bank", [[self.statement_id]])
                                    .then(function () {
                                        self.do_action({
                                            type: 'ir.actions.client',
                                            tag: 'history_back',
                                        });
                                    }, function() {
                                        self.$(".button_close_statement").removeAttr("disabled");
                                    });
                            });
                        }
                    });
            }
        },
    
        updateProgressbar: function() {
            var self = this;
            var done = self.already_reconciled_lines + self.reconciled_lines;
            var total = self.already_reconciled_lines + self.st_lines.length;
            var prog_bar = self.$(".progress .progress-bar");
            prog_bar.attr("aria-valuenow", done);
            prog_bar.css("width", (done/total*100)+"%");
            self.$(".progress .progress-text .valuenow").text(done);
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
    });
    
    instance.web.account.bankStatementReconciliationLine = instance.web.Widget.extend({
        className: 'oe_bank_statement_reconciliation_line',
    
        events: {
            "click .partner_name": "partnerNameClickHandler",
            "click .button_ok": "persistAndDestroy",
            "click .mv_line": "moveLineClickHandler",
            "click .initial_line": "initialLineClickHandler",
            "click .line_open_balance": "lineOpenBalanceClickHandler",
            "click .pager_control_left:not(.disabled)": "pagerControlLeftHandler",
            "click .pager_control_right:not(.disabled)": "pagerControlRightHandler",
            "keyup .filter": "filterHandler",
            "click .line_info_button": function(e){e.stopPropagation()}, // small usability hack
            "click .add_line": "addLineBeingEdited",
            "click .preset": "presetClickHandler",
            "click .do_partial_reconcile_button": "doPartialReconcileButtonClickHandler",
            "click .undo_partial_reconcile_button": "undoPartialReconcileButtonClickHandler",
        },
    
        init: function(parent, context) {
            this._super(parent);
    
            if (context.initial_data_provided) {
                // Process data
                _(context.reconciliation_proposition).each(this.decorateMoveLine.bind(this));
                this.set("mv_lines_selected", context.reconciliation_proposition);
                this.st_line = context.st_line;
                this.partner_id = context.st_line.partner_id;
                this.decorateStatementLine(this.st_line);
    
                // Exclude selected move lines
                var selected_line_ids = _(context.reconciliation_proposition).map(function(o){ return o.id });
                this.getParent().excludeMoveLines(selected_line_ids);
            } else {
                this.set("mv_lines_selected", []);
                this.st_line = undefined;
                this.partner_id = undefined;
            }
    
            this.context = context;
            this.st_line_id = context.st_line_id;
            this.max_move_lines_displayed = this.getParent().max_move_lines_displayed;
            this.animation_speed = this.getParent().animation_speed;
            this.aestetic_animation_speed = this.getParent().aestetic_animation_speed;
            this.model_bank_statement_line = new instance.web.Model("account.bank.statement.line");
            this.model_res_users = new instance.web.Model("res.users");
            this.model_tax = new instance.web.Model("account.tax");
            this.map_account_id_code = this.getParent().map_account_id_code;
            this.map_tax_id_amount = this.getParent().map_tax_id_amount;
            this.formatCurrency = this.getParent().formatCurrency;
            this.presets = this.getParent().presets;
            this.is_valid = true;
            this.is_consistent = true; // Used to prevent bad server requests
            this.filter = "";
    
            this.set("balance", undefined); // Debit is +, credit is -
            this.on("change:balance", this, this.balanceChanged);
            this.set("mode", undefined);
            this.on("change:mode", this, this.modeChanged);
            this.set("pager_index", 0);
            this.on("change:pager_index", this, this.pagerChanged);
            // NB : mv_lines represent the counterpart that will be created to reconcile existing move lines, so debit and credit are inverted
            this.set("mv_lines", []);
            this.on("change:mv_lines", this, this.mvLinesChanged);
            this.on("change:mv_lines_selected", this, this.mvLinesSelectedChanged);
            this.set("lines_created", []);
            this.set("line_created_being_edited", [{'id': 0}]);
            this.on("change:lines_created", this, this.createdLinesChanged);
            this.on("change:line_created_being_edited", this, this.createdLinesChanged);

            //all lines associated to current reconciliation
            this.propositions_lines = undefined;
        },
    
        start: function() {
            var self = this;
            return self._super().then(function() {
                // no animation while loading
                self.animation_speed = 0;
                self.aestetic_animation_speed = 0;
    
                self.is_consistent = false;
                if (self.context.animate_entrance) self.$el.css("opacity", "0");
    
                // Fetch data
                var deferred_fetch_data = new $.Deferred();
                if (! self.context.initial_data_provided) {
                    // Load statement line
                    self.model_bank_statement_line
                        .call("get_statement_line_for_reconciliation", [self.st_line_id])
                        .then(function (data) {
                            self.st_line = data;
                            self.decorateStatementLine(self.st_line);
                            self.partner_id = data.partner_id;
                            $.when(self.loadReconciliationProposition()).then(function(){
                                deferred_fetch_data.resolve();
                            });
                        });
                } else {
                    deferred_fetch_data.resolve();
                }
    
                // Display the widget
                return $.when(deferred_fetch_data).then(function(){
                    //load all lines that can be usefull for counterparts
                    var deferred_total_move_lines_num = self.model_bank_statement_line
                        .call("get_move_lines_counterparts_id", [self.st_line.id, []])
                        .then(function(lines){
                            _(lines).each(self.decorateMoveLine.bind(self));
                            self.propositions_lines = lines;
                        });
                    return deferred_total_move_lines_num;
                }).then(function(){
                    // Render template
                    var presets_array = [];
                    for (var id in self.presets)
                        if (self.presets.hasOwnProperty(id))
                            presets_array.push(self.presets[id]);
                    self.$el.prepend(QWeb.render("bank_statement_reconciliation_line", {line: self.st_line, mode: self.context.mode, presets: presets_array}));
    
                    // Stuff that require the template to be rendered
                    self.$(".match").slideUp(0);
                    self.$(".create").slideUp(0);
                    if (self.st_line.no_match) self.$el.addClass("no_match");
                    if (self.context.mode !== "match") self.render();
                    self.bindPopoverTo(self.$(".line_info_button"));
                    self.createFormWidgets();
                    // Special case hack : no identified partner
                    if (self.st_line.has_no_partner) {
                        self.$el.css("opacity", "0");
                        self.updateBalance();
                        self.$(".change_partner_container").show(0);
                        self.change_partner_field.$el.find("input").attr("placeholder", _t("Select Partner"));
                        self.$(".match").slideUp(0);
                        self.$el.addClass("no_partner");
                        self.set("mode", self.context.mode);
                        self.animation_speed = self.getParent().animation_speed;
                        self.aestetic_animation_speed = self.getParent().aestetic_animation_speed;
                        self.$el.animate({opacity: 1}, self.aestetic_animation_speed);
                        self.is_consistent = true;
                        return;
                    }
    
                    // TODO : the .on handler's returned deferred is lost
                    return $.when(self.set("mode", self.context.mode)).then(function(){
                        self.is_consistent = true;
    
                        // Make sure the display is OK
                        self.balanceChanged();
                        self.createdLinesChanged();
                        self.updateAccountingViewMatchedLines();
    
                        // Make an entrance
                        self.animation_speed = self.getParent().animation_speed;
                        self.aestetic_animation_speed = self.getParent().aestetic_animation_speed;
                        if (self.context.animate_entrance) return self.$el.animate({opacity: 1}, self.aestetic_animation_speed);
                    });
                });
            });
        },
    
        restart: function(mode) {
            var self = this;
            mode = (mode === undefined ? 'inactive' : mode);
            self.$el.css("height", self.$el.outerHeight());
            // Destroy everything
            _.each(self.getChildren(), function(o){ o.destroy() });
            self.is_consistent = false;
            return $.when(self.$el.animate({opacity: 0}, self.animation_speed)).then(function() {
                self.getParent().unexcludeMoveLines(_.map(self.get("mv_lines_selected"), function(o){ return o.id }));
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
    
            var field_manager = new instance.web.FormView (
                this, dataset, false, {
                    initial_mode: 'edit',
                    disable_autofocus: false,
                    $buttons: $(),
                    $pager: $()
            });
    
            field_manager.load_form(dataset);
    
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
            field_manager.fields_view.fields = {};
            for (var i=0; i<create_form_fields_arr.length; i++) {
                field_manager.fields_view.fields[create_form_fields_arr[i].id] = _.extend(new Default_field(), create_form_fields_arr[i].field_properties);
            }
            field_manager.fields_view.fields["change_partner"] = _.extend(new Default_field(), {
                relation: "res.partner",
                string: _t("Partner"),
                type: "many2one",
                domain: [['parent_id','=',false], '|', ['customer','=',true], ['supplier','=',true]],
            });
    
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
                var field = new field_data.constructor(field_manager, node);
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
    
            // generate the change partner "form"
            var change_partner_node = new Default_node("change_partner"); change_partner_node.attrs.modifiers = "";
            self.change_partner_field = new instance.web.form.FieldMany2One(field_manager, change_partner_node);
            self.change_partner_field.appendTo(self.$(".change_partner_container"));
            self.change_partner_field.on("change:value", self.change_partner_field, function() {
                self.changePartner(this.get_value());
            });
    
            field_manager.do_show();
        },
    
        /** Utils */
    
        /* TODO : if t-call for attr, all in qweb */
        decorateStatementLine: function(line){
            line.q_popover = QWeb.render("bank_statement_reconciliation_line_details", {line: line});
        },
    
        // adds fields, prefixed with q_, to the move line for qweb rendering
        decorateMoveLine: function(line){
            line.partial_reconcile = false;
            line.propose_partial_reconcile = false;
            line.q_due_date = (line.date_maturity === false ? line.date : line.date_maturity);
            line.q_amount = (line.debit !== 0 ? "- "+line.q_debit : "") + (line.credit !== 0 ? line.q_credit : "");
            line.q_popover = QWeb.render("bank_statement_reconciliation_move_line_details", {line: line});
            line.q_label = line.name;
            if (line.has_no_partner){
                line.q_label = line.partner_name + ': ' +line.q_label;
            }
    
            // WARNING : pretty much of a ugly hack
            // The value of account_move.ref is either the move's communication or it's name without the slashes
            if (line.ref && line.ref !== line.name.replace(/\//g,''))
                line.q_label += " : " + line.ref;
        },
    
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
            var line = _.find(self.propositions_lines, function(o){ return o.id == line_id});
            $(mv_line).attr('data-selected','true');
            self.getParent().excludeMoveLines([line_id]);
            self.set("mv_lines_selected", self.get("mv_lines_selected").concat(line));
        },

        deselectMoveLine: function(mv_line) {
            var self = this;
            var line_id = mv_line.dataset.lineid;
            var line = _.find(self.propositions_lines, function(o){ return o.id == line_id});
            $(mv_line).attr('data-selected','false');
            self.getParent().unexcludeMoveLines([line_id]);
            self.set("mv_lines_selected",_.filter(self.get("mv_lines_selected"), function(o) { return o.id != line_id }));
        },
    
        /** Matches pagination */
    
        pagerControlLeftHandler: function() {
            var self = this;
            self.set("pager_index", self.get("pager_index")-1 );
        },
    
        pagerControlRightHandler: function() {
            var self = this;
            var new_index = self.get("pager_index")+1;
            self.set("pager_index", new_index );
        },
    
        filterHandler: function() {
            var self = this;
            self.set("pager_index", 0);
            self.filter = self.$(".filter").val();
            self.render();
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
            self.initializeCreateForm();
            var preset = self.presets[e.currentTarget.dataset.presetid];
            for (var key in preset) {
                if (! preset.hasOwnProperty(key) || key === "amount") continue;
                if (self.hasOwnProperty(key+"_field"))
                    self[key+"_field"].set_value(preset[key]);
            }
            var sign = self.amount_field.get_value() < 0 ? -1 : 1;
            if (preset.amount && self.amount_field) {
                if (preset.amount_type === "fixed")
                    self.amount_field.set_value(sign * preset.amount);
                else if (preset.amount_type === "percentage_of_total")
                    self.amount_field.set_value(sign * self.st_line.amount * preset.amount / 100);
                else if (preset.amount_type === "percentage_of_balance") {
                    self.amount_field.set_value(0);
                    self.updateBalance();
                    self.amount_field.set_value(sign * Math.abs(self.get("balance")) * preset.amount / 100);
                }
            }
        },
    
    
        /** Display */
    
        initialLineClickHandler: function() {
            var self = this;
            if (self.get("mode") === "match") {
                self.set("mode", "inactive");
            } else {
                self.set("mode", "match");
            }
        },
    
        lineOpenBalanceClickHandler: function() {
            var self = this;
            if (self.get("mode") === "create") {
                self.addLineBeingEdited();
                self.set("mode", "match");
            } else {
                self.set("mode", "create");
            }
        },
    
        partnerNameClickHandler: function() {
            var self = this;
            self.$(".partner_name").hide();
            self.change_partner_field.$el.find("input").attr("placeholder", self.st_line.partner_name);
            self.$(".change_partner_container").show();
        },
    
    
        /** Views updating */
    
        updateAccountingViewMatchedLines: function() {
            var self = this;
            $.each(self.$(".tbody_matched_lines .bootstrap_popover"), function(){ $(this).popover('destroy') });
            self.$(".tbody_matched_lines").empty();
    
            _(self.get("mv_lines_selected")).each(function(line){
                var $line = $(QWeb.render("bank_statement_reconciliation_move_line", {line: line, selected: true}));
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
    
            _(self.getCreatedLines()).each(function(line){
                var $line = $(QWeb.render("bank_statement_reconciliation_created_line", {line: line}));
                $line.find(".line_remove_button").click(function(){ self.removeLine($(this).closest(".created_line")) });
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

            var visible = 0
            _(self.get("mv_lines")).each(function(line){
                if (visible >= slice_start && visible < slice_end) {
                    var $line = $(QWeb.render("bank_statement_reconciliation_move_line", {line: line, selected: false}));
                    self.bindPopoverTo($line.find(".line_info_button"));
                    table.append($line);
                    nothing_displayed = false;
                }
                visible = visible + 1;
            });
            if (nothing_displayed)
                table.append(QWeb.render("filter_no_match", {filter_str: self.filter}));
        },
    
        updatePagerControls: function() {
            var self = this;
            if (self.get("pager_index") === 0)
                self.$(".pager_control_left").addClass("disabled");
            else
                self.$(".pager_control_left").removeClass("disabled");
            if (self.get('mv_lines').length <= ((self.get("pager_index")+1) * self.max_move_lines_displayed))
                self.$(".pager_control_right").addClass("disabled");
            else
                self.$(".pager_control_right").removeClass("disabled");
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
                    var debit = (balance > 0 ? self.formatCurrency(balance, self.st_line.currency_id) : "");
                    var credit = (balance < 0 ? self.formatCurrency(-1*balance, self.st_line.currency_id) : "");
                    var $line = $(QWeb.render("bank_statement_reconciliation_line_open_balance", {debit: debit, credit: credit, account_code: self.map_account_id_code[self.st_line.open_balance_account_id]}));
                    $line.find('.js_open_balance')[0].innerHTML = "Choose counterpart";
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
                var debit = (balance > 0 ? self.formatCurrency(balance, self.st_line.currency_id) : "");
                var credit = (balance < 0 ? self.formatCurrency(-1*balance, self.st_line.currency_id) : "");
                var $line = $(QWeb.render("bank_statement_reconciliation_line_open_balance", {debit: debit, credit: credit, account_code: self.map_account_id_code[self.st_line.open_balance_account_id]}));
                self.$(".tbody_open_balance").append($line);
            }
        },
    
        modeChanged: function() {
            var self = this;
    
            self.$(".action_pane.active").removeClass("active");
    
            // Special case hack : if no_partner and mode == inactive
            if (self.st_line.has_no_partner) {
                if (self.get("mode") === "inactive") {
                    self.$(".match").slideUp(self.animation_speed);
                    self.$(".create").slideUp(self.animation_speed);
                    self.$(".toggle_match").removeClass("visible_toggle");
                    self.el.dataset.mode = "inactive";
                    return;
                } 
            }
    
            if (self.get("mode") === "inactive") {
                self.$(".match").slideUp(self.animation_speed);
                self.$(".create").slideUp(self.animation_speed);
                self.el.dataset.mode = "inactive";
    
            } else if (self.get("mode") === "match") {
                return $.when(self.render()).then(function() {
                    if (self.$el.hasClass("no_match")) {
                        self.set("mode", "inactive");
                        return;
                    }
                    self.$(".match").slideDown(self.animation_speed);
                    self.$(".create").slideUp(self.animation_speed);
                    self.el.dataset.mode = "match";
                });
    
            } else if (self.get("mode") === "create") {
                self.initializeCreateForm();
                self.$(".match").slideUp(self.animation_speed);
                self.$(".create").slideDown(self.animation_speed);
                self.el.dataset.mode = "create";
            }
        },
    
        pagerChanged: function() {
            var self = this;
            self.render();
        },
    
        mvLinesChanged: function() {
            var self = this;
    
            // If there is no match to display, disable match view and pass in mode inactive
            if (self.get("mv_lines").length === 0 && self.filter === "") {
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
    
            var added_lines_ids = _.map(_.difference(val.newValue, val.oldValue), function(o){ return o.id });
            var removed_lines_ids = _.map(_.difference(val.oldValue, val.newValue), function(o){ return o.id });
    
            self.getParent().excludeMoveLines(added_lines_ids);
            self.getParent().unexcludeMoveLines(removed_lines_ids);
    
            self.updateAccountingViewMatchedLines();
            self.updateBalance();
        },
    
        // Generic function for updating the line_created_being_edited
        formCreateInputChanged: function(elt, val) {
            var self = this;
            var line_created_being_edited = self.get("line_created_being_edited");
            line_created_being_edited[0][elt.corresponding_property] = val.newValue;
             
            line_created_being_edited[0].currency_id = self.st_line.currency_id;
    
            // Specific cases
            if (elt === self.account_id_field)
                line_created_being_edited[0].account_num = self.map_account_id_code[elt.get("value")];
    
            // Update tax line
            var deferred_tax = new $.Deferred();
            if (elt === self.tax_id_field || elt === self.amount_field) {
                var amount = self.amount_field.get("value");
                var tax = self.map_tax_id_amount[self.tax_id_field.get("value")];
                if (amount && tax) {
                    deferred_tax = $.when(self.model_tax
                        .call("compute_for_bank_reconciliation", [self.tax_id_field.get("value"), amount]))
                        .then(function(data){
                            var tax = data.taxes[0];
                            var tax_account_id = (amount > 0 ? tax.account_collected_id : tax.account_paid_id)
                            line_created_being_edited[0].amount = (data.total.toFixed(3) === amount.toFixed(3) ? amount : data.total);
                            line_created_being_edited[1] = {id: line_created_being_edited[0].id, account_id: tax_account_id, account_num: self.map_account_id_code[tax_account_id], label: tax.name, amount: tax.amount, no_remove_action: true, currency_id: self.st_line.currency_id};
                        }
                    );
                } else {
                    line_created_being_edited[0].amount = amount;
                    delete line_created_being_edited[1];
                    deferred_tax.resolve();
                }
            } else { deferred_tax.resolve(); }
    
            $.when(deferred_tax).then(function(){
                // Format amounts
                if (line_created_being_edited[0].amount)
                    line_created_being_edited[0].amount_str = self.formatCurrency(Math.abs(line_created_being_edited[0].amount), line_created_being_edited[0].currency_id);
                if (line_created_being_edited[1] && line_created_being_edited[1].amount)
                    line_created_being_edited[1].amount_str = self.formatCurrency(Math.abs(line_created_being_edited[1].amount), line_created_being_edited[0].currency_id);
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
                line.debit -= balance;
                line.debit_str = self.formatCurrency(line.debit, self.st_line.currency_id);
            } else {
                line.credit -= balance;
                line.credit_str = self.formatCurrency(line.credit, self.st_line.currency_id);
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
                line.debit_str = self.formatCurrency(line.debit, self.st_line.currency_id);
            } else {
                line.credit = -1 * line.initial_amount;
                line.credit_str = self.formatCurrency(line.credit, self.st_line.currency_id);
            }
            line.propose_partial_reconcile = true;
            line.partial_reconcile = false;
        },
    
        updateBalance: function() {
            var self = this;
            var mv_lines_selected = self.get("mv_lines_selected");
            var balance = 0;
            balance -= self.st_line.amount;
            _.each(mv_lines_selected, function(o) {
                balance = balance - o.debit + o.credit;
            });
            _.each(self.getCreatedLines(), function(o) {
                balance += o.amount;
            });
            self.set("balance", balance);
    
            // Propose partial reconciliation if necessary
            var lines_selected_num = mv_lines_selected.length;
            var lines_created_num = self.getCreatedLines().length;
            if (lines_selected_num === 1 && lines_created_num === 0 && self.st_line.amount * balance > 0) {
                mv_lines_selected[0].propose_partial_reconcile = true;
                self.updateAccountingViewMatchedLines();
            }
            if (lines_selected_num !== 1 || lines_created_num !== 0) {
                // remove partial reconciliation stuff if necessary
                _.each(mv_lines_selected, function(line) {
                    if (line.partial_reconcile === true) self.unpartialReconcileLine(line);
                    if (line.propose_partial_reconcile === true) line.propose_partial_reconcile = false;
                });
                self.updateAccountingViewMatchedLines();
            }
        },
    
        loadReconciliationProposition: function() {
            var self = this;
            return self.model_bank_statement_line
                .call("get_reconciliation_proposition", [self.st_line.id, self.getParent().excluded_move_lines_ids])
                .then(function (lines) {
                    _(lines).each(self.decorateMoveLine.bind(self));
                    self.set("mv_lines_selected", self.get("mv_lines_selected").concat(lines));
                });
        },

        render: function() {
            var self = this;
            var lines_to_show = [];
            _.each(self.propositions_lines, function(line){
                var filter = (line.q_label.toLowerCase().indexOf(self.filter.toLowerCase()) > -1 || line.account_code.toLowerCase().indexOf(self.filter.toLowerCase()) > -1);
                if (self.getParent().excluded_move_lines_ids.indexOf(line.id) === -1 && filter) {
                    lines_to_show.push(line);
                }
            });
            self.set("mv_lines", lines_to_show);
        },
    
        // Changes the partner_id of the statement_line in the DB and reloads the widget
        changePartner: function(partner_id) {
            var self = this;
            self.is_consistent = false;
            return self.model_bank_statement_line
                // Update model
                .call("write", [[self.st_line_id], {'partner_id': partner_id}])
                .then(function () {
                    return $.when(self.restart(self.get("mode"))).then(function(){
                        self.is_consistent = true;
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
        prepareCreatedMoveLineForPersisting: function(line) {
            var dict = {};
            
            if (dict['account_id'] === undefined)
                dict['account_id'] = line.account_id;
            dict['name'] = line.label;
            if (line.amount > 0) dict['credit'] = line.amount;
            if (line.amount < 0) dict['debit'] = -1*line.amount;
            if (line.tax_id) dict['tax_code_id'] = line.tax_id;
            if (line.analytic_account_id) dict['analytic_account_id'] = line.analytic_account_id;
    
            return dict;
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
    
        // Persist data, notify parent view and terminate widget
        persistAndDestroy: function() {
            var self = this;
            if (! self.is_consistent) return;
    
            // Prepare data
            var mv_line_dicts = [];
            _.each(self.get("mv_lines_selected"), function(o) { mv_line_dicts.push(self.prepareSelectedMoveLineForPersisting(o)) });
            _.each(self.getCreatedLines(), function(o) { mv_line_dicts.push(self.prepareCreatedMoveLineForPersisting(o)) });
            if (Math.abs(self.get("balance")).toFixed(3) !== "0.000") mv_line_dicts.push(self.prepareOpenBalanceForPersisting());
    
            // Sliding animation
            var height = self.$el.outerHeight();
            var container = $("<div />");
            container.css("height", height)
                     .css("marginTop", self.$el.css("marginTop"))
                     .css("marginBottom", self.$el.css("marginBottom"));
            self.$el.wrap(container);
            var deferred_animation = self.$el.parent().slideUp(self.animation_speed*height/150);
    
            // RPC
            return self.model_bank_statement_line
                .call("process_reconciliation", [self.st_line_id, mv_line_dicts])
                .then(function () {
                    $.each(self.$(".bootstrap_popover"), function(){ $(this).popover('destroy') });
                    return $.when(deferred_animation).then(function(){
                        self.$el.parent().remove();
                        var parent = self.getParent();
                        return $.when(self.destroy()).then(function() {
                            parent.childValidated(self);
                        });
                    });
                }, function(){
                    self.$el.parent().slideDown(self.animation_speed*height/150, function(){
                        self.$el.unwrap();
                    });
                });
    
        },
    });

    instance.web.views.add('tree_account_reconciliation', 'instance.web.account.ReconciliationListView');
    instance.web.account.ReconciliationListView = instance.web.ListView.extend({
        init: function() {
            this._super.apply(this, arguments);
            var self = this;
            this.current_partner = null;
            this.on('record_selected', this, function() {
                if (self.get_selected_ids().length === 0) {
                    self.$(".oe_account_recon_reconcile").attr("disabled", "");
                } else {
                    self.$(".oe_account_recon_reconcile").removeAttr("disabled");
                }
            });
        },
        load_list: function() {
            var self = this;
            var tmp = this._super.apply(this, arguments);
            if (this.partners) {
                this.$el.prepend(QWeb.render("AccountReconciliation", {widget: this}));
                this.$(".oe_account_recon_previous").click(function() {
                    self.current_partner = (((self.current_partner - 1) % self.partners.length) + self.partners.length) % self.partners.length;
                    self.search_by_partner();
                });
                this.$(".oe_account_recon_next").click(function() {
                    self.current_partner = (self.current_partner + 1) % self.partners.length;
                    self.search_by_partner();
                });
                this.$(".oe_account_recon_reconcile").click(function() {
                    self.reconcile();
                });
                this.$(".oe_account_recom_mark_as_reconciled").click(function() {
                    self.mark_as_reconciled();
                });
            }
            return tmp;
        },
        do_search: function(domain, context, group_by) {
            var self = this;
            this.last_domain = domain;
            this.last_context = context;
            this.last_group_by = group_by;
            this.old_search = _.bind(this._super, this);
            var mod = new instance.web.Model("account.move.line", context, domain);
            return mod.call("list_partners_to_reconcile", []).then(function(result) {
                var current = self.current_partner !== null ? self.partners[self.current_partner][0] : null;
                self.partners = result;
                var index = _.find(_.range(self.partners.length), function(el) {
                    if (current === self.partners[el][0])
                        return true;
                });
                if (index !== undefined)
                    self.current_partner = index;
                else
                    self.current_partner = self.partners.length == 0 ? null : 0;
                self.search_by_partner();
            });
        },
        search_by_partner: function() {
            var self = this;
            var fct = function() {
                return self.old_search(new instance.web.CompoundDomain(self.last_domain, 
                    [["partner_id", "in", self.current_partner === null ? [] :
                    [self.partners[self.current_partner][0]] ]]), self.last_context, self.last_group_by);
            };
            if (self.current_partner === null) {
                self.last_reconciliation_date = _t("Never");
                return fct();
            } else {
                return new instance.web.Model("res.partner").call("read",
                    [self.partners[self.current_partner][0], ["last_reconciliation_date"]]).then(function(res) {
                    self.last_reconciliation_date = 
                        instance.web.format_value(res.last_reconciliation_date, {"type": "datetime"}, _t("Never"));
                    return fct();
                });
            }
        },
        reconcile: function() {
            var self = this;
            var ids = this.get_selected_ids();
            if (ids.length === 0) {
                new instance.web.Dialog(this, {
                    title: _t("Warning"),
                    size: 'medium',
                }, $("<div />").text(_t("You must choose at least one record."))).open();
                return false;
            }

            new instance.web.Model("ir.model.data").call("get_object_reference", ["account", "action_view_account_move_line_reconcile"]).then(function(result) {
                var additional_context = _.extend({
                    active_id: ids[0],
                    active_ids: ids,
                    active_model: self.model
                });
                return self.rpc("/web/action/load", {
                    action_id: result[1],
                    context: additional_context
                }).done(function (result) {
                    result.context = instance.web.pyeval.eval('contexts', [result.context, additional_context]);
                    result.flags = result.flags || {};
                    result.flags.new_window = true;
                    return self.do_action(result, {
                        on_close: function () {
                            self.do_search(self.last_domain, self.last_context, self.last_group_by);
                        }
                    });
                });
            });
        },
        mark_as_reconciled: function() {
            var self = this;
            var id = self.partners[self.current_partner][0];
            new instance.web.Model("res.partner").call("mark_as_reconciled", [[id]]).then(function() {
                self.do_search(self.last_domain, self.last_context, self.last_group_by);
            });
        },
        do_select: function (ids, records) {
            this.trigger('record_selected')
            this._super.apply(this, arguments);
        },
    });
    
};
