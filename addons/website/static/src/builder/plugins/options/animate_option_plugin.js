import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { getScrollingElement } from "@web/core/utils/scrolling";
import { AnimateOption } from "./animate_option";
import { ANIMATE } from "@website/builder/option_sequence";
import { _t } from "@web/core/l10n/translation";
import { AnimateText } from "./animate_text";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { ancestors, closestElement, findFurthest } from "@html_editor/utils/dom_traversal";
import { childNodeIndex, DIRECTIONS, nodeSize } from "@html_editor/utils/position";
import { BuilderAction } from "@html_builder/core/builder_action";
import { EmphasizeAnimatedText } from "./emphasize_animated_text";

export class AnimateOptionPlugin extends Plugin {
    static id = "animateOption";
    static dependencies = ["history", "selection", "split"];
    static shared = ["forceAnimation", "getDirectionsItems", "getEffectsItems"];
    animateOptionProps = {
        getDirectionsItems: this.getDirectionsItems.bind(this),
        getEffectsItems: this.getEffectsItems.bind(this),
        canHaveHoverEffect: async (el) => {
            const proms = this.getResource("hover_effect_allowed_predicates").map((p) => p(el));
            const allowed = (await Promise.all(proms)).filter((allowed) => allowed != null);
            return allowed.length && allowed.every(Boolean);
        },
    };
    resources = {
        builder_options: [
            withSequence(ANIMATE, {
                OptionComponent: AnimateOption,
                selector: ".o_animable, section .row > div, img, .fa, .btn",
                exclude:
                    "[data-oe-xpath], .o_not-animable, .s_col_no_resize.row > div, .s_col_no_resize",
                props: this.animateOptionProps,
                // todo: to implement
                // textSelector: ".o_animated_text",
            }),
        ],
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
    };

    setup() {
        this.scrollingElement = getScrollingElement(this.document);
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
     * @returns {{element: HTMLElement, onReset: Function}|{}}
     */
    getAnimatedTextOrCreateDefault() {
        const resetAnimatedText = (el) => {
            const cursors = this.dependencies.selection.preserveSelection();
            el.replaceWith(...el.childNodes);
            cursors.restore();
            this.dependencies.history.addStep();
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
        this.dependencies.history.addStep();

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
        if (
            ancestor &&
            (selection.isCollapsed ||
                this.dependencies.selection.areNodeContentsFullySelected(ancestor))
        ) {
            return ancestor;
        }
    }
    isAnimatedTextActive() {
        return !!this.getAnimatedText();
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
}

export class SetAnimationModeAction extends BuilderAction {
    static id = "setAnimationMode";
    static dependencies = ["animateOption", "imageHover"];
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
            await this.dependencies.imageHover.removeHoverEffect(editingElement);
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
        if (this.animationWithFadein.includes(effectName)) {
            editingElement.classList.add("o_anim_fade_in");
        }
        if (effectName === "onScroll") {
            editingElement.dataset.scrollZoneStart = 0;
            editingElement.dataset.scrollZoneEnd = 100;
        }
        if (effectName === "onHover") {
            await this.dependencies.imageHover.setHoverEffect(editingElement);
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
