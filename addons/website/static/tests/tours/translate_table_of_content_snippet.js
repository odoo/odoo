import {
    clickOnSave,
    clickToolbarButton,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";
import { changeLanguageAndOpenTranslateMode } from "./translate_select_element";

registerWebsitePreviewTour(
    "translate_table_of_content_snippet",
    {
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_table_of_content",
            name: "Table of Content",
            groupName: "Text",
        }),
        ...clickOnSave(),
        ...changeLanguageAndOpenTranslateMode(),
        {
            content: "Edit the table of content's first title's translation",
            trigger: ":iframe #table_of_content_heading_1_1 > span[data-oe-translation-source-sha]",
            run: "editor The translated title",
        },
        ...clickToolbarButton(
            "The translated title",
            "#table_of_content_heading_1_1 > span[data-oe-translation-source-sha]",
            "bold" // could be any edit in that span
        ),
        ...clickOnSave(),
        {
            content: "Verify the title has bold",
            trigger: ":iframe #table_of_content_heading_1_1 strong",
        },
        {
            content: "Verify the navbar link to the title does not have bold",
            trigger: ':iframe [href="#table_of_content_heading_1_1"]:not(:has(strong))',
        },
    ]
);
