/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Field } from "@web/views/fields/field";
import { onWillStart } from "@odoo/owl";


export class LotNumbers extends Field {
    setup() {
        super.setup();
        this.orm = useService("orm");
        onWillStart(async () => {
            this.props['placeholder'] = await this.orm.call(
                'mrp.production',
                'get_placeholder_value',
                [this.props.record.data.production_id[0]],
            );
        });
    }
}

registry.category("fields").add("lot_numbers", {
    component: LotNumbers,
});
