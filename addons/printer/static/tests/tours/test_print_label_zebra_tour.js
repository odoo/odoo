import { registry } from "@web/core/registry";
import * as PrinterUtils from "@printer/../tests/tours/utils";

registry.category("web_tour.tours").add("print_label_zebra_tour", {
    steps: () =>
        [
            PrinterUtils.mockPrinterRequest(),
            {
                content: "Click cog icon",
                trigger: ".o_cp_action_menus .dropdown-toggle",
                run: "click",
            },
            {
                content: "Click 'Print Label' action",
                trigger: ".o-dropdown-item:contains('Print Label')",
                run: "click",
            },
            {
                content: "Select 'ZPL Labels' option",
                trigger: ".o_field_widget[name='print_format'] .o_radio_input[data-value='zpl']",
                run: "click",
            },
            {
                content: "Click 'Print'",
                trigger: ".modal-footer .btn-primary:contains('Print')",
                run: "click",
            },
            {
                content: "Click the printer field to later select the printer",
                trigger: "div[name='printer_ids'] input",
                run: "edit Test Zebra Printer",
            },
            {
                content: "Click 'Test Zebra Printer' in the dropdown",
                trigger: "a span span:contains('Test Zebra Printer')",
                run: "click",
            },
            {
                content: "Check printer has been selected before clicking 'Print'",
                trigger: ".o_tag_badge_text:contains('Test Zebra Printer')",
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
