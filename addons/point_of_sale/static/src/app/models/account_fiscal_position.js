import { registry } from "@web/core/registry";
import { Base } from "./related_models";

export class AccountFiscalPosition extends Base {
    static pythonModel = "account.fiscal.position";

    getTaxesAfterFiscalPosition(taxes) {
        if (!this.tax_ids?.length) {
            return [];
        }

        const newTaxIds = [];
        for (const tax of taxes) {
            if (this.tax_map[tax.id]) {
                for (const mapTaxId of this.tax_map[tax.id]) {
                    newTaxIds.push(mapTaxId);
                }
            } else {
                newTaxIds.push(tax.id);
            }
        }

        return this.models["account.tax"].filter((tax) => newTaxIds.includes(tax.id));
    }
}

registry
    .category("pos_available_models")
    .add(AccountFiscalPosition.pythonModel, AccountFiscalPosition);
