/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";

const columnCountOptSelector = ".snippet-option-layout_column we-select[data-name='column_count_opt']";
const columnsSnippetRow = "iframe .s_three_columns .row";

wTourUtils.registerWebsitePreviewTour("website_update_column_count", {
    test: true,
    url: "/",
    edition: true,
}, () => [
wTourUtils.dragNDrop({
    id: "s_three_columns",
    name: "Columns",
}),
wTourUtils.clickOnSnippet({
    id: "s_three_columns",
    name: "Columns",
}), {
    content: "Open the columns count select",
    trigger: columnCountOptSelector,
}, {
    content: "Set 5 columns on desktop",
    trigger: `${columnCountOptSelector} we-button[data-select-count='5']`,
}, {
    content: "Check that there are now 5 items on 5 columns, and that it didn't change the mobile layout",
    trigger: `${columnsSnippetRow}:has(.col-lg-2:nth-child(5):not(.col-2)):not(:has(:nth-child(6)))`,
    isCheck: true,
}, {
    content: "Check that there is an offset on the 1st item to center the row on desktop, but not on mobile",
    trigger: `${columnsSnippetRow} > .offset-lg-1:not(.offset-1):first-child`,
    isCheck: true,
}, {
    content: "Open the columns count select",
    trigger: columnCountOptSelector,
}, {
    content: "Set 2 columns on desktop",
    trigger: `${columnCountOptSelector} we-button[data-select-count='2']`,
}, {
    content: "Check that there are still 5 items in the row and click on the last one",
    trigger: `${columnsSnippetRow} > :nth-child(5)`,
}, {
    content: "Delete the item",
    trigger: "we-title:contains('Column'):not(:contains('Columns')) .oe_snippet_remove",
}, {
    content: "Toggle mobile view",
    trigger: ".o_we_website_top_actions [data-action='mobile']",
}, {
    content: "Check that there is 1 column on mobile and click on the selector",
    trigger: `${columnCountOptSelector} we-toggler:contains('1')`,
}, {
    content: "Set 3 columns on mobile",
    trigger: `${columnCountOptSelector} we-button[data-select-count='3']`,
}, {
    content: "Check that there are still 4 items but on rows of 3 columns",
    trigger: `${columnsSnippetRow}:has(.col-lg-6.col-4:nth-child(4))`,
    isCheck: true,
},
// As there is no practical way to resize the items through the handles, the
// next step approximates part of what could be reached.
{
    content: "Add a fake resized class on mobile to the 2nd item",
    trigger: `${columnsSnippetRow} > :nth-child(2)`,
    run: ({ tip_widget }) => {
        const secondItemEl = tip_widget.$anchor[0];
        secondItemEl.classList.replace("col-4", "col-6");
        // As this is a hardcoded class replacement, a click is needed to
        // update the column count.
        secondItemEl.previousElementSibling.click();
    },
}, {
    content: "Check that the counter shows 'Custom'",
    trigger: `${columnCountOptSelector} we-toggler:contains('Custom')`,
    isCheck: true,
}, {
    content: "Click on the 2nd item",
    trigger: `${columnsSnippetRow} > :nth-child(2)`,
}, {
    content: "Change the orders of the 2nd and 3rd items",
    trigger: "iframe .o_overlay_move_options [data-name='move_right_opt']",
}, {
    content: "Check that the 1st item now has order: 0 and a class .order-lg-0 " +
             "and that order: 1, .order-lg-0 is set on the 3rd item, and order: 2, .order-lg-0 on the 2nd",
    trigger: `${columnsSnippetRow}:has([style*='order: 0;'].order-lg-0:first-child)`,
    extra_trigger: `${columnsSnippetRow}:has([style*='order: 2;'].order-lg-0:nth-child(2) + [style*='order: 1;'].order-lg-0:nth-child(3))`,
    isCheck: true,
}, {
    content: "Toggle desktop view",
    trigger: ".o_we_website_top_actions [data-action='mobile']",
}, {
    content: "Open the columns count select",
    trigger: columnCountOptSelector,
}, {
    content: "Add 2 more items through the columns counter",
    trigger: `${columnCountOptSelector} we-button[data-select-count='6']`,
}, {
    content: "Check that each item has a different mobile order from 0 to 5",
    trigger: `${columnsSnippetRow}${[0, 1, 2, 3, 4, 5].map(n => `:has([style*='order: ${n};'].order-lg-0)`).join("")}`,
    isCheck: true,
}, {
    content: "Click on the 6th item",
    trigger: `${columnsSnippetRow} > :nth-child(6)`,
}, {
    // TODO: remove this step. It should not be needed, but the build fails
    // without it.
    content: "Wait for move arrows to appear",
    trigger: "iframe .o_overlay_move_options [data-name='move_left_opt']:has(+ .d-none[data-name='move_right_opt'])",
    isCheck: true,
}, {
    content: "Change the orders of the 5th and 6th items to override the mobile orders",
    trigger: "iframe .o_overlay_move_options [data-name='move_left_opt']",
}, {
    content: "Check that there are no orders anymore",
    trigger: `${columnsSnippetRow}:not(:has([style*='order: 0;'])):not(:has(.order-lg-0))`,
    isCheck: true,
},
]);
