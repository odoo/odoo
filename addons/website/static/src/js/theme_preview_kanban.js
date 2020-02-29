odoo.define('website.theme_preview_kanban', function (require) {
"use strict";

var KanbanController = require('web.KanbanController');
var KanbanView = require('web.KanbanView');
var ViewRegistry = require('web.view_registry');

var ThemePreviewKanbanController = KanbanController.extend({
    /**
     * @override
     */
    start: function () {
        this.$el.addClass('o_view_kanban_theme_preview_controller');
        return this._super.apply(this, arguments);
    },
});

var ThemePreviewKanbanView = KanbanView.extend({
    searchMenuTypes: [],

    config: _.extend({}, KanbanView.prototype.config, {
        Controller: ThemePreviewKanbanController,
    }),

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------
    /**
     * @override
     *
     */
    _createControlPanel: function (parent) {
        return this._super.apply(this, arguments).then(controlPanel => {
            var websiteLink = '<a class="btn btn-secondary ml-3" href="/"><i class="fa fa-close"></i></a>';
            controlPanel.$('div.o_cp_searchview').after(websiteLink);
            return controlPanel;
        });
    },
});

ViewRegistry.add('theme_preview_kanban', ThemePreviewKanbanView);

});
