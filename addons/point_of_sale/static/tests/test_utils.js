odoo.define("point_of_sale.test_utils", function (require) {
"use strict";

const RamStorage = require("web.RamStorage");
const {createActionManager} = require("web.test_utils");
const PosDB = require("point_of_sale.DB");

function getPointOfSaleInstance(actionManager) {
    const {widget} = actionManager.getCurrentController();
    return widget;
}

async function createPointOfSale(params) {
    const actionManager = await createActionManager(params);
    await actionManager.doAction("pos.ui");
    const pos = getPointOfSaleInstance(actionManager);
    const db = new PosDB({ storage: new RamStorage() });
    pos.pos.db = db;
    return actionManager;
}

async function isPointOfSaleLoaded(actionManager) {
    return getPointOfSaleInstance(actionManager).ready;
}

async function loadPointOfSale(params) {
    const actionManager = await createPointOfSale(params);
    await isPointOfSaleLoaded(actionManager);
    return actionManager;
}

return {
    getPointOfSaleInstance,
    createPointOfSale,
    isPointOfSaleLoaded,
    loadPointOfSale,
};
});
