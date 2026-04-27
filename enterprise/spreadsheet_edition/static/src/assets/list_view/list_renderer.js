/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import { user } from "@web/core/user";
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
        this.actionService = useService("action");
        useBus(this.env.bus, "insert-list-spreadsheet", this.insertListSpreadsheet.bind(this));
    },

    async insertListSpreadsheet() {
        const model = this.env.model.root;
        const count = model.groups
            ? model.groups.reduce((acc, group) => group.count + acc, 0)
            : model.count;
        const selection = await model.getResIds(true);
        const threshold = selection.length > 0 ? selection.length : Math.min(count, model.limit);
        let name = this.env.config.getDisplayName();
        const sortBy = model.orderBy[0]?.name;
        const groupBy = model.groupBy[0];
        if (sortBy || groupBy) {
            name = _t("%(field name)s by %(order)s", {
                "field name": name,
                order: model.fields[sortBy]?.string ?? groupBy,
            });
        }
        const { list, fields } = await this.getListForSpreadsheet(name);

        // if some records are selected, we replace the domain with a "id in [selection]" clause
        if (selection.length > 0) {
            list.domain = [["id", "in", selection]];
        }
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
        return this.columns
            .filter(
                (col) =>
                    col.type === "field" &&
                    col.field.component !== HandleField &&
                    !col.relatedPropertyField &&
                    !["binary", "json"].includes(fields[col.name].type)
            )
            .map((col) => ({ name: col.name, type: fields[col.name].type }));
    },

    async getListForSpreadsheet(name) {
        const model = this.env.model.root;
        const { actionId } = this.env.config;
        const { xml_id } = actionId ? await this.actionService.loadAction(actionId, this.props.list.context) : {};
        // Remove the `group_by` instructions
        const fieldNames = model.fieldNames;
        const filteredOrderBy = (model.orderBy).filter(order => fieldNames.includes(order.name));
        return {
            list: {
                model: model.resModel,
                domain: this.env.searchModel.domainString,
                orderBy: filteredOrderBy,
                context: omit(model.context, ...Object.keys(user.context)),
                columns: this.getColumnsForSpreadsheet(),
                name,
                actionXmlId: xml_id,
            },
            fields: model.fields,
        };
    },
});
