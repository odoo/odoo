odoo.define('account.move.form', function (require) {
"use strict";

var core = require('web.core');
var FormController = require('web.FormController');
var FormRenderer = require('web.FormRenderer');
var FormView = require('web.FormView');
var view_registry = require('web.view_registry');

var _lt = core._lt;

var AccountMoveFormController = FormController.extend({
    custom_events: _.extend({}, FormController.prototype.custom_events, {
        save_on_tab_switch: '_saveOnTabSwitch',
    }),

    _saveOnTabSwitch: async function() {
        var self = this;
        await self.saveRecord(this.handle, {
            stayInEdit: true,
            reload: true,
        }).then(() => {
            this.displayNotification({
                type: 'info',
                message: _lt('The invoice has been saved'),
            });
        });
        await this.reload();
    },

    start: function () {
        return this._super.apply(this, arguments);
    }
});

var AccountMoveFormRenderer = FormRenderer.extend({
    _renderTagNotebook: function (node) {
        var self = this;
        var $result = this._super.apply(this, arguments);
        var $nav_items = $result.find('ul.nav-tabs li.nav-item').slice(0, 2);
        _.each($nav_items, (nav_item) => {
            $(nav_item).find('a').click(function (event) {
                event.preventDefault();
                self.trigger_up('save_on_tab_switch');
            });
        })
        return $result
    }
});

var AccountMoveFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: AccountMoveFormController,
        Renderer: AccountMoveFormRenderer,
    }),
});

view_registry.add('account_move_form', AccountMoveFormView);

return {
    Controller: AccountMoveFormController,
    Renderer: AccountMoveFormRenderer,
};

});
