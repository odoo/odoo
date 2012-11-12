
openerp.account.quickadd = function (instance) {
    var _t = instance.web._t,
        _lt = instance.web._lt;
    var QWeb = instance.web.qweb;
    
    instance.web.account = instance.web.account || {};
    
    instance.web.views.add('tree_account_move_line_quickadd', 'instance.web.account.QuickAddListView');
    instance.web.account.QuickAddListView = instance.web.ListView.extend({
        _template: 'ListView',

        init: function() {
            var self = this;
            this._super.apply(this, arguments);
            this.journals = [];
            this.periods = [];
            this.current_journal = null;
            this.current_period = null;
            this.default_period = null;
            this.default_journal = null;
        },
        load_list: function() {
            var self = this;
            var tmp = this._super.apply(this, arguments);

            this.$el.prepend(QWeb.render("AccountMoveLineQuickAdd", {widget: this}));
            
            this.$(".oe_account_select_journal").change(function() {
                    self.current_journal = parseInt(this.value);
                    self.do_search(self.last_domain, self.last_context, self.last_group_by);
                });
            this.$(".oe_account_select_period").change(function() {
                    self.current_period = parseInt(this.value);
                    self.do_search(self.last_domain, self.last_context, self.last_group_by);
                });
            return tmp;
        },
        do_search: function(domain, context, group_by) {
            var self = this;
            this.last_domain = domain;
            this.last_context = context;
            this.last_group_by = group_by;
            this.old_search = _.bind(this._super, this);
            var mod = new instance.web.Model("account.move.line", context, domain);
            return $.when(mod.call("list_journals", []).then(function(result) {
                self.journals = result;
            }),mod.call("list_periods", []).then(function(result) {
                self.periods = result;
            }),mod.call("default_get", [['journal_id','period_id'],self.last_context]).then(function(result) {
                self.default_period = result['period_id'];
                self.default_journal = result['journal_id'];
                console.log(result);
            })).then(function () {
                self.current_journal = self.current_journal === null ? self.default_journal : self.current_journal;
                self.current_period = self.current_period === null ? self.default_period :self.current_period;
                return self.search_by_journal_period();
            });
        },
        search_by_journal_period: function() {
            var self = this;
            
            var compoundDomain = new instance.web.CompoundDomain(self.last_domain, 
                [
                ["journal_id", "=", self.current_journal], 
                ["period_id", "=", self.current_period] 
                ]);
            //1
            /*var ncontext = {
                "journal_id": self.current_journal,
                "period_id" :self.current_period,
            };
            var new instance.web.CompoundDomain(self.last_domain = new instance.web.CompoundContext(this.last_context, ncontext);

            _.extend(this.dataset.context, ncontext);
            */
            //2
            /*
            var compoundContext = new instance.web.CompoundContext(self.last_context,{
                "journal_id": self.current_journal,
                "period_id" :self.current_period,
            });
            */
            //3
            self.last_context["journal_id"] = self.current_journal;
            self.last_context["period_id"] = self.current_period;
            var compoundContext = self.last_context;
            debugger;
            return self.old_search(compoundDomain, compoundContext, self.last_group_by);
        },
        /*_next: function (next_record, options) {
            next_record = next_record || 'succ';
            var self = this;
            return this.save_edition().then(function (saveInfo) {
                if (saveInfo.created || self.records.at(self.records.length-1).get("id") === saveInfo.record.get("id")) {
                    return self.start_edition();
                }
                var record = self.records[next_record](
                        saveInfo.record, {wraparound: true});
                return self.start_edition(record, options);
            });
        },*/
    });
};
