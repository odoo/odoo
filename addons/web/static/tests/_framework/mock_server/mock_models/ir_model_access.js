import { Model } from "../mock_model";

export class IrModelAccess extends Model {
    _name = "ir.model.access";

    check_access_rights() {
        return true;
    }
}
