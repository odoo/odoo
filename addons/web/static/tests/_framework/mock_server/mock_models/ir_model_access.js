import { Model } from "../mock_model";

export class IrModelAccess extends Model {
    _name = "ir.model.access";

    has_access() {
        return true;
    }
}
