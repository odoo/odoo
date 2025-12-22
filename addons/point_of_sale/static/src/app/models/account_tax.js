import { registry } from "@web/core/registry";
import { Base } from "./related_models";

export class AccountTax extends Base {
    static pythonModel = "account.tax";

    get sum_repartition_factor() {
        if (this.amount_type !== "group") {
            const factorSum = this.repartition_line_ids.reduce(
                (sum, line) => sum + line.factor_percent,
                0
            );
            return factorSum / 100;
        } else {
            // FIXME: This here is problematic. It's not clear what the sum should be.
            return undefined;
        }
    }
}

registry.category("pos_available_models").add(AccountTax.pythonModel, AccountTax);
