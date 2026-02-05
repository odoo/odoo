import { imStatusDataRegistry } from "@mail/core/common/im_status";
import { _t } from "@web/core/l10n/translation";

imStatusDataRegistry.add(
    "hr-homeworking-home",
    {
        condition: ({ persona }) => persona.main_user_id?.employee_id?.work_location_type === "home",
        icon: "fa fa-home",
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
        condition: ({ persona }) => persona.main_user_id?.employee_id?.work_location_type === "office",
        icon: "fa fa-building",
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
        condition: ({ persona }) => persona.main_user_id?.employee_id?.work_location_type === "other",
        icon: "fa fa-map-marker",
        title: {
            online: _t("User is at other location and online"),
            away: _t("User is at other location and idle"),
            busy: _t("User is at other location and busy"),
            offline: _t("User is at other location and offline"),
            default: _t("User is at the office"),
        },
    },
    { sequence: 60 }
);
