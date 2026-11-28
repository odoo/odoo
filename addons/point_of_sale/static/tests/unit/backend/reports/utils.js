import { useSubEnv } from "@odoo/owl";
import { mockService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { getDefaultConfig } from "@web/views/view";
import { PosReport } from "@point_of_sale/pos_reports/pos_report";

class TestPosReport extends PosReport {
    setup() {
        useSubEnv({ config: getDefaultConfig() });
        super.setup();
    }
}

export async function openReport(report_id = 1, context = {}, params = {}) {
    mockService("pos", () => ({}));
    const component = await mountWithCleanup(TestPosReport, {
        props: {
            action: {
                type: "ir.actions.client",
                tag: "pos_report",
                name: "POS Report",
                params,
                context: { report_id: report_id, ...context },
            },
        },
    });
    return component.report;
}
