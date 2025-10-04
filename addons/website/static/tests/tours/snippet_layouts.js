import {
    insertSnippet,
    registerWebsitePreviewTour,
    clickOnSnippet,
    changeOption,
    goBackToBlocks,
} from "@website/js/tours/tour_utils";
import { editorsWeakMap } from "@html_editor/../tests/tours/helpers/editor";

const snippets = [
    { id: "s_key_images", name: "Key Images" },
    { id: "s_cards_soft", name: "Cards Soft" },
    { id: "s_cards_grid", name: "Cards Grid" },
];

function getSnippetSteps(snippet) {
    const snippetRow = `:iframe .${snippet.id} .row`;
    const steps = [
        ...insertSnippet({
            id: snippet.id,
            name: snippet.name,
            groupName: "Columns",
        }),
        ...clickOnSnippet({
            id: snippet.id,
            name: snippet.name,
        }),
        changeOption(`${snippet.name}`, "[data-action-param='align-items-start']"),
        {
            content: `Check that the vertical alignment is set to center for ${snippet.name}`,
            trigger: `${snippetRow}.align-items-start`,
        },
        changeOption(`${snippet.name}`, "[data-action-param='align-items-center']"),
        {
            content: `Check that the vertical alignment is set to start for ${snippet.name}`,
            trigger: `${snippetRow}.align-items-center`,
        },
        changeOption(`${snippet.name}`, "[data-action-param='align-items-end']"),
        {
            content: `Check that the vertical alignment is set to end for ${snippet.name}`,
            trigger: `${snippetRow}.align-items-end`,
        },
        goBackToBlocks(),
    ];

    if (snippet.id !== "s_key_images") {
        steps.splice(7, 0, {
            content: "Add content to card body to increase its height",
            trigger: `${snippetRow} p`,
            run() {
                this.anchor.textContent +=
                    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.";
                const editor = editorsWeakMap.get(this.anchor.ownerDocument);
                editor.shared.history.addStep();
            },
        });
    }

    return steps;
}

registerWebsitePreviewTour(
    "snippet_layout",
    {
        url: "/",
        edition: true,
    },
    () => snippets.flatMap(getSnippetSteps)
);
