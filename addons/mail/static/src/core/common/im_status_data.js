import { useComponent, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export const imStatusDataRegistry = registry.category("im-status-data");

export const imStatusInfo = {
    online: { text: _t("Online"), class: "text-success" },
    away: { text: _t("Idle"), class: "o-away" },
    offline: { text: _t("Offline"), class: "text-700 opacity-75" },
    bot: { text: _t("Bot"), class: "text-success" },
};

export function getImStatusText(status) {
    return imStatusInfo[status]?.text || _t("No IM status available");
}

export function getImStatusClass(status) {
    return imStatusInfo[status]?.class || "opacity-75";
}

imStatusDataRegistry.add("mail", {
    icon(component) {
        switch (component.persona.im_status) {
            case "online":
                return "fa-circle";
            case "away":
                return "fa-circle";
            case "offline":
                return "fa-circle-o";
            case "bot":
                return "fa-heart";
            default:
                return "fa-question-circle";
        }
    },
    title(component) {
        return getImStatusText(component.persona.im_status);
    },
    ariaLabel(component) {
        return component.persona.im_status
            ? _t("User is %(status)s", { status: getImStatusText(component.persona.im_status) })
            : _t("User IM status is unavailable");
    },
    sequence: 99,
});

function transformData(component, id, data) {
    return {
        get condition() {
            return data.condition === undefined ? true : data.condition(component);
        },
        get icon() {
            return typeof data.icon === "function" ? data.icon(component) : data.icon;
        },
        get title() {
            return typeof data.title === "function" ? data.title(component) : data.title;
        },
        get ariaLabel() {
            return typeof data.ariaLabel === "function"
                ? data.ariaLabel(component)
                : data.ariaLabel;
        },
        get sequence() {
            return typeof data.sequence === "function" ? data.sequence(component) : data.sequence;
        },
    };
}

export function useImStatusData() {
    const component = useComponent();
    const transformedData = imStatusDataRegistry
        .getEntries()
        .map(([id, action]) => transformData(component, id, action));
    const state = useState({
        get activeData() {
            return transformedData
                .sort((a1, a2) => a1.sequence - a2.sequence)
                .find((action) => action.condition);
        },
    });
    return state;
}
