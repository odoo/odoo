odoo.define('event_booth_sale.event_booth_configurator_form_view', function (require) {
'use strict';

const EventBoothConfiguratorFormController = require('event_booth_sale.event_booth_configurator_form_controller');
const FormView = require('web.FormView');
const viewRegistry = require('web.view_registry');

/**
 * @see EventBoothConfiguratorFormController for more information.
 */
const EventBoothConfiguratorFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: EventBoothConfiguratorFormController,
    }),
});

viewRegistry.add('event_booth_configurator_form', EventBoothConfiguratorFormView);

return EventBoothConfiguratorFormView;

});
