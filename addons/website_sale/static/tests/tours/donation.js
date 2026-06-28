import { registry } from "@web/core/registry";
import {
    clickOnSave,
    insertSnippet,
    changeOptionInPopover,
    unfoldOptionsGroup,
    waitForEditMode,
} from "@website/js/tours/tour_utils";

registry.category("web_tour.tours").add("donation_snippet_edition", {
    steps: () => [
        waitForEditMode,
        ...insertSnippet({
            id: "s_donation",
            name: "Donation",
            groupName: "Contact & Forms",
        }),
        ...clickOnSave(),
    ],
});

registry.category("web_tour.tours").add("donation_snippet_use", {
    steps: () => [
        // -- Testing the minimum amount --
        {
            content: "Enter a custom amount smaller than the minimum",
            trigger: "#s_donation_amount_input",
            run: "edit 1",
        },
        {
            content: "Donate with custom amount set",
            trigger: ".s_donation_donate_btn.o_ready_to_donate",
            run: "click",
        },
        {
            content: "Check if alert-danger element exists",
            trigger: "p.alert-danger",
        },
        // -- End of testing the minimum amount --
        {
            content: "Enter a valid custom amount",
            trigger: "#s_donation_amount_input",
            run: "edit 55",
        },
        {
            content: "Donate with custom amount set",
            trigger: ".s_donation_donate_btn.o_ready_to_donate",
            run: "click",
        },
        {
            content: "Go to cart from the notification",
            trigger: "a[href='/shop/cart'].btn-primary",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Check that we landed on the cart page",
            trigger: "#cart_products",
        },
        {
            content: "Check that the donation line is in the cart with quantity 1",
            trigger: ".o_cart_product .js_quantity[value='1']",
        },
        {
            content: "Check that the donation amount on the line is 55",
            trigger: ".o_cart_product:contains('55.00')",
        },
    ],
});

registry.category("web_tour.tours").add("donation_snippet_edition_2", {
    steps: () => [
        waitForEditMode,
        {
            content: "Click on 'Custom Amount' button",
            trigger: ":iframe .s_donation_donate_btn",
            run: "click",
        },
        ...unfoldOptionsGroup("Donation Form"),
        ...changeOptionInPopover("Donation Form", "Custom Amount", "Slider"),
        ...clickOnSave(),
    ]
});

registry.category("web_tour.tours").add("donation_snippet_use_2", {
    steps: () => [
        {
            content: "Click on $10 button",
            trigger: ".s_donation_btn_description button",
            run: "click",
        },
        {
            content: "Donate using the selected amount",
            trigger: ".s_donation_donate_btn.o_ready_to_donate",
            run: "click",
        },
        {
            content: "Go to cart from the notification",
            trigger: "a[href='/shop/cart'].btn-primary",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Check that the donation line is in the cart with quantity 1",
            trigger: ".o_cart_product .js_quantity[value='1']",
        },
        {
            content: "Check that the donation amount on the line is 10",
            trigger: ".o_cart_product:contains('10.00')",
        },
    ],
});

registry.category("web_tour.tours").add("donation_snippet_edition_cart", {
    steps: () => [
        waitForEditMode,
        ...insertSnippet({
            id: "s_donation_inline",
            name: "Donation",
        }),
        ...clickOnSave(),
    ],
});

registry.category("web_tour.tours").add("donation_snippet_use_cart", {
    steps: () => [
        {
            content: "Select a prefilled donation amount",
            trigger: ".s_donation_btn[data-donation-value='10']",
            run: "click",
        },
        {
            content: "Donate while on the cart page",
            trigger: ".s_donation_donate_btn.o_ready_to_donate",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Check that the donation line is in the cart",
            trigger: ".o_cart_product .js_quantity[value='1']",
        },
        {
            content: "Check that the donation amount is 10",
            trigger: ".o_cart_product:contains('10.00')",
        },
    ],
});
