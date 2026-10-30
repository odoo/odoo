import { patch } from "@web/core/utils/patch";
import { PosReportFilters } from "@point_of_sale/pos_reports/components/filters/filters";

patch(PosReportFilters.prototype, {
    get extraOptions() {
        const options = super.extraOptions;

        if (this.report.meta().handler !== "pos.sales.detail.report") {
            return options;
        }

        return [
            ...options,
            {
                name: "Export Employee-wise",
                active: !!this.report.options().employee_wise,
                onSelect: () => {
                    this.report.options.set({
                        ...this.report.options(),
                        employee_wise: !this.report.options().employee_wise,
                    });
                },
            },
        ];
    },
});
