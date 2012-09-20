openerp.account = function (instance) {
    var _t = instance.web._t,
        _lt = instance.web._lt;
    var QWeb = instance.web.qweb;
    
    instance.web.account = {};
    
    instance.web.views.add('account_reconciliation_list', 'instance.web.account.ReconciliationListView');
    instance.web.account.ReconciliationListView = instance.web.ListView.extend({
        init: function() {
            this._super.apply(this, arguments);
            this.current_partner = null;
        },
        on_loaded: function() {
            var self = this;
            var tmp = this._super.apply(this, arguments);
            if (this.partners) {
                this.$el.prepend(QWeb.render("AccountReconciliation", {widget: this}));
                this.$(".oe_account_recon_previous").click(function() {
                    self.current_partner = (self.current_partner - 1) % self.partners.length;
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
            return mod.call("list_partners_to_reconcile", []).pipe(function(result) {
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
            return this.old_search(new instance.web.CompoundDomain(this.last_domain, [["partner_id", "in", this.current_partner === null ? [] :
                [this.partners[this.current_partner][0]] ]]), this.last_context, this.last_group_by);
        },
        reconcile: function() {
            var self = this;
            var ids = this.get_selected_ids();
            if (ids.length === 0) {
                instance.web.dialog($("<div />").text(_t("You must choose at least one record.")), {
                    title: _t("Warning"),
                    modal: true
                });
                return false;
            }

            new instance.web.Model("ir.model.data").call("get_object_reference", ["account", "action_view_account_move_line_reconcile"]).pipe(function(result) {
                var additional_context = _.extend({
                    active_id: ids[0],
                    active_ids: ids,
                    active_model: self.model
                });
                return self.rpc("/web/action/load", {
                    action_id: result[1],
                    context: additional_context
                }, function (result) {
                    result = result.result;
                    result.context = _.extend(result.context || {}, additional_context);
                    result.flags = result.flags || {};
                    result.flags.new_window = true;
                    return self.do_action(result, function () {
                        self.do_search(self.last_domain, self.last_context, self.last_group_by);
                    });
                });
            });
        },
        mark_as_reconciled: function() {
            var self = this;
            var id = self.partners[self.current_partner][0];
            new instance.web.Model("res.partner").call("mark_as_reconciled", [[id]]).pipe(function() {
                self.do_search(self.last_domain, self.last_context, self.last_group_by);
            });
        },
    });
    
};
