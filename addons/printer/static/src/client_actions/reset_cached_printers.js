import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Component, onWillStart, proxy } from "@odoo/owl";

class ReportPrintersLocalStorage extends Component {
    static template = "printer.ReportPrintersLocalStorage";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.printersCache = useService("report_printers_cache");
        this.state = proxy({ reports: [] });

        onWillStart(async () => {
            this.state.reports = await this.orm.searchRead("ir.actions.report", [
                ["id", "in", Object.keys(this.printersCache.cache || [])],
            ]);
        });
    }
    removeFromCache(id) {
        this.printersCache.unCacheReport(id);
        this.state.reports = this.state.reports.filter((report) => report.id !== id);
    }
}

registry.category("actions").add("reset_linked_printers", ReportPrintersLocalStorage);
