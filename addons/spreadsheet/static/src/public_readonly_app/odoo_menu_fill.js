/** @odoo-module **/

import { registries } from "@odoo/o-spreadsheet";

const { clickableCellRegistry } = registries;

const currentlinkCell = clickableCellRegistry.get("link");
currentlinkCell.condition = (position, getters) => {
    const evaluatedCell =getters.getEvaluatedCell(position);
    return evaluatedCell.link && evaluatedCell.link.isExternal;
};
