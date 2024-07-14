/** @odoo-module */

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

export class SidebarPropertiesToolbox extends Component {
    static props = {};
    static template = "web_studio.ViewEditor.InteractiveEditorProperties.Toolbox";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");
    }

    get node() {
        return this.env.viewEditorModel.activeNode;
    }

    get nodeType() {
        return this.node.arch.tagName;
    }

    onRemoveFromView() {
        let nodeHumanName = this.nodeType;
        if (this.nodeType === "t" && this.node.attrs["t-name"] === "kanban-menu") {
            nodeHumanName = _t("dropdown");
        }

        this.dialog.add(ConfirmationDialog, {
            body: _t("Are you sure you want to remove this %s from the view?", nodeHumanName),
            confirm: () => {
                return this.removeNodeFromArch();
            },
            cancel: () => {},
        });
    }

    async openFormAction() {
        const resId = await this.orm.searchRead(
            "ir.model.fields",
            [
                ["model", "=", this.env.viewEditorModel.resModel],
                ["name", "=", this.node.field.name],
            ],
            ["id"]
        );
        return this.action.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "ir.model.fields",
                res_id: resId[0].id,
                views: [[false, "form"]],
                target: "current",
            },
            { clearBreadcrumbs: true }
        );
    }

    removeNodeFromArch(xpath) {
        const target = this.env.viewEditorModel.getFullTarget(xpath || this.node.xpath);
        const operation = {
            type: "remove",
            target,
        };
        this.env.viewEditorModel.resetSidebar();
        return this.env.viewEditorModel.doOperation(operation);
    }
}
