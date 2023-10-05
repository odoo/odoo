/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { x2ManyCommands } from "@web/core/orm_service";
import { Dialog } from '@web/core/dialog/dialog';
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { parseInteger  } from "@web/views/fields/parsers";
import { getId } from "@web/model/relational_model/utils";
import { Component, useRef, xml, onMounted } from "@odoo/owl";

export class GenerateDialog extends Component {
    setup() {
        this.size = 'md';
        if (this.props.type === 'serial') {
            this.title = _t("Generate Serials numbers");
        } else {
            this.title = _t("Import Lots");
        }

        this.nextSerial = useRef('nextSerial');
        this.nextSerialCount = useRef('nextSerialCount');
        this.lots = useRef('lots');
        this.orm = useService("orm");
        onMounted(() => {
            if (this.props.type === 'serial') {
                this.nextSerialCount.el.value = this.props.move.data.product_uom_qty || 2;
            }
        });
    }
    async _onGenerate() {
        const count = parseInteger(this.nextSerialCount.el?.value || '0');
        const move_line_vals = await this.orm.call("stock.move", "action_generate_lot_line_vals", [
            {...this.props.move.context, default_product_id: this.props.move.data.product_id[0]},
            this.props.type,
            this.nextSerial.el?.value,
            count,
            this.lots.el?.value,
        ]);
        const newlines = [];
        let lines = []
        if (this.props.move.data.show_reserved) {
            lines = this.props.move.data.move_line_ids;
        } else {
            lines = this.props.move.data.move_line_nosuggest_ids;
        }

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
        lines.records.push(...newlines);
        lines._commands.push(...newlines.map((record) => [
            x2ManyCommands.CREATE,
            record._virtualId,
        ]));
        await lines._onUpdate();
        this.props.close();
    }
}

GenerateDialog.template = 'stock.generate_serial_dialog';
GenerateDialog.props = {
    type: { type: String },
    move: { type: Object },
    close: { type: Function },
};
GenerateDialog.components = { Dialog };

class GenerateSerials extends Component {
    static template = xml`<button class="btn btn-link" t-on-click="openDialog">Generate Serials</button>`;

    setup(){
        this.dialog = useService("dialog");
    }

    openDialog(ev){
        this.dialog.add(GenerateDialog, {
            move: this.props.record,
            type: 'serial',
        });
    }
}

class ImportLots extends Component {
    static template = xml`<button class="btn btn-link" t-on-click="openDialog">Import Lots</button>`;

    setup(){
        this.dialog = useService("dialog");
    }

    openDialog(ev){
        this.dialog.add(GenerateDialog, {
            move: this.props.record,
            type: 'import',
        });
    }
}
registry.category("view_widgets").add("import_lots", {component: ImportLots});
registry.category("view_widgets").add("generate_serials", {component: GenerateSerials});
