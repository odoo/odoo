import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { user } from "@web/core/user";
import { useOwnedDialogs } from "@web/core/utils/hooks";
import { onWillStart, usePlugin, t, Component, useProps, signal } from "@odoo/owl";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { ORM } from "@web/core/orm_plugin";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";

const BackorderConfirmationDialogProps = {
    removeDemand: t.function(),
    isProcessing: t.signal(),
    close: t.function(),
};

class BackorderConfirmationDialog extends Component {
    static template = "stock.BackorderConfirmationDialog";
    static components = { Dialog };
    props = useProps(BackorderConfirmationDialogProps);

    async removeDemand(createBackorder) {
        try {
            await this.props.removeDemand(createBackorder);
        } finally {
            this.props.close();
        }
    }
}

export class MovesListRenderer extends ListRenderer {
    static createRowTemplate = "stock.AddPackageListRendererRow";

    setup() {
        super.setup();
        this.addDialog = useOwnedDialogs();
        this.orm = usePlugin(ORM);
        this.actionPlugin = usePlugin(ActionPlugin);
        this.isProcessing = signal(false);

        onWillStart(async () => {
            this.hasPackageActive = await user.hasGroup("stock.group_tracking_lot");
        });
    }

    async onClickMovePackage() {
        // If picking doesn't exist yet or location is outdated, it will lead to incorrect results
        const canOpenDialog = await this.forceSave();
        if (!canOpenDialog) {
            return;
        }
        const domain = [];
        if (this.locationId) {
            domain.push(["location_id", "child_of", this.locationId]);
        }
        this.addDialog(SelectCreateDialog, {
            title: _t("Select Packages to Move"),
            noCreate: true,
            multiSelect: true,
            resModel: "stock.package",
            domain,
            context: {
                list_view_ref: "stock.stock_package_view_add_list",
            },
            onSelected: async (resIds) => {
                if (resIds.length) {
                    const done = await this.orm.call("stock.picking", "action_add_entire_packs", [
                        [this.pickingId],
                        resIds,
                    ]);
                    if (done) {
                        await this.actionPlugin.doAction({
                            type: "ir.actions.client",
                            tag: "soft_reload",
                        });
                    }
                }
            },
        });
    }

    get canAddPackage() {
        return (
            this.hasPackageActive &&
            !["done", "cancel"].includes(this.props.list.context.picking_state) &&
            this.props.list.context.picking_type_code !== "incoming"
        );
    }

    async forceSave() {
        // This means the record hasn't been saved once, but we need the picking id to know for which picking we create the move lines.
        const record = this.env.model.root;
        const result = await record.save();
        this.pickingId = record.data.id;
        this.locationId = record.data.location_id?.id;
        return result;
    }

    async removeDemand(record, createBackorder) {
        if (this.isProcessing()) {
            return;
        }
        this.isProcessing.set(true);
        try {
            if (await record.model.root.save()) {
                await this.orm.call("stock.move", "action_remove_demand", [[record.resId], createBackorder]);
                await record.model.root.load();
            }
        } finally {
            this.isProcessing.set(false);
        }
    }

    async onDeleteRecord(record) {
        const picking = record.model.root.data;
        if (!record.resId || ["draft", "cancel"].includes(picking.state)) {
            return super.onDeleteRecord(record);
        }
        const [pickingType] = await this.orm.webRead("stock.picking.type", [picking.picking_type_id.id], {
            specification: { create_backorder: {} },
        });
        const createBackorder = pickingType.create_backorder;
        if (createBackorder === "always") {
            await this.removeDemand(record, true);
        } else if (createBackorder === "never") {
            await this.removeDemand(record, false);
        } else {
            this.addDialog(BackorderConfirmationDialog, {
                isProcessing: this.isProcessing,
                removeDemand: (createBackorder) => this.removeDemand(record, createBackorder),
            });
        }
    }
}

export class StockMoveX2ManyField extends X2ManyField {
    static components = { ...X2ManyField.components, ListRenderer: MovesListRenderer };
}

export const stockMoveX2ManyField = {
    ...x2ManyField,
    component: StockMoveX2ManyField,
};

registry.category("fields").add("stock_move_one2many", stockMoveX2ManyField);
