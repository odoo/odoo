import { startInteractions } from "@web/../tests/public/helpers";
import { expect, test } from "@odoo/hoot";
import { queryAll, queryOne } from "@odoo/hoot-dom";
import { rewrapDynamicSnippet } from "@website/js/content/wrap_dynamic_snippet";

test("rewrap dynamic snippet adapts the number of elements depending on the size", async () => {
    const item = (i) => `
        <div class="carousel-item g-3${
            i === 1 ? " active" : ""
        }" data-rewrap-row-limit="16" data-rewrap-row-number-of-elements="3" data-rewrap-row-number-of-elements-small-devices="2">
            <div class="s_dynamic_snippet_row row g-3 ">
                <div class="d-flex flex-grow-0 flex-shrink-0 col-3" data-rewrap-col="col-3" data-dynamic-carousel-item="">
                    <span class="test-carousel-item" data-item-num="${i}">Content ${i}</span>
                </div>
            </div>
        </div>
        `;
    const itemIds = [1, 2, 3, 4, 5];
    await startInteractions(`
        <div class="test-root">
            <div class="carousel" data-limit="16" data-row-per-slide="1" data-bs-interval="5000" data-bs-ride="carousel" style="--o-carousel-chunk-size: 4;" data-number-of-elements="3" data-number-of-elements-small-device="2">
                <div class="carousel-inner w-100 mx-auto">
                    ${itemIds.map((i) => item(i)).join("")}
                </div>
            </div>
        </div>
    `);

    expect(queryAll(`.test-carousel-item`).map((el) => parseInt(el.dataset.itemNum))).toEqual(
        itemIds
    );

    rewrapDynamicSnippet(queryOne(".test-root"), false);
    expect(".carousel-item.active").toHaveCount(1);
    expect(".carousel-item.active .test-carousel-item").toHaveCount(3);
    expect(queryAll(`.test-carousel-item`).map((el) => parseInt(el.dataset.itemNum))).toEqual(
        itemIds
    );

    rewrapDynamicSnippet(queryOne(".test-root"), true);
    expect(".carousel-item.active").toHaveCount(1);
    expect(".carousel-item.active .test-carousel-item").toHaveCount(2);
    expect(queryAll(`.test-carousel-item`).map((el) => parseInt(el.dataset.itemNum))).toEqual(
        itemIds
    );
});

test("rewrap dynamic snippet hides arrow and disables riding if the number of elements is too low", async () => {
    const item = (i) => `
        <div class="carousel-item g-3${
            i === 1 ? " active" : ""
        }" data-rewrap-row-limit="16" data-rewrap-row-number-of-elements="5" data-rewrap-row-number-of-elements-small-devices="2">
            <div class="s_dynamic_snippet_row row g-3 ">
                <div class="d-flex flex-grow-0 flex-shrink-0 col-3" data-rewrap-col="col-3" data-dynamic-carousel-item="">
                    <span class="test-carousel-item" data-item-num="${i}">Content ${i}</span>
                </div>
            </div>
        </div>
        `;
    const itemIds = [1, 2, 3, 4, 5];
    await startInteractions(`
        <div class="test-root">
            <div class="carousel" data-limit="16" data-row-per-slide="1" data-bs-interval="5000" data-bs-ride="carousel" style="--o-carousel-chunk-size: 4;" data-number-of-elements="5" data-number-of-elements-small-device="2">
                <div class="s_dynamic_snippet_arrows"/>
                <div class="carousel-inner w-100 mx-auto">
                    ${itemIds.map((i) => item(i)).join("")}
                </div>
            </div>
        </div>
    `);

    rewrapDynamicSnippet(queryOne(".test-root"), false);
    expect(".s_dynamic_snippet_arrows").toHaveClass("d-none");
    expect(".carousel").toHaveAttribute("data-bs-ride", "false");

    rewrapDynamicSnippet(queryOne(".test-root"), true);
    expect(".s_dynamic_snippet_arrows").not.toHaveClass("d-none");
    expect(".carousel").toHaveAttribute("data-bs-ride", "carousel");
});
