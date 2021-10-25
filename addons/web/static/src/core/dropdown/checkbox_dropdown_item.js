/** @odoo-module **/

import { CheckBox } from "@web/core/checkbox/checkbox";
import { DropdownItem } from "./dropdown_item";

export class CheckBoxDropdownItem extends DropdownItem {}
CheckBoxDropdownItem.template = "web.CheckBoxDropdownItem";
CheckBoxDropdownItem.props = { ...DropdownItem.props, ...CheckBox.props };
