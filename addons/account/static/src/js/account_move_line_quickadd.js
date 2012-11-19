
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
        start:function(){
            var tmp = this._super.apply(this, arguments);
            var self = this;
            this.$el.parent().prepend(QWeb.render("AccountMoveLineQuickAdd", {widget: this}));
            
            this.$el.parent().find('.oe_account_select_journal').change(function() {
                    self.current_journal = parseInt(this.value);
                    self.do_search(self.last_domain, self.last_context, self.last_group_by);
                });
            this.$el.parent().find('.oe_account_select_period').change(function() {
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
            })).then(function () {
                self.current_journal = self.current_journal === null ? self.default_journal : self.current_journal;
                self.current_period = self.current_period === null ? self.default_period :self.current_period;
                var o;
                //self.$('.oe_account_select_journal',self.$el.parent())[0].children().remove().end();
                self.$el.parent().find('.oe_account_select_journal').children().remove().end();
                for (var i = 0;i < self.journals.length;i++){
                    o = new Option(self.journals[i][1], self.journals[i][0]);
                    self.$el.parent().find('.oe_account_select_journal').append(o);
                }
                self.$el.parent().find('.oe_account_select_period').children().remove().end();
                for (var i = 0;i < self.periods.length;i++){
                    o = new Option(self.periods[i][1], self.periods[i][0]);
                    self.$el.parent().find('.oe_account_select_period').append(o);
                }    
                self.$el.parent().find('.oe_account_select_journal').val(self.current_journal).attr('selected',true);
                self.$el.parent().find('.oe_account_select_period').val(self.current_period).attr('selected',true);
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
            return self.old_search(compoundDomain, compoundContext, self.last_group_by);
        },
        start_edition: function (record, options) {
            this.$el.parent().find('.oe_account_select_journal').attr('disabled', 'disabled');
            this.$el.parent().find('.oe_account_select_period').attr('disabled', 'disabled');
            return this._super.apply(this, arguments);
        },
        cancel_edition: function (force) {
            this.$el.parent().find('.oe_account_select_journal').removeAttr('disabled');
            this.$el.parent().find('.oe_account_select_period').removeAttr('disabled');
            return this._super.apply(this, arguments);
        },
        save_edition: function () {
            var tmp = this._super.apply(this, arguments);
            var self = this;
            tmp.then(function (saveInfo){
                console.log(saveInfo);
                if (saveInfo) {
                    self.$el.parent().find('.oe_account_select_journal').removeAttr('disabled');
                    self.$el.parent().find('.oe_account_select_period').removeAttr('disabled');
                }
            });
            return tmp;
        }
    });
};
