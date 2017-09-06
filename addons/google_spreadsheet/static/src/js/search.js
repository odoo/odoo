odoo.define('google_spreadsheet.google.spreadsheet', function (require) {
"use strict";

var ActionManager = require('web.ActionManager');
var core = require('web.core');
var data = require('web.data');
var Domain = require('web.Domain');
var FavoriteMenu = require('web.FavoriteMenu');
var pyeval = require('web.pyeval');
var ViewManager = require('web.ViewManager');

var QWeb = core.qweb;

FavoriteMenu.include({
    start: function () {
        this._super();
        var am = this.findAncestor(function (a) {
            return a instanceof ActionManager;
        });
        if (am && am.get_inner_widget() instanceof ViewManager) {
            this.view_manager = am.get_inner_widget();
            this.$('.o_favorites_menu').append(QWeb.render('SearchView.addtogooglespreadsheet'));
            this.$('.add-to-spreadsheet').click(this.add_to_spreadsheet.bind(this));
        }
    },
    add_to_spreadsheet: function () {
        var sv_data = this.searchview.build_search_data(),
            model = this.searchview.dataset.model,
            list_view = this.view_manager.views.list,
            list_view_id = list_view ? list_view.view_id : false,
            domain = [],
            groupbys = pyeval.eval('groupbys', sv_data.groupbys).join(" "),
            ds = new data.DataSet(this, 'google.drive.config');

        _.each(sv_data.domains, function (d) {
            domain.push.apply(domain, Domain.prototype.stringToArray(d));
        });
        ds.call('set_spreadsheet', [model, Domain.prototype.arrayToString(domain), groupbys, list_view_id])
            .done(function (res) {
                if (res.url){
                    window.open(res.url, '_blank');
                }
            });
    },
});

});
