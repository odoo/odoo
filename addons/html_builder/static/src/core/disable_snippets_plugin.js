import { omit } from "@web/core/utils/objects";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";

export class DisableSnippetsPlugin extends Plugin {
    static id = "disableSnippets";
    static dependencies = ["setup_editor_plugin", "dropzone", "dropzone_selector"];
    static shared = ["disableUndroppableSnippets"];
    resources = {
        on_removed_handlers: this.disableUndroppableSnippets.bind(this),
        post_undo_handlers: this.disableUndroppableSnippets.bind(this),
        post_redo_handlers: this.disableUndroppableSnippets.bind(this),
        on_mobile_preview_clicked: withSequence(20, this.disableUndroppableSnippets.bind(this)),
    };

    setup() {
        this.snippetModel = this.config.snippetModel;
        this._disableSnippets = this.disableUndroppableSnippets.bind(this);

        // TODO only for website ?
        // TODO improve to add case when "+" menu appears (resize event ?)
        const editableDropdownEls = this.editable.querySelectorAll(".dropdown-menu.o_editable");
        editableDropdownEls.forEach((dropdownEl) => {
            const dropdownToggleEl = dropdownEl.parentNode.querySelector(".dropdown-toggle");
            this.addDomListener(dropdownToggleEl, "shown.bs.dropdown", this._disableSnippets);
            this.addDomListener(dropdownToggleEl, "hidden.bs.dropdown", this._disableSnippets);
        });

        const offcanvasEls = this.editable.querySelectorAll(".offcanvas");
        offcanvasEls.forEach((offcanvasEl) => {
            this.addDomListener(offcanvasEl, "shown.bs.offcanvas", this._disableSnippets);
            this.addDomListener(offcanvasEl, "hidden.bs.offcanvas", this._disableSnippets);
        });

        this.disableUndroppableSnippets();
    }

    /**
     * Makes the snippet that cannot be dropped anywhere appear disabled.
     * TODO: trigger the computation in the situation that needs it.
     */
    disableUndroppableSnippets() {
        const editableAreaEls = this.dependencies.setup_editor_plugin.getEditableAreas();
        const rootEl = this.dependencies.dropzone.getDropRootElement();
        const dropAreasBySelector = this.getDropAreas(editableAreaEls, rootEl);

        // A snippet can only be dropped next/inside elements that are editable
        // and that do not explicitely block them.
        const checkSanitize = (el, snippetEl) => {
            let forbidSanitize = false;
            // Check if the snippet is sanitized/contains such snippets.
            for (const el of [snippetEl, ...snippetEl.querySelectorAll("[data-snippet")]) {
                const snippet = this.snippetModel.getOriginalSnippet(el.dataset.snippet);
                if (snippet && snippet.forbidSanitize) {
                    forbidSanitize = snippet.forbidSanitize;
                    if (forbidSanitize === true) {
                        break;
                    }
                }
            }
            if (forbidSanitize === "form") {
                return !el.closest('[data-oe-sanitize]:not([data-oe-sanitize="allow_form"])');
            } else {
                return forbidSanitize ? !el.closest("[data-oe-sanitize]") : true;
            }
        };
        const canDrop = (snippet) => {
            const snippetEl = snippet.content;
            return !!dropAreasBySelector.find(
                ({ selector, exclude, dropAreaEls }) =>
                    snippetEl.matches(selector) &&
                    !snippetEl.matches(exclude) &&
                    dropAreaEls.some((el) => checkSanitize(el, snippetEl))
            );
        };

        // Disable the snippets that cannot be dropped.
        const snippetGroups = this.snippetModel.snippetsByCategory["snippet_groups"];
        let areGroupsDisabled = false;
        if (snippetGroups.length && !canDrop(snippetGroups[0])) {
            snippetGroups.forEach((snippetGroup) => (snippetGroup.isDisabled = true));
            areGroupsDisabled = true;
        }

        const snippets = [];
        const ignoredCategories = ["snippet_groups"];
        if (areGroupsDisabled) {
            ignoredCategories.push(...["snippet_structure", "snippet_custom"]);
        }
        for (const category in omit(this.snippetModel.snippetsByCategory, ...ignoredCategories)) {
            snippets.push(...this.snippetModel.snippetsByCategory[category]);
        }
        snippets.forEach((snippet) => {
            snippet.isDisabled = !canDrop(snippet);
        });

        // Disable the groups containing only disabled snippets.
        if (!areGroupsDisabled) {
            snippetGroups.forEach((snippetGroup) => {
                if (snippetGroup.groupName !== "custom") {
                    snippetGroup.isDisabled = !snippets.find(
                        (snippet) =>
                            snippet.groupName === snippetGroup.groupName && !snippet.isDisabled
                    );
                } else {
                    const customSnippets = this.snippetModel.snippetsByCategory["snippet_custom"];
                    snippetGroup.isDisabled = !customSnippets.find(
                        (snippet) => !snippet.isDisabled
                    );
                }
            });
        }
    }

    /**
     * Stores the selector/exclude that will make dropzones appear inside the
     * editable elements, as well as the droppable zones (to compute them only
     * once).
     *
     * @param {Array<HTMLElement>} editableAreaEls
     * @param {HTMLElement} rootEl
     * @returns {Array<Object>}
     */
    getDropAreas(editableAreaEls, rootEl) {
        const dropAreasBySelector = [];
        this.getResource("dropzone_selector").forEach((dropzoneSelector) => {
            const {
                selector,
                exclude = false,
                dropIn,
                dropNear,
                excludeNearParent,
            } = dropzoneSelector;

            const dropAreaEls = [];
            if (dropNear) {
                dropAreaEls.push(
                    ...this.dependencies.dropzone.getSelectorSiblings(editableAreaEls, rootEl, {
                        selector: dropNear,
                        excludeNearParent,
                    })
                );
            }
            if (dropIn) {
                dropAreaEls.push(
                    ...this.dependencies.dropzone.getSelectorChildren(editableAreaEls, rootEl, {
                        selector: dropIn,
                    })
                );
            }
            if (dropAreaEls.length) {
                dropAreasBySelector.push({ selector, exclude, dropAreaEls });
            }
        });
        return dropAreasBySelector;
    }
}
