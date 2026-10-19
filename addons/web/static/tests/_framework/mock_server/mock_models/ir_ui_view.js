import { ServerModel } from "../mock_model";

export class IrUiView extends ServerModel {
    _name = "ir.ui.view";

    has_access() {
        return true;
    }
}
