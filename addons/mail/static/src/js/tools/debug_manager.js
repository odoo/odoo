import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

export function manageMessages({ component }) {
    const action = useService("action");
    const resId = component.model.root.resId;
    if (!resId || !user.isSystem) {
        return null; // No record, or not allowed to manage messages
    }
    const description = _t("Messages");
    return {
        type: "item",
        description,
        callback: () => {
            action.doAction({
                res_model: "mail.message",
                name: description,
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
                type: "ir.actions.act_window",
                domain: [
                    ["res_id", "=", resId],
                    ["model", "=", component.props.resModel],
                ],
                context: {
                    default_res_model: component.props.resModel,
                    default_res_id: resId,
                    mail_message_mark_edited: true,
                },
            });
        },
        sequence: 130,
        section: "record",
    };
}

registry.category("debug").category("form").add("mail.manageMessages", manageMessages);
