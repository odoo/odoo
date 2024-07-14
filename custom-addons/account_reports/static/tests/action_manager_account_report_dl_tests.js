/** @odoo-module **/

import { mockDownload } from "@web/../tests/helpers/utils";

import { createWebClient, doAction } from "@web/../tests/webclient/helpers";

let serverData;
QUnit.module('Account Reports', {}, function () {
    QUnit.test('can execute account report download actions', async function (assert) {
        assert.expect(5);

        const actions = {
            1: {
                id: 1,
                data: {
                    model: 'some_model',
                    options: {
                        someOption: true,
                    },
                    output_format: 'pdf',
                },
                type: 'ir_actions_account_report_download',
            },
        };
        serverData = {actions};
        mockDownload((options) => {
            assert.step(options.url);
            assert.deepEqual(options.data, {
                model: 'some_model',
                options: {
                    someOption: true,
                },
                output_format: 'pdf',
            }, "should give the correct data");
            return Promise.resolve();
        });
        const webClient = await createWebClient({
            serverData,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
            },
        });
        await doAction(webClient, 1);

        assert.verifySteps([
            '/web/webclient/load_menus',
            '/web/action/load',
            '/account_reports',
        ]);

    });
});
