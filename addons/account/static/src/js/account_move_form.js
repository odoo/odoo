/** @odoo-module **/

import FormController from 'web.FormController';
import FormRenderer from 'web.FormRenderer';
import FormView from 'web.FormView';
import view_registry from 'web.view_registry';

var AccountMoveFormController = FormController.extend({
    custom_events: _.extend({}, FormController.prototype.custom_events, {
        save_on_tab_switch: '_saveOnTabSwitch',
    }),
    _saveOnTabSwitch: async function(event) {
        let tabName = event.data.originalEvent.target.name
        await this.saveRecord(this.handle, {
            stayInEdit: true,
        });
        await this.reload();
        $(`[name='${tabName}']`).tab('show');
    },
});

var AccountMoveFormRenderer = FormRenderer.extend({
    _renderTagNotebook: function (node) {
        var self = this;
        var $result = this._super.apply(this, arguments);
        var $nav_items = $result.find('ul.nav-tabs li.nav-item').slice(0, 2);
        _.each($nav_items, (nav_item) => {
            $(nav_item).find('a').on('show.bs.tab', function (event) {
                if (self.state.isDirty()) {
                    event.preventDefault();
                    self.trigger_up('save_on_tab_switch', {originalEvent: event});
                }
            });
        })
        return $result
    },
});

var AccountMoveFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: AccountMoveFormController,
        Renderer: AccountMoveFormRenderer,
    }),

});

view_registry.add('account_move_form', AccountMoveFormView);

export {
    AccountMoveFormController,
    AccountMoveFormRenderer,
    AccountMoveFormView,
}
