import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { getScrollingElement } from "@web/core/utils/scrolling";
import { AnimateOption } from "./animate_option";
import { ANIMATE } from "@website/builder/option_sequence";
import { _t } from "@web/core/l10n/translation";
import { AnimateText } from "./animate_text";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { unwrapContents } from "@html_editor/utils/dom";
import { ancestors, closestElement, findFurthest } from "@html_editor/utils/dom_traversal";
import { closestBlock } from "@html_editor/utils/blocks";
import { containsAnyNonPhrasingContent, isVisibleTextNode } from "@html_editor/utils/dom_info";
import { childNodeIndex, DIRECTIONS, nodeSize } from "@html_editor/utils/position";
import { BuilderAction } from "@html_builder/core/builder_action";
import { EmphasizeAnimatedText } from "./emphasize_animated_text";
import { handleImagesIfDataset } from "@html_builder/utils/image";
import { applyFunDependOnSelectorAndExclude } from "@html_builder/plugins/utils";

/**
 * @typedef { Object } AnimateOptionShared
 * @property { AnimateOptionPlugin['forceAnimation'] } forceAnimation
 * @property { AnimateOptionPlugin['getDirectionsItems'] } getDirectionsItems
 * @property { AnimateOptionPlugin['getEffectsItems'] } getEffectsItems
 */

/**
 * @typedef {((editingElement: HTMLElement) => Promise<void>)[]} remove_hover_effect_handlers
 * @typedef {((editingElement: HTMLElement) => Promise<void>)[]} set_hover_effect_handlers
 */

/**
 * @typedef {((el: HTMLElement) => Promise<boolean>)[]} hover_effect_allowed_predicates
 */

export class AnimateOptionPlugin extends Plugin {
    static id = "animateOption";
    static dependencies = ["history", "selection", "split"];
    static shared = [
        "forceAnimation",
        "getDirectionsItems",
        "getEffectsItems",
        "hasAnimationEffect",
        "canHaveHoverEffect",
    ];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [withSequence(ANIMATE, AnimateOption)],
        toolbar_items: [
            {
                id: "animateText",
                groupId: "websiteDecoration",
                description: _t("Animate Text"),
                Component: AnimateText,
                props: {
                    config: this.config.getAnimateTextConfig(),
                    getAnimatedTextOrCreateDefault: this.getAnimatedTextOrCreateDefault.bind(this),
                    isActive: this.isAnimatedTextActive.bind(this),
                    isDisabled: this.isAnimatedTextDisabled.bind(this),
                    animateOptionProps: { ...this.animateOptionProps, requireAnimation: true },
                },
                isAvailable: isHtmlContentSupported,
            },
        ],
        system_classes: ["o_animating"],
        builder_actions: {
            SetAnimationModeAction,
            SetAnimateIntensityAction,
            ForceAnimationAction,
            SetAnimationEffectAction,
        },
        normalize_handlers: this.normalize.bind(this),
        clean_for_save_handlers: this.cleanForSave.bind(this),
        unsplittable_node_predicates: (node) => node.classList?.contains("o_animated_text"),
        collapsed_selection_toolbar_predicate: (selectionData) =>
            !!closestElement(
                selectionData.editableSelection.commonAncestorContainer,
                ".o_animated_text"
            ),
        lower_panel_entries: withSequence(10, { Component: EmphasizeAnimatedText }),
        on_media_dialog_saved_handlers: withSequence(5, this.onMediaDialogSavedHandlers.bind(this)),
        before_save_handlers: () =>
            applyFunDependOnSelectorAndExclude(
                this.cleanImageHoverDataset.bind(this),
                this.editable,
                {
                    selector: "img",
                    exclude: "[data-oe-type='image'] > img",
                }
            ),
    };

    setup() {
        this.scrollingElement = getScrollingElement(this.document);
    }

    async canHaveHoverEffect(el) {
        const proms = this.getResource("hover_effect_allowed_predicates").map((p) => p(el));
        const settledProms = await Promise.all(proms);
        return settledProms.length && settledProms.every(Boolean);
    }

    async onMediaDialogSavedHandlers(elements, { node }) {
        const callback = async (toProcessEl, nodeEl) => {
            const canImgHaveHoverEffect = await this.canHaveHoverEffect(toProcessEl);
            if (!canImgHaveHoverEffect) {
                return;
            }
            toProcessEl.dataset.hoverEffect = nodeEl.dataset.hoverEffect;
            for (const hoverEffectInfo of [
                "hoverEffectColor",
                "hoverEffectStrokeWidth",
                "hoverEffectIntensity",
            ]) {
                if (nodeEl.dataset[hoverEffectInfo]) {
                    toProcessEl.dataset[hoverEffectInfo] = nodeEl.dataset[hoverEffectInfo];
                }
            }
        };
        await handleImagesIfDataset(elements, node, "hoverEffect", callback);
    }

    getEffectsItems(isActiveItem) {
        const isOnAppearance = () => isActiveItem("animation_on_appearance_opt");
        return [
            { className: "o_anim_fade_in", label: "Fade" },
            { className: "o_anim_slide_in", label: "Slide", directionClass: "o_anim_from_right" },
            { className: "o_anim_bounce_in", label: "Bounce" },
            { className: "o_anim_rotate_in", label: "Rotate" },
            { className: "o_anim_zoom_out", label: "Zoom Out" },
            { className: "o_anim_zoom_in", label: "Zoom In" },
            { className: "o_anim_flash", label: "Flash", check: isOnAppearance },
            { className: "o_anim_pulse", label: "Pulse", check: isOnAppearance },
            { className: "o_anim_shake", label: "Shake", check: isOnAppearance },
            { className: "o_anim_tada", label: "Tada", check: isOnAppearance },
            { className: "o_anim_flip_in_x", label: "Flip-In-X", check: isOnAppearance },
            { className: "o_anim_flip_in_y", label: "Flip-In-Y", check: isOnAppearance },
        ];
    }
    getDirectionsItems() {
        const isNotSlideIn = (editingElement) =>
            !editingElement.classList.contains("o_anim_slide_in");
        const isRotate = (editingElement) => editingElement.classList.contains("o_anim_rotate_in");
        const isNotRotate = (editingElement) => !isRotate(editingElement);

        return [
            { className: "", label: "In place", check: isNotSlideIn },

            { className: "o_anim_from_right", label: "From right", check: isNotRotate },
            { className: "o_anim_from_left", label: "From left", check: isNotRotate },
            { className: "o_anim_from_bottom", label: "From bottom", check: isNotRotate },
            { className: "o_anim_from_top", label: "From top", check: isNotRotate },

            { className: "o_anim_from_top_right", label: "From top right", check: isRotate },
            { className: "o_anim_from_top_left", label: "From top left", check: isRotate },
            { className: "o_anim_from_bottom_right", label: "From bottom right", check: isRotate },
            { className: "o_anim_from_bottom_left", label: "From bottom left", check: isRotate },
        ];
    }

    /**
     * Checks whether the given element contains any animation class from the
     * list returned by getEffectsItems().
     *
     * @param {HTMLElement} editingElement- The element to check
     * @returns {boolean} True if at least one animation class is present
     */
    hasAnimationEffect(editingElement) {
        return this.getEffectsItems().some(({ className }) =>
            editingElement.classList.contains(className)
        );
    }

    async forceAnimation(editingElement) {
        editingElement.style.animationName = "dummy";
        if (editingElement.classList.contains("o_animate_on_scroll")) {
            // Trigger a DOM reflow.
            void editingElement.offsetWidth;
            editingElement.style.animationName = "";
            this.window.dispatchEvent(new Event("resize"));
        } else {
            // Trigger a DOM reflow (Needed to prevent the animation from
            // being launched twice when previewing the "Intensity" option).
            await new Promise((resolve) => setTimeout(resolve));
            editingElement.classList.add("o_animating");
            this.scrollingElement.classList.add("o_wanim_overflow_xy_hidden");
            editingElement.style.animationName = "";
            editingElement.addEventListener(
                "animationend",
                () => {
                    this.scrollingElement.classList.remove("o_wanim_overflow_xy_hidden");
                    editingElement.classList.remove("o_animating");
                },
                { once: true }
            );
        }
    }

    /**
     *
     * @returns {{elements: HTMLElement[], onReset: Function}|{}}
     */
    getAnimatedTextOrCreateDefault() {
        const resetAnimatedText = (elements) => {
            const cursors = this.dependencies.selection.preserveSelection();
            for (const element of elements) {
                unwrapContents(element);
            }
            cursors.restore();
            this.dependencies.history.addStep();
        };

        const existingAnimatedTextEls = this.getAnimatedTexts();
        if (existingAnimatedTextEls.length) {
            return { elements: existingAnimatedTextEls, onReset: resetAnimatedText };
        }
        const savePoint = this.dependencies.history.makeSavePoint();
        const { elements: createdAnimatedTextEls, didRemoveOtherTextAnimation } =
            this.createDefaultTextAnimation();
        if (createdAnimatedTextEls?.length) {
            return {
                elements: createdAnimatedTextEls,
                onReset: didRemoveOtherTextAnimation ? resetAnimatedText : savePoint,
            };
        }
        savePoint();
        this.services.notification.add(
            _t(
                "Cannot apply this option on current text selection. Try clearing the format and try again."
            ),
            { type: "danger", sticky: true }
        );
        return {};
    }
    /**
     * @return {HTMLElement?} The `commonAncestorContainer` after the split
     * (null if splits are prevented by an unsplittable node)
     */
    splitForAnimatedText({ anchorNode, focusNode, commonAncestorContainer }) {
        let commonAncestor = commonAncestorContainer;
        for (let [node, forward] of [
            [anchorNode, true],
            [focusNode, false],
        ]) {
            let needToMeetCommonAncestor =
                node !== commonAncestor && node.parentNode !== commonAncestor;
            const animatedTextAncestor = closestElement(node, ".o_animated_text");
            let needToMeetAnimatedTextAncestor =
                !!animatedTextAncestor && commonAncestor.contains(animatedTextAncestor);
            let updatedCommonAncestor = needToMeetCommonAncestor ? undefined : commonAncestor;

            // Go up to the common ancestor of the selection, or to the
            // containing animated text (whichever is the furthest)
            while (needToMeetCommonAncestor || needToMeetAnimatedTextAncestor) {
                if (
                    needToMeetAnimatedTextAncestor &&
                    node.parentNode.classList.contains("o_animated_text")
                ) {
                    needToMeetAnimatedTextAncestor = false;
                }
                const updatingCommonAncestor = commonAncestor === node.parentNode;
                const splitIndex = childNodeIndex(node);
                if (forward ? splitIndex > 0 : splitIndex < node.parentNode.childNodes.length - 1) {
                    // Split the node if needed, abort if unsplittable (unless it is animated text)
                    if (
                        this.dependencies.split.isUnsplittable(node.parentNode) &&
                        !node.parentNode.classList.contains("o_animated_text")
                    ) {
                        return;
                    }
                    node = this.dependencies.split.splitElement(
                        node.parentNode,
                        splitIndex + (forward ? 0 : 1)
                    )[forward ? 1 : 0];
                } else {
                    node = node.parentNode;
                }
                if (updatingCommonAncestor) {
                    updatedCommonAncestor = node.parentNode;
                }
                if (needToMeetCommonAncestor && node.parentNode === commonAncestor) {
                    needToMeetCommonAncestor = false;
                }
            }
            commonAncestor = updatedCommonAncestor || commonAncestor;
        }
        return commonAncestor;
    }
    /**
     * Create spans with the default animation on the selected text.
     *
     * A span is created for each selected line within a block so it never
     * contains block elements or line breaks. Inline ancestors at the selection
     * boundaries are split to keep each span limited to the selected content.
     *
     * @returns {{elements: HTMLElement[], didRemoveOtherTextAnimation: boolean}|{}}
     */
    createDefaultTextAnimation() {
        const selection = this.dependencies.split.splitSelection();
        const selectedTextNodes = this.dependencies.selection
            .getTargetedNodes()
            .filter((node) => node.nodeType === Node.TEXT_NODE && isVisibleTextNode(node));
        const textNodeGroups = [];
        for (const textNode of selectedTextNodes) {
            const block = closestBlock(textNode);
            if (!block) {
                continue;
            }
            const lastTextNodeGroup = textNodeGroups.at(-1);
            const startsNewGroup = !lastTextNodeGroup || lastTextNodeGroup.block !== block;
            if (!startsNewGroup) {
                const range = new Range();
                range.setStartAfter(lastTextNodeGroup.textNodes.at(-1));
                range.setEndBefore(textNode);
            }
            if (startsNewGroup) {
                textNodeGroups.push({ block, textNodes: [textNode] });
            } else {
                lastTextNodeGroup.textNodes.push(textNode);
            }
        }
        if (!textNodeGroups.length) {
            return {};
        }

        const animatedTextEls = [];
        let didRemoveOtherTextAnimation = false;
        for (const { block, textNodes } of textNodeGroups) {
            const startContainer = textNodes[0];
            const endContainer = textNodes.at(-1);
            const commonAncestor = this.splitForAnimatedText({
                anchorNode: startContainer,
                focusNode: endContainer,
                commonAncestorContainer: block,
            });
            if (!commonAncestor) {
                return {};
            }

            const range = new Range();
            range.setStartBefore(
                findFurthest(startContainer, commonAncestor, () => true) || startContainer
            );
            range.setEndAfter(
                findFurthest(endContainer, commonAncestor, () => true) || endContainer
            );
            if (containsAnyNonPhrasingContent(range.cloneContents())) {
                return {};
            }

            const span = this.document.createElement("span");
            range.surroundContents(span);
            // Remove animated text inside the span and containing the span.
            for (const node of [
                ...span.querySelectorAll(".o_animated_text"),
                ...ancestors(span, this.editable).filter((n) =>
                    n.classList.contains("o_animated_text")
                ),
            ]) {
                unwrapContents(node);
                didRemoveOtherTextAnimation = true;
            }
            span.classList.add("o_animated_text", "o_animate_preview");
            span.classList.add("o_animate", "o_anim_fade_in"); // default animation
            animatedTextEls.push(span);
        }

        const firstAnimatedTextEl = animatedTextEls[0];
        const lastAnimatedTextEl = animatedTextEls.at(-1);
        this.dependencies.selection.setSelection(
            selection.direction === DIRECTIONS.RIGHT
                ? {
                      anchorNode: firstAnimatedTextEl,
                      anchorOffset: 0,
                      focusNode: lastAnimatedTextEl,
                      focusOffset: nodeSize(lastAnimatedTextEl),
                  }
                : {
                      anchorNode: lastAnimatedTextEl,
                      anchorOffset: nodeSize(lastAnimatedTextEl),
                      focusNode: firstAnimatedTextEl,
                      focusOffset: 0,
                  }
        );
        this.dependencies.history.addStep();

        return { elements: animatedTextEls, didRemoveOtherTextAnimation };
    }
    /**
     * Returns the animated text elements that correspond to the current
     * selection.
     *
     * @returns {HTMLElement[]}
     */
    getAnimatedTexts() {
        const selection = this.dependencies.selection.getSelectionData().editableSelection;
        const normalizeText = (text) => text.replace(/\s+/g, " ").trim();
        const selectionText = normalizeText(selection.textContent());
        const ancestor = closestElement(selection.commonAncestorContainer, ".o_animated_text");
        if (ancestor) {
            const ancestorText = normalizeText(ancestor.innerText);
            if (selection.isCollapsed || selectionText === ancestorText) {
                return [ancestor];
            }
        }
        if (selection.isCollapsed) {
            return [];
        }

        const animatedTextEls = [...this.editable.querySelectorAll(".o_animated_text")].filter(
            (element) => selection.intersectsNode(element)
        );
        const animatedText = normalizeText(
            animatedTextEls.map((element) => element.innerText).join(" ")
        );
        return animatedTextEls.length && selectionText === animatedText ? animatedTextEls : [];
    }
    isAnimatedTextActive() {
        return !!this.getAnimatedTexts().length;
    }
    isAnimatedTextDisabled() {
        return 2 <= this.dependencies.selection.getTargetedNodes().size;
    }

    normalize(root) {
        const previewEls = [...root.querySelectorAll(".o_animate_preview")];
        if (root.classList.contains("o_animate_preview")) {
            previewEls.push(root);
        }
        for (const el of previewEls) {
            if (el.classList.contains("o_animate")) {
                el.classList.remove("o_animate_preview");
            }
        }

        const animateEls = [...root.querySelectorAll(".o_animate")];
        if (root.classList.contains("o_animate")) {
            animateEls.push(root);
        }
        for (const el of animateEls) {
            if (!el.classList.contains("o_animate_preview")) {
                el.classList.add("o_animate_preview");
            }
        }
        const animateImg = animateEls
            .map((el) => (el.tagName === "IMG" && el) || el.querySelectorAll("img"))
            .flat()
            .filter(Boolean);
        for (const img of animateImg) {
            img.loading = "eager";
        }
    }
    cleanForSave({ root }) {
        for (const el of root.querySelectorAll(".o_animate_preview")) {
            el.classList.remove("o_animate_preview");
        }
    }
    async cleanImageHoverDataset(imgEl) {
        if (!imgEl.dataset.hoverEffect) {
            return;
        }
        const canImgHaveHoverEffect = await this.canHaveHoverEffect(imgEl);
        if (!canImgHaveHoverEffect) {
            delete imgEl.dataset.hoverEffect;
            delete imgEl.dataset.hoverEffectColor;
            delete imgEl.dataset.hoverEffectStrokeWidth;
            delete imgEl.dataset.hoverEffectIntensity;
            imgEl.classList.remove("o_animate_on_hover");
        }
    }
}

export class SetAnimationModeAction extends BuilderAction {
    static id = "setAnimationMode";
    static dependencies = ["animateOption"];
    setup() {
        this.animationWithFadein = ["onAppearance", "onScroll"];
        this.scrollingElement = getScrollingElement(this.document);
    }
    // todo: to remove after having the commit of louis
    isApplied() {
        return true;
    }
    async clean({ editingElement, value: effectName, nextAction }) {
        this.scrollingElement.classList.remove("o_wanim_overflow_xy_hidden");
        editingElement.classList.remove(
            "o_animating",
            "o_animate_both_scroll",
            "o_visible",
            "o_animated",
            "o_animate_out"
        );
        editingElement.style.animationDelay = "";
        editingElement.style.animationPlayState = "";
        editingElement.style.animationName = "";
        editingElement.style.visibility = "";

        if (effectName === "onScroll") {
            delete editingElement.dataset.scrollZoneStart;
            delete editingElement.dataset.scrollZoneEnd;
        }
        if (effectName === "onHover") {
            // Use getResource instead of this.dependencies as imageHover is not
            // included in translation. This implementation is a hack and could
            // be improved.
            await this.getResource("remove_hover_effect_handlers")[0](editingElement);
        }

        const isNextAnimationFadein = this.animationWithFadein.includes(nextAction.value);
        if (!isNextAnimationFadein) {
            this._removeEffectAndDirectionClasses(editingElement.classList);
            editingElement.style.setProperty("--wanim-intensity", "");
            editingElement.style.animationDuration = "";
            this._setImagesLazyLoading(editingElement);
        }
    }

    async apply({ editingElement, value: effectName, params: { forceAnimation } }) {
        const { hasAnimationEffect } = this.dependencies.animateOption;
        // Prevent adding fade-in when another animation class is already present.
        if (this.animationWithFadein.includes(effectName) && !hasAnimationEffect(editingElement)) {
            editingElement.classList.add("o_anim_fade_in");
        }
        if (effectName === "onScroll") {
            editingElement.dataset.scrollZoneStart = 0;
            editingElement.dataset.scrollZoneEnd = 100;
        }
        if (effectName === "onHover") {
            // Use getResource instead of this.dependencies as imageHover is not
            // included in translation. This implementation is a hack and could
            // be improved.
            await this.getResource("set_hover_effect_handlers")[0](editingElement);
        }
        if (forceAnimation) {
            this.dependencies.animateOption.forceAnimation(editingElement);
        }
    }
    /**
     * Adds the lazy loading on images because animated images can appear before
     * or after their parents and cause bugs in the animations. To put "lazy"
     * back on the "loading" attribute, we simply remove the attribute as it is
     * automatically added on page load.
     *
     * @private
     */
    _setImagesLazyLoading(editingElement) {
        const imgEls = editingElement.matches("img")
            ? [editingElement]
            : editingElement.querySelectorAll("img");
        for (const imgEl of imgEls) {
            // Let the automatic system add the loading attribute
            imgEl.removeAttribute("loading");
        }
    }
    _removeEffectAndDirectionClasses(targetClassList) {
        const classes = this.dependencies.animateOption
            .getEffectsItems()
            .map(({ className }) => className)
            .concat(
                this.dependencies.animateOption
                    .getDirectionsItems()
                    .map(({ className }) => className)
                    .filter(Boolean)
            );

        const classesToRemove = intersect(classes, [...targetClassList]);
        for (const className of classesToRemove) {
            targetClassList.remove(className);
        }
    }
}
export class SetAnimateIntensityAction extends BuilderAction {
    static id = "setAnimateIntensity";
    static dependencies = ["animateOption"];
    getValue({ editingElement }) {
        const intensity = parseInt(
            this.window.getComputedStyle(editingElement).getPropertyValue("--wanim-intensity")
        );
        return intensity;
    }
    apply({ editingElement, value }) {
        editingElement.style.setProperty("--wanim-intensity", `${value}`);
        this.dependencies.animateOption.forceAnimation(editingElement);
    }
}
export class ForceAnimationAction extends BuilderAction {
    static id = "forceAnimation";
    static dependencies = ["animateOption"];
    // todo: to remove after having the commit of louis
    isActive() {
        return true;
    }
    apply({ editingElement }) {
        this.dependencies.animateOption.forceAnimation(editingElement);
    }
}
export class SetAnimationEffectAction extends BuilderAction {
    static id = "setAnimationEffect";
    static dependencies = ["animateOption"];
    isApplied({ editingElement, value: className }) {
        return editingElement.classList.contains(className);
    }
    clean({ editingElement }) {
        const classNames = this.dependencies.animateOption
            .getEffectsItems()
            .map(({ className }) => className)
            .concat(
                this.dependencies.animateOption
                    .getDirectionsItems()
                    .map(({ className }) => className)
            );
        for (const className of classNames) {
            if (editingElement.classList.contains(className)) {
                editingElement.classList.remove(className);
            }
        }
    }
    apply({ editingElement, params: { mainParam: directionClassName }, value: effectClassName }) {
        if (directionClassName) {
            editingElement.classList.add(directionClassName);
        }
        editingElement.classList.add(effectClassName);
        this.dependencies.animateOption.forceAnimation(editingElement);
    }
}

registry.category("website-plugins").add(AnimateOptionPlugin.id, AnimateOptionPlugin);

function intersect(a, b) {
    return a.filter((value) => b.includes(value));
}
