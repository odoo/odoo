openerp.mass_mailing = function (instance) {
    var _t = instance.web._t;

    openerp.web_kanban.KanbanRecord.include({
        on_card_clicked: function (event) {
            if (this.view.dataset.model === 'mail.mass_mailing.campaign') {
                this.$('.oe_mailings').click();
            } else {
                this._super.apply(this, arguments);
            }
        },
    });

    instance.web.form.CharDomainButton = instance.web.form.AbstractField.extend({
        template: 'CharDomainButton',
        init: function(field_manager, node) {
            this._super.apply(this, arguments);
        },
        start: function() {
            var self=this;
            this._super.apply(this, arguments);
            $('button', this.$el).on('click', self.on_click);
            this.set_button();
        },
        set_button: function() {
            var self = this;
            // debugger
            if (this.get('value')) {
                // TODO: rpc to copute X
                var domain = instance.web.pyeval.eval('domain', this.get('value'));
                var relation = this.getParent().fields.mailing_model.get('value')[0];
                var ds = new instance.web.DataSetStatic(self, relation, self.build_context());
                ds.call('search_count', [domain]).then(function (results) {
                    $('.oe_domain_count', self.$el).text(results + ' records selected');
                    $('button span', self.$el).text(' Change selection');
                });
            } else {
                $('.oe_domain_count', this.$el).text('0 record selected');
                $('button span', this.$el).text(' Select records');
            };
        },
        on_click: function(ev) {
            var self = this;
            var model = this.options.model || this.field_manager.get_field_value(this.options.model_field);
            this.pop = new instance.web.form.SelectCreatePopup(this);
            this.pop.select_element(
                model, {title: 'Select records...'},
                [], this.build_context());
            this.pop.on("elements_selected", self, function() {
                var self2 = this;
                var search_data = this.pop.searchview.build_search_data()
                instance.web.pyeval.eval_domains_and_contexts({
                    domains: search_data.domains,
                    contexts: search_data.contexts,
                    group_by_seq: search_data.groupbys || []
                }).then(function (results) {
                    // if selected IDS change domain
                    var domain = self2.pop.dataset.domain.concat(results.domain || []);
                    self.set_value(JSON.stringify(domain))
                });
            });
            event.preventDefault();
        },
        set_value: function(value_) {
            var self = this;
            this.set('value', value_ || false);
            this.set_button();
         },
    });

    instance.web.form.widgets = instance.web.form.widgets.extend(
        {'char_domain': 'instance.web.form.CharDomainButton'}
    );

};
