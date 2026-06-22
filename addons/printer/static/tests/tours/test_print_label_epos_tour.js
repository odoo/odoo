import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("print_label_epos_tour", {
    steps: () =>
        [
            {
                content: "Click cog icon",
                trigger: ".o_cp_action_menus .dropdown-toggle",
                run: "click",
            },
            {
                content: "Click 'Print' section",
                trigger: ".o-dropdown-item:contains('Print')",
                run: "click",
            },
            {
                content: "Click 'Shipping Labels' action",
                trigger: ".o-dropdown-item:contains('Shipping Labels')",
                run: "click",
            },
            {
                content: "Click the printer field to later select the printer",
                trigger: "div[name='printer_ids'] input",
                run: "click",
            },
            {
                content: "Click the printer field to later select the printer",
                trigger: "#printer_ids_0_0_0",
                run: "click",
            },
            {
                content: "Check printer has been selected before clicking 'Print'",
                trigger: ".o_tag_badge_text:contains('Test Epson Printer')",
            },
            {
                content: "Click 'Print'",
                trigger: ".modal-footer .btn-primary:contains('Print')",
                run: "click",
            },
            {
                content: "Wait for the print request to be sent",
                trigger: "body",
                run: async () => {
                    await new Promise((resolve) => setTimeout(resolve, 1000));
                },
            }
        ].flat(),
});
