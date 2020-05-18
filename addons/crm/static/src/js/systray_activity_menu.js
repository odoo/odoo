odoo.define('crm.systray.ActivityMenu', function (require) {
"use strict";

var ActivityMenu = require('mail.systray.ActivityMenu');

ActivityMenu.include({

    //--------------------------------------------------
    // Private
    //--------------------------------------------------

    /**
     * @override
     */
    _getViewsList(model) {
        if (model === "crm.lead") {
                return [[false, 'list'], [false, 'kanban'],
                        [false, 'form'], [false, 'calendar'],
                        [false, 'pivot'], [false, 'graph'],
                        [false, 'activity']
                    ];
        }
        return this._super(...arguments);
    },
});
});
