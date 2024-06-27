import { describe, test } from "@odoo/hoot";
import {
    click,
    contains,
    insertText,
    openDiscuss,
    start,
    startServer
} from "@mail/../tests/mail_test_helpers";
import { Command, onRpc, serverState } from "@web/../tests/web_test_helpers";
import { defineCrmModels } from "@crm/../tests/crm_test_helpers";

describe.current.tags("desktop");
defineCrmModels();

test("Can open lead from internal link", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });

    onRpc("discuss.channel", "execute_command_lead", (params) => {
        const { body } = params.kwargs;
        const leadName = body.substring("/lead".length).trim();
        const leadId = pyEnv["crm.lead"].create({ name: leadName });
        pyEnv["bus.bus"]._sendone(
            serverState.partnerId,
            "discuss.channel/transient_message",
            {
                body: `
                    <span class="o_mail_notification">
                        Create a new lead: <a href="#" data-oe-model="crm.lead" data-oe-id="${leadId}">${leadName}</a>
                    </span>`,
                thread: { model: "discuss.channel", id: params.args[0][0] },
            }
        );
        return true;
    });

    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "/lead My Lead");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await click('.o_mail_notification a[data-oe-model="crm.lead"]');
    await contains(".o-mail-ChatWindow-header", { text: "Visitor" });
    await contains(".o_form_view .o_last_breadcrumb_item span", { text: "My Lead" });
});
