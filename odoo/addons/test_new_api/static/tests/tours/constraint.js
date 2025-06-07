/** @odoo-module **/

    import { registry } from "@web/core/registry";
    import { stepUtils } from "@web_tour/tour_service/tour_utils";

    registry.category("web_tour.tours").add('sql_constaint', {
        url: '/odoo/action-test_new_api.action_categories?debug=1',
        steps: () => [
    {
        content: "wait web client",
        trigger: '.o_breadcrumb:contains(Categories)',
        run: "click",
    }, { // create test category
        content: "create new category",
        trigger: 'button.o_list_button_add',
        run: "click",
    }, {
        content: "insert content",
        trigger: '.o_required_modifier input',
        run: "edit Test Category",
    }, { // try to insert a value that will raise the SQL constraint
        content: "insert invalid value",
        trigger: '.o_field_widget[name="color"] input',
        run: "edit -1",
    }, { // save
        content: "save category",
        trigger: 'button.o_form_button_save',
        run: "click",
    }, { // check popup content
        content: "check notification box",
        trigger: '.o_error_dialog:contains(The color code must be positive!)',
    }, {
        content: "close notification box",
        trigger: '.modal-footer .btn-primary',
        run: "click",
    },
    ...stepUtils.discardForm(),
    ]});
