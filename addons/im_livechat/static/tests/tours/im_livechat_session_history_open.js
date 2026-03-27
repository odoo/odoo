import { whenReady } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { patchWithCleanup } from "@web/../tests/helpers/utils";

let firstChannelId;
registry.category("web_tour.tours").add("im_livechat_session_history_open", {
    steps: () => [
        {
            trigger: "body",
            async run() {
                await whenReady();
                const busService = odoo.__WOWL_DEBUG__.root.env.services.bus_service;
                patchWithCleanup(busService, {
                    addChannel(channel) {
                        document.body.classList.add(`o-bus-channel-${channel}`);
                        return super.addChannel(...arguments);
                    },
                    deleteChannel(channel) {
                        document.body.classList.remove(`o-bus-channel-${channel}`);
                        return super.deleteChannel(...arguments);
                    },
                });
            },
        },
        {
            trigger: ".o_switch_view[data-tooltip='List']",
            run: "click",
        },
        {
            trigger: ".o_data_cell:contains('test 2')",
            run: "click",
        },
        {
            trigger: ".o-mail-Message-content:contains('Test Channel 2 Msg')",
            async run({ waitFor }) {
                firstChannelId =
                    odoo.__WOWL_DEBUG__.root.env.services.action.currentController.state.resId;
                await waitFor(`body.o-bus-channel-discuss\\.channel_${firstChannelId}`, {
                    timeout: 3000,
                });
            },
        },
        {
            trigger: ".oi-chevron-right",
            run: "click",
        },
        {
            trigger: ".o-mail-Message-content:contains('Test Channel 1 Msg')",
            async run({ waitFor }) {
                await waitFor(`body:not(.o-bus-channel-discuss\\.channel_${firstChannelId})`, {
                    timeout: 3000,
                });
                const channelId =
                    odoo.__WOWL_DEBUG__.root.env.services.action.currentController.state.resId;
                await waitFor(`body.o-bus-channel-discuss\\.channel_${channelId}`, {
                    trimeout: 3000,
                });
            },
        },
    ],
});
