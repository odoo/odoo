odoo.define('stock.stock_traceability_report_backend_tests', function (require) {
    "use strict";

    const LegacyControlPanel = require('web.ControlPanel');
    const { ControlPanel } = require("@web/search/control_panel/control_panel");
    const dom = require('web.dom');
    const StockReportGeneric = require('stock.stock_report_generic');
    const testUtils = require('web.test_utils');

    const { dom: domUtils } = testUtils;
    const {
        destroy,
        getFixture,
        legacyExtraNextTick,
        patchWithCleanup,
    } = require("@web/../tests/helpers/utils");
    const { createWebClient, doAction } = require('@web/../tests/webclient/helpers');

    const { onMounted, onWillUnmount } = owl;

    /**
     * Helper function to instantiate a stock report action.
     * @param {Object} params
     * @param {Object} params.action
     * @param {boolean} [params.debug]
     * @returns {Promise<StockReportGeneric>}
     */
    async function createStockReportAction(params) {
        const parent = await testUtils.createParent(params);
        const report = new StockReportGeneric(parent, params.action);
        const target = testUtils.prepareTarget(params.debug);

        const _destroy = report.destroy;
        report.destroy = function () {
            report.destroy = _destroy;
            parent.destroy();
        };
        const fragment = document.createDocumentFragment();
        await report.appendTo(fragment);
        dom.prepend(target, fragment, {
            callbacks: [{ widget: report }],
            in_DOM: true,
        });
        // Wait for the ReportWidget to be appended
        await testUtils.nextTick();

        return report;
    }

    QUnit.module('Stock', {}, function () {
        QUnit.module('Traceability report');

        QUnit.test("Rendering with no lines", async function (assert) {
            assert.expect(1);

            const template = `
                <div class="container-fluid o_stock_reports_page o_stock_reports_no_print">
                    <div class="o_stock_reports_table table-responsive">
                        <span class="text-center">
                            <h1>No operation made on this lot.</h1>
                        </span>
                    </div>
                </div>`;
            const report = await createStockReportAction({
                action: {
                    context: {},
                    params: {},
                },
                data: {
                    'stock.traceability.report': {
                        fields: {},
                        get_html: () => ({ html: template }),
                    },
                },
            });

            // HTML content is nested in a div inside of the content
            assert.strictEqual(report.el.querySelector('.o_content > div').innerHTML, template,
                "Displayed template should match");

            report.destroy();
        });

        QUnit.test("mounted is called once when returning on 'Stock report' from breadcrumb", async assert => {
            // This test can be removed as soon as we don't mix legacy and owl layers anymore.
            assert.expect(7);

            let mountCount = 0;

            patchWithCleanup(ControlPanel.prototype, {
                setup() {
                    this._super();
                    onMounted(() => {
                        mountCount = mountCount + 1;
                        this.__uniqueId = mountCount;
                        assert.step(`mounted ${this.__uniqueId}`);
                    });
                    onWillUnmount(() => {
                        assert.step(`willUnmount ${this.__uniqueId}`);
                    });
                },
            });

            patchWithCleanup(LegacyControlPanel.prototype, {
                setup() {
                    this._super();
                    onMounted(() => {
                        mountCount = mountCount + 1;
                        this.__uniqueId = mountCount;
                        assert.step(`mounted ${this.__uniqueId} (legacy)`);
                    });
                    onWillUnmount(() => {
                        assert.step(`willUnmount ${this.__uniqueId} (legacy)`);
                    });
                },
            });
            const serverData = {
                models: {
                    partner: {
                        fields: {
                            display_name: { string: "Displayed name", type: "char" },
                        },
                        records: [
                            {id: 1, display_name: "Genda Swami"},
                        ],
                    },
                },
                views: {
                    'partner,false,form': '<form><field name="display_name"/></form>',
                    'partner,false,search': '<search></search>',
                },
                actions: {
                    42: {
                        id: 42,
                        name: "Stock report",
                        tag: 'stock_report_generic',
                        type: 'ir.actions.client',
                        context: {},
                        params: {},
                    },
                },
            };

            const target = getFixture();
            const webClient = await createWebClient({
                serverData,
                mockRPC: function (route) {
                    if (route === '/web/dataset/call_kw/stock.traceability.report/get_html') {
                        return Promise.resolve({
                            html: '<a class="o_stock_reports_web_action" href="#" data-active-id="1" data-res-model="partner">Go to form view</a>',
                        });
                    }
                },
            });

            await doAction(webClient, 42);
            await domUtils.click(target.querySelector('.o_stock_reports_web_action'));
            await legacyExtraNextTick();
            await domUtils.click(target.querySelector('.breadcrumb-item'));
            await legacyExtraNextTick();

            destroy(webClient);

            assert.verifySteps([
                'mounted 1 (legacy)',
                'willUnmount 1 (legacy)',
                'mounted 2',
                'willUnmount 2',
                'mounted 3 (legacy)',
                'willUnmount 3 (legacy)',
            ]);
        });
    });
});
