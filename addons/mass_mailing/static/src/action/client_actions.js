import { markup } from "@odoo/owl";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { htmlSprintf } from "@web/core/utils/html";

registry.category("actions").add("res_partner_to_list_results", (action) => {
    const { notification, next } = action.params;
    const { button, message, type } = notification;
    const actionService = useService("action");
    const notificationService = useService("notification");
    const onButtonClick = function () {
        this.close(); // Close notification
        return actionService.doAction(button.action);
    };
    notificationService.add(htmlSprintf(message, { NOTIF_NEWLINE: markup`<br/>` }), {
        buttons: [{ name: button.name, onClick: onButtonClick }],
        className: isMobileOS() ? "o_line_clamp_2" : "o_line_clamp_3",
        type,
    });
    return next;
});
