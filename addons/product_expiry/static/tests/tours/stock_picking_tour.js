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

registry.category("web_tour.tours").add('test_modify_removal_and_expiration_dates', {
    steps: () => [
        {
            trigger: "button:contains('Details')",
            run: "click",
        },
        {
            trigger: 'td.o_field_cell[name="expiration_date"]',
            run: 'click',
        },
        {
            trigger: 'td.o_field_cell[name="expiration_date"] input',
            content: "Expiration date modification",
            run: () => {
                const exp_date = document.querySelector("td.o_field_cell[name=expiration_date]");
                const input = exp_date.querySelector('input.o_input');
                if (input) {
                    input.value = "01/26/2026 00:00:00";
                    input.dispatchEvent(new Event("change", { bubbles: true, cancelable: true }));
                }
            },
        },
        {
            trigger: 'td.o_field_cell[name="removal_date"] input',
            content: "Removal date verification",
            run: () => {
                const rem_date = document.querySelector("td.o_field_cell[name=removal_date]");
                const input = rem_date.querySelector('input.o_input');

                if (input.value !== "01/26/2026 00:00") {
                    throw new Error(`Removal date should be 01/26/2026, not ${input.value}.`);
                }
            },
        },
        {
            trigger: 'td[name="removal_date"]',
            run: "click",
        },
        {
            trigger: 'td.o_field_cell[name="removal_date"] input',
            content: "Removal date modification",
            run: () => {
                const rem_date = document.querySelector("td.o_field_cell[name=removal_date]");
                const input = rem_date.querySelector('input.o_input');
                if (input) {
                    input.value = "01/12/2026 00:00:00";
                    input.dispatchEvent(new Event("change", { bubbles: true, cancelable: true }));
                }
            },
        },
        {
            trigger: 'td.o_field_cell[name="expiration_date"] input',
            content: "Removal and expiration date verification before save",
            run: () => {
                const exp_date = document.querySelector("td.o_field_cell[name=expiration_date]");
                const input_exp = exp_date.querySelector('input.o_input');

                if (input_exp.value !== "01/26/2026 00:00") {
                    throw new Error(`Expiration date should be 01/26/2026, not ${input_exp.value}.`);
                }

                const rem_date = document.querySelector("td.o_field_cell[name=removal_date]");
                const input_rem = rem_date.querySelector('input.o_input');

                if (input_rem.value !== "01/12/2026 00:00") {
                    throw new Error(`Removal date should be 01/12/2026, not ${input_rem.value}.`);
                }
            },
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
        {
            trigger: "button:contains('Details')",
            content: "Reopen the line view",
            run: "click",
        },
        {
            trigger: 'td.o_field_cell[name="expiration_date"]',
            content: "Removal and expiration date verification after save",
            run: () => {
                const exp_date = document.querySelector("td.o_field_cell[name=expiration_date]");

                if (exp_date.innerText.trim() !== "01/26/2026 00:00") {
                    throw new Error(`Expiration date should be 01/26/2026, not ${exp_date.innerText.trim()}.`);
                }

                const rem_date = document.querySelector("td.o_field_cell[name=removal_date]");

                if (rem_date.innerText.trim() !== "01/12/2026 00:00") {
                    throw new Error(`Removal date should be 01/12/2026, not ${rem_date.innerText.trim()}.`);
                }
            },
        },
    ],
});
