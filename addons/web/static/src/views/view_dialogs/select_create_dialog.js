/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { View } from "@web/views/view";
import { escape } from "@web/core/utils/strings";

import { FormViewDialog } from "./form_view_dialog";

import { Component, markup, useState } from "@odoo/owl";

export class SelectCreateDialog extends Component {
    setup() {
        this.viewService = useService("view");
        this.dialogService = useService("dialog");
        this.state = useState({ resIds: [] });
        this.baseViewProps = {
            display: { searchPanel: false },
            editable: false, // readonly
            noBreadcrumbs: true,
            noContentHelp: markup(`<p>${escape(this.env._t("No records found!"))}</p>`),
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

SelectCreateDialog.defaultProps = {
    dynamicFilters: [],
    multiSelect: true,
    searchViewId: false,
    type: "list",
};

/**
 * Props: (to complete)
 *
 * resModel
 * domain
 * context
 * title
 * onSelected
 * type
 */
