import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class accordionOptionPlugin extends Plugin {
    static id = "accordionOptionPlugin";
    static dependencies = ["clone", "media"];
    resources = {
        builder_options: [
            {
                template: "html_builder.AccordionOption",
                selector: ".s_accordion",
            },
            {
                template: "html_builder.AccordionItemOption",
                selector: ".s_accordion .accordion-item",
            },
        ],
        builder_actions: this.getActions(),
    };

    getActions() {
        return {
            defineCustomIcon: {
                load: async () => {
                    let selectedIconClass;
                    await new Promise((resolve) => {
                        const onClose = this.dependencies.media.openMediaDialog({
                            noImages: true,
                            noDocuments: true,
                            noVideos: true,
                            extraTabs: [],
                            save: (icon) => {
                                selectedIconClass = icon.className;
                                resolve();
                            },
                        });
                        onClose.then(resolve);
                    });
                    return selectedIconClass;
                },
                apply: ({ editingElement, param, loadResult }) => {
                    const isActiveIcon = param.isActiveIcon;
                    const media = document.createElement("i");
                    media.className = isActiveIcon
                        ? editingElement.dataset.activeCustomIcon
                        : editingElement.dataset.inactiveCustomIcon;
                    const customClass = loadResult;
                    const activeIconsEls =
                        editingElement.querySelectorAll(".o_custom_icon_active i");
                    const inactiveIconsEls = editingElement.querySelectorAll(
                        ".o_custom_icon_inactive i"
                    );
                    const iconsEls = isActiveIcon ? activeIconsEls : inactiveIconsEls;
                    iconsEls.forEach((iconEl) => {
                        iconEl.removeAttribute("class");
                        iconEl.classList.add(...customClass.split(" "));
                    });
                    if (iconsEls === activeIconsEls) {
                        editingElement.dataset.activeCustomIcon = customClass;
                    } else {
                        editingElement.dataset.inactiveCustomIcon = customClass;
                    }
                },
            },
            customAccordionIcon: {
                apply: ({ editingElement, param, value }) => {
                    const accordionButtonEls = editingElement.querySelectorAll(".accordion-button");
                    const activeCustomIcon =
                        editingElement.dataset.activeCustomIcon || "fa fa-arrow-up";
                    const inactiveCustomIcon =
                        editingElement.dataset.inactiveCustomIcon || "fa fa-arrow-down";
                    if (value) {
                        if (value === "custom") {
                            editingElement.dataset.activeCustomIcon = activeCustomIcon;
                            editingElement.dataset.inactiveCustomIcon = inactiveCustomIcon;
                        }
                        accordionButtonEls.forEach((item) => {
                            let el = item.querySelector(".o_custom_icons_wrap");
                            if (!el) {
                                el = document.createElement("span");
                                el.className =
                                    "o_custom_icons_wrap position-relative d-block flex-shrink-0 overflow-hidden";
                                item.appendChild(el);
                            }

                            while (el.firstChild) {
                                el.removeChild(el.firstChild);
                            }
                            if (!param.selectIcons) {
                                return;
                            }
                            const customIconsClasses =
                                "position-absolute top-0 end-0 bottom-0 start-0 d-flex align-items-center justify-content-center";
                            const customIconActiveEl = document.createElement("span");
                            customIconActiveEl.className = customIconsClasses;
                            customIconActiveEl.classList.add("o_custom_icon_active");
                            const customIconActiveIEl = document.createElement("i");
                            customIconActiveIEl.className = activeCustomIcon;
                            customIconActiveEl.appendChild(customIconActiveIEl);
                            el.appendChild(customIconActiveEl);
                            const customIconInactiveEl = document.createElement("span");
                            customIconInactiveEl.className = customIconsClasses;
                            customIconInactiveEl.classList.add("o_custom_icon_inactive");
                            const customIconInactiveIEl = document.createElement("i");
                            customIconInactiveIEl.className = inactiveCustomIcon;
                            customIconInactiveEl.appendChild(customIconInactiveIEl);
                            el.appendChild(customIconInactiveEl);
                        });
                    } else {
                        accordionButtonEls.forEach((item) => {
                            const customIconWrapEl = item.querySelector(".o_custom_icons_wrap");
                            if (customIconWrapEl) {
                                customIconWrapEl.remove();
                            }
                        });
                    }
                    if (value !== "custom") {
                        delete editingElement.dataset.activeCustomIcon;
                        delete editingElement.dataset.inactiveCustomIcon;
                    }
                },
            },
        };
    }
}

registry.category("website-plugins").add(accordionOptionPlugin.id, accordionOptionPlugin);
