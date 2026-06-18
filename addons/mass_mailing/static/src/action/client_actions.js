import { registry } from "@web/core/registry";
import { htmlSprintf } from "@web/core/utils/html";
import { markup } from "@odoo/owl";

registry.category("actions").add("res_partner_to_list_results", (env, action) => {
    const { notification, next } = action.params;
    const { button, message, type } = notification;
    const onButtonClick = function () {
        this.close(); // Close notification
        return env.services.action.doAction(button.action);
    };
    env.services.notification.add(htmlSprintf(message, { NOTIF_NEWLINE: markup`<br/>` }), {
        buttons: [{ name: button.name, onClick: onButtonClick }],
        className: env.isMobile ? "o_line_clamp_2" : "o_line_clamp_3",
        type,
    });
    return next;
});
