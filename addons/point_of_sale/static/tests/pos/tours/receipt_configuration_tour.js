import { waitFor } from "@odoo/hoot-dom";
import { registry } from "@web/core/registry";

async function checkReceiptLayout(layout) {
    await waitFor("body .receipt_preview_spinner.d-none", { timeout: 10000 });

    const iframe = document.querySelector("iframe");
    const receipt = iframe.contentDocument.querySelector(".pos-receipt");

    if (!iframe || !receipt) {
        new Error("Preview receipt is missing in the receipt configurator.");
    }

    if (!receipt.classList.contains(`pos-receipt-${layout}-layout`)) {
        new Error(`Preview receipt does not use the '${layout}' layout.`);
    }
}

registry.category("web_tour.tours").add("ReceiptLayoutConfigurationTour", {
    steps: () =>
        [
            {
                content: "Click to open the receipt configurator",
                trigger: "button[name=action_view_pos_receipt_layout]",
                run: "click",
            },
            {
                content: "Check receipt configurator is open",
                trigger: ".modal-header .modal-title:contains('Configure receipt')",
            },
            {
                content: "Check the preview receipt uses the default 'default' layout",
                trigger: "div[name=receipt_preview] .o_receipt_preview_iframe_wrapper iframe",
                timeout: 15000,
                run: async () => await checkReceiptLayout("default"),
            },
            {
                content: "Select the 'Boxes' layout option",
                trigger: "div[name=receipt_layout] span:contains('Boxes')",
                run: "click",
            },
            {
                content: "Verify the preview updates to use the 'Boxes' layout",
                trigger: "div[name=receipt_preview] .o_receipt_preview_iframe_wrapper iframe",
                timeout: 15000,
                run: async () => await checkReceiptLayout("Boxes"),
            },
            {
                content: "Click to save your layout configuration",
                trigger: ".modal-footer button[name=receipt_layout_save]",
                run: "click",
            },
            {
                content: "Return to the home menu",
                trigger: ".o_main_navbar a[title='Home menu']",
                run: "click",
            },
        ].flat(),
});
