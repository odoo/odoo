import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class RatingOptionPlugin extends Plugin {
    static id = "ratingOption";
    static dependencies = ["history", "media"];
    selector = ".s_rating";
    resources = {
        builder_options: {
            template: "html_builder.RatingOption",
            selector: ".s_rating",
        },
        builder_actions: this.getActions(),
    };
    getActions() {
        return {
            setIcons: {
                apply: ({ editingElement, param: iconParam }) => {
                    editingElement.dataset.icon = iconParam;
                    renderIcons(editingElement);
                    delete editingElement.dataset.activeCustomIcon;
                    delete editingElement.dataset.inactiveCustomIcon;
                },
                isApplied: ({ editingElement, param: iconParam }) =>
                    getIconType(editingElement) === iconParam,
            },
            customIcon: {
                load: async ({ editingElement, param: customParam }) =>
                    new Promise((resolve) => {
                        const isCustomActive = customParam === "customActiveIcon";
                        const media = document.createElement("i");
                        media.className = isCustomActive
                            ? getActiveCustomIcons(editingElement)
                            : getInactiveCustomIcons(editingElement);
                        const mediaDialogParams = {
                            noImages: true,
                            noDocuments: true,
                            noVideos: true,
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
                    }),
                apply: ({ editingElement, loadResult: savedIconEl, param: customParam }) => {
                    if (!savedIconEl) {
                        return;
                    }
                    const isCustomActive = customParam === "customActiveIcon";
                    const customClass = savedIconEl.className;
                    const activeIconEls = getActiveIcons(editingElement);
                    const inactiveIconEls = getInactiveIcons(editingElement);
                    const iconEls = isCustomActive ? activeIconEls : inactiveIconEls;
                    iconEls.forEach((iconEl) => (iconEl.className = customClass));
                    const faClassActiveCustomIcons =
                        activeIconEls.length > 0
                            ? activeIconEls[0].getAttribute("class")
                            : customClass;
                    const faClassInactiveCustomIcons =
                        inactiveIconEls.length > 0
                            ? inactiveIconEls[0].getAttribute("class")
                            : customClass;
                    editingElement.dataset.activeCustomIcon = faClassActiveCustomIcons;
                    editingElement.dataset.inactiveCustomIcon = faClassInactiveCustomIcons;
                    editingElement.dataset.icon = "custom";
                },
            },
            activeIconsNumber: {
                apply: ({ editingElement, value }) => {
                    const nbActiveIcons = parseInt(value);
                    const nbTotalIcons = getAllIcons(editingElement).length;
                    createIcons({
                        editingElement: editingElement,
                        nbActiveIcons: nbActiveIcons,
                        nbTotalIcons: nbTotalIcons,
                    });
                },
                getValue: ({ editingElement }) => getActiveIcons(editingElement).length,
            },
            totalIconsNumber: {
                apply: ({ editingElement, value }) => {
                    const nbTotalIcons = Math.max(parseInt(value), 1);
                    const nbActiveIcons = getActiveIcons(editingElement).length;
                    createIcons({
                        editingElement: editingElement,
                        nbActiveIcons: nbActiveIcons,
                        nbTotalIcons: nbTotalIcons,
                    });
                },
                getValue: ({ editingElement }) => getAllIcons(editingElement).length,
            },
        };
    }
}

registry.category("website-plugins").add(RatingOptionPlugin.id, RatingOptionPlugin);

function createIcons({ editingElement, nbActiveIcons, nbTotalIcons }) {
    const activeIconEl = editingElement.querySelector(".s_rating_active_icons");
    const inactiveIconEl = editingElement.querySelector(".s_rating_inactive_icons");
    const iconEls = getAllIcons(editingElement);
    [...iconEls].forEach((iconEl) => iconEl.remove());
    for (let i = 0; i < nbTotalIcons; i++) {
        if (i < nbActiveIcons) {
            activeIconEl.appendChild(document.createElement("i"));
        } else {
            inactiveIconEl.append(document.createElement("i"));
        }
    }
    renderIcons(editingElement);
}
function getActiveCustomIcons(editingElement) {
    return editingElement.dataset.activeCustomIcon || "";
}
function getActiveIcons(editingElement) {
    return editingElement.querySelectorAll(".s_rating_active_icons > i");
}
function getAllIcons(editingElement) {
    return editingElement.querySelectorAll(".s_rating_icons i");
}
function getIconType(editingElement) {
    return editingElement.dataset.icon;
}
function getInactiveCustomIcons(editingElement) {
    return editingElement.dataset.inactiveCustomIcon || "";
}
function getInactiveIcons(editingElement) {
    return editingElement.querySelectorAll(".s_rating_inactive_icons  > i");
}
function renderIcons(editingElement) {
    const iconType = getIconType(editingElement);
    const icons = {
        "fa-star": "fa-star-o",
        "fa-thumbs-up": "fa-thumbs-o-up",
        "fa-circle": "fa-circle-o",
        "fa-square": "fa-square-o",
        "fa-heart": "fa-heart-o",
    };
    const faClassActiveIcons =
        iconType === "custom" ? getActiveCustomIcons(editingElement) : "fa " + iconType;
    const faClassInactiveIcons =
        iconType === "custom" ? getInactiveCustomIcons(editingElement) : "fa " + icons[iconType];
    const activeIconEls = getActiveIcons(editingElement);
    const inactiveIconEls = getInactiveIcons(editingElement);
    activeIconEls.forEach((activeIconEl) => (activeIconEl.className = faClassActiveIcons));
    inactiveIconEls.forEach((inactiveIconEl) => (inactiveIconEl.className = faClassInactiveIcons));
}
