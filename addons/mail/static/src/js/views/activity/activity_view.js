odoo.define('mail.ActivityView', function (require) {
"use strict";

var ActivityController = require('mail.ActivityController');
var ActivityModel = require('mail.ActivityModel');
var ActivityRenderer = require('mail.ActivityRenderer');
var AbstractView = require('web.AbstractView');
var core = require('web.core');
var view_registry = require('web.view_registry');

var _lt = core._lt;

var ActivityView = AbstractView.extend({
    accesskey: "a",
    display_name: _lt('Activity'),
    icon: 'fa-th',
    config: _.extend({}, AbstractView.prototype.config, {
        Controller: ActivityController,
        Model: ActivityModel,
        Renderer: ActivityRenderer,
    }),
    viewType: 'activity',
    groupable: false,
});

view_registry.add('activity', ActivityView);

return ActivityView;

});
