/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Field } from "@web/views/fields/field";
import { StockMove } from "./stock_move";
import { useService } from "@web/core/utils/hooks";
import { MrpTimer } from "@mrp/widgets/timer";
import { markup } from "@odoo/owl";

export class MrpWorkorder extends StockMove {
    static components = { ...StockMove.components, Field, MrpTimer };
    static template = "mrp_workorder.WorkOrder";
    static props = {
        ...StockMove.props,
        selectWorkcenter: { optional: true, type: Function },
        qualityChecks: { optional: true, type: Array },
        sessionOwner: Object,
        updateEmployees: Function,
    };

    setup() {
        super.setup();
        this.isLongPressable = true;
        this.dialogService = useService("dialog");
        this.name = this.props.record.data.name;
        this.note = false;
        this.checks = this.props.record.data.check_ids;
    }

    get active() {
        return this.props.record.data.employee_ids.records.length != 0;
    }

    get cssClass() {
        let cssClass = super.cssClass;
        if (this.active) {
            cssClass += " o_active";
        }
        return cssClass;
    }

    get isComplete() {
        return this.props.record.data.state === "done";
    }

    get workcenter() {
        return this.props.record.data.workcenter_id;
    }

    get checksInfo() {
        if (!this.checks.count) {
            return "";
        }
        const doneChecks = this.checks.records.filter(
            (qc) => qc.data.quality_state != "none"
        ).length;
        const checks = this.checks.count;
        return `${doneChecks}/${checks}`;
    }

    async displayInstruction() {
        if (this.hasOperationNote && !this.note) {
            this.note = await this.fetchOperationNote(this);
        }
        const params = {
            body: this.note,
            confirmLabel: _t("Discard"),
            title: this.props.record.data.display_name,
        };
        if (!this.isComplete) {
            params.confirm = async () => {
                await this.props.record.model.orm.call(
                    this.props.record.resModel,
                    "button_finish",
                    this.props.record.resIds
                );
                await this.env.reload(this.props.record);
            };
            params.confirmLabel = _t("Validate");
            params.cancel = () => {};
            params.cancelLabel = _t("Discard");
        }
        this.dialogService.add(ConfirmationDialog, params);
    }

    async longPress() {
        const { record } = this.props;
        await record.model.orm.call(record.resModel, "button_finish", [record.resId]);
        await this.env.reload(this.props.record);
    }

    async clicked() {
        // Override with an empty body to cancel the behavior of clicked() in the 'StockMove' parent class
    }
}

export async function fetchOperationNote(record) {
   const operationNote = await record.props.record.model.orm.read(
            "mrp.workorder",
            [record.props.record.resId],
            ["operation_note"]
        );
    return markup(operationNote[0].operation_note);
}
