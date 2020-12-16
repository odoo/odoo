odoo.define('lunch.LunchListView', function (require) {
"use strict";

var LunchListController = require('lunch.LunchListController');
var LunchListRenderer = require('lunch.LunchListRenderer');

var core = require('web.core');
var ListView = require('web.ListView');
var view_registry = require('web.view_registry');

var _lt = core._lt;

var LunchListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: LunchListController,
        Renderer: LunchListRenderer,
    }),
    display_name: _lt('Lunch List'),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _createSearchModel(params, extraExtensions = {}) {
        Object.assign(extraExtensions, { Lunch: {} });
        return this._super(params, extraExtensions);
    },

});

view_registry.add('lunch_list', LunchListView);

return LunchListView;

});
