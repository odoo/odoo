import { onWillDestroy, Plugin, providePlugins, t, useConfig, usePlugin } from "@odoo/owl";
import { services } from "@web/core/services";

const GROUPS = new Map();

function getGroup(id) {
    if (!GROUPS.has(id)) {
        GROUPS.set(id, {
            group: new Set(),
            count: 0,
        });
    }
    GROUPS.get(id).count++;
    return GROUPS.get(id).group;
}

function removeGroup(id) {
    const groupData = GROUPS.get(id);
    groupData.count--;
    if (groupData.count <= 0) {
        GROUPS.delete(id);
    }
}

class DropdownGroupPlugin extends Plugin {
    /** @private */
    groupId = useConfig("groupId", t.string().optional());

    /** @private */
    items = new Set();
    isInGroup = true;

    get isOpen() {
        return this.isInGroup && [...this.items].some((dropdown) => dropdown.isOpen);
    }

    setup() {
        if (this.groupId) {
            this.group = getGroup(this.groupId);
            onWillDestroy(() => {
                removeGroup(this.groupId);
            });
        }
    }

    add(state) {
        this.items.add(state);
    }

    remove(state) {
        this.items.delete(state);
    }
}

class GlobalDropdownGroupPlugin extends Plugin {
    static id = "DropdownGroupPlugin";

    isInGroup = false;
    isOpen = false;

    add() {}
    remove() {}
}
services.add(GlobalDropdownGroupPlugin);

/**
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
    const group = usePlugin(DropdownGroupPlugin);
    group.add(state);
    onWillDestroy(() => group.remove(state));
    return group;
}

export function provideDropdownGroup(groupId) {
    providePlugins([DropdownGroupPlugin], { groupId });
}
