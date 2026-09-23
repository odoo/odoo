// @ts-check

import { Model } from "../mock_model.js";

export class IrAccess extends Model {
    _name = "ir.access";

    has_access() {
        return true;
    }
}
