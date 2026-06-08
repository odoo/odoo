import { NATIVE_MUTATION_TYPES } from "@html_editor/core/dom_observer_plugin";
import { Plugin } from "@html_editor/plugin";
import { isElement } from "@html_editor/utils/dom_info";
import { registry } from "@web/core/registry";

export class BootstrapOptionPlugin extends Plugin {
    static id = "bootstrapOption";
    static dependencies = ["customizeWebsite"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        is_mutation_savable_predicates: this.filterBootstrapMutations.bind(this),
        is_classlist_mutation_savable_predicates: this.filterBootstrapClassListMutations.bind(this),
    };

    /**
     * @param {import("@html_editor/core/dom_observer_plugin").EditorMutation<"classList">} record
     * @returns {boolean | undefined}
     */
    filterBootstrapClassListMutations(record) {
        // Dropdown classes to ignore.
        const dropdownClasses = ["show"];
        // Offcanvas classes to ignore.
        const offcanvasClasses = ["show", "showing"];
        if (record.target.matches(".dropdown-toggle, .dropdown-menu")) {
            // Do not record when showing/hiding a dropdown.
            if (dropdownClasses.includes(record.className)) {
                return false;
            }
        } else if (record.target.matches(".offcanvas, .offcanvas-backdrop")) {
            // Do not record when showing/hiding an offcanvas.
            if (offcanvasClasses.includes(record.className)) {
                return false;
            }
        }
    }

    /**
     * @param {import("@html_editor/core/dom_observer_plugin").NativeMutation} mutation
     * @returns {boolean | undefined}
     */
    filterBootstrapMutations(mutation) {
        // Dropdown attributes to ignore.
        const dropdownToggleAttributes = ["aria-expanded"];
        const dropdownMenuAttributes = ["data-popper-placement", "style", "data-bs-popper"];
        // Offcanvas attributes to ignore.
        const offcanvasAttributes = ["aria-modal", "aria-hidden", "role", "style"];

        if (mutation.type === NATIVE_MUTATION_TYPES.ATTRIBUTES) {
            if (mutation.target.matches(".dropdown-menu")) {
                // Do not record when showing/hiding a dropdown.
                if (dropdownMenuAttributes.includes(mutation.attributeName)) {
                    return false;
                }
            } else if (mutation.target.matches(".dropdown-toggle")) {
                if (dropdownToggleAttributes.includes(mutation.attributeName)) {
                    return false;
                }
            } else if (mutation.target.matches(".offcanvas")) {
                // Do not record when showing/hiding an offcanvas.
                if (offcanvasAttributes.includes(mutation.attributeName)) {
                    return false;
                }
            }
        } else if (mutation.type === NATIVE_MUTATION_TYPES.CHILD_LIST) {
            const addedOrRemovedNode = mutation.addedNodes[0] || mutation.removedNodes[0];
            // Do not record the addition/removal of the offcanvas backdrop.
            if (
                addedOrRemovedNode && isElement(addedOrRemovedNode) && addedOrRemovedNode.matches(".offcanvas-backdrop")
            ) {
                return false;
            }
        }
    }
}

registry.category("website-plugins").add(BootstrapOptionPlugin.id, BootstrapOptionPlugin);
