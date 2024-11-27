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
                    if (exp_date.innerText.trim() !== "06/03/2025 00:00") {
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
            trigger: "button.o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_form_saved",
        },
    ],
});
