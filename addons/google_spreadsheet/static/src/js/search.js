odoo.define('google_spreadsheet.google.spreadsheet', ['web.core', 'web.data', 'web.FavoriteMenu', 'web.FormView', 'web.pyeval'], function (require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var FavoriteMenu = require('web.FavoriteMenu');
var FormView = require('web.FormView');
var pyeval = require('web.pyeval');

var QWeb = core.qweb;

FormView.include({
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

FavoriteMenu.include({
    prepare_dropdown_menu: function (filters) {
        this._super(filters);
        this.$('.favorites-menu').append(QWeb.render('SearchView.addtogooglespreadsheet'));
        this.$('.add-to-spreadsheet').click(this.add_to_spreadsheet.bind(this));
    },
    add_to_spreadsheet: function () {
        var sv_data = this.searchview.build_search_data(),
            model = this.searchview.dataset.model,
            view_manager = this.searchview.getParent(),
            list_view = view_manager.views.list,
            list_view_id = list_view ? list_view.view_id : false,
            context = this.searchview.dataset.get_context() || [],
            compound_context = new data.CompoundContext(context),
            compound_domain = new data.CompoundDomain(context),
            groupbys = pyeval.eval('groupbys', sv_data.groupbys).join(" "),
            ds = new data.DataSet(this, 'google.drive.config');

        _.each(sv_data.contexts, compound_context.add, compound_context);
        _.each(sv_data.domains, compound_domain.add, compound_domain);

        compound_domain = JSON.stringify(compound_domain.eval());
        ds.call('set_spreadsheet', [model, compound_domain, groupbys, list_view_id])
            .done(function (res) {
                if (res.url){
                    window.open(res.url, '_blank');
                }
            });
    },
});

});
