import { SEE_RECORD_LIST, SEE_RECORD_LIST_VISIBLE } from "@spreadsheet/list/list_actions";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";

const { clickableCellRegistry } = spreadsheet.registries;
const { openLink } = spreadsheet.links;

clickableCellRegistry.add("list", {
    condition: SEE_RECORD_LIST_VISIBLE,
    execute: SEE_RECORD_LIST,
    sequence: 10,
    title: _t("Open record"),
});

clickableCellRegistry.add("link_with_tooltip", {
    condition: (position, getters) => !!getters.getEvaluatedCell(position).link,
    execute: (position, env, isMiddleClick) =>
        openLink(env.model.getters.getEvaluatedCell(position).link, env, isMiddleClick),
    sequence: 2,
    titleCompute: (position, getters) => {
        const link = getters.getEvaluatedCell(position).link;
        if (link.isExternal) {
            return _t("Go to url: %s", link.url);
        } else {
            return _t("Go to %s", link.label);
        }
    },
});
