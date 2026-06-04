import { ImageSelector } from "./image_selector";
import { IconSelector } from "./icon_selector";
import { _t } from "@web/core/l10n/translation";

export const TABS = {
    IMAGES: {
        id: "IMAGES",
        title: _t("Images"),
        Component: ImageSelector,
        sequence: 10,
    },
    ICONS: {
        id: "ICONS",
        title: _t("Icons"),
        Component: IconSelector,
        sequence: 20,
    },
};

/**
 * Render the selected media for insertion in the editor
 *
 * @param orm
 * @param {String} activeTab
 * @param {Object} availableTabs
 * @param {HTMLElement} oldMediaNode
 * @param {Array<Object>} selectedMedia
 * @param {Array<String>} extraClassesToAdd
 * @returns {Array<HTMLElement>}
 */
export async function renderMedia({
    orm,
    activeTab,
    availableTabs,
    oldMediaNode,
    selectedMedia,
    extraClassesToAdd,
    extraClassesToRemove,
}) {
    const elements = await availableTabs[activeTab].Component.createElements(selectedMedia, {
        orm: orm,
    });
    elements.forEach((element) => {
        if (oldMediaNode) {
            const oldMediaClasses = [...oldMediaNode.classList].filter(
                // If we replace an existing icon from the media dialog, we
                // don't want to keep the filled state if the new icon is not
                // filled. We also want to remove FA classes in case we replace
                // a legacy FA icon.
                (cls) =>
                    !["oi-filled", "fab", "fad", "far", "fa"].includes(cls) &&
                    !cls.startsWith("fa-")
            );
            element.classList.add(...oldMediaClasses);
            const style = oldMediaNode.getAttribute("style");
            if (style) {
                element.setAttribute("style", style);
            }
        }
        for (const otherTab of Object.keys(availableTabs).filter((key) => key !== activeTab)) {
            for (const property of availableTabs[otherTab].Component.mediaSpecificStyles) {
                element.style.removeProperty(property);
            }
            element.classList.remove(...availableTabs[otherTab].Component.mediaSpecificClasses);
            const extraClassesToRemove = [];
            for (const name of availableTabs[otherTab].Component.mediaExtraClasses) {
                if (typeof name === "string") {
                    extraClassesToRemove.push(name);
                } else {
                    // Regex
                    for (const className of element.classList) {
                        if (className.match(name)) {
                            extraClassesToRemove.push(className);
                        }
                    }
                }
            }
            // Remove classes that do not also exist in the target type.
            element.classList.remove(
                ...extraClassesToRemove.filter((candidateName) => {
                    for (const name of availableTabs[activeTab].Component.mediaExtraClasses) {
                        if (typeof name === "string") {
                            if (candidateName === name) {
                                return false;
                            }
                        } else {
                            // Regex
                            if (candidateName.match(name)) {
                                return false;
                            }
                        }
                    }
                    return true;
                })
            );
        }

        element.classList.add(...extraClassesToAdd);

        element.classList.remove(...extraClassesToRemove);
        element.classList.remove("o_modified_image_to_save");
        element.classList.remove("oe_edited_link");
        element.classList.add(...availableTabs[activeTab].Component.mediaSpecificClasses);
    });
    return elements;
}
