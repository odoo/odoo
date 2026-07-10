import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { getScrollingElement } from "@web/core/utils/scrolling";
import { _t } from "@web/core/l10n/translation";
import { AnimateText } from "./animate_text";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { ancestors, closestElement, findFurthest } from "@html_editor/utils/dom_traversal";
import { childNodeIndex, DIRECTIONS, nodeSize } from "@html_editor/utils/position";
import { BuilderAction } from "@html_builder/core/builder_action";
import { EmphasizeAnimatedText } from "./emphasize_animated_text";
import { handleImagesIfDataset } from "@html_builder/utils/image";
import { applyFunDependOnSelectorAndExclude } from "@html_builder/plugins/utils";
import {
    applyDefaultAnimationClass,
    DEFAULT_ANIMATION_CLASS,
    getDefaultAnimationSelector,
} from "@website/utils/animate_default";

const ANIMATED_SELECTOR = `.o_animate, .${DEFAULT_ANIMATION_CLASS}`;

/**
 * The values the theme's animation applies, and the property each is read from.
 * The delay comes from "--wanim-base-delay" and not from the computed
 * "animation-delay", which also holds the position of the block in its row (see
 * "--wanim-index" in website.scss) and stops being true when that row changes.
 */
const DEFAULT_ANIMATION_STYLES = [
    ["animation-duration", "animation-duration"],
    ["animation-delay", "--wanim-base-delay"],
    ["--wanim-intensity", "--wanim-intensity"],
];

/**
 * @typedef { Object } AnimateOptionShared
 * @property { AnimateOptionPlugin['forceAnimation'] } forceAnimation
 * @property { AnimateOptionPlugin['getDirectionsItems'] } getDirectionsItems
 * @property { AnimateOptionPlugin['getEffectsItems'] } getEffectsItems
 * @property { AnimateOptionPlugin['getEffectClass'] } getEffectClass
 * @property { AnimateOptionPlugin['isDefaultAnimationEnabled'] } isDefaultAnimationEnabled
 * @property { AnimateOptionPlugin['getDefaultAnimationClasses'] } getDefaultAnimationClasses
 * @property { AnimateOptionPlugin['getDirectionClass'] } getDirectionClass
 * @property { AnimateOptionPlugin['setDirectionClass'] } setDirectionClass
 */

/**
 * @typedef {((editingElement: HTMLElement) => Promise<void>)[]} on_hover_animation_mode_cleaned_handlers
 * @typedef {((editingElement: HTMLElement) => Promise<void>)[]} on_hover_animation_mode_applied_handlers
 */

/**
 * @typedef {((el: HTMLElement) => boolean | undefined)[]} can_have_hover_effect_predicates
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
        "getEffectClass",
        "canHaveHoverEffect",
        "isDefaultAnimationEnabled",
        "getDefaultAnimationClasses",
        "getDirectionClass",
        "setDirectionClass",
    ];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
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
        toolbar_namespace_providers: [
            withSequence(90, (targetedNodes, editableSelection) =>
                closestElement(editableSelection.commonAncestorContainer, ".o_animated_text")
                    ? "compact"
                    : undefined
            ),
        ],
        system_classes: ["o_animating", DEFAULT_ANIMATION_CLASS],
        builder_actions: {
            SetAnimationModeAction,
            SetAnimateIntensityAction,
            ForceAnimationAction,
            SetAnimationEffectAction,
            SetAnimationDirectionAction,
        },
        normalize_processors: this.normalize.bind(this),
        clean_for_save_processors: this.cleanForSave.bind(this),
        is_node_splittable_predicates: (node) => {
            if (node.classList?.contains("o_animated_text")) {
                return false;
            }
        },
        lower_panel_entries: withSequence(10, { Component: EmphasizeAnimatedText }),
        // This is done to clean the dataset of the images saved in the db.
        on_will_save_handlers: () =>
            applyFunDependOnSelectorAndExclude(
                this.cleanImageHoverDataset.bind(this),
                this.editable,
                {
                    selector: "img",
                    exclude: "[data-oe-type='image'] > img",
                }
            ),
        on_will_save_media_dialog_handlers: withSequence(
            5,
            this.onWillSaveMediaDialogHandlers.bind(this)
        ),
    };

    setup() {
        this.scrollingElement = getScrollingElement(this.document);
    }

    isDefaultAnimationEnabled() {
        return !!getDefaultAnimationSelector(this.document);
    }

    async canHaveHoverEffect(el) {
        const proms = this.getResource("hover_effect_image_dataset_providers").map((p) => p(el));
        const datasets = await Promise.all(proms);
        const dataset = Object.assign({}, ...datasets);
        return this.checkPredicates("can_have_hover_effect_predicates", el, dataset) ?? false;
    }

    async onWillSaveMediaDialogHandlers(elements, { node }) {
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
        const isOnAppearance = () =>
            isActiveItem("animation_on_appearance_opt") || isActiveItem("animation_default_opt");
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
            this.getEffectClass(editingElement) !== "o_anim_slide_in";
        const isRotate = (editingElement) =>
            this.getEffectClass(editingElement) === "o_anim_rotate_in";
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

    /**
     * The effect class the element animates with or, on the theme's animation,
     * the one it is equivalent to. Empty when it does not animate.
     */
    getEffectClass(editingElement) {
        if (editingElement.classList.contains(DEFAULT_ANIMATION_CLASS)) {
            return this.getDefaultAnimationClasses(editingElement).effectClass;
        }
        return (
            this.getEffectsItems()
                .map(({ className }) => className)
                .find((className) => editingElement.classList.contains(className)) || ""
        );
    }

    /**
     * The effect and direction the theme's animation is equivalent to. The
     * element carries neither class, so both are read back from the keyframes,
     * named after their effect class and an optional direction suffix (e.g.
     * "o_anim_fade_in_up").
     *
     * @returns {{effectClass: string, directionClass: string}} an empty
     *      direction when the animation plays in place
     */
    getDefaultAnimationClasses(editingElement) {
        const { animationName } = this.window.getComputedStyle(editingElement);
        const effectClass =
            this.getEffectsItems()
                .map(({ className }) => className)
                .find((className) => animationName.startsWith(className)) || "o_anim_fade_in";
        return {
            effectClass,
            // No suffix: it plays in place, whatever direction the snippet asks.
            directionClass:
                animationName === effectClass
                    ? ""
                    : this.getAppliedDirectionClass(editingElement) || "o_anim_from_bottom",
        };
    }

    getAppliedDirectionClass(editingElement) {
        return (
            this.getDirectionsItems()
                .map(({ className }) => className)
                .find((className) => className && editingElement.classList.contains(className)) ||
            ""
        );
    }

    /**
     * The class the element carries or, on the theme's animation, the direction
     * its keyframes imply. Empty when the animation plays in place.
     */
    getDirectionClass(editingElement) {
        return editingElement.classList.contains(DEFAULT_ANIMATION_CLASS)
            ? this.getDefaultAnimationClasses(editingElement).directionClass
            : this.getAppliedDirectionClass(editingElement);
    }

    /**
     * Sets the direction the element animates from, empty for in place.
     */
    setDirectionClass(editingElement, className) {
        if (editingElement.classList.contains(DEFAULT_ANIMATION_CLASS)) {
            this.convertDefaultAnimationToCustom(editingElement);
        }
        editingElement.classList.remove(
            ...this.getDirectionsItems()
                .map((item) => item.className)
                .filter(Boolean)
        );
        if (className) {
            editingElement.classList.add(className);
        }
        this.forceAnimation(editingElement);
    }

    /**
     * Turns the theme's animation into an equivalent custom one: what the CSS
     * was applying is made explicit, so that the block keeps looking the same
     * once the theme option no longer drives it.
     */
    convertDefaultAnimationToCustom(editingElement) {
        const style = this.window.getComputedStyle(editingElement);
        // The theme's animation is faster and subtler than "o_animate". What
        // the edit triggering this just set inline is the user's, not the
        // theme's, and stays.
        const valuesToKeep = DEFAULT_ANIMATION_STYLES.filter(
            ([property]) => !editingElement.style.getPropertyValue(property)
        ).map(([property, source]) => [property, style.getPropertyValue(source).trim()]);
        const { effectClass, directionClass } = this.getDefaultAnimationClasses(editingElement);
        const appliedClass = this.getAppliedDirectionClass(editingElement);
        if (directionClass) {
            // Only implicit in the CSS: make it explicit.
            editingElement.classList.add(directionClass);
        } else if (appliedClass) {
            // Plays in place: the direction the snippet asks for is ignored.
            editingElement.classList.remove(appliedClass);
        }
        editingElement.classList.add(effectClass);
        editingElement.classList.replace(DEFAULT_ANIMATION_CLASS, "o_animate");
        for (const [property, value] of valuesToKeep) {
            if (value) {
                editingElement.style.setProperty(property, value);
            }
        }
    }

    async forceAnimation(editingElement) {
        // Editing a setting makes the animation the user's: it has to become
        // explicit, or it is lost or silently switches to another type.
        if (editingElement.classList.contains(DEFAULT_ANIMATION_CLASS)) {
            this.convertDefaultAnimationToCustom(editingElement);
        }
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
     * @returns {{element: HTMLElement, onReset: Function}|{}}
     */
    getAnimatedTextOrCreateDefault() {
        const resetAnimatedText = (el) => {
            const cursors = this.dependencies.selection.preserveSelection();
            el.replaceWith(...el.childNodes);
            cursors.restore();
            this.dependencies.history.commit();
        };

        const existingAnimatedTextEl = this.getAnimatedText();
        if (existingAnimatedTextEl) {
            return { element: existingAnimatedTextEl, onReset: resetAnimatedText };
        }
        const savePoint = this.dependencies.history.makeSavePoint();
        const { element: createdAnimatedTextEl, didRemoveOtherTextAnimation } =
            this.createDefaultTextAnimation();
        if (createdAnimatedTextEl) {
            return {
                element: createdAnimatedTextEl,
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
            let needToMeetAnimatedTextAncestor = !!closestElement(node, ".o_animated_text");
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
     * Create a span with the default animation, on the selection
     *
     * @returns {{element: HTMLElement, didRemoveOtherTextAnimation: boolean}|{}}
     */
    createDefaultTextAnimation() {
        /*
        We need to create 1 element with the content of the selection to set the
        text animation. This element must be the only animated text element for
        the selected text

        To be able to create 1 new element containing the selection, we need to
        split the elements that are descendants of the common ancestor and that
        contains one end of the selection.

        To remove any other overlapping animation on text, we need to:
        - remove the animation on the part of a splitted element that falls
          inside the selection
        - split ancestor animated text that fully contains the selection, to
          remove the animation on the part containing the selection
        - remove text animation inside of the created element

        If these splits would split an unsplittable node, we abort
        */
        const selection = this.dependencies.split.splitSelection();
        const commonAncestor = this.splitForAnimatedText(selection);
        if (!commonAncestor) {
            return {};
        }
        const { startContainer, endContainer, direction } = selection;

        const range = new Range();
        range.setStartBefore(
            findFurthest(startContainer, commonAncestor, () => true) || startContainer
        );
        range.setEndAfter(findFurthest(endContainer, commonAncestor, () => true) || endContainer);
        const span = this.document.createElement("span");
        range.surroundContents(span);
        // Remove animated text inside the span and containing the span (the ancestors have been split so it only contains the span)
        let didRemoveOtherTextAnimation = false;
        for (const node of [
            ...span.querySelectorAll(".o_animated_text"),
            ...ancestors(span, this.editable).filter((n) =>
                n.classList.contains("o_animated_text")
            ),
        ]) {
            node.replaceWith(...node.childNodes);
            didRemoveOtherTextAnimation = true;
        }
        span.classList.add("o_animated_text", "o_animate_preview");
        span.classList.add("o_animate", "o_anim_fade_in"); // default animation
        this.dependencies.selection.setSelection(
            direction === DIRECTIONS.RIGHT
                ? {
                      anchorNode: span,
                      anchorOffset: 0,
                      focusNode: span,
                      focusOffset: nodeSize(span),
                  }
                : {
                      anchorNode: span,
                      anchorOffset: nodeSize(span),
                      focusNode: span,
                      focusOffset: 0,
                  }
        );
        this.dependencies.history.commit();

        return { element: span, didRemoveOtherTextAnimation };
    }
    /**
     * Returns the element that is an animated text that corresponds to the
     * current selection (if there is any)
     *
     * @returns {HTMLElement?}
     */
    getAnimatedText() {
        const selection = this.dependencies.selection.getSelectionData().editableSelection;
        const ancestor = closestElement(selection.commonAncestorContainer, ".o_animated_text");
        if (ancestor) {
            const selectionText = selection.toString().replace(/\s+/g, " ").trim();
            const ancestorText = ancestor.innerText.replace(/\s+/g, " ").trim();
            if (selection.isCollapsed || selectionText === ancestorText) {
                return ancestor;
            }
        }
    }
    isAnimatedTextActive() {
        return !!this.getAnimatedText();
    }
    isAnimatedTextDisabled() {
        return 2 <= this.dependencies.selection.getTargetedNodes().size;
    }

    normalize(root) {
        applyDefaultAnimationClass(root);

        const previewEls = [...root.querySelectorAll(".o_animate_preview")];
        if (root.classList.contains("o_animate_preview")) {
            previewEls.push(root);
        }
        for (const el of previewEls) {
            if (el.matches(ANIMATED_SELECTOR)) {
                el.classList.remove("o_animate_preview");
            }
        }

        const animateEls = [...root.querySelectorAll(ANIMATED_SELECTOR)];
        if (root.matches(ANIMATED_SELECTOR)) {
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
        return root;
    }
    cleanForSave(root) {
        const selector = `.o_animate_preview, .${DEFAULT_ANIMATION_CLASS}`;
        for (const el of root.querySelectorAll(selector)) {
            el.classList.remove("o_animate_preview", DEFAULT_ANIMATION_CLASS);
        }
        return root;
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

registry.category("website-plugins").add(AnimateOptionPlugin.id, AnimateOptionPlugin);
registry.category("translation-plugins").add(AnimateOptionPlugin.id, AnimateOptionPlugin);

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
            await this.triggerAsync("on_hover_animation_mode_cleaned_handlers", editingElement);
        }

        const isNextAnimationFadein = this.animationWithFadein.includes(nextAction.value);
        if (!isNextAnimationFadein) {
            this._removeEffectAndDirectionClasses(editingElement.classList);
            editingElement.style.setProperty("--wanim-intensity", "");
            editingElement.style.animationDuration = "";
            this._setImagesLazyLoading(editingElement);
        }
    }

    async apply({ editingElement, value: effectName, params: { forceAnimation, isDefault } }) {
        const { hasAnimationEffect, getEffectsItems } = this.dependencies.animateOption;
        if (isDefault) {
            // Back to an animation applying no class of its own: whatever the
            // custom one left behind would override it. The direction class
            // stays, the theme animates from it (see "$o-no-direction").
            editingElement.classList.remove(...getEffectsItems().map(({ className }) => className));
            for (const [property] of DEFAULT_ANIMATION_STYLES) {
                editingElement.style.removeProperty(property);
            }
            return;
        }
        // Remove appearance-only effects when switching to "On Scroll" so the
        // default "Fade" effect can be applied.
        if (effectName === "onScroll") {
            const invalidEffect = getEffectsItems().find(
                (effect) => effect.check && editingElement.classList.contains(effect.className)
            );
            invalidEffect && editingElement.classList.remove(invalidEffect.className);
            editingElement.dataset.scrollZoneStart = 0;
            editingElement.dataset.scrollZoneEnd = 100;
        }
        // Prevent adding fade-in when another animation class is already present.
        if (this.animationWithFadein.includes(effectName) && !hasAnimationEffect(editingElement)) {
            editingElement.classList.add("o_anim_fade_in");
        }
        if (effectName === "onHover") {
            // Use getResource instead of this.dependencies as imageHover is not
            // included in translation. This implementation is a hack and could
            // be improved.
            await this.triggerAsync("on_hover_animation_mode_applied_handlers", editingElement);
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
export class SetAnimationDirectionAction extends BuilderAction {
    static id = "setAnimationDirection";
    static dependencies = ["animateOption"];
    isApplied({ editingElement, value: className }) {
        return className === this.dependencies.animateOption.getDirectionClass(editingElement);
    }
    apply({ editingElement, value: className }) {
        this.dependencies.animateOption.setDirectionClass(editingElement, className);
    }
}
export class SetAnimationEffectAction extends BuilderAction {
    static id = "setAnimationEffect";
    static dependencies = ["animateOption"];
    isApplied({ editingElement, value: className }) {
        if (editingElement.classList.contains(DEFAULT_ANIMATION_CLASS)) {
            // No effect class: show the one it is equivalent to.
            const { effectClass } =
                this.dependencies.animateOption.getDefaultAnimationClasses(editingElement);
            return className === effectClass;
        }
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

function intersect(a, b) {
    return a.filter((value) => b.includes(value));
}
