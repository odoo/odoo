/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { View } from "../view";
import { useService } from "@web/core/utils/hooks";

const { onWillStart, useState } = owl;

export class SelectCreateDialog extends Dialog {
    setup() {
        super.setup();
        this.viewService = useService("view");
        this.state = useState({
            resIds: [],
        });

        this.title = this.props.title;

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
            selectRecord: (resId) => {
                if (this.props.onSelected) {
                    this.props.onSelected([resId]);
                    this.close();
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

    select() {
        if (this.props.onSelected) {
            this.props.onSelected(this.state.resIds);
            this.close();
        }
    }
    createEditRecord() {}
}
SelectCreateDialog.components = { View };
SelectCreateDialog.bodyTemplate = "web.SelectCreateDialogBody";
SelectCreateDialog.footerTemplate = "web.SelectCreateDialogFooter";

SelectCreateDialog.defaultProps = {
    multiSelect: true,
};
