/** @odoo-module alias=web.dom_ready **/

export default new Promise(function (resolve, reject) {
    $(resolve);
});
