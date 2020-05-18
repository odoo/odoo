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

    // CHAT MIXIN
    var ChatMixin = {
        /**
         * @override
         */
        _render: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                var $chat_button = self.$el.find('.o_employee_chat_btn');
                if (self.state.context.uid === self.state.data.user_id.res_id) { // Hide the button for yourself
                    $chat_button.hide();
                }
                else {
                    $chat_button.off('click').on('click', self._onOpenChat.bind(self));
                }
            });
        },

        destroy: function () {
            this.$el.find('.o_employee_chat_btn').off('click');
            return this._super();
        },

        _onOpenChat: function(ev) {
            ev.preventDefault();
            ev.stopImmediatePropagation();
            this.trigger_up('open_chat', {
                partner_id: this.state.data.user_partner_id.res_id
            });
            return true;
        },
    };

    // USAGE OF CHAT MIXIN IN FORM VIEWS
    var EmployeeFormRenderer = FormRenderer.extend(ChatMixin);

    var EmployeeFormController = FormController.extend({
        custom_events: _.extend({}, FormController.prototype.custom_events, {
            open_chat: '_onOpenChat'
        }),

        _onOpenChat: function (ev) {
            this.call('mail_service', 'openDMChatWindow', ev.data.partner_id);
        },
    });

    var EmployeeFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: EmployeeFormController,
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

    var EmployeeKanbanController = KanbanController.extend({
        custom_events: _.extend({}, KanbanController.prototype.custom_events, {
            open_chat: '_onOpenChat'
        }),

        _onOpenChat: function (ev) {
            this.call('mail_service', 'openDMChatWindow', ev.data.partner_id);
        },
    });

    var EmployeeKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: EmployeeKanbanController,
            Renderer: EmployeeKanbanRenderer
        }),
    });

    viewRegistry.add('hr_employee_kanban', EmployeeKanbanView);
});
