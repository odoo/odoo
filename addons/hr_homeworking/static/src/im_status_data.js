import { getImStatusText, imStatusDataRegistry } from "@mail/core/common/im_status_data";
import { _t } from "@web/core/l10n/translation";

const workLocationMap = {
    home: {
        icon: "fa-home",
        title: _t("At Home (%(status)s)"),
        ariaLabel: _t("User is at home and %(status)s"),
    },
    office: {
        icon: "fa-building",
        title: _t("At the Office (%(status)s)"),
        ariaLabel: _t("User is at the office and %(status)s"),
    },
    other: {
        icon: "fa-map-marker",
        title: _t("At Other location (%(status)s)"),
        ariaLabel: _t("User is at other location and %(status)s"),
    },
};

imStatusDataRegistry.add("hr-homeworking", {
    condition(component) {
        return component.persona.remote_work_location_type;
    },
    icon(component) {
        return workLocationMap[component.persona.remote_work_location_type].icon;
    },
    title(component) {
        return _t(
            workLocationMap[component.persona.remote_work_location_type].title,
            { status: getImStatusText(component.persona.im_status) }
        )
    },
    ariaLabel(component) {
        return _t(
            workLocationMap[component.persona.remote_work_location_type].ariaLabel,
            { status: getImStatusText(component.persona.im_status) }
        )
    },
    sequence: 60,
});
