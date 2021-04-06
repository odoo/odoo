/** @odoo-module **/

import { Registry } from "../core/registry";
import {
  documentationItem,
  logOutItem,
  odooAccountItem,
  preferencesItem,
  separator,
  shortCutsItem,
  supportItem,
} from "./user_menu/user_menu_items";

// -----------------------------------------------------------------------------
// Default UserMenu items
// -----------------------------------------------------------------------------
export const userMenuRegistry = (odoo.userMenuRegistry = new Registry());

userMenuRegistry
  .add("documentation", documentationItem, {sequence: 10})
  .add("support", supportItem, {sequence: 20})
  .add("shortcuts", shortCutsItem, {sequence: 30})
  .add("separator", separator, {sequence: 40})
  .add("profile", preferencesItem, {sequence: 50})
  .add("odoo_account", odooAccountItem, {sequence: 60})
  .add("log_out", logOutItem, {sequence: 70});
