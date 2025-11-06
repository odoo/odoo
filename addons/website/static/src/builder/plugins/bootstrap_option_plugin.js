import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

/**
 * Checks if the classes that changed during the mutation are all to be ignored.
 * (The mutation can be discarded if it is the case, when filtering the mutation
 * records).
 *
 * @param {Object} record the current mutation
 * @param {Array} excludedClasses the classes to ignore
 * @returns {Boolean}
 */
function checkForExcludedClasses(record, excludedClasses) {
    const classBefore = (record.oldValue && record.oldValue.split(" ")) || [];
    const classAfter = [...record.target.classList];
    const changedClasses = [
        ...classBefore.filter((c) => c && !classAfter.includes(c)),
        ...classAfter.filter((c) => c && !classBefore.includes(c)),
    ];
    return changedClasses.every((c) => excludedClasses.includes(c));
}

class BootstrapOptionPlugin extends Plugin {
    static id = "bootstrapOption";
    static dependencies = ["customizeWebsite"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        savable_mutation_record_predicates: this.filterBootstrapMutations.bind(this),
    };

    filterBootstrapMutations(record) {
        // Dropdown attributes to ignore.
        const dropdownClasses = ["show"];
        const dropdownToggleAttributes = ["aria-expanded"];
        const dropdownMenuAttributes = ["data-popper-placement", "style", "data-bs-popper"];
        // Offcanvas attributes to ignore.
        const offcanvasClasses = ["show", "showing"];
        const offcanvasAttributes = ["aria-modal", "aria-hidden", "role", "style"];

        if (
            !(record.type === "attributes" || record.type === "childList") //&&
            // !record.target.closest("header#top")
        ) {
            return true;
        }

        if (record.type === "attributes") {
            // Do not record when showing/hiding a dropdown.
            if (
                record.target.matches(".dropdown-toggle, .dropdown-menu") &&
                record.attributeName === "class"
            ) {
                if (checkForExcludedClasses(record, dropdownClasses)) {
                    return false;
                }
            } else if (
                record.target.matches(".dropdown-menu") &&
                dropdownMenuAttributes.includes(record.attributeName)
            ) {
                return false;
            } else if (
                record.target.matches(".dropdown-toggle") &&
                dropdownToggleAttributes.includes(record.attributeName)
            ) {
                return false;
            }

            // Do not record when showing/hiding an offcanvas.
            if (
                record.target.matches(".offcanvas, .offcanvas-backdrop") &&
                record.attributeName === "class"
            ) {
                if (checkForExcludedClasses(record, offcanvasClasses)) {
                    return false;
                }
            } else if (
                record.target.matches(".offcanvas") &&
                offcanvasAttributes.includes(record.attributeName)
            ) {
                return false;
            }
        } else if (record.type === "childList") {
            const addedOrRemovedNode = record.addedNodes[0] || record.removedNodes[0];
            // Do not record the addition/removal of the offcanvas backdrop.
            if (
                addedOrRemovedNode.nodeType === Node.ELEMENT_NODE &&
                addedOrRemovedNode.matches(".offcanvas-backdrop")
            ) {
                return false;
            }
        }

        return true;
    }
}

registry.category("website-plugins").add(BootstrapOptionPlugin.id, BootstrapOptionPlugin);
