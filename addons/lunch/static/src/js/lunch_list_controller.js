odoo.define('lunch.LunchListController', function (require) {
"use strict";

/**
 * This file defines the Controller for the Lunch List view, which is an
 * override of the ListController.
 */

var ListController = require('web.ListController');
var LunchControllerCommon = require('lunch.LunchControllerCommon');

var LunchListController = ListController.extend(LunchControllerCommon, {
    custom_events: _.extend({}, ListController.prototype.custom_events, LunchControllerCommon.custom_events),
});

return LunchListController;

});
