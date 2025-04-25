import { isElementVisible } from "@html_builder/utils/utils";
import { Plugin } from "@html_editor/plugin";
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

    setup() {
        this.snippetModel = this.services["html_builder.snippets"];
        this.dropzoneSelectors = this.getResource("dropzone_selector");
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
        if (isElementVisible(openModalEl)) {
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
     * @returns {Object} [selectorChildren, selectorSiblings]
     */
    getSelectors(snippetEl) {
        let selectorChildren = [];
        let selectorSiblings = [];
        const selectorExcludeAncestor = [];

        const editableAreaEls = this.dependencies.setup_editor_plugin.getEditableAreas();
        const rootEl = this.getDropRootElement();
        this.dropzoneSelectors.forEach((dropzoneSelector) => {
            const {
                selector,
                exclude = false,
                dropIn,
                dropNear,
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
                if (excludeAncestor) {
                    selectorExcludeAncestor.push(excludeAncestor);
                }
            }
        });

        // Prevent dropping an element into another one.
        // (E.g. ToC inside another ToC)
        if (selectorExcludeAncestor.length) {
            const excludeAncestor = selectorExcludeAncestor.join(",");
            selectorSiblings = selectorSiblings.filter((el) => !el.closest(excludeAncestor));
            selectorChildren = selectorChildren.filter((el) => !el.closest(excludeAncestor));
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

        return {
            selectorSiblings: new Set(selectorSiblings),
            selectorChildren: new Set(selectorChildren),
            selectorSanitized,
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
        const invisibleClasses =
            ".o_snippet_invisible, .o_snippet_mobile_invisible, .o_snippet_desktop_invisible";
        if (el.closest(invisibleClasses) && el.closest("[data-invisible]")) {
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
     * Creates a dropzone element.
     * This allows to add data on the dropzone depending on the hook
     * environment.
     * TODO
     * @param {HTMLElement} hookEl the dropzone parent
     * @param {boolean} [vertical=false]
     * @param {Object} [style]
     * @returns {HTMLElement}
     */
    createDropzone(hookEl, isVertical, style) {
        const dropzoneEl = this.document.createElement("div");
        dropzoneEl.classList.add("oe_drop_zone", "oe_insert");

        // Set the messages to display in the dropzone.
        const editorMessagesAttributes = [
            "data-editor-message-default",
            "data-editor-message",
            "data-editor-sub-message",
        ];
        for (const messageAttribute of editorMessagesAttributes) {
            const message = hookEl.getAttribute(messageAttribute);
            if (message) {
                dropzoneEl.setAttribute(messageAttribute, message);
            }
        }

        if (isVertical) {
            dropzoneEl.classList.add("oe_vertical");
        }
        if (style) {
            Object.assign(dropzoneEl.style, style);
        }
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
     * @typedef Selectors
     * @property {Set<HTMLElement>} selectorSiblings elements which must have
     *   siblings drop zones
     * @property {Set<HTMLElement>} selectorChildren elements which must have
     *   child drop zones between each existing child
     * @property {Set<HTMLElement>} selectorSanitized sanitized elements in
     *   which an indicative drop zone preventing the drop must be inserted
     * @property {Set<HTMLElement>|Array<HTMLElement>} selectorGrids elements
     *   which are in grid mode and for which a grid drop zone must be inserted
     */
    /**
     * @typedef Options
     * @property {Boolean} toInsertInline true if the dragged element is inline
     * @property {Boolean}fromIframe TODO
     */
    /**
     * Creates drop zones in the DOM (= locations where dragged elements may be
     * dropped).
     *
     * @param {Selectors} selectors
     * @param {Options} options
     * @returns
     */
    activateDropzones(
        { selectorSiblings, selectorChildren, selectorSanitized, selectorGrids = [] },
        { toInsertInline, fromIframe } = {}
    ) {
        // TODO improve this portion
        const targets = [];
        for (const el of selectorChildren) {
            targets.push(...el.children);
            el.prepend(this.createDropzone(el));
        }
        targets.push(...selectorSiblings);

        for (const target of targets) {
            if (!target.nextElementSibling?.classList.contains("oe_drop_zone")) {
                target.after(this.createDropzone(target.parentElement));
            }

            if (!target.previousElementSibling?.classList.contains("oe_drop_zone")) {
                target.before(this.createDropzone(target.parentElement));
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
