/** @odoo-module */

import {
    registries,
} from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";

registries.topbarMenuRegistry.addChild("version_history", ["file"], {
    name: _t("See version history"),
    sequence: 55,
    isVisible: (env) => env.showHistory,
    execute: (env) => env.showHistory(),
    icon: "o-spreadsheet-Icon.VERSION_HISTORY",
});
