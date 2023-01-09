odoo.define('website/static/tests/dashboard_tests', function (require) {
"use strict";

const ControlPanel = require('web.ControlPanel');
const Dashboard = require('website.backend.dashboard');
const testUtils = require("web.test_utils");
const { patch, unpatch } = require('web.utils');

const { createParent, nextTick, prepareTarget } = testUtils;

QUnit.module('Website Backend Dashboard', {
}, function () {
    QUnit.test("mounted is called once for the dashboard's ControlPanel", async function (assert) {
        // This test can be removed as soon as we don't mix legacy and owl layers anymore.
        assert.expect(5);

        patch(ControlPanel.prototype, 'test.ControlPanel', {
            setup() {
                this._super();
                owl.onMounted(() => {
                    assert.step('mounted');
                });
                owl.onWillUnmount(() => {
                    assert.step('willUnmount');
                })
            },
        });

        const params = {
            mockRPC: (route) => {
                if (route === '/website/fetch_dashboard_data') {
                    return Promise.resolve({
                        dashboards: {
                            sales: { summary: {} },
                        },
                        groups: { system: true, website_designer: true },
                        websites: [
                            {id: 1, name: "My Website", domain: "", selected: true},
                        ],
                    });
                }
                return this._super(...arguments);
            },
        };
        const parent = await createParent(params);
        const dashboard = new Dashboard(parent, {});
        await dashboard.appendTo(document.createDocumentFragment());

        assert.verifySteps([]);

        dashboard.$el.appendTo(prepareTarget());
        dashboard.on_attach_callback();

        await nextTick();

        assert.verifySteps(['mounted']);

        dashboard.destroy();
        assert.verifySteps(['willUnmount']);

        unpatch(ControlPanel.prototype, 'test.ControlPanel');
    });
});

});
