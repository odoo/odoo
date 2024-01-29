import { Model } from "../mock_model";

export class IrRule extends Model {
    _name = "ir.rule";

    check_access_rights() {
        return true;
    }
}
