odoo.define('hr.employee_chat', function (require) {
'use strict';
    var viewRegistry = require('web.view_registry');

    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var FormRenderer = require('web.FormRenderer');

    const ListController = require('web.ListController');
    const ListView = require('web.ListView');

    var KanbanController = require('web.KanbanController');
    var KanbanView = require('web.KanbanView');
    var KanbanRenderer = require('web.KanbanRenderer');
    var KanbanRecord = require('web.KanbanRecord');

    const ChatMixin = require('hr.chat_mixin');


    const core = require('web.core');
    const _t = core._t;

    // USAGE OF CHAT MIXIN IN FORM VIEWS
    var EmployeeFormRenderer = FormRenderer.extend(ChatMixin);

    const EmployeeArchiveMixin = {
        _getArchiveAction: function (id) {
            return {
                type: 'ir.actions.act_window',
                name: _t('Employee Termination'),
                res_model: 'hr.departure.wizard',
                views: [[false, 'form']],
                view_mode: 'form',
                target: 'new',
                context: {
                    'active_id': id,
                    'toggle_active': true,
                }
            }
        }
    };

    const EmployeeFormController = FormController.extend(EmployeeArchiveMixin, {
        /**
         * Override the archive action to directly open the departure wizard
         * @override
         * @private
         */
        _getActionMenuItems: function (state) {
            let self = this;
            let actionMenuItems = this._super(...arguments);
            const activeField = this.model.getActiveField(state);
            if (actionMenuItems != null && this.archiveEnabled && activeField in state.data) {
                //This might break in future version, don't see a better way however
                let archiveString = _t("Archive");
                let archiveMenuItem = actionMenuItems.items.other.find(item => {return (item.description === archiveString)});
                if (archiveMenuItem) {
                    archiveMenuItem.callback = () => {self.do_action(
                        self._getArchiveAction(self.model.localIdsToResIds([this.handle])[0]), {
                        on_close: function () {
                            self.update({}, {reload: true});
                        }
                    })}
                }
            }
            return actionMenuItems;
        }
    })

    var EmployeeFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: EmployeeFormController,
            Renderer: EmployeeFormRenderer
        }),
    });

    viewRegistry.add('hr_employee_form', EmployeeFormView);

    const EmployeeListController = ListController.extend(EmployeeArchiveMixin, {
        /**
         * Override the archive action to directly open the departure wizard
         * @override
         * @private
         */
        _getActionMenuItems: function (state) {
            let self = this;
            let actionMenuItems = this._super(...arguments);
            if (actionMenuItems != null && this.archiveEnabled) {
                //This might break in future version, don't see a better way however
                let archiveString = _t("Archive");
                let archiveMenuItem = actionMenuItems.items.other.find(item => {return (item.description === archiveString)});
                if (archiveMenuItem) {
                    //On this one we want the default action when multiple are selected
                    let originalCallback = archiveMenuItem.callback;
                    archiveMenuItem.callback = () => {
                        let records = self.getSelectedRecords()
                        if (records.length == 1 && records[0].data.active === true) {
                            self.do_action(
                                self._getArchiveAction(records[0].res_id), {
                                on_close: function () {
                                    self.update({}, {reload: true});
                                }
                            })
                        } else {
                            originalCallback();
                        }
                    };
                }
            }
            return actionMenuItems;
        }
    });

    const EmployeeListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: EmployeeListController,
        })
    })

    viewRegistry.add('hr_employee_list', EmployeeListView);

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
