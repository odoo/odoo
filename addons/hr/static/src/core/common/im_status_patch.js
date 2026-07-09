import { imStatusDataRegistry } from "@mail/core/common/im_status";
import { _t } from "@web/core/l10n/translation";

imStatusDataRegistry.add(
    "hr-homeworking-home",
    {
        condition: ({ user }) => user?.employee_id?.work_location_type === "home",
        icon: "home",
        icon_class: "",
        title: {
            online: _t("User is at home and online"),
            away: _t("User is at home and idle"),
            busy: _t("User is at home and busy"),
            offline: _t("User is at home and offline"),
            default: _t("User is at home"),
        },
    },
    { sequence: 60 }
);
imStatusDataRegistry.add(
    "hr-homeworking-office",
    {
        condition: ({ user }) => user?.employee_id?.work_location_type === "office",
        icon: "business",
        icon_class: "oi-filled",
        title: {
            online: _t("User is at the office and online"),
            away: _t("User is at the office and idle"),
            busy: _t("User is at the office and busy"),
            offline: _t("User is at the office and offline"),
            default: _t("User is at the office"),
        },
    },
    { sequence: 60 }
);
imStatusDataRegistry.add(
    "hr-homeworking-other",
    {
        condition: ({ user }) => user?.employee_id?.work_location_type === "other",
        icon: "location_on",
        icon_class: "",
        title: {
            online: _t("User is at other location and online"),
            away: _t("User is at other location and idle"),
            busy: _t("User is at other location and busy"),
            offline: _t("User is at other location and offline"),
            default: _t("User is at other location"),
        },
    },
    { sequence: 60 }
);
