import { imStatusDataRegistry } from "@mail/core/common/im_status";
import { _t } from "@web/core/l10n/translation";

imStatusDataRegistry.add(
    "hr-holidays",
    {
        condition: ({ persona }) => Boolean(persona.main_user_id?.employee_id?.leave_date_to),
        icon: "fa fa-plane",
        title: {
            online: _t("User is on leave and online"),
            away: _t("User is on leave and idle"),
            busy: _t("User is on leave and busy"),
            default: _t("User is on leave"),
        },
    },
    { sequence: 50 }
);
