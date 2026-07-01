import { DROPDOWN_GROUP } from "@web/core/dropdown/dropdown_group";
import { useEnv, useLayoutEffect } from "@web/owl2/utils";

/**
 * @typedef {{
 *  isInGroup: boolean;
 *  readonly isOpen: boolean;
 * }} DropdownGroupState
 *
 * @typedef {(typeof import("../dropdown").dropdownProps)["state"]} DropdownState
 */

/**
 * Will add (and remove) a dropdown from a parent
 * DropdownGroup component, allowing it to know
 * if it's in a group and if the group is open.
 *
 * @param {DropdownState} state
 */
export function useDropdownGroup(state) {
    const env = useEnv();

    /** @type {DropdownGroupState} */
    const group = {
        isInGroup: DROPDOWN_GROUP in env,
        get isOpen() {
            return this.isInGroup && [...env[DROPDOWN_GROUP]].some((dropdown) => dropdown.isOpen);
        },
    };

    if (group.isInGroup) {
        useLayoutEffect(() => {
            env[DROPDOWN_GROUP].add(state);
            return () => env[DROPDOWN_GROUP].delete(state);
        });
    }

    return group;
}
