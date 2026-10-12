import { mailModels } from "@mail/../tests/mail_test_helpers";

import { serverState } from "@web/../tests/web_test_helpers";

export class IrWebSocket extends mailModels.IrWebSocket {
    /**
     * @override
     * @type {typeof busModels.IrWebSocket["prototype"]["_build_bus_channel_list"]}
     */
    _build_bus_channel_list(channels) {
        channels = [...super._build_bus_channel_list(channels)];
        const result = channels;
        for (const channel of channels) {
            if (channel === "im_livechat.looking_for_help") {
                result.push([
                    this.env["res.groups"].browse(serverState.groupLivechatId)[0],
                    "LOOKING_FOR_HELP",
                ]);
            }
        }
        return result.filter((channel) => channel !== "im_livechat.looking_for_help");
    }
}
