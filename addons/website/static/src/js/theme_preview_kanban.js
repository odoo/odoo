odoo.define('website.theme_preview_kanban', function (require) {
"use strict";

var KanbanController = require('web.KanbanController');
var KanbanView = require('web.KanbanView');
var ViewRegistry = require('web.view_registry');
const ThemePreviewControllerCommon = require('website.theme_preview_form').ThemePreviewControllerCommon;

var ThemePreviewKanbanController = KanbanController.extend(ThemePreviewControllerCommon, {
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
    /**
     * Called when user click on any button in kanban view.
     * Targeted buttons are selected using name attribute value.
     * 
     * @override
     */
    _onButtonClicked: function (ev) {
        const attrName = ev.data.attrs.name;
        if (attrName === 'button_choose_theme' || attrName === 'button_refresh_theme') {
            this._handleThemeAction(ev.data.record.res_id, attrName);
        } else {
            this._super(...arguments);
        }
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
