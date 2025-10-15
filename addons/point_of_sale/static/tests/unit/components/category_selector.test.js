import { expect, test, describe, beforeEach } from "@odoo/hoot";

import { setupPosEnv } from "../utils";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { CategorySelector } from "@point_of_sale/app/components/category_selector/category_selector";
import { PosCategory } from "../data/pos_category.data";
import { definePosModels } from "../data/generate_model_definitions";
import { ProductTemplate } from "../data/product_template.data";
import { PosConfig } from "../data/pos_config.data";

definePosModels();

describe("With restricted categories", () => {
    describe("Without child categories", () => {
        beforeEach(async () => {
            const catDrink = addCategory({ name: "Drinks", sequence: 2 });
            const catFood = addCategory({ name: "Food", sequence: 1 });
            const posConfig = PosConfig._records[0];
            posConfig.iface_available_categ_ids = [catDrink.id, catFood.id];
            posConfig.limit_categories = true;
            addProduct({ name: "Water", pos_categ_id: catDrink.id });
            addProduct({ name: "Burger", pos_categ_id: catFood.id });
            this.pos = await setupPosEnv();

            this.catDrink = this.pos.models["pos.category"].get(catDrink.id);
            this.catFood = this.pos.models["pos.category"].get(catFood.id);

            expect(this.pos.models["pos.category"].getAll().length).toBeGreaterThan(
                this.pos.config.iface_available_categ_ids.length
            ); // All cats are loaded
        });

        test("return root categories sorted by sequence", async () => {
            const comp = await mountWithCleanup(CategorySelector, {});
            const categories = comp.getCategoriesAndSub(this.pos);
            assertCategories(categories, [
                {
                    id: this.catFood.id,
                    name: this.catFood.name,
                    isChildren: true,
                    isSelected: false,
                },
                {
                    id: this.catDrink.id,
                    name: this.catDrink.name,
                    isChildren: true,
                    isSelected: false,
                },
            ]);
        });

        test("mark category as selected", async () => {
            const comp = await mountWithCleanup(CategorySelector, {});
            this.pos.selectedCategory = this.catDrink;
            const categories = comp.getCategoriesAndSub(this.pos);
            assertCategories(categories, [
                {
                    id: this.catFood.id,
                    name: this.catFood.name,
                    isChildren: false,
                    isSelected: false,
                },
                {
                    id: this.catDrink.id,
                    name: this.catDrink.name,
                    isChildren: false,
                    isSelected: true,
                },
            ]);
        });

        test("update selection state when switching between categories", async () => {
            const comp = await mountWithCleanup(CategorySelector, {});
            this.pos.selectedCategory = this.catDrink;
            comp.getCategoriesAndSub(this.pos);
            this.pos.selectedCategory = this.catFood;
            const categories = comp.getCategoriesAndSub(this.pos);

            assertCategories(categories, [
                {
                    id: this.catFood.id,
                    name: this.catFood.name,
                    isChildren: false,
                    isSelected: true,
                },
                {
                    id: this.catDrink.id,
                    name: this.catDrink.name,
                    isChildren: false,
                    isSelected: false,
                },
            ]);
        });

        test("reset to default state when category is unselected", async () => {
            const comp = await mountWithCleanup(CategorySelector, {});
            this.pos.selectedCategory = this.catFood;
            comp.getCategoriesAndSub(this.pos);

            this.pos.selectedCategory = null;
            const categories = comp.getCategoriesAndSub(this.pos);

            assertCategories(categories, [
                {
                    id: this.catFood.id,
                    name: this.catFood.name,
                    isChildren: true,
                    isSelected: false,
                },
                {
                    id: this.catDrink.id,
                    name: this.catDrink.name,
                    isChildren: true,
                    isSelected: false,
                },
            ]);
        });
    });

    describe('With child categories"', () => {
        beforeEach(async () => {
            // Food hierarchy: Food > Burger > Best Burger
            const catFood = addCategory({ name: "Food", sequence: 1 });
            const catBurger = addCategory({ name: "Burger", sequence: 2 });
            const catBestBurger = addCategory({ name: "Best Burger", sequence: 3 });
            const catBestBurgerHidden = addCategory({ name: "Best Burger Hidden", sequence: 3 });
            catFood.child_ids = [catBurger.id];
            catBurger.parent_id = catFood.id;
            catBurger.child_ids = [catBestBurger.id, catBestBurgerHidden.id];
            catBestBurger.parent_id = catBurger.id;
            catBestBurgerHidden.parent_id = catBurger.id;

            // Drinks hierarchy: Drinks > [Soft, Cocktail]
            const catDrink = addCategory({ name: "Drinks", sequence: 4 });
            const catSoft = addCategory({ name: "Soft", sequence: 6 });
            const catCocktail = addCategory({ name: "Cocktail", sequence: 7 });
            catDrink.child_ids = [catCocktail.id, catSoft.id]; // Unordered on purpose
            catSoft.parent_id = catDrink.id;
            catCocktail.parent_id = catDrink.id;
            const product = addProduct({ name: "Demo" });
            product.pos_categ_ids = [
                catFood.id,
                catBurger.id,
                catBestBurger.id,
                catBestBurgerHidden.id,
                catDrink.id,
                catSoft.id,
                catCocktail.id,
            ];
            const posConfig = PosConfig._records[0];
            posConfig.iface_available_categ_ids = [
                catFood.id,
                catBurger.id,
                catBestBurger.id,
                catDrink.id,
                catSoft.id,
                catCocktail.id,
            ]; //exclude catBestBurgerHidden

            posConfig.limit_categories = true;
            this.pos = await setupPosEnv();

            this.catFood = this.pos.models["pos.category"].get(catFood.id);
            this.catBurger = this.pos.models["pos.category"].get(catBurger.id);
            this.catBestBurger = this.pos.models["pos.category"].get(catBestBurger.id);

            this.catDrink = this.pos.models["pos.category"].get(catDrink.id);
            this.catSoft = this.pos.models["pos.category"].get(catSoft.id);
            this.catCocktail = this.pos.models["pos.category"].get(catCocktail.id);
        });

        test("return only root categories when no category is selected", async () => {
            const comp = await mountWithCleanup(CategorySelector, {});
            const categories = comp.getCategoriesAndSub();
            assertCategories(categories, [
                { id: this.catFood.id, name: "Food", isChildren: true, isSelected: false },
                { id: this.catDrink.id, name: "Drinks", isChildren: true, isSelected: false },
            ]);
        });

        test("show immediate children when root category is selected", async () => {
            const comp = await mountWithCleanup(CategorySelector, {});
            this.pos.selectedCategory = this.catFood;
            const categories = comp.getCategoriesAndSub();

            assertCategories(categories, [
                { id: this.catFood.id, name: "Food", isChildren: false, isSelected: true },
                { id: this.catDrink.id, name: "Drinks", isChildren: false, isSelected: false },
                { id: this.catBurger.id, name: "Burger", isChildren: true, isSelected: false },
            ]);
        });

        test("show parent categories when second-level category is selected", async () => {
            const comp = await mountWithCleanup(CategorySelector, {});
            this.pos.selectedCategory = this.catBurger;
            const categories = comp.getCategoriesAndSub();

            assertCategories(categories, [
                { id: this.catFood.id, name: "Food", isChildren: false, isSelected: true },
                { id: this.catDrink.id, name: "Drinks", isChildren: false, isSelected: false },
                { id: this.catBurger.id, name: "Burger", isChildren: false, isSelected: true },
                {
                    id: this.catBestBurger.id,
                    name: "Best Burger",
                    isChildren: true,
                    isSelected: false,
                },
            ]);
        });

        test("show parent categories when third-level category is selected", async () => {
            const comp = await mountWithCleanup(CategorySelector, {});
            this.pos.selectedCategory = this.catBestBurger;
            const categories = comp.getCategoriesAndSub();

            assertCategories(categories, [
                { id: this.catFood.id, name: "Food", isChildren: false, isSelected: true },
                { id: this.catDrink.id, name: "Drinks", isChildren: false, isSelected: false },
                { id: this.catBurger.id, name: "Burger", isChildren: false, isSelected: true },
                {
                    id: this.catBestBurger.id,
                    name: "Best Burger",
                    isChildren: false,
                    isSelected: true,
                },
            ]);
        });

        test("show children sorted by sequence when parent is selected", async () => {
            const comp = await mountWithCleanup(CategorySelector, {});
            this.pos.selectedCategory = this.catDrink;
            const categories = comp.getCategoriesAndSub();

            // Soft (sequence: 6) should come before Cocktail (sequence: 7)
            expect(this.catSoft.sequence).toBeLessThan(this.catCocktail.sequence);
            assertCategories(categories, [
                { id: this.catFood.id, name: "Food", isChildren: false, isSelected: false },
                { id: this.catDrink.id, name: "Drinks", isChildren: false, isSelected: true },
                { id: this.catSoft.id, name: "Soft", isChildren: true, isSelected: false },
                { id: this.catCocktail.id, name: "Cocktail", isChildren: true, isSelected: false },
            ]);
        });

        test("switch to different category", async () => {
            const comp = await mountWithCleanup(CategorySelector, {});
            this.pos.selectedCategory = this.catCocktail;
            const categories = comp.getCategoriesAndSub();

            assertCategories(categories, [
                { id: this.catFood.id, name: "Food", isChildren: false, isSelected: false },
                { id: this.catDrink.id, name: "Drinks", isChildren: false, isSelected: true },
                { id: this.catSoft.id, name: "Soft", isChildren: false, isSelected: false },
                { id: this.catCocktail.id, name: "Cocktail", isChildren: false, isSelected: true },
            ]);
        });
    });
});

describe("Without restricted categories", () => {
    beforeEach(async () => {
        const posConfig = PosConfig._records[0];
        posConfig.iface_available_categ_ids = false;
        posConfig.limit_categories = true;

        const catFood = addCategory({ name: "Food", sequence: 1 });
        const catBurger = addCategory({ name: "Burger", sequence: 2 });
        catFood.child_ids = [catBurger.id];
        catBurger.parent_id = catFood.id;

        const product = addProduct({ name: "Demo" });
        product.pos_categ_ids = [catBurger.id, catFood.id];
        this.pos = await setupPosEnv();

        this.catFood = this.pos.models["pos.category"].get(catFood.id);
        this.catBurger = this.pos.models["pos.category"].get(catBurger.id);
    });

    test("root categories", async () => {
        const comp = await mountWithCleanup(CategorySelector, {});
        const categories = comp
            .getCategoriesAndSub()
            .filter((c) => c.id === this.catFood.id || c.id === this.catBurger.id);
        expect(categories.length).toBe(1);

        assertCategories(categories, [
            { id: this.catFood.id, name: "Food", isChildren: true, isSelected: false },
        ]);
    });

    test("select parent category", async () => {
        const comp = await mountWithCleanup(CategorySelector, {});
        this.pos.selectedCategory = this.catFood;
        const categories = comp
            .getCategoriesAndSub()
            .filter((c) => c.id === this.catFood.id || c.id === this.catBurger.id);

        assertCategories(categories, [
            { id: this.catFood.id, name: "Food", isChildren: false, isSelected: true },
            { id: this.catBurger.id, name: "Burger", isChildren: true, isSelected: false },
        ]);
    });

    test("select child category", async () => {
        const comp = await mountWithCleanup(CategorySelector, {});
        this.pos.selectedCategory = this.catBurger;
        const categories = comp
            .getCategoriesAndSub()
            .filter((c) => c.id === this.catFood.id || c.id === this.catBurger.id);

        assertCategories(categories, [
            { id: this.catFood.id, name: "Food", isChildren: false, isSelected: true },
            { id: this.catBurger.id, name: "Burger", isChildren: false, isSelected: true },
        ]);
    });
});

// Helper functions
function assertCategory(category, expected) {
    expect(category.id).toBe(expected.id);
    expect(category.name).toBe(expected.name);
    expect(category.isChildren).toBe(expected.isChildren);
    expect(category.isSelected).toBe(expected.isSelected);
}

function assertCategories(categories, expectedCategories) {
    expect(categories.length).toBe(expectedCategories.length);
    expectedCategories.forEach((expected, index) => {
        assertCategory(categories[index], expected);
    });
}

let productId = 900;

function addProduct({ name, pos_categ_id, price = 10 }) {
    const record = {
        id: productId++,
        name: name,
        display_name: name,
        list_price: price,
        standard_price: price,
        type: "consu",
        pos_categ_ids: [pos_categ_id],
        available_in_pos: true,
        active: true,
    };

    ProductTemplate._records.push(record);
    return record;
}

let catId = 100;
function addCategory({ name, parent_id = false, child_ids = [], sequence = 1 }) {
    const record = {
        id: catId++,
        name: name,
        sequence: sequence,
        parent_id: parent_id,
        child_ids: child_ids,
        has_image: false,
    };
    PosCategory._records.push(record);
    return record;
}
