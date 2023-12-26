odoo.define('hr.employee_chat', function (require) {
'use strict';
    var viewRegistry = require('web.view_registry');

    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var FormRenderer = require('web.FormRenderer');

    var KanbanController = require('web.KanbanController');
    var KanbanView = require('web.KanbanView');
    var KanbanRenderer = require('web.KanbanRenderer');
    var KanbanRecord = require('web.KanbanRecord');

    const { Component } = owl;

    // CHAT MIXIN
    var ChatMixin = {
        /**
         * @override
         */
        _render: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                var $chat_button = self.$el.find('.o_employee_chat_btn');
                $chat_button.off('click').on('click', self._onOpenChat.bind(self));
            });
        },

        destroy: function () {
            if (this.$el) {
                this.$el.find('.o_employee_chat_btn').off('click');
            }
            return this._super();
        },

        _onOpenChat: function (ev) {
            ev.preventDefault();
            ev.stopImmediatePropagation();
            const env = Component.env;
            env.messaging.openChat({ employeeId: this.state.data.id });
            return true;
        },
    };

    // USAGE OF CHAT MIXIN IN FORM VIEWS
    var EmployeeFormRenderer = FormRenderer.extend(ChatMixin);

    var EmployeeFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: FormController,
            Renderer: EmployeeFormRenderer
        }),
    });

    viewRegistry.add('hr_employee_form', EmployeeFormView);

    // USAGE OF CHAT MIXIN IN KANBAN VIEWS
    var EmployeeKanbanRecord = KanbanRecord.extend(ChatMixin);

    var EmployeeKanbanRenderer = KanbanRenderer.extend({
        config: Object.assign({}, KanbanRenderer.prototype.config, {
            KanbanRecord: EmployeeKanbanRecord,
        }),
    });

    var EmployeeKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: KanbanController,
            Renderer: EmployeeKanbanRenderer
        }),
    });

    viewRegistry.add('hr_employee_kanban', EmployeeKanbanView);
});
