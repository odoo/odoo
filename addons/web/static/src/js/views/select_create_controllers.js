odoo.define('web.select_create_controllers', function (require) {
"use strict";

return {};

});

odoo.define('web._select_create_controllers', function (require) {
"use strict";

var KanbanController = require('web.KanbanController');
var ListController = require('web.ListController');
var SelectCreateControllersRegistry = require('web.select_create_controllers');

var SelectCreateKanbanController = KanbanController.extend({
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Override to select the clicked record instead of opening it
     *
     * @override
     * @private
     */
    _onOpenRecord: function (ev) {
        var selectedRecord = this.model.get(ev.data.id);
        this.trigger_up('select_record', {
            id: selectedRecord.res_id,
            display_name: selectedRecord.data.display_name,
        });
    },
});

var SelectCreateListController = ListController.extend({
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Override to select the clicked record instead of opening it
     *
     * @override
     * @private
     */
    _onOpenRecord: function (ev) {
        var selectedRecord = this.model.get(ev.data.id);
        this.trigger_up('select_record', {
            id: selectedRecord.res_id,
            display_name: selectedRecord.data.display_name,
        });
    },
});

_.extend(SelectCreateControllersRegistry, {
    SelectCreateListController: SelectCreateListController,
    SelectCreateKanbanController: SelectCreateKanbanController,
});

});
