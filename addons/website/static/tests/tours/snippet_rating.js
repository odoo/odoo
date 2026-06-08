import { registry } from "@web/core/registry";
import {
    changeOptionInPopover,
    clickOnSnippet,
    insertSnippet,
    waitForEditMode,
} from "@website/js/tours/tour_utils";

registry.category("web_tour.tours").add("snippet_rating", {
    steps: () => [
        waitForEditMode,
        ...insertSnippet({ id: "s_rating", name: "Rating" }),
        ...clickOnSnippet({ id: "s_rating", name: "Rating" }),
        ...changeOptionInPopover("Rating", "Title Position", "Left"),
        {
            content: "Check whether s_rating_inline class applied or not",
            trigger: ":iframe .s_rating_inline",
        },
        ...changeOptionInPopover("Rating", "Title Position", "None"),
        {
            content: "Check whether s_rating_no_title class applied or not",
            trigger: ":iframe .s_rating_no_title",
        },
        ...changeOptionInPopover("Rating", "Title Position", "Top"),
        {
            content: "Check whether s_rating_no_title class removed or not",
            trigger: ":iframe .s_rating:not(.s_rating_no_title)",
        },
    ],
});
