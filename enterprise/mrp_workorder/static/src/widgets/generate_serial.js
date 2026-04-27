/** @odoo-module **/

import { patch } from "@web/core/utils/patch";

import { GenerateDialog } from "@stock/widgets/generate_serial";

patch(GenerateDialog.prototype, {
    async _onGenerate() {
        if (!this.props.move.context.default_picking_type_id) {
            this.props.move.context.default_picking_type_id =
                this.props.move.data.picking_type_id[0];
        }
        if (!this.props.move.context.default_company_id) {
            this.props.move.context.default_company_id = this.props.move.data.company_id[0];
        }
        super._onGenerate();
    },
});
