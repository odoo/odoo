import { imStatusDataRegistry } from "@mail/core/common/im_status";
import { _t } from "@web/core/l10n/translation";

imStatusDataRegistry.add(
    "hr-holidays",
    {
        condition: ({ user }) => Boolean(user?.employee_id?.leave_date_to),
        icon: "fa fa-plane",
        title: ({ user }) => {
            const backOn = user?.outOfOfficeDateEndText;
            const tag = (base) => (backOn ? `${base} · ${backOn}` : base);
            return {
                online: tag(_t("User is on leave and online")),
                away: tag(_t("User is on leave and idle")),
                busy: tag(_t("User is on leave and busy")),
                default: tag(_t("User is on leave")),
            };
        },
    },
    { sequence: 50 }
);
