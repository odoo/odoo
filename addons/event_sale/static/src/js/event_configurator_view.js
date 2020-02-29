odoo.define('event.EventConfiguratorFormView', function (require) {
"use strict";

var EventConfiguratorFormController = require('event.EventConfiguratorFormController');
var FormView = require('web.FormView');
var viewRegistry = require('web.view_registry');

/**
 * @see EventConfiguratorFormController for more information
 */
var EventConfiguratorFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: EventConfiguratorFormController
    }),
});

viewRegistry.add('event_configurator_form', EventConfiguratorFormView);

return EventConfiguratorFormView;

});
