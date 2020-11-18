odoo.define('web_tour.kanban_record_quick_create', function (require) {
"use strict";

var RecordQuickCreate = require('web.kanban_record_quick_create');

RecordQuickCreate.include({
    /**
     * Small override to take into account that a click can occur within a tour tooltip.
     * When that happens, we don't want to close the kanban quick create.
     *
     * Indeed, some tour steps can take place *within* (visually) a quick create card and
     * if the card closes when the user clicks on a tip, it creates a bad user experience.
     *
     * @override
     * @private
     * @param {MouseEvent} ev
     */
    _onWindowClicked: function (ev) {
        if ($(ev.target).closest('.o_tooltip.o_tooltip_visible').length !== 0) {
            return;
        }

        this._super(...arguments);
    }
});

return RecordQuickCreate;

});
