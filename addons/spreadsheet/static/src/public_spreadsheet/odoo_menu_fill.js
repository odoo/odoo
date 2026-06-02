/** @odoo-module **/

import { registries } from "@odoo/o-spreadsheet";
import {
    isIrMenuXmlUrl,
    isMarkdownIrMenuIdUrl,
    isMarkdownViewUrl,
} from "@spreadsheet/ir_ui_menu/odoo_menu_link_cell";
import { _t } from "@web/core/l10n/translation";

const { clickableCellRegistry, urlRegistry } = registries;

const currentlinkCell = clickableCellRegistry.get("link");
currentlinkCell.condition = (position, getters) => {
    const evaluatedCell = getters.getEvaluatedCell(position);
    return evaluatedCell.link && evaluatedCell.link.isExternal;
};

const NEUTRALIZED_LINK = {
    sequence: 65,
    createLink(url, label) {
        return {
            url,
            label: label,
            isExternal: false,
            isUrlEditable: false,
        };
    },
    urlRepresentation(url) {
        return _t("Internal link");
    },
    open(url) {
        return;
    },
};

urlRegistry.replace("OdooMenuIdLink", {
    ...NEUTRALIZED_LINK,
    match: isMarkdownIrMenuIdUrl,
});

urlRegistry.replace("OdooMenuXmlLink", {
    ...NEUTRALIZED_LINK,
    match: isIrMenuXmlUrl,
});

urlRegistry.replace("OdooViewLink", {
    ...NEUTRALIZED_LINK,
    match: isMarkdownViewUrl,
});
