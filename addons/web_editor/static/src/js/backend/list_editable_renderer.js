/** @odoo-module **/

import ListRenderer from "web.ListRenderer";

ListRenderer.include({
    _onWindowClicked: function (event) {
        // ignore clicks in the web_editor toolbar
        if ($(event.target).closest(".oe-toolbar").length) {
            return;
        }
        return this._super.apply(this, arguments);
    },
});
