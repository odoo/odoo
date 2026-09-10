<<<<<<< 157874aad3aebef5bc9268de6e17530641107e31
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('test_generate_serial_with_expiration', {
    steps: () => [
        {
            trigger: "button:contains('Details')",
            run: "click",
        },
        {
            trigger: '.o_widget_generate_serials > button',
            run: "click",
        },
        {
            trigger: ".modal .btn-primary:contains('New')",
            run: "click",
        },
        {
            trigger: ".modal .btn-primary:contains('Generate')",
            run: "click",
        },
        // Check that the expiration date is now set after generating Serials/Lots.
        {
            trigger: "td.o_field_cell[name=expiration_date]",
            run: () => {
                const exp_dates = document.querySelectorAll("td.o_field_cell[name=expiration_date]");
                for (const exp_date of exp_dates) {
                    if (exp_date.innerText.trim() !== "Jun 3, 2020, 12:00 AM") {
                        throw new Error("Expiration date should be Jun 3, 12:00 AM.");
                    }
                }
            }
        },
        {
            trigger: ".modal button:contains(save)",
            run: "click",
        },
        {
            trigger: "button.o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_form_saved",
        },
    ],
});
||||||| 9b26cc0cf68a44fa900a98cfadeb87bc78ea29ca
=======
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('test_generate_serial_with_expiration', {
    steps: () => [
        {
            trigger: ".o_list_renderer .fa-list",
            run: "click",
        },
        {
            trigger: "h4:contains('Stock move')",
        },
        {
            trigger: '.o_widget_generate_serials > button',
            run: "click",
        },
        {
            trigger: ".modal div[name=next_serial] input",
            run: "edit serial_n_1",
        },
        {
            trigger: ".modal div[name=next_serial_count] input",
            run: "edit 2 && click body",
        },
        {
            trigger: ".modal .btn-primary:contains('Generate')",
            run: "click",
        },
        // Check that the expiration date is now set after generating Serials/Lots.
        {
            trigger: "td.o_field_cell[name=expiration_date]",
            run: () => {
                const exp_dates = document.querySelectorAll("td.o_field_cell[name=expiration_date]");
                for (const exp_date of exp_dates) {
                    if (exp_date.innerText.trim() !== "06/03/2025 00:00:00") {
                        throw new Error("Expiration date should be 06/03/2025.");
                    }
                }
            }
        },
        {
            trigger: ".modal button:contains(save)",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal))",
        },
        {
            trigger: "button.o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_form_saved",
        },
    ],
});
>>>>>>> d7fb1772b5b61ef19456af6aeda16a88c73a65a6
