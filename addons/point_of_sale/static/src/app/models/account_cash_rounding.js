import * as numbers from "@point_of_sale/app/utils/numbers";
import { registry } from "@web/core/registry";
export class AccountCashRounding extends numbers.AbstractNumbers {
    static pythonModel = "account.cash.rounding";
    get precision() {
        return this.rounding;
    }
    get method() {
        return this.rounding_method;
    }
}

registry
    .category("pos_available_models")
    .add(AccountCashRounding.pythonModel, AccountCashRounding);
