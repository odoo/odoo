import { describe, expect, test } from "@odoo/hoot";
import { queryAllTexts, waitFor } from "@odoo/hoot-dom";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { onRpc } from "@web/../tests/web_test_helpers";

setupInteractionWhiteList([
    "website_sale.product_categories",
    "website_sale.product_categories_menu",
]);

describe.current.tags("interaction_dev");

async function getRequestedCategoryIds(request) {
    const { params } = JSON.parse(new TextDecoder().decode(await request.arrayBuffer()));
    return params.category_ids;
}

function getCategoryData(categoryId, childCategories = []) {
    return {
        category: { id: categoryId, name: `Category ${categoryId}`, url: "#", unpublished: false },
        child_categories: childCategories,
    };
}

/**
 * Mock the route, with the given top-level categories, every category having one child.
 */
function mockRoute(topCategoryIds = []) {
    onRpc("/website_sale/snippet/product_categories", async (request) => ({
        categories: Object.fromEntries(
            (await getRequestedCategoryIds(request)).map((categoryId) => [
                categoryId,
                getCategoryData(categoryId, [
                    { id: 10 + categoryId, name: `Child ${categoryId}`, url: "#" },
                ]),
            ])
        ),
        top_category_ids: topCategoryIds,
    }));
}

/**
 * Return the menu of the "Odoo Menu" template, with a column for each given category.
 */
function getMenu(columnCategoryIds) {
    const columns = columnCategoryIds.map(
        (categoryId) => `
            <div
                class="s_product_categories"
                data-parent-category-id="${categoryId}"
                data-show-parent="true"
            ></div>
        `
    );
    return `<div class="row s_product_categories_menu">${columns.join("")}</div>`;
}

test("a menu and its columns fetch their categories in a single call", async () => {
    onRpc("/website_sale/snippet/product_categories", async (request) => {
        expect.step(await getRequestedCategoryIds(request));
        return { categories: {}, top_category_ids: [] };
    });
    await startInteractions(getMenu([1, 2]));
    expect.verifySteps([[1, 2]]);
});

test("snippets with nothing to display are hidden", async () => {
    onRpc("/website_sale/snippet/product_categories", () => ({
        // Category 1 cannot be displayed, category 2 has no child and its heading is hidden
        categories: { 2: getCategoryData(2) },
        top_category_ids: [],
    }));
    await startInteractions(`
        <div class="s_product_categories" data-parent-category-id="1"></div>
        <div class="s_product_categories" data-parent-category-id="2"></div>
    `);
    expect(".s_product_categories:not(.d-none)").toHaveCount(0);
});

test("a menu gets a column for each new top-level category, by sequence", async () => {
    mockRoute([1, 2, 3]);
    await startInteractions(getMenu([1, 3]));
    await waitFor(".s_product_categories[data-parent-category-id='2'] [name='category_heading']");
    expect(queryAllTexts("[name='category_heading']")).toEqual([
        "Category 1",
        "Category 2",
        "Category 3",
    ]);
});

test("a menu without any column gets a column for each top-level category", async () => {
    mockRoute([1]);
    await startInteractions(`<div class="row s_product_categories_menu"></div>`);
    await waitFor(".s_product_categories[data-parent-category-id='1'] [name='category_heading']");
    expect(queryAllTexts("[name='category_heading']")).toEqual(["Category 1"]);
});
