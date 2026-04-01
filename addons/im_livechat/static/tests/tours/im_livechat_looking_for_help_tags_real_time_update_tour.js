import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

let bobChatId;
let tagId;
registry.category("web_tour.tours").add("im_livechat.looking_for_help_tags_real_time_update_tour", {
    steps: () => [
        {
            trigger: ".o_control_panel .active:contains(Looking for Help)",
        },
        {
            trigger: ".o_optional_columns_dropdown_toggle",
            run: "click",
        },
        {
            trigger: '.o-dropdown-item input[name="livechat_conversation_tag_ids"]',
            run: "click",
        },
        {
            trigger: ".o_optional_columns_dropdown_toggle",
            run: "click",
        },
        {
            trigger: ".o_list_table:has(.o_data_row:contains(bob_looking_for_help))",
        },
        {
            trigger: '.o_data_cell[name="livechat_conversation_tag_ids"]:not(:has(.o_tag))',
            async run() {
                const { orm } = odoo.__WOWL_DEBUG__.root.env.services;
                [bobChatId] = await orm.search("discuss.channel", [
                    ["livechat_status", "=", "need_help"],
                    ["livechat_agent_partner_ids.name", "like", "bob_looking_for_help%"],
                ]);
                [tagId] = await orm.create("im_livechat.conversation.tag", [{ name: "Discuss" }]);
                // Simulate other user adding a tag
                await rpc("/im_livechat/conversation/update_tags", {
                    channel_id: bobChatId,
                    tag_ids: [tagId],
                    method: "ADD",
                });
            },
        },
        {
            trigger:
                '.o_data_cell[name="livechat_conversation_tag_ids"]:has(.o_tag:contains(Discuss))',
            async run() {
                // Simulate other user removing a tag
                await rpc("/im_livechat/conversation/update_tags", {
                    channel_id: bobChatId,
                    tag_ids: [tagId],
                    method: "DELETE",
                });
            },
        },
        { trigger: '.o_data_cell[name="livechat_conversation_tag_ids"]:not(:has(.o_tag))' },
    ],
});
