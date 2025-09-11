import { registerWebsitePreviewTour, insertSnippet } from "@website/js/tours/tour_utils";

function checkReplaceButton(columnIndex) {
    return [
        {
            content: `Click inside the dropped banner categories snippet (column ${columnIndex}) to load its options`,
            trigger: `:iframe .s_banner_categories div[class='container'] div div:nth-child(${columnIndex})`,
            run: "click",
        },
        {
            content: "Check on the replace button",
            trigger: "[data-container-title='Column'] [data-action-id='replaceBgImage']",
        },
    ];
}

registerWebsitePreviewTour("banner_categories_image_replaceable", {
    url: "/",
    edition: true,
}, () => [
    ...insertSnippet({
        id: "s_banner_categories",
        name: "Banner Categories",
        groupName: "Catalog",
    }),
    ...checkReplaceButton(2),
    ...checkReplaceButton(3),
    ...checkReplaceButton(4),
]);
