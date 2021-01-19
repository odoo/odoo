odoo.define('event_booth_sale.event_booth_configurator_form_view', function (require) {
'use strict';

var EventBoothConfiguratorFormController = require('event_booth_sale.event_booth_configurator_form_controller');
var FormView = require('web.FormView');
var viewRegistry = require('web.view_registry');

/**
 * @see EventBoothConfiguratorFormController for more information.
 */
var EventBoothConfiguratorFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: EventBoothConfiguratorFormController
    }),
});

viewRegistry.add('event_booth_configurator_form', EventBoothConfiguratorFormView);

return EventBoothConfiguratorFormView;

});
