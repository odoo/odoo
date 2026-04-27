/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import DocumentViewer from "@mrp_workorder/components/viewer";
import { formatFloat } from "@web/views/fields/formatters";
import { FloatField } from "@web/views/fields/float/float_field";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { TabletImageField } from "@quality/tablet_image_field/tablet_image_field";
import { useService, useBus } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";
import { HtmlField } from "@html_editor/fields/html_field";

export class MrpQualityCheckConfirmationDialog extends ConfirmationDialog {
    static props = {
        ...ConfirmationDialog.props,
        record: Object,
        reload: { type: Function, optional: true },
        qualityCheckDone: { type: Function, optional: true },
        worksheetData: { type: Object, optional: true },
        checkInstruction: { type: Object, optional: true },
        openPreviousCheck: { type: Function, optional: true },
        openNextCheck: { type: Function, optional: true },
    };
    static template = "mrp_workorder.MrpQualityCheckConfirmationDialog";
    static components = {
        ...ConfirmationDialog.components,
        DocumentViewer,
        FloatField,
        Many2OneField,
        TabletImageField,
        HtmlField,
    };

    setup() {
        super.setup();
        this.barcode = useService("barcode");
        this.notification = useService("notification");
        this.action = useService("action");
        useBus(this.props.record.model.bus, "update", this.render.bind(this, true));
        useBus(this.barcode.bus, "barcode_scanned", (event) =>
            this._onBarcodeScanned(event.detail.barcode)
        );
        this.state = useState({ disabled: false });
        this.formatFloat = formatFloat;
        const { component_tracking, test_type, product_tracking } = this.recordData;
        this.displayLot =
            Boolean(component_tracking && component_tracking !== "none") ||
            Boolean(test_type === "register_production" && product_tracking !== "none");
        this.trackingNumberLabel = test_type === "register_production" ? product_tracking : component_tracking;
    }

    get confirmLabel() {
        if (["instructions", "passfail"].includes(this.recordData.test_type)) {
            return _t("Next");
        } else if (this.recordData.test_type === "print_label") {
            return _t("Print Labels");
        }
        return _t("Validate");
    }


    get shouldDisplayValidateButton() {
        return this.recordData.test_type !== 'passfail' || this.recordData.quality_state !== 'none'
    }

    async validate() {
        this.state.disabled = true;
        if (this.recordData.test_type === "print_label") {
            return this.doActionAndClose("action_print", false);
        } else if (this.recordData.test_type === "measure") {
            return this.doActionAndClose("do_measure");
        } else if (this.recordData.test_type === "worksheet") {
            return this.doActionAndClose("action_worksheet_check", false);
        }
        const skipSave = ["instructions", "passfail"].includes(this.recordData.test_type);
        await this.doActionAndClose("action_next", !skipSave);
        if (this.recordData.test_type === "register_production"){
            await this.props.record.model.orm.call("mrp.production", "set_qty_producing", [this.recordData.production_id[0]]);
        }
    }

    async continueProduction() {
        this.state.disabled = true;
        const skipSave = ["instructions", "passfail"].includes(this.recordData.test_type);
        this.doActionAndClose("action_continue", !skipSave, true);
    }

    async openWorksheet() {
        const res = await this.props.record.model.orm.call(
            this.props.record.resModel,
            "action_quality_worksheet",
            [this.props.record.resId]
        );
        this.action.doAction(res);
    }

    async pass() {
        this.state.disabled = true;
        this.doActionAndClose("action_pass_and_next");
    }

    async fail() {
        this.state.disabled = true;
        this.doActionAndClose("action_fail_and_next");
    }

    async doActionAndClose(action, saveModel = true, reloadChecks = false){
        this.state.disabled = true;
        try {
            if (saveModel) {
                await this.props.record.save();
            }
            const res = await this.props.record.model.orm.call(this.props.record.resModel, action, [this.props.record.resId])
            if (res) {
                this.action.doAction(res, {
                    onClose: () => {
                        this.props.reload(this.props.record);
                    },
                });
                if (res.type === "ir.actions.act_window") {
                    this.props.close();
                    return;
                }
            }
            if (!reloadChecks) {
                await this.props.record.load();
            }
            await this.props.qualityCheckDone(reloadChecks, this.props.record.data.quality_state);
            this.props.close();
        } catch (e) {
            this.state.disabled = false;
            throw e;
        }
    }

    async _onBarcodeScanned (barcode){
        if (["register_consumed_materials", "register_byproducts"].includes(this.recordData.test_type)){
            const lot = await this.props.record.model.orm.search('stock.lot', [
                ["name", "=", barcode],
                ["product_id", "=", this.recordData.component_id[0]],
                "|", ["company_id", "=", false], ["company_id", "=", this.recordData.company_id[0]],
            ]);
            if (lot.length) {
                this.props.record.update({ lot_id: [lot[0], barcode] });
                this.state.disabled = false;
                this.render();
            }
        }
    }

    async actionGenerateSerial() {
        this.state.disabled = true;
        await this.props.record.model.orm.call(
            "quality.check",
            "action_generate_serial_number_and_pass",
            [this.props.record.resId]
        );
        await this.props.record.load();
        this.state.disabled = false;
        this.render();
    }

    get lotInfo() {
        const productId = this.recordData.component_id?.[0] || this.props.record.data.product_id[0];
        return {
            name: "lot_id",
            record: this.props.record,
            canQuickCreate: false,
            context: {
                default_product_id: productId,
                active_mo_id: this.recordData.production_id[0],
                default_company_id: this.recordData.company_id[0],
            },
            domain: [
                "&",
                ["product_id", "=", productId],
                "|",
                ["company_id", "=", false],
                ["company_id", "=", this.recordData.company_id[0]],
            ],
        };
    }

    get measureInfo() {
        return {
            name: "measure",
            record: this.props.record,
        };
    }

    get note() {
        const note = this.recordData.note;
        return note && !["<p><br></p>", `<div><br></div>`].includes(note) && note != "false"
            ? note
            : undefined;
    }

    get htmlInfo() {
        return {
            name: "note",
            record: this.props.record,
            readonly: true,
            embeddedComponents: true,
        }
    }

    get picInfo() {
        return {
            name: "picture",
            record: this.props.record,
            width: 100,
            height: 100,
        };
    }

    get qtyDoneInfo() {
        return {
            name: "qty_done",
            record: this.props.record,
        };
    }

    get recordData() {
        return this.props.record.data;
    }

    back() {
        this.state.disabled = true;
        if (this.props.openPreviousCheck) {
            this.props.openPreviousCheck();
        }
        this.props.close();
    }

    skip() {
        this.state.disabled = true;
        if (this.props.openNextCheck) {
            this.props.openNextCheck();
        }
        this.props.close();
    }
}
