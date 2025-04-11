import * as ProductPage from "./product_page_util";

export function clickKioskCategory(categoryName) {
    return {
        content: `Click on category '${categoryName}'`,
        trigger: `.category_btn:contains('${categoryName}')`,
        run: "click",
    };
}

export function clickBack() {
    return ProductPage.clickBack;
}

export function clickCancel() {
    return ProductPage.clickCancel();
}
