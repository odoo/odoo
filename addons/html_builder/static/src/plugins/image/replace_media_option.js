import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

export class ReplaceMediaOption extends BaseOptionComponent {
    static template = "html_builder.ReplaceMediaOption";
    static props = {};
    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            canSetLink: this.canSetLink(editingElement),
            hasHref: this.hasHref(editingElement),
        }));
    }
    canSetLink(editingElement) {
        return (
            isImageSupportedForStyle(editingElement) &&
            !searchSupportedParentLinkEl(editingElement).matches("a[data-oe-xpath]") &&
            !editingElement.classList.contains("media_iframe_video")
        );
    }
    hasHref(editingElement) {
        const parentEl = searchSupportedParentLinkEl(editingElement);
        return parentEl.tagName === "A" && parentEl.hasAttribute("href");
    }
}

export function isImageSupportedForStyle(img) {
    if (!img.parentElement) {
        return false;
    }

    // See also `[data-oe-type='image'] > img` added as data-exclude of some
    // snippet options.
    const isTFieldImg = "oeType" in img.parentElement.dataset;

    // Editable root elements are technically *potentially* supported here (if
    // the edited attributes are not computed inside the related view, they
    // could technically be saved... but as we cannot tell the computed ones
    // apart from the "static" ones, we choose to not support edition at all in
    // those "root" cases).
    // See also `[data-oe-xpath]` added as data-exclude of some snippet options.
    const isEditableRootElement = "oeXpath" in img.dataset;

    return !isTFieldImg && !isEditableRootElement;
}

export function searchSupportedParentLinkEl(editingElement) {
    const parentEl = editingElement.parentElement;
    return parentEl.matches("figure") ? parentEl.parentElement : parentEl;
}
