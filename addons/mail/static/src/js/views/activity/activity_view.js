odoo.define('mail.ActivityView', function (require) {
"use strict";

var ActivityController = require('mail.ActivityController');
var ActivityModel = require('mail.ActivityModel');
var ActivityRenderer = require('mail.ActivityRenderer');
var BasicView = require('web.BasicView');
var core = require('web.core');
var view_registry = require('web.view_registry');

var _lt = core._lt;

var ActivityView = BasicView.extend({
    accesskey: "a",
    display_name: _lt('Activity'),
    icon: 'fa-clock-o',
    config: _.extend({}, BasicView.prototype.config, {
        Controller: ActivityController,
        Model: ActivityModel,
        Renderer: ActivityRenderer,
    }),
    viewType: 'activity',
    searchMenuTypes: ['filter', 'favorite'],

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);

        this.loadParams.type = 'list';
        // limit makes no sense in this view as we display all records having activities
        this.loadParams.limit = false;

        this.rendererParams.templates = _.findWhere(this.arch.children, { 'tag': 'templates' });
    },
});

view_registry.add('activity', ActivityView);

return ActivityView;

});
