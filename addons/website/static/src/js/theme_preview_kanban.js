odoo.define('website.theme_preview_kanban', function (require) {
"use strict";

var KanbanController = require('web.KanbanController');
var KanbanView = require('web.KanbanView');
var ViewRegistry = require('web.view_registry');

var ThemePreviewKanbanController = KanbanController.extend({
    /**
     * @override
     */
    start: async function () {
        await this._super(...arguments);
        this.el.classList.add('o_view_kanban_theme_preview_controller');
        const websiteLink = Object.assign(document.createElement('a'), {
            className: 'btn btn-secondary ml-3',
            href: '/',
            innerHTML: '<i class="fa fa-close"></i>',
        });
        this._controlPanelWrapper.el.querySelector('.o_cp_top').appendChild(websiteLink);
    },
});

var ThemePreviewKanbanView = KanbanView.extend({
    searchMenuTypes: [],

    config: _.extend({}, KanbanView.prototype.config, {
        Controller: ThemePreviewKanbanController,
    }),
});

ViewRegistry.add('theme_preview_kanban', ThemePreviewKanbanView);

});
