odoo.define('project.ProjectFormView', function (require) {
    "use strict";


    var ProjectFormController = require('project.ProjectFormController');
    var FormView = require('web.FormView');
    var viewRegistry = require('web.view_registry');

    var ProjectFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: ProjectFormController,
        }),
    });

    viewRegistry.add('project_form', ProjectFormView);

    return ProjectFormView;
    });
