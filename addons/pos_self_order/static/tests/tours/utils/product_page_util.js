import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import { negateStep } from "@point_of_sale/../tests/generic_helpers/utils";

export function clickProduct(productName) {
    return {
        content: `Click on product '${productName}'`,
        trigger: `.o_self_product_box span:contains('${productName}')`,
        run: "click",
    };
}
export function clickCategory(categoryName) {
    return {
        content: `Click on category '${categoryName}'`,
        trigger: `.category_btn:contains('${categoryName}')`,
        run: "click",
    };
}

export function clickChildCategory(childCategoryName) {
    return {
        content: `Click on child category '${childCategoryName}'`,
        trigger: `.child_category_btn:contains('${childCategoryName}')`,
        run: "click",
    };
}

export function waitProduct(productName) {
    return {
        content: `Wait for product '${productName}'`,
        trigger: `.o_self_product_box span:contains('${productName}')`,
    };
}

export function checkReferenceNotInProductName(productName, reference) {
    return {
        content: `Check product label has '${productName}' and not ${reference}`,
        trigger: `.o_self_product_box span:contains('${productName}'):not(:contains("${reference}"))`,
    };
}

export function clickBack() {
    return {
        content: `Click on back button`,
        trigger: `.btn.btn-back`,
        run: "click",
    };
}

export function clickCancel() {
    return [
        {
            content: `Click on Cancel button`,
            trigger: `.btn.btn-cancel`,
            run: "click",
        },
        {
            content: `Click on button Cancel Order`,
            trigger: `.btn.btn-primary:contains('Cancel Order')`,
            run: "click",
        },
    ];
}

export function clickDiscard() {
    return {
        content: "Click on Discard button",
        trigger: ".btn.btn-link .oi-close",
        run: "click",
    };
}

export function setupAttribute(attributes, addToCart = true) {
    const steps = [];
    if (addToCart) {
        steps.push({
            content: `Click on 'Add to cart' button`,
            trigger: `.btn.btn-primary`,
            run: "click",
        });
    }

    for (const attr of attributes) {
        steps.unshift({
            content: `Select value ${attr.value} for attribute ${attr.name}`,
            trigger: `h2:contains("${attr.name}") + div.row button:contains("${attr.value}")`,
            run: "click",
        });
    }

    return steps;
}

export function verifyIsCheckedAttribute(attribute, values = []) {
    return {
        content: `Select value for attribute ${attribute}`,
        trigger: `div h2:contains("${attribute}")`,
        run: () => {
            const attributesValues = Array.from(document.querySelectorAll("div h2")).find((el) =>
                el.textContent.includes(attribute)
            );
            if (!attributesValues) {
                throw Error(`${attribute} not found.`);
            }
            const rowDiv = attributesValues.nextElementSibling;
            if (!rowDiv || !rowDiv.matches("div.row")) {
                throw Error("Sibling div.row not found or is incorrect.");
            }

            const selectedButtons = rowDiv.querySelectorAll(".border-primary");
            // Extract text content of selected buttons
            const selectedValues = Array.from(selectedButtons).map((btn) =>
                btn.querySelector("span")?.textContent.trim()
            );

            // Check if all expected values are selected
            for (const val of values) {
                if (!selectedValues.includes(val)) {
                    throw new Error(
                        `Expected value "${val}" for attribute "${attribute}" is not selected.`
                    );
                }
            }

            // Optionally, verify that no unexpected values are selected
            if (selectedValues.length !== values.length) {
                throw new Error(
                    `Mismatch in selected values for attribute "${attribute}". Expected: ${values.join(
                        ", "
                    )}, Found: ${selectedValues.join(", ")}`
                );
            }
        },
    };
}

export function clickComboProduct(productName) {
    return {
        content: `Click on combo product '${productName}'`,
        trigger: `.combo_product_box span:contains('${productName}')`,
        run: "click",
    };
}

export function setupCombo(products, addToCart = true) {
    const steps = [];

    for (const product of products) {
        steps.push(clickComboProduct(product.product));

        if (product.attributes.length > 0) {
            Utils.checkMissingRequiredsExists();
            steps.push(...setupAttribute(product.attributes));
            negateStep(Utils.checkMissingRequiredsExists());
        }
    }

    if (addToCart) {
        steps.push({
            content: `Click on 'Add to cart' button`,
            trigger: `.btn.btn-primary`,
            run: "click",
        });
    }

    return steps;
}

export function checkProductOutOfStock(productName) {
    return {
        content: `Check if '${productName}' is marked as out of stock`,
        trigger: `.o_self_product_box:has(span:contains('${productName}')):has(div:contains('Out of stock'))`,
    };
}

export function checkProductLoaded(productName) {
    return {
        content: `Check product '${productName}' is loaded`,
        trigger: `.product_container .o_self_product_box .self_order_product_name > span:contains('${productName}')`,
    };
}

export function checkProductNotLoaded(productName) {
    const selector = ".product_container .o_self_product_box .self_order_product_name > span";
    return {
        content: `Check product '${productName}' is not loaded`,
        trigger: selector,
        run: () => {
            const productElements = document.querySelectorAll(selector);
            const texts = productElements?.values().map((el) => el.textContent.trim());
            if (texts && texts.some((text) => text === productName.trim())) {
                throw Error(`Product ${productName} should not be loaded.`);
            }
        },
    };
}

export function checkCategoryButtonNotLoaded(categoryName) {
    const selector = ".category_container .category_btn span";
    return {
        content: `Check category '${categoryName}' is not loaded`,
        trigger: selector,
        run: () => {
            const categoryElements = document.querySelectorAll(selector);
            const texts = categoryElements?.values().map((el) => el.textContent.trim());
            if (texts && texts.some((text) => text === categoryName.trim())) {
                throw Error(`Category ${categoryName} should not be loaded.`);
            }
        },
    };
}

export function checkActiveCategoryButton(categoryName) {
    return {
        content: `Check active category is '${categoryName}'`,
        trigger: `.category_container .category_btn > div.text-bg-primary > span:contains('${categoryName}')`,
    };
}

export function checkActiveSubcategoryButton(categoryName) {
    return {
        content: `Check active category is '${categoryName}'`,
        trigger:
            categoryName === "All"
                ? ".sub_category_container .child_category_all.btn-light"
                : `.sub_category_container .child_category_btn.btn-light > span:contains('${categoryName}')`,
    };
}

export function clickOnCategory(categoryName) {
    return {
        content: `Click on category '${categoryName}'`,
        trigger: `.category_container .category_btn span:contains('${categoryName}')`,
        run: "click",
    };
}

export function clickOnCategoryNotLoaded(categoryName) {
    return [
        {
            content: "Open category list",
            trigger: ".category_container .category_end .fa-list-ul",
            run: "click",
        },
        {
            content: `Click on ${categoryName} category`,
            trigger: `.modal .modal-body > div:contains('${categoryName}')`,
            run: "click",
        },
    ];
}

export function clickOnSubcategory(categoryName) {
    return {
        content: `Click on subcategory '${categoryName}'`,
        trigger:
            categoryName === "All"
                ? ".sub_category_container .child_category_all"
                : `.sub_category_container .child_category_btn > span:contains('${categoryName}')`,
        run: "click",
    };
}

export function checkCategoryLoaded(categoryName) {
    return {
        content: `Check category '${categoryName}' is loaded`,
        trigger: `.product_container .product_list_category:contains('${categoryName}')`,
    };
}

export function checkCategoryNotLoaded(categoryName) {
    return {
        content: `Check category '${categoryName}' is not loaded`,
        trigger: ".product_container",
        run: () => {
            const categoryElements = document.querySelectorAll(
                ".product_container .product_list_category"
            );
            const texts = Array.from(categoryElements).map((el) => el.textContent.trim());
            if (texts && texts.some((text) => text === categoryName.trim())) {
                throw Error(`Category ${categoryName} should not be loaded.`);
            }
        },
    };
}
