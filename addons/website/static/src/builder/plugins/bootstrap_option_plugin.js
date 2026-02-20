import { Plugin } from "@html_editor/plugin";
import { isElement } from "@html_editor/utils/dom_info";
import { registry } from "@web/core/registry";

class BootstrapOptionPlugin extends Plugin {
    static id = "bootstrapOption";
    static dependencies = ["customizeWebsite"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        is_mutation_record_savable_predicates: this.filterBootstrapMutations.bind(this),
    };

    /**
     * @param {import("@html_editor/core/history_plugin").HistoryMutationRecord} record
     */
    filterBootstrapMutations(record) {
        // Dropdown attributes to ignore.
        const dropdownClasses = ["show"];
        const dropdownToggleAttributes = ["aria-expanded"];
        const dropdownMenuAttributes = ["data-popper-placement", "style", "data-bs-popper"];
        // Offcanvas attributes to ignore.
        const offcanvasClasses = ["show", "showing"];
        const offcanvasAttributes = ["aria-modal", "aria-hidden", "role", "style"];

        if (record.type === "classList") {
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
        } else if (record.type === "attributes") {
            if (record.target.matches(".dropdown-menu")) {
                // Do not record when showing/hiding a dropdown.
                if (dropdownMenuAttributes.includes(record.attributeName)) {
                    return false;
                }
            } else if (record.target.matches(".dropdown-toggle")) {
                if (dropdownToggleAttributes.includes(record.attributeName)) {
                    return false;
                }
            } else if (record.target.matches(".offcanvas")) {
                // Do not record when showing/hiding an offcanvas.
                if (offcanvasAttributes.includes(record.attributeName)) {
                    return false;
                }
            }
        } else if (record.type === "childList") {
            const addedOrRemovedNode = (record.addedTrees[0] || record.removedTrees[0]).node;
            // Do not record the addition/removal of the offcanvas backdrop.
            if (
                isElement(addedOrRemovedNode) && addedOrRemovedNode.matches(".offcanvas-backdrop")
            ) {
                return false;
            }
        }
    }
}

registry.category("website-plugins").add(BootstrapOptionPlugin.id, BootstrapOptionPlugin);
