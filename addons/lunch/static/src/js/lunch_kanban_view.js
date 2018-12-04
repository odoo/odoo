odoo.define('lunch.LunchKanbanView', function (require) {
"use strict";

var LunchKanbanController = require('lunch.LunchKanbanController');
var LunchKanbanModel = require('lunch.LunchKanbanModel');
var LunchKanbanRenderer = require('lunch.LunchKanbanRenderer');

var config = require('web.config');
var core = require('web.core');
var KanbanView = require('web.KanbanView');
var view_registry = require('web.view_registry');

var _lt = core._lt;

if (config.device.isMobile) {
    // use the classical KanbanView in mobile
    view_registry.add('lunch_kanban', KanbanView);
    return;
}

var LunchKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Controller: LunchKanbanController,
        Model: LunchKanbanModel,
        Renderer: LunchKanbanRenderer,
    }),
    display_name: _lt('Lunch Kanban'),
    groupable: false,

    /**
     * @override
     */
    init: function () {
        return this._super.apply(this, arguments);
    },
});

view_registry.add('lunch_kanban', LunchKanbanView);

return LunchKanbanView;

});
