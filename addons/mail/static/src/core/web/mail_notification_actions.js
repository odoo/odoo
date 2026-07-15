import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

registry.category("actions").add("action_send_mail_callback", async () => {
    const action = useService("action");
    await action.doAction({ type: "ir.actions.act_window_close" });
});
