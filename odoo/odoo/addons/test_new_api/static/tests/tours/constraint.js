/** @odoo-module **/

    import { registry } from "@web/core/registry";
    import { stepUtils } from "@web_tour/tour_service/tour_utils";

    registry.category("web_tour.tours").add('sql_constaint', {
        url: '/web?debug=1#action=test_new_api.action_categories',
        test: true,
        steps: () => [
    {
        content: "wait web client",
        trigger: '.o_breadcrumb:contains(Categories)',
    }, { // create test category
        content: "create new category",
        trigger: 'button.o_list_button_add',
    }, {
        content: "insert content",
        trigger: '.o_required_modifier input',
        run: 'text Test Category',
    }, { // try to insert a value that will raise the SQL constraint
        content: "insert invalid value",
        trigger: '.o_field_widget[name="color"] input',
        run: 'text -1',
    }, { // save
        content: "save category",
        trigger: 'button.o_form_button_save',
    }, { // check popup content
        content: "check notification box",
        trigger: '.o_error_dialog:contains(The color code must be positive!)',
        run() {}
    }, {
        content: "close notification box",
        trigger: '.modal-footer .btn-primary',
    },
    ...stepUtils.discardForm(),
    ]});
