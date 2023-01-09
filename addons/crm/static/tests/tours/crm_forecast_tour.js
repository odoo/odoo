/** @odoo-module */
import tour from 'web_tour.tour';
const today = moment();

tour.register('crm_forecast', {
    test: true,
    url: "/web",
}, [
    tour.stepUtils.showAppsMenuItem(),
    {
        trigger: ".o_app[data-menu-xmlid='crm.crm_menu_root']",
        content: "open crm app",
    }, {
        trigger: '.dropdown-toggle[data-menu-xmlid="crm.crm_menu_report"]',
        content: 'Open Reporting menu',
        run: 'click',
    }, {
        trigger: '.dropdown-item[data-menu-xmlid="crm.crm_menu_forecast"]',
        content: 'Open Forecast menu',
        run: 'click',
    }, {
        trigger: '.o_column_quick_create:contains(Add next month)',
        content: 'Wait page loading'
    }, {
        trigger: ".o-kanban-button-new",
        content: "click create",
        run: 'click',
    }, {
        trigger: ".o_field_widget[name=name] input",
        content: "complete name",
        run: "text Test Opportunity 1",
    }, {
        trigger: ".o_field_widget[name=expected_revenue] input",
        content: "complete expected revenue",
        run: "text 999999",
    }, {
        trigger: "button.o_kanban_edit",
        content: "edit lead",
    }, {
        trigger: "div[name=date_deadline] input",
        content: "complete expected closing",
        run: `text ${today.format("MM/DD/YYYY")}`,
    }, {
        trigger: "div[name=date_deadline] input",
        content: "click to make the datepicker disappear",
        run: "click"
    }, {
        trigger: "body:not(:has(div.bootstrap-datetimepicker-widget))",
        content: "wait for date_picker to disappear",
        run: function () {},
    }, {
        trigger: '.o_back_button',
        content: 'navigate back to the kanban view',
        position: "bottom",
        run: "click"
    }, {
        trigger: ".o_kanban_record .o_kanban_record_title:contains('Test Opportunity 1')",
        content: "move to the next month",
        run: function (actions) {
            const undefined_groups = $('.o_column_title:contains("None")').length;
            actions.drag_and_drop_native(`.o_opportunity_kanban .o_kanban_group:eq(${1 + undefined_groups})`, this.$anchor);
        },
    }, {
        trigger: ".o_kanban_record .o_kanban_record_title:contains('Test Opportunity 1')",
        content: "edit lead",
        run: "click"
    }, {
        trigger: ".o_field_widget[name=date_deadline] input",
        content: "complete expected closing",
        run: function (actions) {
            actions.text(`text ${moment(today).add(5, 'months').startOf('month').subtract(1, 'days').format("MM/DD/YYYY")}`, this.$anchor);
            this.$anchor[0].dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "Escape" }));
        },
    }, {
        trigger: "body:not(:has(div.bootstrap-datetimepicker-widget))",
        content: "wait for date_picker to disappear",
        run: function () {},
    }, {
        trigger: ".o_field_widget[name=probability] input",
        content: "max out probability",
        run: "text 100"
    }, {
        trigger: '.o_back_button',
        content: 'navigate back to the kanban view',
        position: "bottom",
        run: "click"
    }, {
        trigger: '.o_kanban_add_column',
        content: "add next month",
        run: "click"
    }, {
        trigger: ".o_kanban_record:contains('Test Opportunity 1'):contains('Won')",
        content: "assert that the opportunity has the Won banner",
        run: function () {},
    }
]);
