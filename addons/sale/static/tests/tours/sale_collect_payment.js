import { registry } from "@web/core/registry";

const openActionMenu = {
    content: "Open the action menu",
    trigger: ".o_form_view .o_cp_action_menus .dropdown-toggle",
    run: "click",
};
const openCollectPayment = {
    content: "Open the Collect Payment menu",
    trigger: "button.o-dropdown:contains(Collect Payment)",
    run: "click",
};
const closeDialog = {
    content: "Close the dialog",
    trigger: ".modal button[special=cancel]",
    run: "click",
};
const dialogIsClosed = {
    content: "Check the dialog is closed",
    trigger: "body:not(:has(.modal))",
};

registry.category("web_tour.tours").add("sale_collect_payment_on_confirmed_order", {
    steps: () => [
        openActionMenu,
        openCollectPayment,
        {
            content: "Open the payment wizard",
            trigger: ".o_menu_item:contains(Mark as Paid)",
            run: "click",
        },
        {
            content: "Pay a part of the order",
            trigger: ".modal div[name=amount] input",
            run: "edit 40 && press Tab",
        },
        {
            content: "Create the payment",
            trigger: ".modal button[name=action_create_payments]:visible",
            run: "click",
        },
        dialogIsClosed,
        {
            content: "Check the order now has an invoice",
            trigger: "button[name=action_view_invoice]:contains(1)",
        },
        openActionMenu,
        openCollectPayment,
        {
            content: "Open the payment link wizard",
            trigger: ".o_menu_item:contains(Payment Link)",
            run: "click",
        },
        {
            content: "Check the link suggests the remaining amount",
            trigger: ".modal div[name=amount] input:value(60.00)",
        },
        closeDialog,
        dialogIsClosed,
    ],
});
