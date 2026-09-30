import { ServerModel } from "../mock_model";

export class IrHttp extends ServerModel {
    _name = "ir.http";

    lazy_session_info() {
        return {};
    }
}
