import { registry } from "@web/core/registry";

registry.category("actions").add("action_send_mail_callback", async (env, action) => {
    await env.services.action.doAction({ type: "ir.actions.act_window_close" });
});
