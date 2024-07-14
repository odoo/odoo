/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { MrpWorkorder } from "./mrp_workorder";
import { MrpQualityCheckConfirmationDialog } from "../dialog/mrp_quality_check_confirmation_dialog";
import { FileUploader } from "@web/views/fields/file_handler";
import { useService } from "@web/core/utils/hooks";

import { useRef } from "@odoo/owl";

export class QualityCheck extends MrpWorkorder {
    static template = "mrp_workorder.QualityCheck";
    static components = {
        ...MrpWorkorder.components,
        MrpQualityCheckConfirmationDialog,
        FileUploader,
    };
    static props = {
        ...MrpWorkorder.props,
        displayInstruction: Function,
        quantityToProduce: { optional: true, type: Number },
    };

    setup() {
        super.setup();
        this.fieldState = "quality_state";
        this.isLongPressable = false;
        this.name = this.props.record.data.title || this.props.record.data.name;
        this.note = this.props.record.data.note;
        this.action = useService("action");
        this.fileUploaderToggle = useRef("fileUploaderToggle");
    }

    clicked() {
        this.props.displayInstruction();
    }

    async pass() {
        const { parent, record } = this.props;
        if (["instructions", "passfail"].includes(record.data.test_type)) {
            return this._pass();
        } else if (record.data.test_type === "register_production") {
            if (record.data.quality_state !== "none" || record.data.lot_id) {
                return this.clicked();
            } else if (record.data.product_tracking === "serial") {
                await record.model.orm.call(
                    record.resModel,
                    "action_generate_serial_number_and_pass",
                    [record.resId]
                );
            } else {
                if (record.data.product_tracking === "lot") {
                    await record.model.orm.call(
                        record.resModel,
                        "action_generate_serial_number_and_pass",
                        [record.resId]
                    );
                }
                parent.update({ qty_producing: this.props.quantityToProduce });
                record.update({ qty_done: this.props.quantityToProduce });
                await Promise.all(this.env.model.root.records.map(async (record) => record.save()));
                await record.model.orm.call(record.resModel, "action_next", [record.resId]);
            }
            this.env.reload();
            return;
        } else if (record.data.test_type === "print_label") {
            const res = await record.model.orm.call(record.resModel, "action_print", [
                record.resId,
            ]);
            this.action.doAction(res);
            this._pass();
            return;
        } else if (record.data.test_type === "picture") {
            this.fileUploaderToggle.el.click();
            return;
        }
        this.clicked();
    }

    get active() {
        return false;
    }

    get failed() {
        return this.state === "fail";
    }

    get isComplete() {
        return this.passed || this.failed;
    }

    get icon() {
        switch (this.props.record.data.test_type) {
            case "picture":
                return "fa fa-camera";
            case "register_consumed_materials":
            case "register_byproduct":
                return "fa fa-barcode";
            case "instructions":
                return "fa fa-square-o";
            case "passfail":
                return "fa fa-check";
            case "measure":
                return "fa fa-arrows-h";
            case "print_label":
                return "fa fa-print";
            default:
                return "fa fa-lightbulb-o";
        }
    }

    get passed() {
        return this.state === "pass";
    }

    get showMeasure() {
        return (
            this.props.record.data.quality_state === "pass" &&
            this.props.record.data.test_type === "measure"
        );
    }

    get uom() {
        if (this.displayUOM) {
            return this.props.uom[1];
        }
        return this.quantityToProduce === 1 ? _t("Unit") : _t("Units");
    }

    async onFileUploaded(info) {
        this.props.record.update({ picture: info.data, quality_state: "pass" });
        this.props.record.save({ reload: false });
    }

    _pass() {
        this.props.record.update({ quality_state: "pass" });
        this.props.record.save({ reload: false });
    }

    get lotInfo(){
        const recordData = this.props.record.data;
        if (recordData.quality_state === 'pass' && recordData.test_type === 'register_consumed_materials'){
            if (recordData.component_tracking === 'lot'){
                return recordData.qty_done + ' ' + recordData.component_uom_id[1];
            }
            if (recordData.component_tracking === 'serial'){
                return recordData.lot_id[1];
            }
        }
    }

    get shouldDisplayCheckmark() {
        return this.state === "pass" && !(this.showMeasure || this.lotInfo);
    }
}
