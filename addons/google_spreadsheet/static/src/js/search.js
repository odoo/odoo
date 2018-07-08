odoo.define('google_spreadsheet.google.spreadsheet', function (require) {
"use strict";

var ActionManager = require('web.ActionManager');
var core = require('web.core');
var data = require('web.data');
var Domain = require('web.Domain');
var FavoriteMenu = require('web.FavoriteMenu');
var pyUtils = require('web.py_utils');

var QWeb = core.qweb;

FavoriteMenu.include({
    start: function () {
        this._super();
        if (this.action.type === 'ir.actions.act_window') {
            this.$('.o_favorites_menu').append(QWeb.render('SearchView.addtogooglespreadsheet'));
            this.$('.add-to-spreadsheet').click(this.add_to_spreadsheet.bind(this));
        }
    },
    add_to_spreadsheet: function () {
        // AAB: trigger_up an event that will be intercepted by the controller,
        // as soon as the controller is the parent of the control panel
        var am = this.findAncestor(function (a) {
            return a instanceof ActionManager;
        });
        var controller = am.getCurrentController();
        var sv_data = this.searchview.build_search_data(),
            model = this.searchview.dataset.model,
            list_view = _.findWhere(controller.widget.actionViews, {type: 'list'}),
            list_view_id = list_view ? list_view.viewID : false,
            domain = [],
            groupbys = pyUtils.eval('groupbys', sv_data.groupbys).join(" "),
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
