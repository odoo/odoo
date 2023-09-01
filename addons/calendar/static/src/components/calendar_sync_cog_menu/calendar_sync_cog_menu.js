/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const cogMenuRegistry = registry.category("cogMenu");

export class CalendarSyncCogMenu extends Component {
    static props = {};
    static template = "calendar.CalendarSyncCogMenu";
    static components = { DropdownItem };

    setup() {
        this.actionService = useService("action");
    }

    startCalendarSync() {
        this.actionService.doAction({
            name: _t('Connect your Calendar'),
            type: 'ir.actions.act_window',
            res_model: 'calendar.provider.config',
            views: [[false, "form"]],
            view_mode: "form",
            target: 'new',
            context: {
                'dialog_size': 'medium',
            }
        });
    }
};

cogMenuRegistry.add(
    'calendar-sync-cog-menu',
    {
        Component: CalendarSyncCogMenu,
        groupNumber: 10,
        isDisplayed: ({ config }) => {
            return config.viewSubType === "attendee_calendar";
        },
    },
);
