import { scrollToWindow } from "@html_builder/utils/utils";
import { Plugin } from "@html_editor/plugin";
import { isBlock } from "@html_editor/utils/blocks";
import { _t } from "@web/core/l10n/translation";
import { closest, touching } from "@web/core/utils/ui";

export class DropZonePlugin extends Plugin {
    static id = "dropzone";
    static dependencies = ["history", "setup_editor_plugin"];
    static shared = [
        "displayDropZone",
        "dragElement",
        "clearDropZone",
        "getAddElement",
        "getDropRootElement",
        "getSelectorSiblings",
        "getSelectorChildren",
        "getSelectors",
    ];

    resources = {
        savable_mutation_record_predicates: this.isMutationRecordSavable.bind(this),
    };

    setup() {
        this.dropZoneElements = [];
        this.dropzoneSelectors = this.getResource("dropzone_selector");
    }

    /**
     * @param {MutationRecord} record
     * @return {boolean}
     */
    isMutationRecordSavable(record) {
        if (record.type === "childList") {
            const node = record.addedNodes[0] || record.removedNodes[0];
            if (isBlock(node) && node.classList.contains("oe_drop_zone")) {
                return false;
            }
        }
        return true;
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
        if (openModalEl) {
            return openModalEl;
        }
        const openDropdownEl = this.editable.querySelector(
            ".o_editable.dropdown-menu.show, .dropdown-menu.show .o_editable.dropdown-menu"
        );
        if (openDropdownEl) {
            return openDropdownEl.parentNode;
        }
        const openOffcanvasEl = this.editable.querySelector(".offcanvas.show");
        if (openOffcanvasEl) {
            return openOffcanvasEl;
        }
    }

    /**
     * Gets the selectors that determine where the given snippet can be placed.
     *
     * @param {Object} snippet
     * @returns {Object} [selectorChildren, selectorSiblings]
     */
    getSelectors(snippet) {
        const snippetEl = snippet.content;
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
            selectorChildren = selectorChildren.filter((el) => !el.closest(excludeAncestor));
            selectorSiblings = selectorSiblings.filter((el) => !el.closest(excludeAncestor));
        }

        // TODO add excludeAncestors in dropzone_selectors
        // TODO checkSanitize here ?

        return {
            selectorChildren: new Set(selectorChildren),
            selectorSiblings: new Set(selectorSiblings),
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

    createDropZone() {
        const dropZoneEl = this.document.createElement("div");
        dropZoneEl.className = "oe_drop_zone oe_insert";
        dropZoneEl.dataset.editorMessage = _t("DRAG BUILDING BLOCKS HERE");
        this.dropZoneElements.push(dropZoneEl);
        return dropZoneEl;
    }

    displayDropZone(selectorSiblings, selectorChildren) {
        this.clearDropZone();

        const targets = [];
        for (const el of selectorChildren) {
            targets.push(...el.children);
            el.prepend(this.createDropZone());
        }
        targets.push(...selectorSiblings);

        for (const target of targets) {
            if (!target.nextElementSibling?.classList.contains("oe_drop_zone")) {
                target.after(this.createDropZone());
            }

            if (!target.previousElementSibling?.classList.contains("oe_drop_zone")) {
                target.before(this.createDropZone());
            }
        }
    }

    clearDropZone() {
        if (this.dropZoneElements.length) {
            for (const el of this.editable.querySelectorAll(".oe_drop_zone")) {
                el.remove();
            }
        }

        this.dropZoneElements = [];
    }

    dragElement(element, x, y) {
        const { height, width } = element.getClientRects()[0];
        const position = { x, y, height, width };
        const dropzoneEl = closest(touching(this.dropZoneElements, position), position);
        if (this.currentDropzoneEl !== dropzoneEl) {
            this.currentDropzoneEl?.classList.remove("o_dropzone_highlighted");
            this.currentDropzoneEl = dropzoneEl;
            if (dropzoneEl) {
                dropzoneEl.classList.add("o_dropzone_highlighted");
            }
        }
    }

    /**
     * @param {Object} [position] - set if drag & drop, not set if click
     * @param {Number} position.x
     * @param {Number} position.y
     * @returns {Function}
     */
    getAddElement(position) {
        // Drag & drop over sidebar: cancel the action.
        if (position && !touching([this.document.body], position).length) {
            // TODO: do we want that key with an empty function? Or should we
            // check everytime we call getAddElement if the result is undefined
            // before continuing?
            this.clearDropZone();
            return;
        }
        const dropZone = position
            ? closest(touching(this.dropZoneElements, position), position) ||
              closest(this.dropZoneElements, position)
            : closest(this.dropZoneElements, {
                  x: window.innerWidth / 2,
                  y: window.innerHeight / 2,
              });
        if (!dropZone) {
            this.clearDropZone();
            return;
        }

        let target = dropZone.previousSibling;
        let insertMethod = "after";
        if (!target) {
            target = dropZone.nextSibling;
            insertMethod = "before";
        }
        if (!target) {
            target = dropZone.parentElement;
            insertMethod = "appendChild";
        }
        this.clearDropZone();
        return async (elementToAdd) => {
            // TODO: refactor if a new mutex system is implemented
            target[insertMethod](elementToAdd);
            const proms = [];
            for (const handler of this.getResource("on_add_element_handlers")) {
                proms.push(handler({ elementToAdd: elementToAdd }));
            }
            this.services.ui.block();
            await Promise.all(proms);
            this.services.ui.unblock();
            scrollToWindow(elementToAdd, { behavior: "smooth", offset: 50 });
            this.dependencies.history.addStep();
        };
    }
}
