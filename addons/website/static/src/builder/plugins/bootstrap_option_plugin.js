import { Plugin } from "@html_editor/plugin";
import { isElement } from "@html_editor/utils/dom_info";
import { registry } from "@web/core/registry";

class BootstrapOptionPlugin extends Plugin {
    static id = "bootstrapOption";
    static dependencies = ["customizeWebsite"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        savable_mutation_record_predicates: this.filterBootstrapMutations.bind(this),
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
            // Do not record when showing/hiding a dropdown.
            if (record.target.matches(".dropdown-toggle, .dropdown-menu")) {
                return !dropdownClasses.includes(record.className);
            }
            // Do not record when showing/hiding an offcanvas.
            if (record.target.matches(".offcanvas, .offcanvas-backdrop")) {
                return !offcanvasClasses.includes(record.className);
            }
            return true;
        }
        if (record.type === "attributes") {
            // Do not record when showing/hiding a dropdown.
            if (record.target.matches(".dropdown-menu")) {
                return !dropdownMenuAttributes.includes(record.attributeName);
            }
            if (record.target.matches(".dropdown-toggle")) {
                return !dropdownToggleAttributes.includes(record.attributeName);
            }
            // Do not record when showing/hiding an offcanvas.
            if (record.target.matches(".offcanvas")) {
                return !offcanvasAttributes.includes(record.attributeName);
            }
            return true;
        }
        if (record.type === "childList") {
            const addedOrRemovedNode = (record.addedTrees[0] || record.removedTrees[0]).node;
            // Do not record the addition/removal of the offcanvas backdrop.
            return !(
                isElement(addedOrRemovedNode) && addedOrRemovedNode.matches(".offcanvas-backdrop")
            );
        }
        return true;
    }
}

registry.category("website-plugins").add(BootstrapOptionPlugin.id, BootstrapOptionPlugin);
