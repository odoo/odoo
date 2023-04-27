odoo.define('base_automation.BaseAutomatioErrorDialog', function (require) {
    "use strict";

    const CrashManager = require('web.CrashManager');
    const ErrorDialog = CrashManager.ErrorDialog;
    const ErrorDialogRegistry = require('web.ErrorDialogRegistry');
    const session = require('web.session');

    const BaseAutomationErrorDialog = ErrorDialog.extend({
        xmlDependencies: (ErrorDialog.prototype.xmlDependencies || []).concat(
            ['/base_automation/static/src/xml/base_automation_error_dialog.xml']
        ),
        template: 'CrashManager.BaseAutomationError',
        events: {
            'click .o_disable_action_button': '_onDisableAction',
            'click .o_edit_action_button': '_onEditAction',
        },
        /**
        * Assign the `base_automation` object based on the error data,
        * which is then used by the `CrashManager.BaseAutomationError` template
        * and the events defined above.
        * @override
        * @param {Object} error
        * @param {string} error.data.context.base_automation.id  the ID of the failing automated action
        * @param {string} error.data.context.base_automation.name  the name of the failing automated action
        */
        init: function (parent, options, error) {
            this._super.apply(this, arguments);
            this.base_automation = error.data.context.base_automation;
            this.is_admin = session.is_admin;
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
        * This method is called when the user clicks on the 'Disable action' button
        * displayed when a crash occurs in the evaluation of an automated action.
        * Then, we write `active` to `False` on the automated action to disable it.
        *
        * @private
        * @param {MouseEvent} ev
        */
        _onDisableAction: function (ev) {
            ev.preventDefault();
            this._rpc({
                model: 'base.automation',
                method: 'write',
                args: [[this.base_automation.id], {
                    active: false,
                }],
            }).then(this.destroy.bind(this));
        },
        /**
        * This method is called when the user clicks on the 'Edit action' button
        * displayed when a crash occurs in the evaluation of an automated action.
        * Then, we redirect the user to the automated action form.
        *
        * @private
        * @param {MouseEvent} ev
        */
        _onEditAction: function (ev) {
            ev.preventDefault();
            this.do_action({
                name: 'Automated Actions',
                res_model: 'base.automation',
                res_id: this.base_automation.id,
                views: [[false, 'form']],
                type: 'ir.actions.act_window',
                view_mode: 'form',
            });
        },
    });

    ErrorDialogRegistry.add('base_automation', BaseAutomationErrorDialog);

});
