import { registry } from "@web/core/registry";

/**
 * @param {"list" | "kanban"} viewType
 * @returns {import("@web_tour/tour_service/tour_service").TourStep[]}
 */
function getSteps(viewType) {
    let bobChatId;
    return [
        {
            trigger: ".o_control_panel .active:contains(Looking for Help)",
        },
        {
            trigger:
                viewType === "list"
                    ? ".o_list_table:has(.o_data_row:contains(bob_looking_for_help))"
                    : ".o_kanban_renderer:has(.o_kanban_record [name=livechat_agent_partner_ids] [aria-label^=bob_looking_for_help])",
            async run() {
                const { orm } = odoo.__WOWL_DEBUG__.root.env.services;
                [bobChatId] = await orm.search("discuss.channel", [
                    ["livechat_status", "=", "need_help"],
                    ["livechat_agent_partner_ids.name", "like", "bob_looking_for_help%"],
                ]);
                await orm.write("discuss.channel", [bobChatId], {
                    livechat_status: "in_progress",
                });
            },
        },
        {
            trigger:
                viewType === "list"
                    ? ".o_list_table:not(:has(.o_data_row:contains(bob_looking_for_help)))"
                    : ".o_kanban_renderer:not(:has(.o_kanban_record [name=livechat_agent_partner_ids] [aria-label^=bob_looking_for_help]))",
            async run() {
                const { orm } = odoo.__WOWL_DEBUG__.root.env.services;
                await orm.write("discuss.channel", [bobChatId], {
                    livechat_status: "need_help",
                });
            },
        },
        {
            trigger:
                viewType === "list"
                    ? ".o_list_table:has(.o_data_row:contains(bob_looking_for_help))"
                    : ".o_kanban_renderer:has(.o_kanban_record [name=livechat_agent_partner_ids] [aria-label^=bob_looking_for_help])",
        },
    ];
}
registry.category("web_tour.tours").add("im_livechat.looking_for_help_list_real_time_update_tour", {
    steps: () => getSteps("list"),
});
registry
    .category("web_tour.tours")
    .add("im_livechat.looking_for_help_kanban_real_time_update_tour", {
        steps: () => getSteps("kanban"),
    });
