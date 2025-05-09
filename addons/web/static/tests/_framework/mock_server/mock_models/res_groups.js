import { serverState } from "../../mock_server_state.hoot";
import { ServerModel } from "../mock_model";
import * as fields from "../mock_fields";

export class ResGroups extends ServerModel {
    _name = "res.groups";

    full_name = fields.Char({ compute: "_compute_full_name" });

    _compute_full_name() {
        for (const group of this) {
            const privilegeName = group.privilege_id?.name;
            const groupName = group.name;
            const shortDisplayName = this.env.context?.short_display_name;
            if (privilegeName && !shortDisplayName) {
                group.full_name = `${privilegeName} / ${groupName}`;
            } else {
                group.full_name = groupName;
            }
        }
    }

    _records = [
        {
            id: serverState.groupId,
            name: "Internal User",
            privilege_id: false,
        },
    ];
}
