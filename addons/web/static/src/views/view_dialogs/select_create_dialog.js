/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { View } from "@web/views/view";
import { escape } from "@web/core/utils/strings";

import { FormViewDialog } from "./form_view_dialog";

import { Component, markup, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class SelectCreateDialog extends Component {
    setup() {
        this.viewService = useService("view");
        this.dialogService = useService("dialog");
        this.state = useState({ resIds: [] });
        // ℹ️ `_t` can only be inlined directly inside JS template literals
        // after Babel has been updated to version 2.12.
        const translatedText = _t("No records found!");
        this.baseViewProps = {
            display: { searchPanel: false },
            editable: false, // readonly
            noBreadcrumbs: true,
            noContentHelp: markup(`<p>${escape(translatedText)}</p>`),
            showButtons: false,
            selectRecord: (resId) => this.select([resId]),
            onSelectionChanged: (resIds) => {
                this.state.resIds = resIds;
            },
        };
    }

    get viewProps() {
        const type = this.env.isSmall ? "kanban" : "list";
        const props = {
            loadIrFilters: true,
            ...this.baseViewProps,
            context: this.props.context,
            domain: this.props.domain,
            dynamicFilters: this.props.dynamicFilters,
            resModel: this.props.resModel,
            searchViewId: this.props.searchViewId,
            type,
        };
        if (type === "list") {
            props.allowSelectors = this.props.multiSelect;
        } else if (type === "kanban") {
            props.forceGlobalClick = true;
        }
        return props;
    }

    async select(resIds) {
        if (this.props.onSelected) {
            await this.props.onSelected(resIds);
            this.props.close();
        }
    }

    async unselect() {
        if (this.props.onUnselect) {
            await this.props.onUnselect();
            this.props.close();
        }
    }

    get canUnselect() {
        return this.env.isSmall && !!this.props.onUnselect;
    }

    async createEditRecord() {
        if (this.props.onCreateEdit) {
            await this.props.onCreateEdit();
            this.props.close();
        } else {
            this.dialogService.add(FormViewDialog, {
                context: this.props.context,
                resModel: this.props.resModel,
                onRecordSaved: (record) => {
                    this.props.onSelected([record.resId]);
                    this.props.close();
                },
            });
        }
    }
}
SelectCreateDialog.components = { Dialog, View };
SelectCreateDialog.template = "web.SelectCreateDialog";
SelectCreateDialog.props = {
    context: { type: Object, optional: true },
    domain: { type: Array, optional: true },
    dynamicFilters: { type: Array, optional: true },
    resModel: String,
    searchViewId: { type: [Number, { value: false }], optional: true },
    multiSelect: { type: Boolean, optional: true },
    onSelected: { type: Function, optional: true },
    close: { type: Function, optional: true },
    onCreateEdit: { type: Function, optional: true },
    title: { type: String, optional: true },
    noCreate: { type: Boolean, optional: true },
    onUnselect: { type: Function, optional: true },
};
SelectCreateDialog.defaultProps = {
    dynamicFilters: [],
    multiSelect: true,
    searchViewId: false,
    domain: [],
    context: {},
};

registry.category("dialogs").add("select_create", SelectCreateDialog);
