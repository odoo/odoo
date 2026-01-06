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
export async function renderMedia({ orm, activeTab, availableTabs, oldMediaNode, selectedMedia, extraClassesToAdd, extraClassesToRemove }) {
    const elements = await availableTabs[activeTab].Component.createElements(
        selectedMedia,
        { orm: orm }
    );
    elements.forEach((element) => {
        if (oldMediaNode) {
            element.classList.add(...oldMediaNode.classList);
            const style = oldMediaNode.getAttribute("style");
            if (style) {
                element.setAttribute("style", style);
            }
            if (activeTab === TABS.IMAGES.id) {
                if (oldMediaNode.dataset.shape) {
                    element.dataset.shape = oldMediaNode.dataset.shape;
                }
                if (oldMediaNode.dataset.shapeColors) {
                    element.dataset.shapeColors = oldMediaNode.dataset.shapeColors;
                }
                if (oldMediaNode.dataset.shapeFlip) {
                    element.dataset.shapeFlip = oldMediaNode.dataset.shapeFlip;
                }
                if (oldMediaNode.dataset.shapeRotate) {
                    element.dataset.shapeRotate = oldMediaNode.dataset.shapeRotate;
                }
                if (oldMediaNode.dataset.hoverEffect) {
                    element.dataset.hoverEffect = oldMediaNode.dataset.hoverEffect;
                }
                if (oldMediaNode.dataset.hoverEffectColor) {
                    element.dataset.hoverEffectColor =
                        oldMediaNode.dataset.hoverEffectColor;
                }
                if (oldMediaNode.dataset.hoverEffectStrokeWidth) {
                    element.dataset.hoverEffectStrokeWidth =
                        oldMediaNode.dataset.hoverEffectStrokeWidth;
                }
                if (oldMediaNode.dataset.hoverEffectIntensity) {
                    element.dataset.hoverEffectIntensity =
                        oldMediaNode.dataset.hoverEffectIntensity;
                }
            }
        }
        for (const otherTab of Object.keys(availableTabs).filter(
            (key) => key !== activeTab
        )) {
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
                    for (const name of availableTabs[activeTab].Component
                        .mediaExtraClasses) {
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
        element.classList.add(
            ...availableTabs[activeTab].Component.mediaSpecificClasses
        );
    });
    return elements;
}

export async function saveMediaAndClose(){
    if (saveSelectedMedia) {
        const elements = await this.renderMedia({
            orm: this.orm,
            activeTab: this.activeTab,
            availableTabs: this.tabs,
            oldMediaNode: this.props.media,
            selectedMedia: selectedMedia,
            extraClassesToAdd: this.extraClassesToAdd(),
        });
        if (this.props.multiImages) {
            await this.props.save(elements, selectedMedia, this.state.activeTab);
        } else {
            await this.props.save(elements[0], selectedMedia, this.state.activeTab);
        }
    }
    this.props.close();
}
