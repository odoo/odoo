import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Component, onWillStart, useState } from "@odoo/owl";

class ReportPrintersLocalStorage extends Component {
    static template = "printer.ReportPrintersLocalStorage";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.printersCache = useService("report_printers_cache");
        this.state = useState({
            reports: this.printersCache.cache
                ? Object.keys(this.printersCache.cache)
                : []
        });
        onWillStart(async () => {
            this.state.reportList = await this.orm.searchRead("ir.actions.report", [
                ["id", "in", this.state.reports],
            ]);
        });
    }
    removeFromCache(event, id) {
        this.printersCache.unCacheReport(id);
        this.state.reportList = this.state.reports.filter((report) => report.id !== id);
    }
}

registry.category("actions").add("reset_linked_printers", ReportPrintersLocalStorage);
