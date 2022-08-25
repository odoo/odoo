odoo.define('lunch.LunchKanbanView', function (require) {
"use strict";

var LunchKanbanController = require('lunch.LunchKanbanController');
var LunchKanbanRenderer = require('lunch.LunchKanbanRenderer');

var core = require('web.core');
var KanbanView = require('web.KanbanView');
var view_registry = require('web.view_registry');

var _lt = core._lt;

var LunchKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Controller: LunchKanbanController,
        Renderer: LunchKanbanRenderer,
    }),
    display_name: _lt('Lunch Kanban'),

    /**
     * @override
     */
    _createSearchModel(params, extraExtensions = {}) {
        Object.assign(extraExtensions, { Lunch: {} });
        return this._super(params, extraExtensions);
    },
});

view_registry.add('lunch_kanban', LunchKanbanView);

return LunchKanbanView;

});
