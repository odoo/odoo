/** @odoo-module */
import { Component, useState } from "@odoo/owl";

import { Pager } from "@web/core/pager/pager";
import { RecordSelector } from "@web/core/record_selectors/record_selector";

export class ReportRecordNavigation extends Component {
    static components = { RecordSelector, Pager };
    static template = "web_studio.ReportEditor.ReportRecordNavigation";
    static props = {};

    setup() {
        this.reportEditorModel = useState(this.env.reportEditorModel);
    }

    get multiRecordSelectorProps() {
        const currentId = this.reportEditorModel.reportEnv.currentId;
        return {
            resModel: this.reportEditorModel.reportResModel,
            update: (resId) => {
                this.reportEditorModel.loadReportHtml({ resId });
            },
            resId: currentId,
            domain: this.reportEditorModel.getModelDomain(),
            context: { studio: false },
        };
    }

    get pagerProps() {
        const { reportEnv } = this.reportEditorModel;
        const { ids, currentId } = reportEnv;
        return {
            limit: 1,
            offset: ids.indexOf(currentId),
            total: ids.length,
        };
    }

    updatePager({ offset }) {
        const ids = this.reportEditorModel.reportEnv.ids;
        const resId = ids[offset];
        this.reportEditorModel.loadReportHtml({ resId });
    }
}
