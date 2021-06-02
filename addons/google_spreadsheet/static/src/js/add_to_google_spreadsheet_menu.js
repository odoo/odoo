odoo.define('board.AddToGoogleSpreadsheetMenu', function (require) {
"use strict";

var ActionManager = require('web.ActionManager');
var core = require('web.core');
var data = require('web.data');
var Domain = require('web.Domain');
var favorites_submenus_registry = require('web.favorites_submenus_registry');
var pyUtils = require('web.py_utils');
var Widget = require('web.Widget');

var QWeb = core.qweb;

var AddToGoogleSpreadsheetMenu = Widget.extend({
    events: _.extend({}, Widget.prototype.events, {
        'click .add_to_spreadsheet': '_onAddToSpreadsheetClick',
    }),
    /**
     * @override
     * @param {Object} params
     * @param {Object} params.action an ir.actions description
     */
    init: function (parent, params) {
        this._super(parent);
        this.action = params.action;
    },
    /**
     * @override
     */
    start: function () {
        if (this.action.type === 'ir.actions.act_window') {
            this._render();
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _addToSpreadsheet: function () {
        // AAB: trigger_up an event that will be intercepted by the controller,
        // as soon as the controller is the parent of the control panel
        var actionManager = this.findAncestor(function (ancestor) {
            return ancestor instanceof ActionManager;
        });
        var controller = actionManager.getCurrentController();
        var searchQuery;
        // TO DO: for now the domains in query are evaluated.
        // This should be changed I think.
        this.trigger_up('get_search_query', {
            callback: function (query) {
                searchQuery = query;
            }
        });
        var modelName = this.action.res_model;
        var list_view = _.findWhere(controller.widget.actionViews, {type: 'list'});
        var list_view_id = list_view ? list_view.viewID : false;
        var domain = searchQuery.domain;
        var groupBys = pyUtils.eval('groupbys', searchQuery.groupBys).join(" ");
        var ds = new data.DataSet(this, 'google.drive.config');

        ds.call('set_spreadsheet', [modelName, Domain.prototype.arrayToString(domain), groupBys, list_view_id])
            .then(function (res) {
                if (res.url){
                    window.open(res.url, '_blank');
                }
            });
    },
    /**
     * Renders the `SearchView.addtogooglespreadsheet` template.
     *
     * @private
     */
    _render: function () {
        var $el = QWeb.render('SearchView.addtogooglespreadsheet', {widget: this});
        this._replaceElement($el);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {jQueryEvent} event
     */
     _onAddToSpreadsheetClick: function (event) {
        event.preventDefault();
        event.stopPropagation();
        this._addToSpreadsheet();
     },
});

favorites_submenus_registry.add('add_to_google_spreadsheet_menu', AddToGoogleSpreadsheetMenu, 20);

return AddToGoogleSpreadsheetMenu;

});
