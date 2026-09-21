// @ts-check

import { Domain } from "@web/core/domain";
import { OdooCorePlugin } from "@spreadsheet/plugins";

export class PivotOdooCorePlugin extends OdooCorePlugin {
    handlers = {
        // this command is deprecated. use UPDATE_PIVOT instead
        UPDATE_ODOO_PIVOT_DOMAIN: this.onUpdateOdooPivotDomain,
    };

    onUpdateOdooPivotDomain(cmd) {
        this.dispatch("UPDATE_PIVOT", {
            pivotId: cmd.pivotId,
            pivot: {
                ...this.getters.getPivotCoreDefinition(cmd.pivotId),
                domain: cmd.domain,
            },
        });
    }

    /**
     * Transform the domain of a pivot definition to a more readable format
     *
     * @param {Object} data
     */
    export(data) {
        if (data.pivots) {
            for (const id in data.pivots) {
                if (data.pivots[id].type === "ODOO") {
                    data.pivots[id].domain = new Domain(data.pivots[id].domain).toJson();
                }
            }
        }
    }
}
