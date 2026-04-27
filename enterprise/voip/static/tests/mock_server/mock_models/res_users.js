import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";

export class ResUsers extends mailModels.ResUsers {
    voip_provider_id = fields.Many2one({
        relation: "voip.provider",
        default() {
            return this.env["voip.provider"][0].id;
        },
    });

    /** @override */
    _init_store_data(store) {
        const VoipCall = this.env["voip.call"];
        const VoipProvider = this.env["voip.provider"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        super._init_store_data(...arguments);
        const [user] = ResUsers.search_read([["id", "=", this.env.uid]]);
        if (user) {
            const [provider] = VoipProvider.search_read([["id", "=", user.voip_provider_id[0]]]);
            store.add({
                voipConfig: {
                    missedCalls: VoipCall._get_number_of_missed_calls(),
                    mode: provider.mode,
                    pbxAddress: provider.pbx_ip || "localhost",
                    webSocketUrl: provider.ws_server || "ws://localhost",
                },
            });
        }
    }
}
