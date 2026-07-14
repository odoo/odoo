import { serverState } from "../../mock_server_state.hoot";
import { ServerModel } from "../mock_model";

export class ResGroups extends ServerModel {
    _name = "res.groups";

    _records = [
        {
            id: serverState.groupId,
            name: "Internal User",
        },
    ];
}
