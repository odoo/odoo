import { Component } from "@odoo/owl";
import { registries } from "@spreadsheet/o_spreadsheet/o_spreadsheet";
const { topbarComponentRegistry } = registries;

export class CollaborativeStatus extends Component {
    static template = "spreadsheet_edition.CollaborativeStatus";
    static props = {};

    get isSynced() {
        return this.env.model.getters.isFullySynchronized();
    }

    get connectedUsers() {
        const connectedUsers = [];
        for (const client of this.env.model.getters.getConnectedClients()) {
            if (!connectedUsers.some((user) => user.id === client.userId)) {
                connectedUsers.push({
                    id: client.userId,
                    name: client.name,
                });
            }
        }
        return connectedUsers;
    }

    get tooltipInfo() {
        return JSON.stringify({
            users: this.connectedUsers.map((/**@type User*/ user) => {
                return {
                    name: user.name,
                    avatar: `/web/image?model=res.users&field=avatar_128&id=${user.id}`,
                };
            }),
        });
    }
}

topbarComponentRegistry.add("collaborative_status", {
    component: CollaborativeStatus,
    sequence: 10,
});
