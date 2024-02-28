/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import DashboardLinkPlugin from "./dashboard_link_plugin";

const { uiPluginRegistry } = spreadsheet.registries;

uiPluginRegistry.add("odooDashboardClickLink", DashboardLinkPlugin);
