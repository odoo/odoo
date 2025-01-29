import { SEE_RECORD_LIST, SEE_RECORD_LIST_VISIBLE } from "@spreadsheet/list/list_actions";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";

const { clickableCellRegistry } = spreadsheet.registries;

clickableCellRegistry.add("list", {
    condition: SEE_RECORD_LIST_VISIBLE,
    execute: SEE_RECORD_LIST,
    sequence: 10,
    title: _t("Open record"),
});
