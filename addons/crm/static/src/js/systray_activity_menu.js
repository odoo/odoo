odoo.define('crm.systray.ActivityMenu', function (require) {
    "use strict";

    const ActivityMenu = require('mail.systray.ActivityMenu');

    ActivityMenu.patch("crm.systray.ActivityMenu", (T) => {
        class CrmActivityMenu extends T {

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
                return super._getViewsList(...arguments);
            }

            //-----------------------------------------
            // Handlers
            //-----------------------------------------

            /**
             * @private
             * @override
             */
            _onActivityFilterClick(event) {
                // fetch the data from the button otherwise fetch the ones from the parent (.o_mail_preview).
                const data = Object.assign({}, event.currentTarget.dataset, event.target.dataset);
                const context = {};
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
                    this.env.bus.trigger("do-action", {
                        action: "crm.crm_lead_action_my_activities",
                        options: {
                            additional_context: context,
                        },
                    });
                } else {
                    super._onActivityFilterClick(...arguments);
                }
            }
        }

        return CrmActivityMenu;
    });
});
