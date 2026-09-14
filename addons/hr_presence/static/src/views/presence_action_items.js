/** @odoo-module native */
import { COG_GROUP } from "@web/search/cog_menu/cog_menu_group";
import { HrPresenceSubMenu } from "../search/hr_presence_sub_menu/hr_presence_sub_menu.js";

// hr_presence.ir.actions.server declares hr_presence_section, and
// ir.actions.actions ships it with the binding, so identifying a presence
// action costs no round-trip. Sections are drawn in this order, with one
// divider between them; binding_sequence orders the items inside each.
const SECTION_ORDER = ["state", "follow_up"];

/**
 * Collapse the presence actions bound to hr.employee into one gear submenu.
 *
 * @param {Array<Record<string, any>>} actionItems
 * @param {Function} onItemSelected
 * @returns {Array<Record<string, any>>}
 */
export function groupPresenceActionItems(actionItems, onItemSelected) {
    const presenceItems = [];
    const otherItems = [];
    for (const item of actionItems) {
        const section = SECTION_ORDER.indexOf(item.action?.hr_presence_section);
        if (section === -1) {
            otherItems.push(item);
        } else {
            presenceItems.push({ ...item, groupNumber: section });
        }
    }
    if (!presenceItems.length) {
        return otherItems;
    }
    return [
        ...otherItems,
        {
            key: "hr_presence_control",
            groupNumber: COG_GROUP.ACTIONS,
            Component: HrPresenceSubMenu,
            props: { items: presenceItems, onItemSelected },
        },
    ].toSorted((item1, item2) => item1.groupNumber - item2.groupNumber);
}

/**
 * The form cog menu and the list action menu differ only in their base class.
 *
 * @template {new (...args: any[]) => any} T
 * @param {T} Base
 * @returns {T}
 */
export function withPresenceSubMenu(Base) {
    return class extends Base {
        /** @override */
        async getActionItems(props) {
            return groupPresenceActionItems(await super.getActionItems(props), (item) =>
                this.onItemSelected(item),
            );
        }
    };
}
