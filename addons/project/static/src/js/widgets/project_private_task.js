/** @odoo-module alias=project.project_private_task **/
"use strict";

import field_registry from 'web.field_registry';
import { FieldMany2One } from 'web.relational_fields';
import core from 'web.core';

const QWeb = core.qweb;

const ProjectPrivateTask = FieldMany2One.extend({
    /**
     * @override
     * @private
     */
    _renderReadonly: function() {
        this._super.apply(this, arguments);
        if (!this.m2o_value) {
            this.$el.empty();
            this.$el.append(QWeb.render('project.task.PrivateProjectName'));
            this.$el.addClass('pe-none');
        }
    },
});

field_registry.add('project_private_task', ProjectPrivateTask);
