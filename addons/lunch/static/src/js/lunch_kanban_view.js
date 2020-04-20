odoo.define('lunch.LunchKanbanView', function (require) {
"use strict";

var LunchKanbanController = require('lunch.LunchKanbanController');
var LunchKanbanModel = require('lunch.LunchKanbanModel');
var LunchKanbanRenderer = require('lunch.LunchKanbanRenderer');

var core = require('web.core');
var KanbanView = require('web.KanbanView');
var view_registry = require('web.view_registry');

var _lt = core._lt;

var LunchKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Controller: LunchKanbanController,
        Model: LunchKanbanModel,
        Renderer: LunchKanbanRenderer,
    }),
    display_name: _lt('Lunch Kanban'),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getViewDomain: function (parent) {
        const model = this.getModel(parent);
        return model.getLocationDomain();
    },
});

view_registry.add('lunch_kanban', LunchKanbanView);

return LunchKanbanView;

});
