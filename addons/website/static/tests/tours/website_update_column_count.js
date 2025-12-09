import {
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
    toggleMobilePreview,
    changeOptionInPopover,
} from "@website/js/tours/tour_utils";

const columnCountOptSelector = "div[data-label='Layout'] .dropdown-toggle";
const columnsSnippetRow = ":iframe .s_three_columns .row";
const textImageSnippetRow = ":iframe .s_text_image .row";
const changeFirstAndSecondColumnsMobileOrder = (snippetRowSelector, snippetName) => [
    {
        content: `Scroll into view`,
        trigger: `${snippetRowSelector} > div:nth-child(1)`,
        run() {
            this.anchor.scrollIntoView();
        },
    },
    {
        content: `Click on the first column of the '${snippetName}' snippet`,
        trigger: `${snippetRowSelector} > div:nth-child(1)`,
        run: "click",
    },
    {
        content: "Change the orders of the 1st and 2nd columns",
        trigger: "body .o_overlay_options button[title='Move down']",
        run: "click",
    },
];

const addMobileOrderToTextImageSnippet = [
    ...changeFirstAndSecondColumnsMobileOrder(textImageSnippetRow, "Text-Image"),
    {
        content: "Check that the mobile order classes and styles are correct",
        trigger:
            `${textImageSnippetRow}:has(.order-lg-0[style*='order: 1;']:nth-child(1))` +
            ":has(.order-lg-0[style*='order: 0;']:nth-child(2))",
    },
];

const checkIfNoMobileOrder = (snippetRowSelector) => ({
    content: "Check that the mobile order classes and styles were removed",
    trigger: `${snippetRowSelector}:not(:has(.order-lg-0[style*='order: ']))`,
});

registerWebsitePreviewTour(
    "website_update_column_count",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_three_columns",
            name: "Columns",
            groupName: "Columns",
        }),
        ...clickOnSnippet({
            id: "s_three_columns",
            name: "Columns",
        }),
        ...changeOptionInPopover("Columns", "Layout", "[data-action-value='5']"),
        {
            content:
                "Check that there are now 5 items on 5 columns, and that it didn't change the mobile layout",
            trigger: `${columnsSnippetRow}:has(.col-lg-2:nth-child(5):not(.col-2)):not(:has(:nth-child(6)))`,
        },
        {
            content:
                "Check that there is an offset on the 1st item to center the row on desktop, but not on mobile",
            trigger: `${columnsSnippetRow} > .offset-lg-1:not(.offset-1):first-child`,
        },
        ...changeOptionInPopover("Columns", "Layout", "[data-action-value='2']"),
        {
            content: "Check that there are still 5 items in the row and click on the last one",
            trigger: `${columnsSnippetRow} > :nth-child(5)`,
            run: "click",
        },
        {
            content: "Delete the item",
            trigger: "div[data-container-title='Card'] .oe_snippet_remove",
            run: "click",
        },
        {
            content: "Toggle mobile view",
            trigger: ".o-snippets-top-actions button[data-action='mobile']",
            run: "click",
        },
        {
            content: "Check that there is 1 column on mobile and click on the selector",
            trigger: `${columnCountOptSelector}:contains('1')`,
            run: "click",
        },
        {
            content: "Set 3 columns on mobile",
            trigger: ".o_popover div[data-action-id='changeColumnCount'][data-action-value='3']",
            run: "click",
        },
        {
            content: "Check that there are still 4 items but on rows of 3 columns",
            trigger: `${columnsSnippetRow}:has(.col-lg-6.col-4:nth-child(4))`,
        },
        // As there is no practical way to resize the items through the handles,
        // the next step approximates part of what could be reached.
        {
            content: "Click on the 2nd item",
            trigger: `${columnsSnippetRow} > :nth-child(2)`,
            run: "click",
        },
        {
            content: "Add a fake resized class on mobile to the 2nd item",
            trigger: `${columnsSnippetRow} > :nth-child(2)`,
            async run() {
                const overlayEl = document.querySelector(".oe_overlay.oe_active .o_side_x.e");

                const triggerPointerEvent = (type, x, y) => {
                    const event = new PointerEvent(type, {
                        bubbles: true,
                        pageX: x,
                        pageY: y,
                        clientX: x,
                        clientY: y,
                        pointerType: "mouse",
                    });
                    (type === "pointermove" ? window : overlayEl).dispatchEvent(event);
                };

                // Trigger pointer down
                triggerPointerEvent("pointerdown", 100, 100);
                // Wait for the mutex/this.next to lock and sizingResolve to be
                // ready.
                await new Promise((resolve) => setTimeout(resolve, 0));
                // Dragging
                triggerPointerEvent("pointermove", 150, 100);
                triggerPointerEvent("pointerup", 150, 100);
            },
        },
        {
            content: "Check that the counter shows 'Custom'",
            trigger: `${columnCountOptSelector}:contains('Custom')`,
        },
        {
            content: "Click on the 2nd item",
            trigger: `${columnsSnippetRow} > :nth-child(2)`,
            run: "click",
        },
        {
            content: "Change the orders of the 2nd and 3rd items",
            trigger: ".o_overlay_options [aria-label='Move right']",
            run: "click",
        },
        {
            trigger: `${columnsSnippetRow}:has([style*='order: 2;'].order-lg-0:nth-child(2) + [style*='order: 1;'].order-lg-0:nth-child(3))`,
        },
        {
            content:
                "Check that the 1st item now has order: 0 and a class .order-lg-0 " +
                "and that order: 1, .order-lg-0 is set on the 3rd item, and order: 2, .order-lg-0 on the 2nd",
            trigger: `${columnsSnippetRow}:has([style*='order: 0;'].order-lg-0:first-child)`,
        },
        {
            content: "Toggle desktop view",
            trigger: ".o-snippets-top-actions button[data-action='mobile']",
            run: "click",
        },
        ...changeOptionInPopover("Columns", "Layout", "[data-action-value='6']"),
        {
            content: "Check that each item has a different mobile order from 0 to 5",
            trigger: `${columnsSnippetRow}${[0, 1, 2, 3, 4, 5]
                .map((n) => `:has([style*='order: ${n};'].order-lg-0)`)
                .join("")}`,
        },
        {
            content: "Click on the 6th item",
            trigger: `${columnsSnippetRow} > :nth-child(6)`,
            run: "click",
        },
        {
            content: "Change the orders of the 5th and 6th items to override the mobile orders",
            trigger: ".o_overlay_options [aria-label='Move left']",
            run: "click",
        },
        {
            content: "Check that there are no orders anymore",
            trigger: `${columnsSnippetRow}:not(:has([style*='order: 0;'])):not(:has(.order-lg-0))`,
        },
    ]
);

registerWebsitePreviewTour(
    "website_mobile_order_with_drag_and_drop",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({ id: "s_three_columns", name: "Columns", groupName: "Columns" }),
        ...insertSnippet({ id: "s_text_image", name: "Text - Image", groupName: "Content" }),
        ...toggleMobilePreview(true),
        // Add a mobile order to the "Columns" snippet columns.
        ...changeFirstAndSecondColumnsMobileOrder(columnsSnippetRow, "Columns"),
        {
            content: "Check that the mobile order classes and styles are correct",
            trigger:
                `${columnsSnippetRow}:has(.order-lg-0[style*='order: 1;']:nth-child(1))` +
                ":has(.order-lg-0[style*='order: 0;']:nth-child(2))" +
                ":has(.order-lg-0[style*='order: 2;']:nth-child(3))",
        },
        // Add a mobile order to the "Text-Image" snippet columns.
        ...addMobileOrderToTextImageSnippet,
        // Test the drag and drop in the same snippet.
        ...toggleMobilePreview(false),
        {
            content: "Drag a 'Text-Image' column and drop it in the same snippet",
            trigger: "body .o_overlay_options .o_move_handle",
            run(helpers) {
                return helpers.drag_and_drop(textImageSnippetRow, {
                    position: "bottom",
                    relative: true,
                });
            },
        },
        checkIfNoMobileOrder(textImageSnippetRow),
        // Add again a mobile order to the "Text-Image" snippet columns.
        ...toggleMobilePreview(true),
        ...addMobileOrderToTextImageSnippet,
        // Test the drag and drop from "Columns" to "Text-Image".
        ...toggleMobilePreview(false),
        {
            content: "Click on the second column of the 'Columns' snippet",
            trigger: `${columnsSnippetRow} > div:nth-child(2)`,
            run: "click",
        },
        {
            content: "Drag the second column of 'Columns' and drop it in 'Text-Image'",
            trigger:
                "body .o_overlay_options .o_move_handle, body .o_overlay_options .o_move_handle:not(:visible)",
            run: `drag_and_drop ${textImageSnippetRow}`,
        },
        checkIfNoMobileOrder(textImageSnippetRow),
        {
            content: "Check that the order gap left in 'Columns' was filled",
            trigger:
                `${columnsSnippetRow}:has(.order-lg-0[style*='order: 0;']:nth-child(1))` +
                ":has(.order-lg-0[style*='order: 1;']:nth-child(2))",
        },
    ]
);
