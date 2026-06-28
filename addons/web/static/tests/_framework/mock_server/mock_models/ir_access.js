import { Model } from "../mock_model";

export class IrAccess extends Model {
    _name = "ir.access";

    has_access() {
        return true;
    }
}
