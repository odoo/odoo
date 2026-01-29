/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const commandCategoryRegistry = registry.category("command_categories");

commandCategoryRegistry
    .add("discuss_mentioned", { namespace: "@", name: _t("Mentions") }, { sequence: 10 })
    .add("discuss_recent", { namespace: "#", name: _t("Recent") }, { sequence: 10 });
