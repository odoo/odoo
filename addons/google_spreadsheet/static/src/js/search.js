openerp.google_spreadsheet = function(instance) {
    var _t = instance.web._t,
        QWeb = instance.web.qweb;

    instance.web.FormView.include({
        on_processed_onchange: function(result, processed) {
            var self = this;
            var fields = self.fields;
            _(result.selection).each(function (selection, fieldname) {
                var field = fields[fieldname];
                if (!field) { return; }
                field.field.selection = selection;
                field.values = selection;
                field.renderElement(); 
            });
            return this._super(result, processed);
        },
    });
    instance.web.search.FavoriteMenu.include({
        prepare_dropdown_menu: function (filters) {
            this._super(filters);
            this.$('.favorites-menu').append(QWeb.render('SearchView.addtogooglespreadsheet'));
            this.$('.add-to-spreadsheet').click(this.add_to_spreadsheet.bind(this));
        },
        add_to_spreadsheet: function () {
            var data = this.searchview.build_search_data(),
                model = this.searchview.dataset.model,
                view_manager = this.searchview.getParent(),
                list_view = view_manager.views.list,
                list_view_id = list_view ? list_view.view_id : false,
                context = this.searchview.dataset.get_context() || [],
                domain = this.searchview.dataset.get_domain() || [],
                compound_context = new instance.web.CompoundContext(context),
                compound_domain = new instance.web.CompoundDomain(context),
                groupbys = instance.web.pyeval.eval('groupbys', data.groupbys).join(" "),
                ds = new instance.web.DataSet(this, 'google.drive.config');

            _.each(data.contexts, compound_context.add, compound_context);
            _.each(data.domains, compound_domain.add, compound_domain);

            compound_domain = JSON.stringify(compound_domain.eval());
            ds.call('set_spreadsheet', [model, compound_domain, groupbys, list_view_id])
                .done(function (res) {
                    if (res['url']){
                        window.open(res['url'], '_blank');
                    }
                });
        },
    });
};