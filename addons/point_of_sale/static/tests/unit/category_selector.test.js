import { expect, test, describe, beforeEach } from "@odoo/hoot";
import { getCategoriesAndSub } from "@point_of_sale/app/components/category_selector/utils";

class MockCategory {
    constructor(props = {}) {
        for (const [key, value] of Object.entries(props)) {
            this[key] = value;
        }
    }

    get allParents() {
        // TODO avoid mock >= 18.3
        const parents = [];
        let parent = this.parent_id;

        if (!parent) {
            return parents;
        }

        while (parent) {
            parents.unshift(parent);
            parent = parent.parent_id;
        }

        return parents.reverse();
    }
}

class FakePos {
    categories = [];
    config = {};
    selectedCategory = null;

    constructor() {
        this.models = {
            "pos.category": {
                getAll: () => this.categories,
            },
        };
    }
}

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

describe("Without restricted categories", () => {
    describe("Without child categories", () => {
        beforeEach(() => {
            this.pos = new FakePos();
            this.food = new MockCategory({ id: 1, name: "Food", parent_id: null, sequence: 1 });
            this.drinks = new MockCategory({ id: 2, name: "Drinks", parent_id: null, sequence: 2 });
            this.pos.categories = [this.drinks, this.food]; // Intentionally unsorted
        });

        test("return root categories sorted by sequence", () => {
            const categories = getCategoriesAndSub(this.pos);
            assertCategories(categories, [
                { id: 1, name: "Food", isChildren: true, isSelected: false },
                { id: 2, name: "Drinks", isChildren: true, isSelected: false },
            ]);
        });

        test("mark category as selected", () => {
            this.pos.selectedCategory = this.drinks;
            const categories = getCategoriesAndSub(this.pos);

            assertCategories(categories, [
                { id: 1, name: "Food", isChildren: false, isSelected: false },
                { id: 2, name: "Drinks", isChildren: false, isSelected: true },
            ]);
        });

        test("update selection state when switching between categories", () => {
            this.pos.selectedCategory = this.drinks;
            getCategoriesAndSub(this.pos);

            this.pos.selectedCategory = this.food;
            const categories = getCategoriesAndSub(this.pos);

            assertCategories(categories, [
                { id: 1, name: "Food", isChildren: false, isSelected: true },
                { id: 2, name: "Drinks", isChildren: false, isSelected: false },
            ]);
        });

        test("reset to default state when category is unselected", () => {
            this.pos.selectedCategory = this.food;
            getCategoriesAndSub(this.pos);

            this.pos.selectedCategory = null;
            const categories = getCategoriesAndSub(this.pos);

            assertCategories(categories, [
                { id: 1, name: "Food", isChildren: true, isSelected: false },
                { id: 2, name: "Drinks", isChildren: true, isSelected: false },
            ]);
        });
    });

    describe('With child categories"', () => {
        beforeEach(() => {
            this.pos = new FakePos();

            // Food hierarchy: Food > Burger > Best Burger
            this.food = new MockCategory({ id: 1, name: "Food", parent_id: null, sequence: 1 });
            this.burger = new MockCategory({
                id: 2,
                name: "Burger",
                parent_id: this.food,
                sequence: 2,
            });
            this.bestBurger = new MockCategory({
                id: 3,
                name: "Best Burger",
                parent_id: this.burger,
                sequence: 3,
            });
            this.food.child_ids = [this.burger];
            this.burger.child_ids = [this.bestBurger];

            // Drinks hierarchy: Drinks > [Soft, Cocktail]
            this.drinks = new MockCategory({ id: 4, name: "Drinks", parent_id: null, sequence: 4 });
            this.soft = new MockCategory({
                id: 6,
                name: "Soft",
                parent_id: this.drinks,
                sequence: 6,
            });
            this.cocktail = new MockCategory({
                id: 5,
                name: "Cocktail",
                parent_id: this.drinks,
                sequence: 7,
            });
            this.drinks.child_ids = [this.cocktail, this.soft];

            this.pos.categories = [
                this.food,
                this.burger,
                this.bestBurger,
                this.drinks,
                this.cocktail, //Unsorted on purpose
                this.soft,
            ];
        });

        test("return only root categories when no category is selected", () => {
            const categories = getCategoriesAndSub(this.pos);

            assertCategories(categories, [
                { id: 1, name: "Food", isChildren: true, isSelected: false },
                { id: 4, name: "Drinks", isChildren: true, isSelected: false },
            ]);
        });

        test("show immediate children when root category is selected", () => {
            this.pos.selectedCategory = this.food;
            const categories = getCategoriesAndSub(this.pos);

            assertCategories(categories, [
                { id: 1, name: "Food", isChildren: false, isSelected: true },
                { id: 4, name: "Drinks", isChildren: false, isSelected: false },
                { id: 2, name: "Burger", isChildren: true, isSelected: false },
            ]);
        });

        test("show parent categories when second-level category is selected", () => {
            this.pos.selectedCategory = this.burger;
            const categories = getCategoriesAndSub(this.pos);

            assertCategories(categories, [
                { id: 1, name: "Food", isChildren: false, isSelected: true },
                { id: 4, name: "Drinks", isChildren: false, isSelected: false },
                { id: 2, name: "Burger", isChildren: false, isSelected: true },
                { id: 3, name: "Best Burger", isChildren: true, isSelected: false },
            ]);
        });

        test("show parent categories when third-level category is selected", () => {
            this.pos.selectedCategory = this.bestBurger;
            const categories = getCategoriesAndSub(this.pos);

            assertCategories(categories, [
                { id: 1, name: "Food", isChildren: false, isSelected: true },
                { id: 4, name: "Drinks", isChildren: false, isSelected: false },
                { id: 2, name: "Burger", isChildren: false, isSelected: true },
                { id: 3, name: "Best Burger", isChildren: false, isSelected: true },
            ]);
        });

        test("show children sorted by sequence when parent is selected", () => {
            this.pos.selectedCategory = this.drinks;
            const categories = getCategoriesAndSub(this.pos);

            // Soft (sequence: 6) should come before Cocktail (sequence: 7)
            assertCategories(categories, [
                { id: 1, name: "Food", isChildren: false, isSelected: false },
                { id: 4, name: "Drinks", isChildren: false, isSelected: true },
                { id: 6, name: "Soft", isChildren: true, isSelected: false },
                { id: 5, name: "Cocktail", isChildren: true, isSelected: false },
            ]);
        });

        test("switch to different category", () => {
            this.pos.selectedCategory = this.cocktail;
            const categories = getCategoriesAndSub(this.pos);

            assertCategories(categories, [
                { id: 1, name: "Food", isChildren: false, isSelected: false },
                { id: 4, name: "Drinks", isChildren: false, isSelected: true },
                { id: 6, name: "Soft", isChildren: false, isSelected: false },
                { id: 5, name: "Cocktail", isChildren: false, isSelected: true },
            ]);
        });
    });
});

describe("With restricted categories", () => {
    describe("Without child categories", () => {
        beforeEach(() => {
            this.pos = new FakePos();
            this.food = new MockCategory({ id: 1, name: "Food", parent_id: null, sequence: 1 });
            this.drinks = new MockCategory({ id: 2, name: "Drinks", parent_id: null, sequence: 3 });
            this.hiddenRoot = new MockCategory({
                id: 3,
                name: "Hidden",
                parent_id: null,
                sequence: 1,
            });

            this.pos.categories = [this.drinks, this.food, this.hiddenRoot]; //All categories are loaded
            this.pos.config.limit_categories = true;
            this.pos.config.iface_available_categ_ids = [this.drinks, this.food];
        });

        test("return only restricted categories", () => {
            const categories = getCategoriesAndSub(this.pos);
            assertCategories(categories, [
                { id: 1, name: "Food", isChildren: true, isSelected: false },
                { id: 2, name: "Drinks", isChildren: true, isSelected: false },
            ]);
        });

        test("select category", () => {
            this.pos.selectedCategory = this.drinks;
            const categories = getCategoriesAndSub(this.pos);
            assertCategories(categories, [
                { id: 1, name: "Food", isChildren: false, isSelected: false },
                { id: 2, name: "Drinks", isChildren: false, isSelected: true },
            ]);
        });
    });

    describe("With sub categories", () => {
        beforeEach(() => {
            this.pos = new FakePos();
            this.food = new MockCategory({ id: 1, name: "Food", parent_id: null, sequence: 1 });
            this.foodHidden = new MockCategory({
                id: 99,
                name: "foodHidden",
                parent_id: this.food,
                sequence: 1,
            });
            this.food.child_ids = [this.foodHidden];

            this.drinks = new MockCategory({ id: 2, name: "Drinks", parent_id: null, sequence: 3 });
            this.soft = new MockCategory({
                id: 6,
                name: "Soft",
                parent_id: this.drinks,
                sequence: 6,
            });
            this.cocktail = new MockCategory({
                id: 5,
                name: "Cocktail",
                parent_id: this.drinks,
                sequence: 7,
            });

            this.drinkHidden = new MockCategory({
                id: 93,
                name: "drinkHidden",
                parent_id: this.drinks,
                sequence: 1,
            });

            this.drinks.child_ids = [this.cocktail, this.soft, this.drinkHidden];

            this.pos.categories = [
                this.drinks,
                this.food,
                this.soft,
                this.cocktail,
                this.drinkHidden,
                this.foodHidden,
            ]; //All categories are loaded
            this.pos.config.limit_categories = true;
            this.pos.config.iface_available_categ_ids = [
                this.drinks,
                this.food,
                this.soft,
                this.cocktail,
            ];
        });

        test("show only restricted sub categories", () => {
            assertCategories(getCategoriesAndSub(this.pos), [
                { id: 1, name: "Food", isChildren: true, isSelected: false },
                { id: 2, name: "Drinks", isChildren: true, isSelected: false },
            ]);

            //select food (the hidden cat is not displayed)
            this.pos.selectedCategory = this.food;
            assertCategories(getCategoriesAndSub(this.pos), [
                { id: 1, name: "Food", isChildren: false, isSelected: true },
                { id: 2, name: "Drinks", isChildren: false, isSelected: false },
            ]);

            //select drink (the hidden cat is not displayed)
            this.pos.selectedCategory = this.drinks;
            assertCategories(getCategoriesAndSub(this.pos), [
                { id: 1, name: "Food", isChildren: false, isSelected: false },
                { id: 2, name: "Drinks", isChildren: false, isSelected: true },
                { id: 6, name: "Soft", isChildren: true, isSelected: false },
                { id: 5, name: "Cocktail", isChildren: true, isSelected: false },
            ]);
        });

        test("show third level category as root if the second level category is hidden", () => {
            this.superDrink = new MockCategory({
                id: 999,
                name: "Super cocktail",
                parent_id: this.cocktail,
                sequence: 999,
            });
            this.cocktail.child_ids = [this.superDrink];

            //cocktail is not available
            this.pos.config.iface_available_categ_ids = [
                this.food,
                this.drinks,
                this.soft,
                this.superDrink,
            ];

            this.pos.categories.push(this.superDrink);

            assertCategories(getCategoriesAndSub(this.pos), [
                { id: 1, name: "Food", isChildren: true, isSelected: false },
                { id: 2, name: "Drinks", isChildren: true, isSelected: false },
                { id: 999, name: "Super cocktail", isChildren: true, isSelected: false },
            ]);
            this.pos.selectedCategory = this.drinks;
            assertCategories(getCategoriesAndSub(this.pos), [
                { id: 1, name: "Food", isChildren: false, isSelected: false },
                { id: 2, name: "Drinks", isChildren: false, isSelected: true },
                { id: 999, name: "Super cocktail", isChildren: false, isSelected: false },
                { id: 6, name: "Soft", isChildren: true, isSelected: false },
            ]);
        });
    });
});
