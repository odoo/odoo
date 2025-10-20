    import { registry } from "@web/core/registry";
    import { stepUtils } from "@web_tour/tour_utils";

    registry.category("web_tour.tours").add('sql_constraint', {
        url: '/odoo/action-test_translation.action_constraint?debug=1',
        steps: () => [
    {
        content: "wait web client",
        trigger: '.o_breadcrumb:contains(Constraint translation)',
        run: "click",
    }, {
        content: "create new code",
        trigger: 'button.o_list_button_add',
        run: "click",
    }, {
        content: "insert invalid code value",
        trigger: '.o_field_widget[name="code"] input',
        run: "edit -1",
    }, {
        content: "save code",
        trigger: 'button.o_form_button_save',
        run: "click",
    }, {
        content: "check notification box",
        trigger: '.o_error_dialog:contains(The code must be positive !)',
    }, {
        content: "close notification box",
        trigger: '.modal-footer .btn-primary',
        run: "click",
    },
    ...stepUtils.discardForm(),
    ]});
