/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { ListController } from '@web/views/list/list_controller';
import { download } from "@web/core/network/download";
var ajax = require('web.ajax');
var Dialog = require('web.Dialog');

patch(ListController.prototype, "CustomListView", {
    /**
     * Duplicate selected records and reload the page.
     */
    async _onDuplicateSelectedRecords() {
        for (var record in this.model.root.records) {
            if (this.model.root.records[record].selected) {
                await this.model.root.records[record].duplicate();
            }
        }
        window.location.reload();
    },
    /**
     * Get the action menu items and add a "Duplicate" option.
     *
     * @returns {Object} Action menu items.
     */
    getActionMenuItems() {
        const actionMenuItems = this._super.apply(this, arguments);
        var self = this;
        if (actionMenuItems) {
            actionMenuItems.other.splice(1, 0, {
                description: this.env._t("Duplicate"),
                callback: (x) => {
                    this._onDuplicateSelectedRecords();
                }
            });
        }
        return actionMenuItems;
    },
    /**
     * Handle the click event for exporting data to a PDF.
     */
    _onClickPDF: async function() {
        var self = this;
        // Retrieve the fields to export
        const fields = this.props.archInfo.columns
            .filter((col) => col.optional === false || col.optional === "show")
            .map((col) => this.props.fields[col.name])
        const exportFields = fields.map((field) => ({
            name: field.name,
            label: field.label || field.string,
        }));
        const resIds = await this.getSelectedResIds();
        var length_field = Array.from(Array(exportFields.length).keys());
        // Make a JSON-RPC request to retrieve the data for the report
        ajax.jsonRpc('/get_data', 'call', {
            'model': this.model.root.resModel,
            'res_ids': resIds.length > 0 && resIds,
            'fields': exportFields,
            'grouped_by': this.model.root.groupBy,
            'context': this.props.context,
            'domain': this.model.root.domain,
            'context': this.props.context,
        }).then(function(data) {
            var model = self.model.root.resModel
            // Generate and download the PDF report
            return self.model.action.doAction({
                type: "ir.actions.report",
                report_type: "qweb-pdf",
                report_name: 'custom_list_view.print_pdf_listview',
                report_file: "custom_list_view.print_pdf_listview",
                data: {
                    'length': length_field,
                    'record': data
                }
            });
        });
    },
    /**
     * Handle the click event for exporting data to Excel.
     */
    _onClickExcel: async function() {
        // Retrieve the fields to export
        const fields = this.props.archInfo.columns
            .filter((col) => col.optional === false || col.optional === "show")
            .map((col) => this.props.fields[col.name])
            .filter((field) => field.exportable !== false);
        const exportFields = fields.map((field) => ({
            name: field.name,
            label: field.label || field.string,
            store: field.store,
            type: field.field_type || field.type,
        }));
        const resIds = await this.getSelectedResIds();
        const import_compat = false
        // Make a request to download the Excel file
        await download({
            data: {
                data: JSON.stringify({
                    import_compat,
                    context: this.props.context,
                    domain: this.model.root.domain,
                    fields: exportFields,
                    groupby: this.model.root.groupBy,
                    ids: resIds.length > 0 && resIds,
                    model: this.model.root.resModel,
                }),
            },
            url: `/web/export/xlsx`,
        });
    },
    /**
     * Handle the click event for exporting data to CSV.
     */
    _onClickCSV: async function() {
        const fields = this.props.archInfo.columns
            .filter((col) => col.optional === false || col.optional === "show")
            .map((col) => this.props.fields[col.name])
            .filter((field) => field.exportable !== false);
        const exportFields = fields.map((field) => ({
            name: field.name,
            label: field.label || field.string,
            store: field.store,
            type: field.field_type || field.type,
        }));
        const resIds = await this.getSelectedResIds();
        const import_compat = false
        // Make a request to download the CSV file
        await download({
            data: {
                data: JSON.stringify({
                    import_compat,
                    context: this.props.context,
                    domain: this.model.root.domain,
                    fields: exportFields,
                    groupby: this.model.root.groupBy,
                    ids: resIds.length > 0 && resIds,
                    model: this.model.root.resModel,
                }),
            },
            url: `/web/export/csv`,
        });
    },
    /**
     * Handle the click event for copying data to the clipboard.
     */
    _onClickCopy: async function() {
        var self = this;
        // Retrieve the fields to export
        const fields = this.props.archInfo.columns
            .filter((col) => col.type === "field")
            .map((col) => this.props.fields[col.name])
        const exportFields = fields.map((field) => ({
            name: field.name,
            label: field.label || field.string,
        }));
        const resIds = await this.getSelectedResIds();
        var length_field = Array.from(Array(exportFields.length).keys());
        // Make a JSON-RPC request to retrieve the data to copy
        ajax.jsonRpc('/get_data/copy', 'call', {
            'model': this.model.root.resModel,
            'res_ids': resIds.length > 0 && resIds,
            'fields': exportFields,
            'grouped_by': this.model.root.groupBy,
            'context': this.props.context,
            'domain': this.model.root.domain,
            'context': this.props.context,
        }).then(function(data) {
            // Format the data as text and copy it to the clipboard
            var recText = data.map(function(record) {
                return record.join("\t"); // Join the elements of each array with tabs ("\t")
            }).join("\n");
            // Copy the recText to the clipboard
            navigator.clipboard.writeText(recText);
            Dialog.alert(self, "Records Copied to Clipboard ", {});
        });
    },
});
