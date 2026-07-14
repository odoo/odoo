/** @odoo-module **/

import {
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
    toggleMobilePreview,
} from '@website/js/tours/tour_utils';

const columnCountOptSelector = ".snippet-option-layout_column we-select[data-name='column_count_opt']";
const columnsSnippetRow = ":iframe .s_three_columns .row";
const textImageSnippetRow = ":iframe .s_text_image .row";
const changeFirstAndSecondColumnsMobileOrder = (snippetRowSelector, snippetName) => {
    return [{
        content: `Click on the first column of the '${snippetName}' snippet`,
        trigger: `${snippetRowSelector} > div:nth-child(1)`,
        run: "click",
    }, {
        content: "Change the orders of the 1st and 2nd columns",
        trigger: ":iframe .o_overlay_move_options [data-name='move_right_opt']",
        run: "click",
    }];
};

const addMobileOrderToTextImageSnippet = [
    ...changeFirstAndSecondColumnsMobileOrder(textImageSnippetRow, "Text-Image"),
    {
        content: "Check that the mobile order classes and styles are correct",
        trigger: `${textImageSnippetRow}:has(.order-lg-0[style*='order: 1;']:nth-child(1))`
            + ":has(.order-lg-0[style*='order: 0;']:nth-child(2))",
    },
];

const checkIfNoMobileOrder = (snippetRowSelector) => {
    return {
        content: "Check that the mobile order classes and styles were removed",
        trigger: `${snippetRowSelector}:not(:has(.order-lg-0[style*='order: ']))`,
    };
};

registerWebsitePreviewTour("website_update_column_count", {
    url: "/",
    edition: true,
}, () => [
...insertSnippet({
    id: "s_three_columns",
    name: "Columns",
    groupName: "Columns",
}),
...clickOnSnippet({
    id: "s_three_columns",
    name: "Columns",
}), {
    content: "Open the columns count select",
    trigger: columnCountOptSelector,
    run: "click",
}, {
    content: "Set 5 columns on desktop",
    trigger: `${columnCountOptSelector} we-button[data-select-count='5']`,
    run: "click",
}, {
    content: "Check that there are now 5 items on 5 columns, and that it didn't change the mobile layout",
    trigger: `${columnsSnippetRow}:has(.col-lg-2:nth-child(5):not(.col-2)):not(:has(:nth-child(6)))`,
}, {
    content: "Check that there is an offset on the 1st item to center the row on desktop, but not on mobile",
    trigger: `${columnsSnippetRow} > .offset-lg-1:not(.offset-1):first-child`,
}, {
    content: "Open the columns count select",
    trigger: columnCountOptSelector,
    run: "click",
}, {
    content: "Set 2 columns on desktop",
    trigger: `${columnCountOptSelector} we-button[data-select-count='2']`,
    run: "click",
}, {
    content: "Check that there are still 5 items in the row and click on the last one",
    trigger: `${columnsSnippetRow} > :nth-child(5)`,
    run: "click",
}, {
    content: "Delete the item",
    trigger: "we-title:contains('Card') .oe_snippet_remove",
    run: "click",
}, {
    content: "Toggle mobile view",
    trigger: ".o_we_website_top_actions [data-action='mobile']",
    run: "click",
}, {
    content: "Check that there is 1 column on mobile and click on the selector",
    trigger: `${columnCountOptSelector} we-toggler:contains('1')`,
    run: "click",
}, {
    content: "Set 3 columns on mobile",
    trigger: `${columnCountOptSelector} we-button[data-select-count='3']`,
    run: "click",
}, {
    content: "Check that there are still 4 items but on rows of 3 columns",
    trigger: `${columnsSnippetRow}:has(.col-lg-6.col-4:nth-child(4))`,
},
// As there is no practical way to resize the items through the handles, the
// next step approximates part of what could be reached.
{
    content: "Add a fake resized class on mobile to the 2nd item",
    trigger: `${columnsSnippetRow} > :nth-child(2)`,
    run() {
        this.anchor.classList.replace("col-4", "col-6");
        // As this is a hardcoded class replacement, a click is needed to
        // update the column count.
        this.anchor.previousElementSibling.click();
    },
}, {
    content: "Check that the counter shows 'Custom'",
    trigger: `${columnCountOptSelector} we-toggler:contains('Custom')`,
}, {
    content: "Click on the 2nd item",
    trigger: `${columnsSnippetRow} > :nth-child(2)`,
    run: "click",
}, {
    content: "Change the orders of the 2nd and 3rd items",
    trigger: ":iframe .o_overlay_move_options [data-name='move_right_opt']",
    run: "click",
},
{
    trigger: `${columnsSnippetRow}:has([style*='order: 2;'].order-lg-0:nth-child(2) + [style*='order: 1;'].order-lg-0:nth-child(3))`,
},
{
    content: "Check that the 1st item now has order: 0 and a class .order-lg-0 " +
             "and that order: 1, .order-lg-0 is set on the 3rd item, and order: 2, .order-lg-0 on the 2nd",
    trigger: `${columnsSnippetRow}:has([style*='order: 0;'].order-lg-0:first-child)`,
}, {
    content: "Toggle desktop view",
    trigger: ".o_we_website_top_actions [data-action='mobile']",
    run: "click",
}, {
    content: "Open the columns count select",
    trigger: columnCountOptSelector,
    run: "click",
}, {
    content: "Add 2 more items through the columns counter",
    trigger: `${columnCountOptSelector} we-button[data-select-count='6']`,
    run: "click",
}, {
    content: "Check that each item has a different mobile order from 0 to 5",
    trigger: `${columnsSnippetRow}${[0, 1, 2, 3, 4, 5].map(n => `:has([style*='order: ${n};'].order-lg-0)`).join("")}`,
}, {
    content: "Click on the 6th item",
    trigger: `${columnsSnippetRow} > :nth-child(6)`,
    run: "click",
}, {
    // TODO: remove this step. It should not be needed, but the build fails
    // without it.
    content: "Wait for move arrows to appear",
    trigger: ":iframe .o_overlay_move_options:has([data-name='move_left_opt'] + .d-none[data-name='move_right_opt'])",
}, {
    content: "Change the orders of the 5th and 6th items to override the mobile orders",
    trigger: ":iframe .o_overlay_move_options [data-name='move_left_opt']",
    run: "click",
}, {
    content: "Check that there are no orders anymore",
    trigger: `${columnsSnippetRow}:not(:has([style*='order: 0;'])):not(:has(.order-lg-0))`,
},
]);

registerWebsitePreviewTour("website_mobile_order_with_drag_and_drop", {
    url: "/",
    edition: true,
}, () => [
    ...insertSnippet({id: "s_three_columns", name: "Columns", groupName: "Columns"}),
    ...insertSnippet({id: "s_text_image", name: "Text - Image", groupName: "Content"}),
    ...toggleMobilePreview(true),
    // Add a mobile order to the "Columns" snippet columns.
    ...changeFirstAndSecondColumnsMobileOrder(columnsSnippetRow, "Columns"),
    {
        content: "Check that the mobile order classes and styles are correct",
        trigger: `${columnsSnippetRow}:has(.order-lg-0[style*='order: 1;']:nth-child(1))`
            + ":has(.order-lg-0[style*='order: 0;']:nth-child(2))"
            + ":has(.order-lg-0[style*='order: 2;']:nth-child(3))",
    },
    // Add a mobile order to the "Text-Image" snippet columns.
    ...addMobileOrderToTextImageSnippet,
    // Test the drag and drop in the same snippet.
    ...toggleMobilePreview(false),
    {
        content: "Drag a 'Text-Image' column and drop it in the same snippet",
        trigger: ":iframe .o_overlay_move_options .o_move_handle",
        run: `drag_and_drop ${textImageSnippetRow}`,
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
    }, {
        content: "Drag the second column of 'Columns' and drop it in 'Text-Image'",
        trigger: ":iframe .o_overlay_move_options .o_move_handle",
        run: `drag_and_drop ${textImageSnippetRow}`,
    },
    checkIfNoMobileOrder(textImageSnippetRow),
    {
        content: "Check that the order gap left in 'Columns' was filled",
        trigger: `${columnsSnippetRow}:has(.order-lg-0[style*='order: 0;']:nth-child(1))`
            + ":has(.order-lg-0[style*='order: 1;']:nth-child(2))",
    },
]);
