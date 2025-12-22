import { useComponent, useEffect, useEnv } from "@odoo/owl";
import { DROPDOWN_GROUP } from "@web/core/dropdown/dropdown_group";

/**
 * @typedef DropdownGroupState
 * @property {boolean} isInGroup
 * @property {boolean} isOpen
 */

/**
 * Will add (and remove) a dropdown from a parent
 * DropdownGroup component, allowing it to know
 * if it's in a group and if the group is open.
 *
 * @returns {DropdownGroupState}
 */
export function useDropdownGroup() {
    const env = useEnv();

    const group = {
        isInGroup: DROPDOWN_GROUP in env,
        get isOpen() {
            return this.isInGroup && [...env[DROPDOWN_GROUP]].some((dropdown) => dropdown.isOpen);
        },
    };

    if (group.isInGroup) {
        const dropdown = useComponent();
        useEffect(() => {
            env[DROPDOWN_GROUP].add(dropdown.state);
            return () => env[DROPDOWN_GROUP].delete(dropdown.state);
        });
    }

    return group;
}
