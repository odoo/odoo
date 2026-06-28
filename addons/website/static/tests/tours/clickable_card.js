import {
    insertSnippet,
    changeOption,
    changeOptionInPopover,
    clickOnSave,
    clickOnElement,
    openLinkPopup,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "clickable_card",
    {
        edition: true,
    },
    () => [
        ...insertSnippet({ id: "s_title", name: "Title", groupName: "Text" }),
        {
            content: "Drag a Card into the Title section",
            trigger:
                ".o-snippets-menu .o_block_tab:not(.o_we_ongoing_insertion) .o_snippet[name='Card'].o_draggable .o_snippet_thumbnail",
            run: "drag_and_drop :iframe .s_title .oe_drop_zone:last",
        },
        {
            content: "Add a Button inside the Card",
            trigger:
                ".o-snippets-menu .o_block_tab:not(.o_we_ongoing_insertion) .o_snippet[name='Button'].o_draggable .o_snippet_thumbnail",
            run: "drag_and_drop :iframe .s_title .s_card .oe_drop_zone:last",
        },
        {
            content: "Scroll to the button",
            trigger: ":iframe .s_title .s_card .btn",
            run: function () {
                this.anchor.scrollIntoView();
            },
        },
        ...openLinkPopup({
            trigger: ":iframe .s_title .s_card .btn.btn-primary",
            url: "/contactus",
            edit: true,
        }),
        {
            content: "Enter the URL for the button link",
            trigger: ".o-we-linkpopover .o_we_href_input_link",
            run: "edit #",
        },
        {
            content: "Select matching URL from autocomplete",
            trigger: "ul.ui-autocomplete li a:contains('#bottom')",
            run: "click",
        },
        clickOnElement("card image", ":iframe .s_title .s_card img"),
        changeOption("Image", "setLink"),
        {
            content: "Enter the URL for the image link",
            trigger: "div[data-action-id='setUrl'] input",
            run: "edit #",
        },
        {
            content: "Select matching URL from autocomplete",
            trigger: "ul.ui-autocomplete li a:contains('#bottom')",
            run: "click",
        },
        ...changeOptionInPopover("Image", "Animation", "On Hover"),
        clickOnElement("card container", ":iframe .s_title .s_card"),
        changeOption("Card", "[data-action-id='setCardClickable'] input"),
        {
            content: "Enter the URL for the card link",
            trigger: "div[data-action-id='setCardAnchorUrl'] input",
            run: "edit #",
        },
        {
            content: "Select matching URL from autocomplete",
            trigger: "ul.ui-autocomplete li a:contains('#top')",
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "Scroll to the #bottom anchor",
            trigger: ":iframe #bottom",
            run() {
                this.anchor.scrollIntoView(true);
            },
        },
        {
            content: "Click inside the card",
            trigger: ":iframe .s_title .s_card .card-body",
            run() {
                const rect = this.anchor.getBoundingClientRect();
                this.anchor.ownerDocument
                    .elementFromPoint(rect.x + rect.width / 2, rect.y + rect.height / 2)
                    .click();
            },
        },
        {
            content: "Check that the scroll reached top",
            trigger: ":iframe body",
            async run({ waitUntil }) {
                await waitUntil(() => this.anchor.ownerDocument.scrollingElement.scrollTop == 0, {
                    timeout: 3000,
                    message: "Did not scroll to top",
                });
            },
        },
        {
            content: "Scroll to the #bottom again",
            trigger: ":iframe #bottom",
            run() {
                this.anchor.scrollIntoView(true);
            },
        },
        {
            content: "Click on the button inside the card",
            trigger: ":iframe .s_title .s_card .btn.btn-primary",
            run() {
                const rect = this.anchor.getBoundingClientRect();
                this.anchor.ownerDocument
                    .elementFromPoint(rect.x + rect.width / 2, rect.y + rect.height / 2)
                    .click();
            },
        },
        {
            content: "Check that the scroll reached top",
            trigger: ":iframe body",
            async run({ waitUntil }) {
                await waitUntil(() => this.anchor.ownerDocument.scrollingElement.scrollTop == 0, {
                    timeout: 3000,
                    message: "Did not scroll to top",
                });
            },
        },
    ]
);
