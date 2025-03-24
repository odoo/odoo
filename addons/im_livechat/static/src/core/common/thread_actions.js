import { threadActionsRegistry } from "@mail/core/common/thread_actions";

const actinConfig = threadActionsRegistry.get("view-contact");

threadActionsRegistry.add("livechat-visitorPartner-contact", {
    ...actinConfig,
    condition(component) {
        return (
            component.thread?.channel_type === "livechat" &&
            component.thread?.livechatVisitorMember?.persona.type === "partner"
        );
    },
    open(component) {
        const visitor = component.thread.livechatVisitorMember;
        component.actionService?.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "res.partner",
                views: [[false, "form"]],
                search_view_id: [false],
                res_id: visitor?.persona.id,
            },
            { newWindow: !!component.env.inDiscussApp }
        );
    },
});
