/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useService, useBus } from "@web/core/utils/hooks";
import { omit } from "@web/core/utils/objects";
import { SpreadsheetSelectorDialog } from "../components/spreadsheet_selector_dialog/spreadsheet_selector_dialog";
import { HandleField } from "@web/views/fields/handle/handle_field";
import { _t } from "@web/core/l10n/translation";

patch(ListRenderer.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        this.dialogService = useService("dialog");
        this.userService = useService("user");
        useBus(this.env.bus, "insert-list-spreadsheet", this.insertListSpreadsheet.bind(this));
    },

    insertListSpreadsheet() {
        const model = this.env.model.root;
        const count = model.groups
            ? model.groups.reduce((acc, group) => group.count + acc, 0)
            : model.count;
        const threshold = Math.min(count, model.limit);
        let name = this.env.config.getDisplayName();
        const sortBy = model.orderBy[0];
        if (sortBy) {
            name = _t("%(field name)s by %(order)s", {
                "field name": name,
                order: model.fields[sortBy.name].string,
            });
        }
        const { list, fields } = this.getListForSpreadsheet(name);
        const actionOptions = {
            preProcessingAsyncAction: "insertList",
            preProcessingAsyncActionData: { list, threshold, fields },
        };
        const params = {
            threshold,
            type: "LIST",
            name,
            actionOptions,
        };
        this.dialogService.add(SpreadsheetSelectorDialog, params);
    },

    getColumnsForSpreadsheet() {
        const fields = this.env.model.root.fields;
        return this.state.columns
            .filter(
                (col) =>
                    col.type === "field" &&
                    col.field.component !== HandleField &&
                    !col.relatedPropertyField &&
                    !["binary", "json"].includes(fields[col.name].type)
            )
            .map((col) => ({ name: col.name, type: fields[col.name].type }));
    },

    getListForSpreadsheet(name) {
        const model = this.env.model.root;
        return {
            list: {
                model: model.resModel,
                domain: this.env.searchModel.domainString,
                orderBy: model.orderBy,
                context: omit(model.context, ...Object.keys(this.userService.context)),
                columns: this.getColumnsForSpreadsheet(),
                name,
            },
            fields: model.fields,
        };
    },
});
