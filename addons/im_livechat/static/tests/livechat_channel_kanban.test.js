import { defineLivechatModels } from "@im_livechat/../tests/livechat_test_helpers";
import { start, startServer } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";

import { mountView } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("kanban card is flagged only on a channel with an available operator", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Agent", im_status: "online" });
    pyEnv["im_livechat.channel"].create([
        { name: "Staffed", available_operator_ids: [userId], user_ids: [userId] },
        { name: "Empty" },
    ]);
    await start();
    await mountView({
        type: "kanban",
        resModel: "im_livechat.channel",
        arch: `
            <kanban js_class="im_livechat.livechat_channel_kanban">
                <templates>
                    <t t-name="menu">
                        <a type="open" class="dropdown-item">Configure Channel</a>
                    </t>
                    <t t-name="card">
                        <main>
                            <field name="name"/>
                            <field name="available_operator_ids" widget="many2many_avatar_user" readonly="True"/>
                        </main>
                    </t>
                </templates>
            </kanban>
        `,
    });
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(2);
    expect(".o_kanban_record:eq(0)").toHaveClass("o-livechat-ChannelKanban-available");
    expect(".o_kanban_record:eq(1)").not.toHaveClass("o-livechat-ChannelKanban-available");
});
