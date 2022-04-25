/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { sprintf } from "@web/core/utils/strings";
import { View } from "@web/views/view";
import { useService } from "@web/core/utils/hooks";

const { Component, markup, useState } = owl;

export class SelectCreateDialog extends Component {
    setup() {
        super.setup();
        this.viewService = useService("view");
        this.state = useState({
            resIds: [],
        });

        let viewId = "false";
        if (this.props.context) {
            viewId = this.props.context.tree_view_ref || "false";
        }

        this.propsView = {
            viewId,
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
            noContentHelp: markup(sprintf("<p>%s</p>", this.env._t("No records found!"))),
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
