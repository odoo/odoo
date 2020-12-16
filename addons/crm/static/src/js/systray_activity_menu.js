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

    //-----------------------------------------
    // Handlers
    //-----------------------------------------

    /**
     * @private
     * @override
     */
    _onActivityFilterClick: function (event) {
        // fetch the data from the button otherwise fetch the ones from the parent (.o_mail_preview).
        var data = _.extend({}, $(event.currentTarget).data(), $(event.target).data());
        var context = {};
        if (data.res_model === "crm.lead") {
            if (data.filter === 'my') {
                context['search_default_activities_overdue'] = 1;
                context['search_default_activities_today'] = 1;
            } else {
                context['search_default_activities_' + data.filter] = 1;
            }
            // Necessary because activity_ids of mail.activity.mixin has auto_join
            // So, duplicates are faking the count and "Load more" doesn't show up
            context['force_search_count'] = 1;
            this.do_action('crm.crm_lead_action_my_activities', {
                additional_context: context,
                clear_breadcrumbs: true,
            });
        } else {
            this._super.apply(this, arguments);
        }
    },
});
});
