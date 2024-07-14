/** @odoo-module **/

import { registry } from "@web/core/registry";
import { PivotRenderer } from "@web/views/pivot/pivot_renderer";
import { intersection, unique } from "@web/core/utils/arrays";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { PERIODS } from "@spreadsheet_edition/assets/helpers";
import { omit } from "@web/core/utils/objects";

import { _t } from "@web/core/l10n/translation";
import { SpreadsheetSelectorDialog } from "@spreadsheet_edition/assets/components/spreadsheet_selector_dialog/spreadsheet_selector_dialog";

import { onWillStart } from "@odoo/owl";

patch(PivotRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this.userService = useService("user");
        this.notification = useService("notification");
        this.actionService = useService("action");
        onWillStart(async () => {
            const insertionGroups = registry.category("spreadsheet_view_insertion_groups").getAll();
            const userGroups = await Promise.all(
                insertionGroups.map((group) => this.userService.hasGroup(group))
            );
            this.canInsertPivot = userGroups.some((group) => group);
        });
    },

    onInsertInSpreadsheet() {
        let name = this.model.metaData.title;
        const groupBy =
            this.model.metaData.fullColGroupBys[0] || this.model.metaData.fullRowGroupBys[0];
        if (groupBy) {
            let [field, period] = groupBy.split(":");
            period = PERIODS[period];
            if (period) {
                name = _t("%(name)s by %(field)s (%(period)s)", {
                    name,
                    field: this.model.metaData.fields[field].string,
                    period,
                });
            } else {
                name = _t("%(name)s by %(field)s", {
                    name,
                    field: this.model.metaData.fields[field].string,
                });
            }
        }
        const actionOptions = {
            preProcessingAsyncAction: "insertPivot",
            preProcessingAsyncActionData: {
                data: this.model.data,
                metaData: this.model.metaData,
                searchParams: {
                    ...this.model.searchParams,
                    domain: this.env.searchModel.domainString,
                    context: omit(
                        this.model.searchParams.context,
                        ...Object.keys(this.userService.context),
                        "pivot_measures",
                        "pivot_row_groupby",
                        "pivot_column_groupby"
                    ),
                },
                name,
            },
        };
        const params = {
            type: "PIVOT",
            name,
            actionOptions,
        };
        this.env.services.dialog.add(SpreadsheetSelectorDialog, params);
    },

    hasDuplicatedGroupbys() {
        const fullColGroupBys = this.model.metaData.fullColGroupBys;
        const fullRowGroupBys = this.model.metaData.fullRowGroupBys;
        // without aggregator
        const colGroupBys = fullColGroupBys.map((el) => el.split(":")[0]);
        const rowGroupBys = fullRowGroupBys.map((el) => el.split(":")[0]);
        return (
            unique([...fullColGroupBys, ...fullRowGroupBys]).length <
                fullColGroupBys.length + fullRowGroupBys.length ||
            // can group by the same field with different aggregator in the same dimension
            intersection(colGroupBys, rowGroupBys).length
        );
    },

    isInsertButtonDisabled() {
        return (
            !this.model.hasData() ||
            this.model.metaData.activeMeasures.length === 0 ||
            this.model.useSampleModel ||
            this.hasDuplicatedGroupbys()
        );
    },

    getInsertButtonTooltip() {
        return this.hasDuplicatedGroupbys() ? _t("Pivot contains duplicate groupbys") : undefined;
    },
});
