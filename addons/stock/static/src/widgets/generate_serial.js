/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { x2ManyCommands } from "@web/core/orm_service";
import { Dialog } from '@web/core/dialog/dialog';
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { parseInteger  } from "@web/views/fields/parsers";
import { getId } from "@web/model/relational_model/utils";
import { Component, useRef, onMounted } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class GenerateDialog extends Component {
    static template = "stock.generate_serial_dialog";
    static components = { Dialog };
    static props = {
        mode: { type: String },
        move: { type: Object },
        close: { type: Function },
    };
    setup() {
        this.size = 'md';
        if (this.props.mode === 'generate') {
            this.title = this.props.move.data.has_tracking === 'lot'
            ? _t("Generate Lot numbers")
            : _t("Generate Serial numbers");
        } else {
            this.title = this.props.move.data.has_tracking === 'lot' ? _t("Import Lots") : _t("Import Serials");
        }

        this.nextSerial = useRef('nextSerial');
        this.nextSerialCount = useRef('nextSerialCount');
        this.totalReceived = useRef('totalReceived');
        this.keepLines = useRef('keepLines');
        this.lots = useRef('lots');
        this.orm = useService("orm");
        onMounted(() => {
            if (this.props.mode === 'generate') {
                this.nextSerialCount.el.value = this.props.move.data.product_uom_qty || 2;
                if (this.props.move.data.has_tracking === 'lot') {
                    this.totalReceived.el.value = this.props.move.data.quantity;
                }
            }
        });
    }
    async _onGenerate() {
        let count;
        let qtyToProcess;
        if (this.props.move.data.has_tracking === 'lot'){
            count = parseFloat(this.nextSerialCount.el?.value || '0');
            qtyToProcess = parseFloat(this.totalReceived.el?.value || this.props.move.data.product_qty);
        } else {
            count = parseInteger(this.nextSerialCount.el?.value || '0');
            qtyToProcess = this.props.move.data.product_qty;
        }
        const move_line_vals = await this.orm.call("stock.move", "action_generate_lot_line_vals", [{
                ...this.props.move.context,
                default_product_id: this.props.move.data.product_id[0],
                default_location_dest_id: this.props.move.data.location_dest_id[0],
                default_location_id: this.props.move.data.location_id[0],
                default_tracking: this.props.move.data.has_tracking,
                default_quantity: qtyToProcess,
            },
            this.props.mode,
            this.nextSerial.el?.value,
            count,
            this.lots.el?.value,
        ]);
        const newlines = [];
        let lines = []
        lines = this.props.move.data.move_line_ids;

        // create records directly from values to bypass onchanges
        for (const values of move_line_vals) {
            newlines.push(
                lines._createRecordDatapoint(values, {
                    mode: 'readonly',
                    virtualId: getId("virtual"),
                    manuallyAdded: false,
                })
            );
        }
        if (!this.keepLines.el.checked) {
            await lines._applyCommands(lines._currentIds.map((currentId) => [
                x2ManyCommands.DELETE,
                currentId,
            ]));
        }
        lines.records.push(...newlines);
        lines._commands.push(...newlines.map((record) => [
            x2ManyCommands.CREATE,
            record._virtualId,
        ]));
        lines._currentIds.push(...newlines.map((record) => record._virtualId));
        await lines._onUpdate();
        this.props.close();
    }
}

class GenerateSerials extends Component {
    static template = "stock.GenerateSerials";
    static props = {...standardWidgetProps};

    setup(){
        this.dialog = useService("dialog");
    }

    openDialog(ev){
        this.dialog.add(GenerateDialog, {
            move: this.props.record,
            mode: 'generate',
        });
    }
}

class ImportLots extends Component {
    static template = "stock.ImportLots";
    static props = {...standardWidgetProps};
    setup(){
        this.dialog = useService("dialog");
    }

    openDialog(ev){
        this.dialog.add(GenerateDialog, {
            move: this.props.record,
            mode: 'import',
        });
    }
}
registry.category("view_widgets").add("import_lots", {component: ImportLots});
registry.category("view_widgets").add("generate_serials", {component: GenerateSerials});
