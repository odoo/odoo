/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";
import { Persona } from "@mail/core/common/persona_model";
import { Command } from "@mail/../tests/helpers/command";

import { contains } from "@web/../tests/utils";
import { patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module("im_status");

QUnit.test("change icon on change partner im_status for leave variants", async () => {
    const pyEnv = await startServer();
    pyEnv["res.partner"].write([pyEnv.currentPartnerId], {
        im_status: "online",
        out_of_office_date_end: "2023-01-01",
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: pyEnv.currentPartnerId })],
        channel_type: "chat",
    });
    patchWithCleanup(Persona, { IM_STATUS_DEBOUNCE_DELAY: 0 });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-ImStatus .fa-plane[title='Online']");

    pyEnv["bus.bus"]._sendone("broadcast", "bus.bus/im_status_updated", {
        partner_id: pyEnv.currentPartnerId,
        im_status: "leave_offline",
        presence_status: "offline",
    });
    await contains(".o-mail-ImStatus .fa-plane[title='Out of office']");

    pyEnv["bus.bus"]._sendone("broadcast", "bus.bus/im_status_updated", {
        partner_id: pyEnv.currentPartnerId,
        im_status: "leave_away",
        presence_status: "away",
    });
    await contains(".o-mail-ImStatus .fa-plane[title='Idle']");

    pyEnv["bus.bus"]._sendone("broadcast", "bus.bus/im_status_updated", {
        partner_id: pyEnv.currentPartnerId,
        im_status: "leave_online",
        presence_status: "online",
    });
    await contains(".o-mail-ImStatus .fa-plane[title='Online']");
});
