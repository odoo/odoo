odoo.define('stock.stock_traceability_report_backend_tests', function (require) {
    "use strict";

    const dom = require('web.dom');
    const StockReportGeneric = require('stock.stock_report_generic');
    const testUtils = require('web.test_utils');

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
    });
});
