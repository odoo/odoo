import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { clamp } from "@web/core/utils/numbers";

export class RatingOptionPlugin extends Plugin {
    static id = "ratingOption";
    static dependencies = ["history", "media"];
    /** @type {import("plugins").BuilderResources} */
    resources = {
        so_content_addition_selectors: [".s_rating"],
        builder_actions: {
            SetIconsAction,
            CustomIconAction,
            ActiveIconsNumberAction,
            TotalIconsNumberAction,
        },
    };
}

export class SetIconsAction extends BuilderAction {
    static id = "setIcons";
    apply({ editingElement, params: { mainParam: iconParam } }) {
        editingElement.dataset.ratingIcon = iconParam;
        delete editingElement.dataset.activeCustomIcon;
        delete editingElement.dataset.inactiveCustomIcon;
        delete editingElement.dataset.activeCustomIconFilled;
        delete editingElement.dataset.inactiveCustomIconFilled;
        renderIcons(editingElement);
    }
    isApplied({ editingElement, params: { mainParam: iconParam } }) {
        return getIconType(editingElement) === iconParam;
    }
}
export class CustomIconAction extends BuilderAction {
    static id = "customIcon";
    static dependencies = ["media"];
    async load() {
        return new Promise((resolve) => {
            const media = document.createElement("i");
            const mediaDialogParams = {
                visibleTabs: ["ICONS"],
                media,
                save: (icon) => {
                    resolve(icon);
                },
            };
            const onClose = this.dependencies.media.openMediaDialog(
                mediaDialogParams,
                this.editable
            );
            onClose.then(resolve);
        });
    }
    apply({ editingElement, loadResult: savedIconEl, params: { mainParam: customParam } }) {
        if (!savedIconEl) {
            return;
        }
        const isCustomActive = customParam === "customActiveIcon";
        const customIcon = savedIconEl.dataset.icon;
        const activeIconEls = getActiveIcons(editingElement);
        const inactiveIconEls = getInactiveIcons(editingElement);
        const iconEls = isCustomActive ? activeIconEls : inactiveIconEls;
        iconEls.forEach((iconEl) => (iconEl.dataset.icon = customIcon));
        const oiActiveCustomIcons =
            activeIconEls.length > 0 ? activeIconEls[0].getAttribute("data-icon") : customIcon;
        const oiInactiveCustomIcons =
            inactiveIconEls.length > 0 ? inactiveIconEls[0].getAttribute("data-icon") : customIcon;
        editingElement.dataset.activeCustomIcon = oiActiveCustomIcons;
        editingElement.dataset.inactiveCustomIcon = oiInactiveCustomIcons;
        const filledKey = isCustomActive ? "activeCustomIconFilled" : "inactiveCustomIconFilled";
        editingElement.dataset[filledKey] = String(savedIconEl.classList.contains("oi-filled"));
        editingElement.dataset.ratingIcon = "dark_mode";
        const iconClass = isCustomActive
            ? getActiveIconClass(editingElement)
            : getInactiveIconClass(editingElement);
        renderIconGroup(iconEls, iconClass, customIcon);
    }
}
export class ActiveIconsNumberAction extends BuilderAction {
    static id = "activeIconsNumber";
    apply({ editingElement, value }) {
        const nbActiveIcons = parseInt(value);
        const nbTotalIcons = getAllIcons(editingElement).length;
        createIcons({
            editingElement: editingElement,
            nbActiveIcons: nbActiveIcons,
            nbTotalIcons: nbTotalIcons,
        });
        updateAriaLabel({ editingElement, nbActiveIcons, nbTotalIcons });
    }
    getValue({ editingElement }) {
        return getActiveIcons(editingElement).length;
    }
}
export class TotalIconsNumberAction extends BuilderAction {
    static id = "totalIconsNumber";
    apply({ editingElement, value }) {
        const nbTotalIcons = Math.max(parseInt(value), 1);
        const nbActiveIcons = getActiveIcons(editingElement).length;
        createIcons({
            editingElement: editingElement,
            nbActiveIcons: nbActiveIcons,
            nbTotalIcons: nbTotalIcons,
        });
        updateAriaLabel({ editingElement, nbActiveIcons, nbTotalIcons });
    }
    getValue({ editingElement }) {
        return getAllIcons(editingElement).length;
    }
}

registry.category("builder-plugins").add(RatingOptionPlugin.id, RatingOptionPlugin);

function createIcons({ editingElement, nbActiveIcons, nbTotalIcons }) {
    const activeIconEl = editingElement.querySelector(".s_rating_active_icons");
    const inactiveIconEl = editingElement.querySelector(".s_rating_inactive_icons");
    const iconEls = getAllIcons(editingElement);
    [...iconEls].forEach((iconEl) => iconEl.remove());
    for (let i = 0; i < nbTotalIcons; i++) {
        const targetEl = i < nbActiveIcons ? activeIconEl : inactiveIconEl;
        targetEl.appendChild(document.createElement("i"));
        targetEl.appendChild(document.createTextNode(" "));
    }
    renderIcons(editingElement);
}
function updateAriaLabel({ editingElement, nbActiveIcons, nbTotalIcons }) {
    editingElement.querySelector(".s_rating_icons")?.setAttribute(
        "aria-label",
        _t("%(nbActiveIcons)s out of %(nbTotalIcons)s stars", {
            nbActiveIcons: clamp(parseInt(nbActiveIcons), 0, nbTotalIcons),
            nbTotalIcons,
        })
    );
}
function getActiveIconClass(editingElement) {
    return editingElement.dataset.activeCustomIconFilled === "false" ? "oi" : "oi oi-filled";
}
function getActiveIconName(editingElement) {
    return editingElement.dataset.activeCustomIcon || getIconType(editingElement);
}
function getActiveIcons(editingElement) {
    return editingElement.querySelectorAll(".s_rating_active_icons > i");
}
function getAllIcons(editingElement) {
    return editingElement.querySelectorAll(".s_rating_icons i");
}
function getIconType(editingElement) {
    return editingElement.dataset.ratingIcon;
}
function getInactiveIconClass(editingElement) {
    return editingElement.dataset.inactiveCustomIconFilled === "true" ? "oi oi-filled" : "oi";
}
function getInactiveIconName(editingElement) {
    return editingElement.dataset.inactiveCustomIcon || getIconType(editingElement);
}
function getInactiveIcons(editingElement) {
    return editingElement.querySelectorAll(".s_rating_inactive_icons  > i");
}
function renderIcons(editingElement) {
    renderIconGroup(
        getActiveIcons(editingElement),
        getActiveIconClass(editingElement),
        getActiveIconName(editingElement)
    );
    renderIconGroup(
        getInactiveIcons(editingElement),
        getInactiveIconClass(editingElement),
        getInactiveIconName(editingElement)
    );
}
function renderIconGroup(iconEls, iconClass, iconName) {
    iconEls.forEach((iconEl) => {
        iconEl.className = iconClass;
        iconEl.dataset.icon = iconName;
    });
}
