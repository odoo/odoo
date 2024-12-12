/** @odoo-module **/
import wTourUtils from '@website/js/tours/tour_utils';

wTourUtils.registerWebsitePreviewTour('website_font_family', {
    test: true,
    url: '/',
    edition: true,
}, () => [
    ...wTourUtils.goToTheme(),
    {
        content: "Click on the heading font family selector",
        trigger: "we-select[data-variable='headings-font']",
        run: "click",
    },
    {
        content: "Click on the 'Add a custom font' button",
        trigger: "we-select[data-variable='headings-font'] .o_we_add_font_btn",
        run: "click",
    },
    {
        content: "Simulate file input selection",
        trigger: "input#upload_font",
        run: async function () {
            async function fetchFileAndSimulateInput(filePath, fileInput) {
                try {
                    const response = await fetch(filePath);
                    const blob = await response.blob();
                    const file = new File([blob], "Lato-BlaIta-webfont.woff", { type: "font/woff" });

                    const dataTransfer = new DataTransfer();
                    dataTransfer.items.add(file);
                    fileInput.files = dataTransfer.files;
                    fileInput.dispatchEvent(new Event("change", { bubbles: true }));
                } catch (error) {
                    console.error("Error fetching the file:", error);
                }
            }

            // Fetch the file and simulate the input
            var fileInput = this.anchor;
            await fetchFileAndSimulateInput("/web/static/fonts/lato/Lato-BlaIta-webfont.woff", fileInput);
        }
    },
    {
        content: "Check that the preview of 'Lato-BlaIta-webfont' font is loaded",
        trigger: "div[style*=\"font-family: 'Lato-BlaIta-webfont';\"]",
    },
    {
        content: "Click on the 'Save and reload' button",
        trigger: "button.btn-primary",
        run: "click",
    },
    ...wTourUtils.goToTheme(),
    {
        content: "Verify that 'Lato-BlaIta-webfont' font family is applied",
        trigger: "we-select[data-variable='headings-font'] we-toggler[style*='font-family: Lato-BlaIta-webfont;']",
    },
    {
        content: "Open the heading font family selector",
        trigger: "we-select[data-variable='headings-font'] we-toggler[style*='font-family: Lato-BlaIta-webfont;']",
        run: "click",
    },
    {
        content: "Click on the 'Add a custom font' button again",
        trigger: "we-select[data-variable='headings-font'] .o_we_add_font_btn",
        run: "click",
    },
    {
        content: "Wait for the modal to open and then refresh",
        trigger: "button.btn-secondary",
        run: function () {
            setTimeout(() => {
                this.anchor.click();
            }, 2000);
        },
    },
    {
        content: "Check that 'Lato-BlaIta-webfont' font family is still applied and not reverted",
        trigger: "we-select[data-variable='headings-font'] we-toggler[style*='font-family: Lato-BlaIta-webfont;']",
    },
]);
