odoo.define('mail.ActivityView', function (require) {
"use strict";

const ActivityController = require('mail.ActivityController');
const ActivityModel = require('mail.ActivityModel');
const ActivityRenderer = require('mail.ActivityRenderer');
const BasicView = require('web.BasicView');
const core = require('web.core');
const RendererWrapper = require('web.RendererWrapper');
const view_registry = require('web.view_registry');

const _lt = core._lt;

const ActivityView = BasicView.extend({
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
        this.controllerParams.title = this.arch.attrs.string;
    },
    /**
     *
     * @override
     */
    getRenderer(parent, state) {
        state = Object.assign({}, state, this.rendererParams);
        return new RendererWrapper(null, this.config.Renderer, state);
    },
});

view_registry.add('activity', ActivityView);

return ActivityView;

});
