/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add('timesheet_tour', {
    sequence: 100,
    rainbowManMessage: () => _t("Congratulations, you are now a master of Timesheets."),
    url: "/web",
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="hr_timesheet.timesheet_menu_root"]',
    content: markup(_t('Track the <b>time spent</b> on your projects. <i>It starts here.</i>')),
    position: 'bottom',
}, {
    trigger: '.btn_start_timer',
    content: markup(_t('Launch the <b>timer</b> to start a new activity.')),
    position: 'bottom',
}, {
    trigger: 'div[name=name] input',
    content: markup(_t('Describe your activity <i>(e.g. sent an e-mail, meeting with the customer...)</i>.')),
    position: 'bottom',
}, {
    trigger: 'div[name=project_id] .o_field_many2one_selection',
    content: markup(_t('Select the <b>project</b> on which you are working.')),
    position: 'right',
}, {
    trigger: '.btn_stop_timer',
    content: markup(_t('Stop the <b>timer</b> when you are done. <i>Tip: hit <b>[Enter]</b> in the description to automatically log your activity.</i>')),
    position: 'bottom',
}, {
    trigger: '.btn_timer_line',
    content: markup(_t('Launch the <b>timer</b> for this project by pressing the <b>[a] key</b>. Easily switch from one project to another by using those keys. <i>Tip: you can also directly add 15 minutes to this project by hitting the <b>shift + [A] keys</b>.</i>')),
    position: 'right',
}, {
    trigger: '.o_grid_view .o_grid_row:not(.o_grid_section).o_grid_cell_today',
    content: _t("Click on the cell to set the number of hours you spent on this project."),
    position: 'bottom',
    consumeEvent: 'mouseover',
}, {
    trigger: '.o_grid_view .o_grid_cell',
    extra_trigger: '.o_grid_view .o_grid_row:not(.o_grid_section).o_grid_cell_today',
    content: _t("Click on the cell to set the number of hours you spent on this project."),
    position: 'bottom',
}, {
    trigger: '.o_grid_view .o_grid_cell',
    content: markup(_t('Set the number of hours you spent on this project (e.g. 1:30 or 1.5). <i>Tip: use the tab keys to easily navigate from one cell to another.</i>')),
    position: 'bottom',
    consumeEvent: 'change',
}]});
