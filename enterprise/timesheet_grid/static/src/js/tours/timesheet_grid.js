/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add('timesheet_tour', {
    url: "/odoo",
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="hr_timesheet.timesheet_menu_root"]',
    content: markup(_t('Track the <b>time spent</b> on your projects. <i>It starts here.</i>')),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: '.btn_start_timer',
    content: markup(_t('Launch the <b>timer</b> to start a new activity.')),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: 'div[name=name] input',
    content: markup(_t('Describe your activity <i>(e.g. sent an e-mail, meeting with the customer...)</i>.')),
    tooltipPosition: 'bottom',
    run: "edit My Activity",
}, {
    trigger: 'div[name=project_id] .o_field_many2one_selection',
    content: markup(_t('Select the <b>project</b> on which you are working.')),
    tooltipPosition: 'right',
    run: "click",
}, {
    trigger: '.btn_stop_timer',
    content: markup(_t('Stop the <b>timer</b> when you are done. <i>Tip: hit <b>[Enter]</b> in the description to automatically log your activity.</i>')),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: '.btn_timer_line',
    content: markup(_t('Launch the <b>timer</b> for this project by pressing the <b>[a] key</b>. Easily switch from one project to another by using those keys. <i>Tip: you can also directly add 15 minutes to this project by hitting the <b>shift + [A] keys</b>.</i>')),
    tooltipPosition: 'right',
    run: "click",
}, {
    trigger: '.o_grid_view .o_grid_row:not(.o_grid_section).o_grid_cell_today, .o_grid_component_timesheet_uom',
    content: _t("Click on the cell to set the number of hours you spent on this project."),
    tooltipPosition: 'bottom',
    run: "click",
},
{
    trigger: '.o_grid_view .o_grid_cell',
    content: _t("Click on the cell to set the number of hours you spent on this project."),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: '.o_grid_view .o_grid_cell',
    content: markup(_t('Set the number of hours you spent on this project (e.g. 1:30 or 1.5). <i>Tip: use the tab keys to easily navigate from one cell to another.</i>')),
    tooltipPosition: 'bottom',
    run: "edit 1:30",
}]});
