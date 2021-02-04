odoo.define('web/static/tests/report/client_action_tests', function (require) {
    "use strict";

    const ControlPanel = require('web.ControlPanel');
    const ReportClientAction = require('report.client_action');
    const testUtils = require("web.test_utils");

    const { createActionManager, dom, mock } = testUtils;

    QUnit.module('Client Action Report', {}, () => {
        QUnit.test("mounted is called once when returning on 'Client Action Report' from breadcrumb", async assert => {
            // This test can be removed as soon as we don't mix legacy and owl layers anymore.
            assert.expect(7);

            let mountCount = 0;

            // patch the report client action to override its iframe's url so that
            // it doesn't trigger an RPC when it is appended to the DOM (for this
            // usecase, using removeSRCAttribute doesn't work as the RPC is
            // triggered as soon as the iframe is in the DOM, even if its src
            // attribute is removed right after)
            mock.patch(ReportClientAction, {
                start: function () {
                    var self = this;
                    return this._super.apply(this, arguments).then(function () {
                        self._rpc({route: self.iframe.getAttribute('src')});
                        self.iframe.setAttribute('src', 'about:blank');
                    });
                }
            });

            ControlPanel.patch('test.ControlPanel', T => {
                class ControlPanelPatchTest extends T {
                    mounted() {
                        mountCount = mountCount + 1;
                        this.__uniqueId = mountCount;
                        assert.step(`mounted ${this.__uniqueId}`);
                        super.mounted(...arguments);
                    }
                    willUnmount() {
                        assert.step(`willUnmount ${this.__uniqueId}`);
                        super.mounted(...arguments);
                    }
                }
                return ControlPanelPatchTest;
            });
            const actionManager = await createActionManager({
                actions: [
                    {
                        id: 42,
                        name: "Client Action Report",
                        tag: 'report.client_action',
                        type: 'ir.actions.report',
                        report_type: 'qweb-html',
                    },
                    {
                        id: 43,
                        type: "ir.actions.act_window",
                        res_id: 1,
                        res_model: "partner",
                        views: [
                            [false, "form"],
                        ],
                    }
                ],
                archs: {
                    'partner,false,form': '<form><field name="display_name"/></form>',
                    'partner,false,search': '<search></search>',
                },
                data: {
                    partner: {
                        fields: {
                            display_name: { string: "Displayed name", type: "char" },
                        },
                        records: [
                            {id: 1, display_name: "Genda Swami"},
                        ],
                    },
                },
                mockRPC: function (route) {
                    if (route === '/report/html/undefined?context=%7B%7D') {
                        return Promise.resolve('<a action="go_to_details">Go to detail view</a>');
                    }
                    return this._super.apply(this, arguments);
                },
                intercepts: {
                    do_action: ev => actionManager.doAction(ev.data.action, ev.data.options),
                },
            });

            await actionManager.doAction(42);
            // simulate an action as we are not able to reproduce a real doAction using 'Client Action Report'
            await actionManager.doAction(43);
            await dom.click(actionManager.$('.breadcrumb-item:first'));
            actionManager.destroy();

            assert.verifySteps([
                'mounted 1',
                'willUnmount 1',
                'mounted 2',
                'willUnmount 2',
                'mounted 3',
                'willUnmount 3',
            ]);

            ControlPanel.unpatch('test.ControlPanel');
            mock.unpatch(ReportClientAction);
        });
    });

});
