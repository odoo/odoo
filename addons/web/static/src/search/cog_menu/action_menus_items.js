/** @odoo-module **/

import { ActionMenus } from "@web/search/action_menus/action_menus";


/**
 * Combined Action menus (or Action/Print bar, previously called 'Sidebar')
 *
 * This is a variation of the ActionMenus, combined into a single DropDown.
 *
 * The side bar is the group of dropdown menus located on the left side of the
 * control panel. Its role is to display a list of items depending on the view
 * type and selected records and to execute a set of actions on active records.
 * It is made out of 2 dropdown: Print and Action.
 *
 * @extends Component
 */
export class ActionMenusItems extends ActionMenus {
    static template = "web.ActionMenusItems";
}
