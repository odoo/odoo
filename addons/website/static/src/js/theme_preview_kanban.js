odoo.define('website.theme_preview_kanban', function (require) {
"use strict";

var KanbanController = require('web.KanbanController');
var KanbanView = require('web.KanbanView');
var ViewRegistry = require('web.view_registry');
const ThemePreviewControllerCommon = require('website.theme_preview_form').ThemePreviewControllerCommon;
var core = require('web.core');
var _lt = core._lt;

var ThemePreviewKanbanController = KanbanController.extend(ThemePreviewControllerCommon, {
    /**
     * @override
     */
    start: async function () {
        await this._super(...arguments);

        // hide pager
        this.el.classList.add('o_view_kanban_theme_preview_controller');

        // update breacrumb
        const websiteLink = Object.assign(document.createElement('a'), {
            className: 'btn btn-secondary ml-3 text-black-75',
            href: '/',
            innerHTML: '<i class="fa fa-close"></i>',
        });
        if (!this.initialState.context.module) { // not coming from res.config.settings
            const smallBreadcumb = Object.assign(document.createElement('small'), {
                className: 'mx-2 text-muted',
                innerHTML: _lt("Don't worry, you can switch later."),
            });
            this._controlPanelWrapper.el.querySelector('.o_cp_top li').appendChild(smallBreadcumb);
            this._controlPanelWrapper.el.querySelector('.o_cp_top').appendChild(websiteLink);
        }
        this._controlPanelWrapper.el.querySelector('.o_cp_top .breadcrumb li.active').classList.add('text-black-75');
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
    withSearchBar: false,  // hide searchBar

    config: _.extend({}, KanbanView.prototype.config, {
        Controller: ThemePreviewKanbanController,
    }),
});

ViewRegistry.add('theme_preview_kanban', ThemePreviewKanbanView);

});
