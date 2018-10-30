odoo.define('project.PortalForm', function (require) {
"use strict";

// Instantiate a task form
var FormView = require('web.FormView');
var PortalWebclientView = require('project.PortalWebclientView');
var rootWidget = require('root.widget');

var PortalForm = PortalWebclientView.extend({
    template: 'project.portal_task_view_form',
    init: function (parent, params, options) {
        this.accessToken = params.accessToken;
        this.context = params.context;
        this.is_website = params.is_website;
        this.model = 'project.task';
        this.options = options;
        this.options['search'] = false; // cannot search on a form
        this.projectId = params.projectId;
        this.taskId = params.taskId;
        this.templateEdit = 'project.portaledit_view_task_form';
        this.viewType = 'form';
        this.viewName = 'project.task.form';

        this.domain = [['id', '=', this.taskId]];

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
            currentId: this.taskId,
            readOnlyMode: true,
        };

        return new FormView(viewInfo, params)
            .getController(rootWidget);
    },
});

return PortalForm;
});
