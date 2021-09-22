odoo.define('google_drive.gdrive_integration', function (require) {
    "use strict";

    const FormView = require('web.FormView');
    const testUtils = require('web.test_utils');

    const cpHelpers = testUtils.controlPanel;

    QUnit.module('Google Drive Integration', {
        beforeEach() {
            this.data = {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char", searchable: true },
                    },
                    records: [
                        { id: 1, display_name: "Locomotive Breath" },
                        { id: 2, display_name: "Hey Macarena" },
                    ],
                },
            };
        },
    }, function () {

        QUnit.module('Google Drive ActionMenus');

        QUnit.test('rendering of the google drive attachments in action menus', async function (assert) {
            assert.expect(3);

            const form = await testUtils.createView({
                actionMenusRegistry: true,
                arch:
                    `<form string="Partners">
                        <field name="display_name"/>
                    </form>`,
                data: this.data,
                async mockRPC(route, args) {
                    switch (route) {
                        case '/web/dataset/call_kw/google.drive.config/get_google_drive_config':
                            assert.deepEqual(args.args, ['partner', 1],
                                'The route to get google drive config should have been called');
                            return [{
                                id: 27,
                                name: 'Cyberdyne Systems',
                            }];
                        case '/web/dataset/call_kw/google.drive.config/search_read':
                            return [{
                                google_drive_resource_id: "T1000",
                                google_drive_client_id: "cyberdyne.org",
                                id: 1,
                            }];
                        case '/web/dataset/call_kw/google.drive.config/get_google_drive_url':
                            assert.deepEqual(args.args, [27, 1, 'T1000'],
                                'The route to get the Google url should have been called');
                            return; // do not return anything or it will open a new tab.
                    }
                },
                model: 'partner',
                res_id: 1,
                View: FormView,
                viewOptions: {
                    hasActionMenus: true,
                },
            });
            await cpHelpers.toggleActionMenu(form);

            assert.containsOnce(form, '.oe_share_gdoc_item',
                "The button to the google action should be present");

            await cpHelpers.toggleMenuItem(form, "Cyberdyne Systems");

            form.destroy();
        });

        QUnit.test("no google drive data", async function (assert) {
            assert.expect(1);

            const form = await testUtils.createView({
                actionMenusRegistry: true,
                arch:
                    `<form string="Partners">
                        <field name="display_name"/>
                    </form>`,
                data: this.data,
                model: 'partner',
                res_id: 1,
                View: FormView,
                viewOptions: {
                    hasActionMenus: true,
                    ids: [1, 2],
                    index: 0,
                },
            });

            assert.containsNone(form, ".o_cp_action_menus .o_embed_menu");

            form.destroy();
        });

        QUnit.test('click on the google drive attachments after switching records', async function (assert) {
            assert.expect(4);

            let currentRecordId = 1;
            const form = await testUtils.createView({
                actionMenusRegistry: true,
                arch:
                    `<form string="Partners">
                        <field name="display_name"/>
                    </form>`,
                data: this.data,
                async mockRPC(route, args) {
                    switch (route) {
                        case '/web/dataset/call_kw/google.drive.config/get_google_drive_config':
                            assert.deepEqual(args.args, ['partner', currentRecordId],
                                'The route to get google drive config should have been called');
                            return [{
                                id: 27,
                                name: 'Cyberdyne Systems',
                            }];
                        case '/web/dataset/call_kw/google.drive.config/search_read':
                            return [{
                                google_drive_resource_id: "T1000",
                                google_drive_client_id: "cyberdyne.org",
                                id: 1,
                            }];
                        case '/web/dataset/call_kw/google.drive.config/get_google_drive_url':
                            assert.deepEqual(args.args, [27, currentRecordId, 'T1000'],
                                'The route to get the Google url should have been called');
                            return; // do not return anything or it will open a new tab.
                    }
                },
                model: 'partner',
                res_id: 1,
                View: FormView,
                viewOptions: {
                    hasActionMenus: true,
                    ids: [1, 2],
                    index: 0,
                },
            });

            await cpHelpers.toggleActionMenu(form);
            await cpHelpers.toggleMenuItem(form, "Cyberdyne Systems");

            currentRecordId = 2;
            await cpHelpers.pagerNext(form);

            await cpHelpers.toggleActionMenu(form);
            await cpHelpers.toggleMenuItem(form, "Cyberdyne Systems");

            form.destroy();
        });
    });
});
