/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { View } from "@web/views/view";

const { Component, markup, useState } = owl;

export class SelectCreateDialog extends Component {
    setup() {
        this.viewService = useService("view");
        this.state = useState({ resIds: [] });
        this.viewProps = {
            viewId: (this.props.context && this.props.context.tree_view_ref) || false,
            resModel: this.props.resModel,
            domain: this.props.domain,
            context: this.props.context,
            type: "list", // could be kanban
            editable: false, // readonly
            showButtons: false,
            hasSelectors: this.props.multiSelect,
            selectRecord: async (resId) => {
                if (this.props.onSelected) {
                    await this.props.onSelected([resId]);
                    this.props.close();
                }
            },
            onSelectionChanged: (resIds) => {
                this.state.resIds = resIds;
            },
            noBreadcrumbs: true,
            searchViewId: this.props.searchViewId || false,
            display: { searchPanel: false },
            noContentHelp: markup(`<p>${this.env._t("No records found!")}</p>`),
            dynamicFilters: this.props.dynamicFilters || [],
        };
    }

    async select() {
        if (this.props.onSelected) {
            await this.props.onSelected(this.state.resIds);
            this.props.close();
        }
    }
    async createEditRecord() {
        if (this.props.onCreateEdit) {
            await this.props.onCreateEdit();
            this.props.close();
        }
    }
}
SelectCreateDialog.components = { Dialog, View };
SelectCreateDialog.template = "web.SelectCreateDialog";

SelectCreateDialog.defaultProps = {
    multiSelect: true,
};

/**
 * Props: (to complete)
 *
 * resModel
 * domain
 * context
 * title
 * onSelected
 */
