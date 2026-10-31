import {
    insertSnippet,
    changeOption,
    clickOnSave,
    clickOnElement,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

const clickableBlockSelector =
    ":iframe .s_masonry_block .o_grid_item:has(h2:contains('Community'))";

registerWebsitePreviewTour(
    "clickable_masonry_block",
    {
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_masonry_block_default_template",
            name: "Masonry",
            groupName: "Images",
        }),
        clickOnElement("image block", ":iframe .s_masonry_block .o_grid_item_image img"),
        {
            content: "Wait for the image options",
            trigger: ".o_hb_options_container[data-container-title='Image']",
        },
        {
            content: "Check that image blocks cannot be made clickable",
            trigger:
                ".o_hb_options_container[data-container-title='Block']:not(:has([data-action-id='setElementClickable']))",
        },
        clickOnElement("Community Focus block", clickableBlockSelector),
        changeOption("Block", "[data-action-id='setElementClickable'] input"),
        {
            content: "Enter the URL for the block link",
            trigger: "div[data-action-id='setElementAnchorUrl'] input",
            run: "edit #",
        },
        {
            content: "Select matching URL from autocomplete",
            trigger: "ul.ui-autocomplete li a:contains('#top')",
            run: "click",
        },
        {
            content: "Check that the link is added to the block",
            trigger: `${clickableBlockSelector}:has(a.stretched-link[href='#top'])`,
        },
        ...clickOnSave(),
        {
            content: "Check that the link only covers its own block",
            trigger: `${clickableBlockSelector}:has(a.stretched-link)`,
            run() {
                const doc = this.anchor.ownerDocument;
                const getLinkAtCenter = (el) => {
                    el.scrollIntoView({ block: "center", behavior: "instant" });
                    const { x, y, width, height } = el.getBoundingClientRect();
                    return doc
                        .elementFromPoint(x + width / 2, y + height / 2)
                        ?.closest("a.stretched-link");
                };
                if (!getLinkAtCenter(this.anchor)) {
                    throw new Error("The clickable block should be covered by its link.");
                }
                const otherBlockEl = doc.querySelector(
                    ".s_masonry_block .o_grid_item:not(.o_grid_item_image):not(:has(> .stretched-link))"
                );
                if (getLinkAtCenter(otherBlockEl)) {
                    throw new Error("The link should not cover the other blocks.");
                }
            },
        },
    ]
);
