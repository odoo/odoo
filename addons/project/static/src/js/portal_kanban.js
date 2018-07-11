odoo.define('project.PortalKanban', function (require) {
"use strict";

var KanbanView = require('web.KanbanView');
var PortalWebclientView = require('project.PortalWebclientView');

var PortalKanban = PortalWebclientView.extend({
    custom_events: _.extend({}, PortalWebclientView.prototype.custom_events, {
        saveKanbanTask: '_onSaveKanbanTask',
    }),
    template: 'project.portal_task_view_kanban',
    init: function (parent, params, options) {
        this.accessToken = params.accessToken;
        this.actionXmlId = 'project.action_portal_project_all_tasks';
        this.context = params.context;
        this.is_website = params.is_website;
        this.model = 'project.task';
        this.options = options;
        this.projectId = params.projectId;
        this.templateEdit = 'project.portaledit_view_task_kanban';
        this.viewType = 'kanban';
        this.viewName = 'project.task.kanban';

        this.domain = [['project_id', '=', this.projectId]];

        this._super.apply(this, arguments);
    },
    /**
     * Create a controller for a given view, and make sure that
     * data and libraries are loaded.
     *
     * @param {Object} viewInfo the result of a fields_view_get() method of a model
     * @param {string[]} domain (optional)
     * @returns {Deferred} The deferred resolves to a controller
     */
    _getController: function (viewInfo, domain) {
        domain = domain || this.domain;
        var params = {
            modelName: this.model,
            domain: domain,
            context: this.context,
            readOnlyMode: true,
        };

        var view = new KanbanView(viewInfo, params);

        return view.getController(this);
    },
    /**
     * @param {OdooEvent} event
     * @param {number} event.data.taskId
     */
    _onSaveKanbanTask: function (event) {
        this.currentlyEditedTask = event.data.taskId;
    },
});

return PortalKanban;
});
