import { ServerModel } from "../mock_model";

export class IrUiView extends ServerModel {
    _name = "ir.ui.view";

    check_access_rights() {
        return true;
    }
}
