import { isVisible } from "@html_builder/utils/utils";
import { Plugin } from "@html_editor/plugin";
import { isElement } from "@html_editor/utils/dom_info";
import { _t } from "@web/core/l10n/translation";

export class DropZonePlugin extends Plugin {
    static id = "dropzone";
    static dependencies = ["history", "setup_editor_plugin"];
    static shared = [
        "activateDropzones",
        "removeDropzones",
        "getDropRootElement",
        "getSelectorSiblings",
        "getSelectorChildren",
        "getSelectors",
    ];
    resources = {
        savable_mutation_record_predicates: (record) => {
            if (record.type === "childList") {
                const addedOrRemovedNode = record.addedNodes[0] || record.removedNodes[0];
                // Do not record the addition/removal of the dropzones.
                if (isElement(addedOrRemovedNode) && addedOrRemovedNode.matches(".oe_drop_zone")) {
                    return false;
                }
            }
            return true;
        },
    };

    setup() {
        this.snippetModel = this.config.snippetModel;
        this.dropzoneSelectors = this.getResource("dropzone_selector");
        this.iframe = this.document.defaultView.frameElement;
    }

    /**
     * Returns the root element in which the elements can be dropped.
     * (e.g. if a modal or a dropdown is open, the snippets must be dropped only
     * in this element)
     *
     * @returns {HTMLElement|undefined}
     */
    getDropRootElement() {
        const openModalEl = this.editable.querySelector(".modal.show");
        if (openModalEl && isVisible(openModalEl)) {
            return openModalEl;
        }
        const openDropdownEl = this.editable.querySelector(
            ".o_editable.dropdown-menu.show, .dropdown-menu.show .o_editable.dropdown-menu"
        );
        if (openDropdownEl) {
            return openDropdownEl;
        }
        const openOffcanvasEl = this.editable.querySelector(".offcanvas.show");
        if (openOffcanvasEl) {
            return openOffcanvasEl.querySelector(".offcanvas-body");
        }
    }

    /**
     * Gets the selectors that determine where the given element can be placed.
     *
     * @param {HTMLElement} snippetEl the element
     * @param {Boolean} [checkLockedWithin=false] true if the selectors should
     *   be filtered based on the `dropLockWithin` selectors
     * @param {Boolean} [withGrids=false] true if the elements in grid mode are
     *   considered
     * @returns {Object} [selectorChildren, selectorSiblings]
     */
    getSelectors(snippetEl, checkLockedWithin = false, withGrids = false) {
        let selectorChildren = [];
        let selectorSiblings = [];
        const selectorExcludeAncestor = [];
        const selectorLockedWithin = [];

        const editableAreaEls = this.dependencies.setup_editor_plugin.getEditableAreas();
        const rootEl = this.getDropRootElement();
        this.dropzoneSelectors.forEach((dropzoneSelector) => {
            const {
                selector,
                exclude = false,
                dropIn,
                dropNear,
                dropLockWithin,
                excludeAncestor,
                excludeNearParent,
            } = dropzoneSelector;
            if (snippetEl.matches(selector) && !snippetEl.matches(exclude)) {
                if (dropNear) {
                    selectorSiblings.push(
                        ...this.getSelectorSiblings(editableAreaEls, rootEl, {
                            selector: dropNear,
                            excludeNearParent,
                        })
                    );
                }
                if (dropIn) {
                    selectorChildren.push(
                        ...this.getSelectorChildren(editableAreaEls, rootEl, { selector: dropIn })
                    );
                }
                if (dropLockWithin) {
                    selectorLockedWithin.push(dropLockWithin);
                }
                if (excludeAncestor) {
                    selectorExcludeAncestor.push(excludeAncestor);
                }
            }
        });

        // Remove the dragged element from the selectors.
        selectorSiblings = selectorSiblings.filter((el) => !snippetEl.contains(el));
        selectorChildren = selectorChildren.filter((el) => !snippetEl.contains(el));

        // Prevent dropping an element into another one.
        // (e.g. ToC inside another ToC)
        if (selectorExcludeAncestor.length) {
            const excludeAncestor = selectorExcludeAncestor.join(",");
            selectorSiblings = selectorSiblings.filter((el) => !el.closest(excludeAncestor));
            selectorChildren = selectorChildren.filter((el) => !el.closest(excludeAncestor));
        }

        // Prevent dropping an element outside a given direct or indirect parent
        // (e.g. form field must remain within its own form)
        if (checkLockedWithin && selectorLockedWithin.length) {
            const lockedAncestorsSelector = selectorLockedWithin.join(",");
            const closestLockedAncestorEl = snippetEl.closest(lockedAncestorsSelector);
            const filterFct = (el) =>
                el.closest(lockedAncestorsSelector) === closestLockedAncestorEl;
            selectorSiblings = selectorSiblings.filter(filterFct);
            selectorChildren = selectorChildren.filter(filterFct);
        }

        // Prevent dropping sanitized elements in sanitized zones.
        let forbidSanitize = false;
        // Check if the element is sanitized or if it contains such elements.
        for (const el of [snippetEl, ...snippetEl.querySelectorAll("[data-snippet")]) {
            const snippet = this.snippetModel.getOriginalSnippet(el.dataset.snippet);
            if (snippet && snippet.forbidSanitize) {
                forbidSanitize = snippet.forbidSanitize;
                if (forbidSanitize === true) {
                    break;
                }
            }
        }
        const selectorSanitized = new Set();
        const filterSanitized = (el) => {
            if (el.closest('[data-oe-sanitize="no_block"]')) {
                return false;
            }
            let sanitizedZoneEl;
            if (forbidSanitize === "form") {
                sanitizedZoneEl = el.closest(
                    '[data-oe-sanitize]:not([data-oe-sanitize="allow_form"]):not([data-oe-sanitize="no_block"])'
                );
            } else if (forbidSanitize) {
                sanitizedZoneEl = el.closest(
                    '[data-oe-sanitize]:not([data-oe-sanitize="no_block"])'
                );
            }
            if (sanitizedZoneEl) {
                selectorSanitized.add(sanitizedZoneEl);
                return false;
            }
            return true;
        };
        selectorSiblings = selectorSiblings.filter((el) => filterSanitized(el));
        selectorChildren = selectorChildren.filter((el) => filterSanitized(el));

        // Remove the siblings/children that would add a dropzone as a direct
        // child of a grid and make a dedicated set out of the identified grids.
        const selectorGrids = new Set();
        if (withGrids) {
            const filterGrids = (potentialGridEl) => {
                if (potentialGridEl.matches(".o_grid_mode")) {
                    selectorGrids.add(potentialGridEl);
                    return false;
                }
                return true;
            };
            selectorSiblings = selectorSiblings.filter((el) => filterGrids(el.parentElement));
            selectorChildren = selectorChildren.filter((el) => filterGrids(el));
        }

        return {
            selectorSiblings: new Set(selectorSiblings),
            selectorChildren: new Set(selectorChildren),
            selectorSanitized,
            selectorGrids,
        };
    }

    /**
     * Checks the condition for a sibling/children to be valid.
     *
     * @param {HTMLElement} el A selectorSibling or selectorChildren element
     * @param {HTMLElement} rootEl the root element in which we can drop
     * @returns {Boolean}
     */
    checkSelectors(el, rootEl) {
        if (rootEl && !rootEl.contains(el)) {
            return false;
        }
        // Drop only in visible elements.
        if (!isVisible(el)) {
            return false;
        }
        // Drop only in open dropdown and offcanvas elements.
        if (
            (el.closest(".dropdown-menu") && !el.closest(".dropdown-menu.show")) ||
            (el.closest(".offcanvas") && !el.closest(".offcanvas.show"))
        ) {
            return false;
        }
        return true;
    }

    /**
     * Returns all the elements matching the `dropNear` selector, that are
     * contained in editable elements. They correspond to elements next to which
     * an element can be dropped (= siblings).
     *
     * @param {Array<HTMLElement>} editableAreaEls the editable elements
     * @param {HTMLElement} rootEl the root element in which we can drop
     * @param {String} selector `dropNear` selector
     * @param {String} excludeParent selector allowing to exclude the siblings
     * with a parent matching it.
     * @returns {Array<HTMLElement>}
     */
    getSelectorSiblings(editableAreaEls, rootEl, { selector, excludeParent = false }) {
        const filterFct = (el) =>
            this.checkSelectors(el, rootEl) &&
            // Do not drop blocks into an image field.
            !el.parentNode.closest("[data-oe-type=image]") &&
            !el.matches(".o_not_editable *") &&
            !el.matches(".o_we_no_overlay") &&
            (excludeParent ? !el.parentNode.matches(excludeParent) : true);

        const dropAreaEls = [];
        editableAreaEls.forEach((el) => {
            const areaEls = [...el.querySelectorAll(selector)].filter(filterFct);
            dropAreaEls.push(...areaEls);
        });
        return dropAreaEls;
    }

    /**
     * Returns all the elements matching the `dropIn` selector, that are
     * contained in editable elements. They correspond to the elements in which
     * elements can be dropped as children.
     *
     * @param {Array<HTMLElement>} editableAreaEls the editable elements
     * @param {HTMLElement} rootEl the root element in which we can drop
     * @param {String} selector `dropIn` selector
     * @returns {Array<HTMLElement>}
     */
    getSelectorChildren(editableAreaEls, rootEl, { selector }) {
        const filterFct = (el) =>
            this.checkSelectors(el, rootEl) &&
            // Do not drop blocks into an image field.
            !el.closest("[data-oe-type=image]") &&
            !el.matches('.o_not_editable :not([contenteditable="true"]), .o_not_editable');

        const dropAreaEls = [];
        editableAreaEls.forEach((el) => {
            const areaEls = el.matches(selector) ? [el] : [];
            areaEls.push(...el.querySelectorAll(selector));
            dropAreaEls.push(...areaEls.filter(filterFct));
        });
        return dropAreaEls;
    }

    /**
     * Creates a dropzone and adapts it depending on the hook environment.
     *
     * @param {HTMLElement} parentEl the dropzone parent
     * @param {Boolean} isVertical true if the dropzone should be vertical
     * @param {Object} style the style to assign to the dropzone
     * @returns {HTMLElement}
     */
    createDropzone(parentEl, isVertical, style) {
        const dropzoneEl = this.document.createElement("div");
        dropzoneEl.classList.add("oe_drop_zone", "oe_insert");

        // Set the messages to display in the dropzone.
        const editorMessagesAttributes = [
            "data-editor-message-default",
            "data-editor-message",
            "data-editor-sub-message",
        ];
        for (const messageAttribute of editorMessagesAttributes) {
            const message = parentEl.getAttribute(messageAttribute);
            if (message) {
                dropzoneEl.setAttribute(messageAttribute, message);
            }
        }

        if (isVertical) {
            dropzoneEl.classList.add("oe_vertical");
        }
        Object.assign(dropzoneEl.style, style);
        return dropzoneEl;
    }

    /**
     * Creates a dropzone covering the whole sanitized element in which we
     * cannot drop.
     *
     * @returns {HTMLElement}
     */
    createSanitizedDropzone() {
        const dropzoneEl = this.document.createElement("div");
        dropzoneEl.classList.add(
            "oe_drop_zone",
            "oe_insert",
            "oe_sanitized_drop_zone",
            "text-center",
            "text-uppercase"
        );
        const messageEl = this.document.createElement("p");
        messageEl.textContent = _t("For technical reasons, this block cannot be dropped here");
        dropzoneEl.prepend(messageEl);
        return dropzoneEl;
    }

    /**
     * Creates a dropzone taking the entire area of the given row in grid mode.
     * It will allow to place the elements dragged over it inside the grid it
     * belongs to.
     *
     * @param {Element} rowEl
     * @returns {HTMLElement}
     */
    createGridDropzone(rowEl) {
        const columnCount = 12;
        const rowCount = parseInt(rowEl.dataset.rowCount);
        const dropzoneEl = this.document.createElement("div");
        dropzoneEl.classList.add("oe_drop_zone", "oe_insert", "oe_grid_zone");
        Object.assign(dropzoneEl.style, {
            gridArea: 1 + "/" + 1 + "/" + (rowCount + 1) + "/" + (columnCount + 1),
            minHeight: window.getComputedStyle(rowEl).height,
            width: window.getComputedStyle(rowEl).width,
        });
        return dropzoneEl;
    }

    /**
     * Checks whether the dropzone to insert should be horizontal or vertical.
     *
     * @param {HTMLElement} hookEl the element before/after which the dropzone
     *   will be inserted
     * @param {HTMLElement} parentEl the parent element of `hookEl`
     * @param {Boolean} toInsertInline true if the dragged element is inline
     * @returns {Object} - `vertical[Boolean]`: true if the dropzone is vertical
     *                   - `style[Object]`: the style to add to the dropzone
     */
    setDropzoneDirection(hookEl, parentEl, toInsertInline) {
        let vertical = false;
        const style = {};
        const hookStyle = window.getComputedStyle(hookEl);
        const parentStyle = window.getComputedStyle(parentEl);

        const float = hookStyle.float || hookStyle.cssFloat;
        const { display, flexDirection } = parentStyle;

        if (
            toInsertInline ||
            float === "left" ||
            float === "right" ||
            (display === "flex" && flexDirection === "row")
        ) {
            if (!toInsertInline) {
                style.float = float;
            }
            // Compute the parent content width and the element outer width.
            const parentPaddingX =
                parseFloat(parentStyle.paddingLeft) + parseFloat(parentStyle.paddingRight);
            const parentBorderX =
                parseFloat(parentStyle.borderLeft) + parseFloat(parentStyle.borderRight);
            const hookMarginX =
                parseFloat(hookStyle.marginLeft) + parseFloat(hookStyle.marginRight);

            const parentContentWidth =
                parentEl.getBoundingClientRect().width - parentPaddingX - parentBorderX;
            const hookOuterWidth = hookEl.getBoundingClientRect().width + hookMarginX;

            if (parseInt(parentContentWidth) !== parseInt(hookOuterWidth)) {
                vertical = true;
                const hookOuterHeight = hookEl.getBoundingClientRect().height;
                style.height = Math.max(hookOuterHeight, 30) + "px";
                if (toInsertInline) {
                    style.display = "inline-block";
                    style.verticalAlign = "middle";
                    style.float = "none";
                }
            }
        }

        return { vertical, style };
    }

    /**
     * @typedef Selectors
     * @property {Set<HTMLElement>} selectorSiblings elements which must have
     *   siblings dropzones
     * @property {Set<HTMLElement>} selectorChildren elements which must have
     *   child dropzones between each existing child
     * @property {Set<HTMLElement>} selectorSanitized sanitized elements in
     *   which an indicative dropzone preventing the drop must be inserted
     * @property {Set<HTMLElement>} selectorGrids elements which are in grid
     *   mode and for which a grid dropzone must be inserted
     */
    /**
     * @typedef Options
     * @property {Boolean} toInsertInline true if the dragged element is inline
     * @property {Boolean}isContentInIframe true if the content is inside an
     * iframe
     */
    /**
     * Creates dropzones in the DOM (= locations where dragged elements may be
     * dropped).
     *
     * @param {Selectors} selectors
     * @param {Options} options
     * @returns
     */
    activateDropzones(
        { selectorSiblings, selectorChildren, selectorSanitized, selectorGrids },
        { toInsertInline, isContentInIframe = true } = {}
    ) {
        const isIgnored = (el) => el.matches(".o_we_no_overlay") || !isVisible(el);
        const hookEls = [];
        for (const parentEl of selectorChildren) {
            const validChildrenEls = [...parentEl.children].filter((el) => !isIgnored(el));
            hookEls.push(...validChildrenEls);
            parentEl.prepend(this.createDropzone(parentEl));
        }
        hookEls.push(...selectorSiblings);

        // Inserting the normal dropzones.
        for (const hookEl of hookEls) {
            const parentEl = hookEl.parentElement;
            const { vertical, style } = this.setDropzoneDirection(hookEl, parentEl, toInsertInline);

            let previousEl = hookEl.previousElementSibling;
            while (previousEl && isIgnored(previousEl)) {
                previousEl = previousEl.previousElementSibling;
            }
            if (!previousEl || !previousEl.classList.contains("oe_drop_zone")) {
                hookEl.before(this.createDropzone(parentEl, vertical, style));
            }

            if (hookEl.classList.contains("oe_drop_clone")) {
                continue;
            }

            let nextEl = hookEl.nextElementSibling;
            while (nextEl && isIgnored(nextEl)) {
                nextEl = nextEl.nextElementSibling;
            }
            if (!nextEl || !nextEl.classList.contains("oe_drop_zone")) {
                hookEl.after(this.createDropzone(parentEl, vertical, style));
            }
        }

        // Inserting a sanitized dropzone for each sanitized area.
        for (const sanitizedZoneEl of selectorSanitized) {
            sanitizedZoneEl.style.position = "relative";
            sanitizedZoneEl.prepend(this.createSanitizedDropzone());
        }
        this.sanitizedZoneEls = selectorSanitized;

        // Inserting a grid dropzone for each row in grid mode.
        for (const rowEl of selectorGrids) {
            rowEl.append(this.createGridDropzone(rowEl));
        }

        // In the case where the editable content is in an iframe, take the
        // iframe offset into account to compute the dropzones.
        if (isContentInIframe) {
            const iframeRect = this.iframe.getBoundingClientRect();
            const dropzoneEls = [...this.editable.querySelectorAll(".oe_drop_zone")];
            dropzoneEls.forEach((dropzoneEl) => {
                dropzoneEl.oldGetBoundingRect = dropzoneEl.getBoundingClientRect;
                dropzoneEl.getBoundingClientRect = () => {
                    const rect = dropzoneEl.oldGetBoundingRect();
                    rect.x += iframeRect.x;
                    rect.y += iframeRect.y;
                    return rect;
                };
            });
        }

        return [...this.editable.querySelectorAll(".oe_drop_zone:not(.oe_sanitized_drop_zone)")];
    }

    /**
     * Removes all the dropzones.
     */
    removeDropzones() {
        this.editable.querySelectorAll(".oe_drop_zone").forEach((dropzoneEl) => {
            dropzoneEl.remove();
        });
        this.sanitizedZoneEls.forEach((sanitizedZoneEl) =>
            sanitizedZoneEl.style.removeProperty("position")
        );
        this.sanitizedZoneEls = [];
    }
}
