odoo.define('base_automation.BaseAutomatioErrorDialogTests', function (require) {
'use strict';

    const CrashManager = require('web.CrashManager').CrashManager;
    const session = require('web.session');

    QUnit.module('base_automation', {}, function () {

        QUnit.module('Error Dialog');

        QUnit.test('Error due to an automated action', async function (assert) {
            assert.expect(4);

            let baseAutomationName = 'Test base automation error dialog';
            let error = {
                type: 'Odoo Client Error',
                message: 'Message',
                data: {
                    debug: 'Traceback',
                    context: {
                        exception_class: 'base_automation',
                        base_automation: {
                            id: 1,
                            name: baseAutomationName,
                        },
                    },
                },
            };
            // Force the user session to be admin, to display the disable and edit action buttons,
            // then reset back to the origin value after the test.
            let isAdmin = session.is_admin;
            session.is_admin = true;

            let crashManager = new CrashManager();
            let dialog = crashManager.show_error(error);

            await dialog._opened;

            assert.containsOnce(document.body, '.modal .o_clipboard_button');
            assert.containsOnce(document.body, '.modal .o_disable_action_button');
            assert.containsOnce(document.body, '.modal .o_edit_action_button');
            assert.ok(dialog.$el.text().indexOf(baseAutomationName) !== -1);

            session.is_admin = isAdmin;
            crashManager.destroy();
        });

        QUnit.test('Error not due to an automated action', async function (assert) {
            assert.expect(3);

            let error = {
                type: 'Odoo Client Error',
                message: 'Message',
                data: {
                    debug: 'Traceback',
                },
            };
            let crashManager = new CrashManager();
            let dialog = crashManager.show_error(error);

            await dialog._opened;

            assert.containsOnce(document.body, '.modal .o_clipboard_button');
            assert.containsNone(document.body, '.modal .o_disable_action_button');
            assert.containsNone(document.body, '.modal .o_edit_action_button');

            crashManager.destroy();
        });

    });

});
