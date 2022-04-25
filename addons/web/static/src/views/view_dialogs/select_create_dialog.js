/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { View } from "../view";
import { useService } from "@web/core/utils/hooks";

const { Component, onWillStart, useState } = owl;

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
            type: "list",
            editable: false, // readonly
            showButtons: false,
            hasSelectors: this.props.multiSelect,
            selectRecord: async (resId) => {
                if (this.props.onSelected) {
                    await this.props.onSelected([resId]);
                    this.props.close();
                }
            },
            createRecord: () => {},
            onSelectionChanged: (resIds) => {
                this.state.resIds = resIds;
            },
            noBreadcrumbs: true,
            searchViewId: this.props.searchViewId,
            display: { searchPanel: false },
        };

        onWillStart(async () => {
            if (!("searchViewId" in this.props)) {
                const { views } = await this.viewService.loadViews({
                    resModel: this.props.resModel,
                    context: this.props.context || {},
                    views: [[false, "search"]],
                });
                this.propsView.searchViewId = views.search.id;
            }
        });
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
