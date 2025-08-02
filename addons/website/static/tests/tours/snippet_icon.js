import { insertSnippet, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour("snippet_icon", {
    url: "/",
    edition: true,
}, () => [
    ...insertSnippet({ id: "s_icon", name: "Icon" }, { ignoreLoading: true }),
    {
        content: "Verify if the media dialog opens the Icon tab",
        trigger: ".o_select_media_dialog a.active",
        run: function () {
            if(!this.anchor.textContent.includes("Icons")) {
                console.error("The media dialog should open the Icons tab by default.");
            }
        }
    },
    {
        content: "Close the media dialog without selecting an icon",
        trigger: ".o_select_media_dialog .btn-close",
        run: "click",
    },
    {
        content: "Verify if an icon is there",
        trigger: ":iframe:not(:has(.fa-star-o))",
    },
    ...insertSnippet({ id: "s_icon", name: "Icon" }, { ignoreLoading: true }),
    {
        content: "Insert an Icon",
        trigger: ".font-icons-icons .fa-trophy",
        run: "click",
    },
    {
        content: "Verify if the icon has been added",
        trigger: ":iframe .fa-trophy"
    },
    {
        content: "Double Click on the icon",
        trigger: ":iframe .fa-trophy",
        run: "dblclick",
    },
    {
        content: "Verify if the media dialog opens",
        trigger: ".o_select_media_dialog",
    },
    {
        content: "Close the media dialog",
        trigger: ".o_select_media_dialog .btn-close",
        run: "click",
    },
    {
        content: "Verify if the icon is still present in the footer",
        trigger: ":iframe .fa-trophy",
    },
])
