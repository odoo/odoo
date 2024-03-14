/** @odoo-module **/

import { createRelatedModels } from "@point_of_sale/app/models/related_models";

QUnit.module("models with backlinks", () => {
    QUnit.module("many2one/one2many field relations to other models", (hooks) => {
        let models;

        hooks.beforeEach(() => {
            models = createRelatedModels({
                "product.product": {
                    category_id: { type: "many2one", relation: "product.category" },
                },
                "product.category": {
                    product_ids: {
                        type: "one2many",
                        relation: "product.product",
                        inverse_name: "category_id",
                    },
                },
            }).models;
        });

        QUnit.test("create operation", (assert) => {
            const category = models["product.category"].create({});
            const product = models["product.product"].create({ category_id: category });
            assert.ok(product, "Product should be created");
            assert.equal(product.category_id, category, "Product should belong to the category");
            assert.ok(
                category.product_ids.includes(product),
                "Product should be linked to the category"
            );
        });

        QUnit.test("read operation", (assert) => {
            const c1 = models["product.category"].create({});
            const c2 = models["product.category"].create({});
            const p1 = models["product.product"].create({ category_id: c1 });
            const p2 = models["product.product"].create({ category_id: c1 });
            const p3 = models["product.product"].create({ category_id: c2 });

            // Test reading back the categories directly
            const readC1 = models["product.category"].read(c1.id);
            assert.deepEqual(
                readC1,
                c1,
                "Category 1 should be found and match the created category"
            );
            const readP1 = models["product.product"].read(p1.id);
            assert.deepEqual(readP1, p1, "Product 1 should be found and match the created product");

            // Test the one2many relationship from category to products
            assert.ok(
                readC1.product_ids.includes(p1) && readC1.product_ids.includes(p2),
                "Category 1 should include Product 1 and Product 2"
            );

            // Test the many2one relationship from products to category
            assert.equal(readP1.category_id, c1, "Product 3 should belong to Category 2");

            // Additional checks for completeness
            //todo: make readAll/getAll available

            const readMany = models["product.product"].readMany([p2.id, p3.id]);
            assert.deepEqual(readMany, [p2, p3], "Multiple products should be found");

            const readNonExistent = models["product.product"].read(9999);
            assert.equal(
                readNonExistent,
                undefined,
                "Non-existent product read attempt should return undefined"
            );

            const readNonExistentC = models["product.category"].read(9999);
            assert.equal(
                readNonExistentC,
                undefined,
                "Non-existent category read attempt should return undefined"
            );
        });

        QUnit.test("update operation, many2one", (assert) => {
            const p1 = models["product.product"].create({});
            const p2 = models["product.product"].create({});
            const c1 = models["product.category"].create({});
            p1.update({ category_id: c1 });
            assert.equal(p1.category_id, c1, "Product should be updated with new category");
            assert.ok(c1.product_ids.includes(p1), "Product should be linked to the new category");
            assert.notOk(
                c1.product_ids.includes(p2),
                "Product should be unlinked from the old category"
            );
        });

        QUnit.test("update operation, one2many", (assert) => {
            const p1 = models["product.product"].create({});
            const p2 = models["product.product"].create({});
            const c1 = models["product.category"].create({});
            c1.update({ product_ids: [["link", p1, p2]] });
            assert.ok(c1.product_ids.includes(p1), "Product should be linked to the category");
            assert.ok(c1.product_ids.includes(p2), "Product should be linked to the category");
            assert.equal(p1.category_id, c1, "Product should be updated with new category");
        });

        QUnit.test("update operation, unlink many2one", (assert) => {
            const p1 = models["product.product"].create({ category_id: {} });
            const c1 = p1.category_id;
            assert.ok(c1, "Product should be linked to the category");
            assert.deepEqual(c1.product_ids, [p1], "Category should be linked to the product");

            p1.update({ category_id: undefined });
            assert.equal(p1.category_id, undefined, "Product should be unlinked from the category");
            assert.notOk(
                c1.product_ids.includes(p1),
                "Product should be unlinked from the category"
            );
        });

        QUnit.test("update operation, unlink one2many", (assert) => {
            const p1 = models["product.product"].create({});
            const c1 = models["product.category"].create({});
            c1.update({ product_ids: [["link", p1]] });
            assert.ok(c1.product_ids.includes(p1), "Product should be linked to the category");
            assert.equal(p1.category_id, c1, "Product should be linked to the category");

            c1.update({ product_ids: [["unlink", p1]] });
            assert.notOk(
                c1.product_ids.includes(p1),
                "Product should be unlinked from the category"
            );
            assert.equal(p1.category_id, undefined, "Product should be unlinked from the category");
        });

        QUnit.test("update operation, Clear one2many", (assert) => {
            const category = models["product.category"].create({});
            models["product.product"].create({ name: "Product 1", category_id: category });
            models["product.product"].create({ name: "Product 2", category_id: category });
            models["product.category"].update(category, { product_ids: [["clear"]] });
            const updatedCategory = models["product.category"].read(category.id);
            assert.equal(
                updatedCategory.product_ids.length,
                0,
                "All products should be unlinked from the category"
            );
        });

        QUnit.test("update operation, Clear many2one", (assert) => {
            const category = models["product.category"].create({});
            const product = models["product.product"].create({ category_id: category });
            models["product.product"].update(product, { category_id: undefined });
            const updatedCategory = models["product.category"].read(category.id);
            assert.equal(
                updatedCategory.product_ids.length,
                0,
                "All products should be unlinked from the category"
            );
        });

        QUnit.test("delete operation, one2many item", (assert) => {
            const p1 = models["product.product"].create({});
            const p2 = models["product.product"].create({});
            const c1 = models["product.category"].create({});
            c1.update({ product_ids: [["link", p1, p2]] });

            assert.ok(c1.product_ids.includes(p1), "Product should be linked to the category");

            p1.delete();
            assert.notOk(models["product.product"].read(p1.id), "Product should be deleted");
            assert.notOk(
                c1.product_ids.includes(p1),
                "Product should be unlinked from the category"
            );
        });

        QUnit.test("delete operation, many2one item", (assert) => {
            const p1 = models["product.product"].create({});
            const c1 = models["product.category"].create({});
            p1.update({ category_id: c1 });

            assert.ok(c1.product_ids.includes(p1), "Product should be linked to the category");

            c1.delete();
            assert.notOk(models["product.category"].read(c1.id), "Category should be deleted");
            assert.equal(p1.category_id, undefined, "Product should be unlinked from the category");
        });
    });

    QUnit.module("many2one/one2many field relations to own model", (hooks) => {
        let models;
        hooks.beforeEach(() => {
            models = createRelatedModels({
                "product.category": {
                    parent_id: { type: "many2one", relation: "product.category" },
                    child_ids: {
                        type: "one2many",
                        relation: "product.category",
                        inverse_name: "parent_id",
                    },
                },
            }).models;
        });

        QUnit.test("create operation", (assert) => {
            const c1 = models["product.category"].create({});
            const c2 = models["product.category"].create({ parent_id: c1 });

            assert.ok(c1, "Category should be created");
            assert.equal(c2.parent_id, c1, "Category should have a parent");
            assert.ok(c1.child_ids.includes(c2), "Product should be linked to the category");
        });

        QUnit.test("read operation", (assert) => {
            const c1 = models["product.category"].create({});
            const c2 = models["product.category"].create({ parent_id: c1 });

            const readC1 = models["product.category"].read(c1.id);
            assert.deepEqual(readC1.child_ids, [c2], "Child category should be found");

            const readC2 = models["product.category"].read(c2.id);
            assert.deepEqual(readC2.parent_id, c1, "Parent category should be found");

            const readMany = models["product.category"].readMany([c1.id, c2.id]);
            assert.deepEqual(readMany, [c1, c2], "Multiple categories should be found");
        });

        QUnit.test("update operation, many2one", (assert) => {
            const c1 = models["product.category"].create({});
            const c2 = models["product.category"].create({});
            const c3 = models["product.category"].create({ parent_id: c1 });
            assert.equal(c3.parent_id, c1, "c3's parent should be c1");
            c3.update({ parent_id: c2 });
            assert.equal(c3.parent_id, c2, "Category should be updated with new parent");
            assert.ok(c2.child_ids.includes(c3), "Category should be linked to the new parent");
            assert.notOk(
                c1.child_ids.includes(c3),
                "Category should be unlinked from the old parent"
            );
        });

        QUnit.test("update operation, one2many", (assert) => {
            const c1 = models["product.category"].create({});
            const c2 = models["product.category"].create({});
            assert.notOk(c1.parent_id, "categories are not yet linked");
            c1.update({ child_ids: [["link", c2]] });
            assert.ok(c1.child_ids.includes(c2), "Category should be linked to the parent");
            assert.equal(c2.parent_id, c1, "Category should be linked to the parent");
        });

        QUnit.test("update operation, unlink many2one", (assert) => {
            const c1 = models["product.category"].create({});
            const c2 = models["product.category"].create({});
            c2.update({ parent_id: c1 });
            assert.ok(c2.parent_id, "Category should be linked to the parent");

            c2.update({ parent_id: undefined });
            assert.notOk(c2.parent_id, "Category should be unlinked from the parent");
            assert.notOk(c1.child_ids.includes(c2), "Category should be unlinked from the parent");
        });

        QUnit.test("update operation, unlink one2many", (assert) => {
            const c1 = models["product.category"].create({});
            const c2 = models["product.category"].create({ parent_id: c1 });
            assert.ok(c1.child_ids.includes(c2), "Category should be linked to the parent");

            c1.update({ child_ids: [["unlink", c2]] });
            assert.notOk(c1.child_ids.includes(c2), "Category should be unlinked from the parent");
            assert.notOk(c2.parent_id, "Category should be unlinked from the parent");
        });

        QUnit.test("update operation, Clear one2many", (assert) => {
            const category = models["product.category"].create({});
            models["product.category"].create({ parent_id: category });
            models["product.category"].create({ parent_id: category });
            assert.ok(category.child_ids.length === 2, "category should have 2 children");
            models["product.category"].update(category, { child_ids: [["clear"]] });
            assert.equal(
                category.child_ids.length,
                0,
                "All child categories should be unlinked from the category"
            );
        });

        QUnit.test("update operation, Clear many2one", (assert) => {
            const category = models["product.category"].create({});
            const category1 = models["product.category"].create({
                parent_id: category,
            });
            assert.ok(category.child_ids.includes(category1), "categories should be linked");
            models["product.category"].update(category1, { parent_id: undefined });
            assert.notOk(
                category.child_ids.includes(category1),
                "All child categories should be unlinked from the category"
            );
        });

        QUnit.test("delete operation, one2many item", (assert) => {
            const c1 = models["product.category"].create({});
            const c2 = models["product.category"].create({ parent_id: c1 });

            assert.ok(c1.child_ids.includes(c2), "Category should be linked to the parent");

            c2.delete();
            assert.notOk(models["product.category"].read(c2.id), "Category should be deleted");
            assert.notOk(c1.child_ids.includes(c2), "Category should be unlinked from the parent");
        });

        QUnit.test("delete operation, many2one item", (assert) => {
            const c1 = models["product.category"].create({});
            const c2 = models["product.category"].create({ parent_id: c1 });

            assert.ok(c1.child_ids.includes(c2), "Category should be linked to the parent");

            c1.delete();
            assert.notOk(models["product.category"].read(c1.id), "Category should be deleted");
            assert.equal(c2.parent_id, undefined, "Category should be unlinked from the parent");
        });
    });

    QUnit.module("many2many field relations to other models", (hooks) => {
        let models;
        hooks.beforeEach(() => {
            models = createRelatedModels({
                "product.product": {
                    name: { type: "char" },
                    tag_ids: {
                        type: "many2many",
                        relation: "product.tag",
                        relation_table: "product_tag_product_product_rel",
                    },
                },
                "product.tag": {
                    name: { type: "char" },
                    product_ids: {
                        type: "many2many",
                        relation: "product.product",
                        relation_table: "product_tag_product_product_rel",
                    },
                },
            }).models;
        });

        QUnit.test("create operation, create", (assert) => {
            const tag1 = { name: "Electronics" };
            const tag2 = { name: "New" };
            const product = models["product.product"].create({
                name: "Smartphone",
                tag_ids: [["create", tag1, tag2]],
            });
            assert.ok(product.tag_ids[0].name, tag1.name, "tag1 should be linked with product");
        });

        QUnit.test("create operation, link", (assert) => {
            const tag1 = models["product.tag"].create({ name: "Electronics" });
            const tag2 = models["product.tag"].create({ name: "New" });
            const product = models["product.product"].create({
                name: "Smartphone",
                tag_ids: [["link", tag1, tag2]],
            });
            assert.ok(product.tag_ids.includes(tag1), "tag1 should be linked with product");
            assert.ok(
                tag1.product_ids.includes(product),
                "Product should be linked with both tags"
            );
        });

        QUnit.test("read operation", (assert) => {
            const p1 = models["product.product"].create({});
            const p2 = models["product.product"].create({});
            const p3 = models["product.product"].create({});
            const t1 = models["product.tag"].create({ product_ids: [["link", p1, p2, p3]] });
            const t2 = models["product.tag"].create({ product_ids: [["link", p1, p2]] });
            // Test reading back the tags directly
            const readT1 = models["product.tag"].read(t1.id);
            assert.deepEqual(readT1, t1, "Tag 1 should be found and match the created tag");
            const readP1 = models["product.product"].read(p1.id);
            assert.deepEqual(readP1, p1, "Product should be found");
            // Test the many2many relationship
            assert.ok(readT1.product_ids.includes(p1), "Product 1 should belong to Tag 1");
            assert.ok(readT1.product_ids.includes(p2), "Product 2 should belong to Tag 1");
            assert.ok(readT1.product_ids.includes(p3), "Product 3 should belong to Tag 1");
            assert.ok(readP1.tag_ids.includes(t1, t2), "Product 1 should belong to Tag 1 and 2");
            const readMany = models["product.product"].readMany([p2.id, p3.id]);
            assert.deepEqual(readMany, [p2, p3], "Multiple products should be found");
        });

        QUnit.test("update operation, many2many", (assert) => {
            const p1 = models["product.product"].create({});
            const p2 = models["product.product"].create({});
            const t1 = models["product.tag"].create({});
            assert.notOk(p1.tag_ids.includes(t1), "product and tag not yet linked");
            p1.update({ tag_ids: [["link", t1]] });
            assert.ok(p1.tag_ids.includes(t1), "Product should be updated with new tag");
            assert.ok(t1.product_ids.includes(p1), "Product should be linked to the new tag");
            assert.notOk(t1.product_ids.includes(p2), "t1 shouldn't be linked to p2");
            t1.update({ product_ids: [["link", p2]] });
            assert.ok(t1.product_ids.includes(p2), "Product should be linked to the tag");
        });

        QUnit.test("update operation, unlink many2many", (assert) => {
            const p1 = models["product.product"].create({});
            const t1 = models["product.tag"].create({});

            t1.update({ product_ids: [["link", p1]] });
            assert.ok(t1.product_ids.includes(p1), "Product should be linked to the tag");
            assert.ok(p1.tag_ids.includes(t1), "Product should be linked to the tag");

            t1.update({ product_ids: [["unlink", p1]] });
            assert.notOk(t1.product_ids.includes(p1), "Product should be unlinked from the tag");
            assert.notOk(p1.tag_ids.length > 0, "Product should be unlinked from the tag");
        });

        QUnit.test("update operation, Clear many2many", (assert) => {
            const tag1 = models["product.tag"].create({});
            const tag2 = models["product.tag"].create({});
            const product = models["product.product"].create({ tag_ids: [["link", tag1, tag2]] });
            assert.ok(product.tag_ids.length === 2, "tags are linked to the product");
            product.update({ tag_ids: [["clear"]] });
            assert.equal(product.tag_ids.length, 0, "All tags should be unlinked from the product");
        });

        QUnit.test("delete operation, many2many item", (assert) => {
            const p1 = models["product.product"].create({});
            const p2 = models["product.product"].create({});
            const t1 = models["product.tag"].create({});
            t1.update({ product_ids: [["link", p1, p2]] });

            assert.ok(t1.product_ids.includes(p1), "Product should be linked to the tag");

            p1.delete();
            assert.notOk(models["product.product"].read(p1.id), "Product should be deleted");
            assert.notOk(t1.product_ids.includes(p1), "Product should be unlinked from the tag");
        });
    });

    QUnit.module("many2many field relations to own model", (hooks) => {
        let models;
        hooks.beforeEach(() => {
            models = createRelatedModels({
                "note.note": {
                    name: { type: "char" },
                    parent_ids: {
                        type: "many2many",
                        relation: "note.note",
                        relation_table: "note_note_rel",
                    },
                    child_ids: {
                        type: "many2many",
                        relation: "note.note",
                        relation_table: "note_note_rel",
                    },
                },
            }).models;
        });

        QUnit.test("create operation, link", (assert) => {
            const note1 = models["note.note"].create({ name: "Emergency" });
            const note2 = models["note.note"].create({ name: "New" });
            const note = models["note.note"].create({
                name: "To Serve",
                child_ids: [["link", note1, note2]],
            });
            assert.ok(note.child_ids.includes(note1), "note1 should be linked with note");
            assert.ok(note1.parent_ids.includes(note), "note should be linked with note1");
        });

        QUnit.test("read operation", (assert) => {
            const n1 = models["note.note"].create({});
            const n2 = models["note.note"].create({});
            const n3 = models["note.note"].create({});
            const n4 = models["note.note"].create({ parent_ids: [["link", n1, n2, n3]] });
            const n5 = models["note.note"].create({ parent_ids: [["link", n1, n2]] });
            // Test reading back the tags directly
            const readN1 = models["note.note"].read(n1.id);
            assert.deepEqual(readN1, n1, "Note 1 should be found and match the created note");
            const readN4 = models["note.note"].read(n4.id);
            assert.deepEqual(readN4, n4, "Note should be found");
            // Test the many2many relationship
            assert.ok(
                [n1, n2, n3].every((n) => readN4.parent_ids.includes(n)),
                "Note 1 should include Note 1, 2 and 3"
            );
            assert.ok(
                [n4, n5].every((n) => readN1.child_ids.includes(n)),
                "Note 1 should belong to Note 1 and 2"
            );
            const readMany = models["note.note"].readMany([n2.id, n3.id]);
            assert.deepEqual(readMany, [n2, n3], "Multiple notes should be found");
        });

        QUnit.test("update operation, many2many", (assert) => {
            const n1 = models["note.note"].create({});
            const n2 = models["note.note"].create({});
            const n3 = models["note.note"].create({});
            n1.update({ parent_ids: [["link", n3]] });
            assert.ok(n1.parent_ids.includes(n3), "Note should be updated with new parent");
            assert.ok(n3.child_ids.includes(n1), "Note should be linked to the new child");
            n3.update({ parent_ids: [["link", n2]] });
            assert.ok(n3.parent_ids.includes(n2), "Note should be linked to the new parent");
            n3.update({ parent_ids: [["unlink", n2]] });
            assert.notOk(n3.parent_ids.includes(n2), "Note should be unlinked from the old parent");
            assert.notOk(n2.child_ids.includes(n3), "Note should be unlinked from the old child");
        });

        QUnit.test("update operation, unlink many2many", (assert) => {
            const n1 = models["note.note"].create({});
            const n2 = models["note.note"].create({});

            n2.update({ parent_ids: [["link", n1]] });
            assert.ok(n2.parent_ids.includes(n1), "Note should be linked to the tag");
            assert.ok(n1.child_ids.includes(n2), "Note should be linked to the tag");

            n2.update({ parent_ids: [["unlink", n1]] });
            assert.notOk(n2.parent_ids.includes(n1), "Note should be unlinked from the tag");
            assert.notOk(n1.child_ids.length > 0, "Note should be unlinked from the tag");
            assert.ok(n2, "Note should be linked to the tag");
        });

        QUnit.test("update operation, Clear many2many", (assert) => {
            const note = models["note.note"].create({});
            const note2 = models["note.note"].create({});
            const note3 = models["note.note"].create({ parent_ids: [["link", note, note2]] });
            assert.equal(note3.parent_ids.length, 2, "note 3 should have parent notes");
            models["note.note"].update(note3, { parent_ids: [["clear"]] });
            assert.equal(
                note3.parent_ids.length,
                0,
                "All parent notes should be unlinked from the note"
            );
            assert.equal(
                note.child_ids.length,
                0,
                "All child notes should be unlinked from the note"
            );
        });

        QUnit.test("delete operation, many2many item", (assert) => {
            const n1 = models["note.note"].create({});
            const n2 = models["note.note"].create({});
            const n3 = models["note.note"].create({});
            n3.update({ parent_ids: [["link", n1, n2]] });

            assert.ok(
                [n1, n2].every((n) => n3.parent_ids.includes(n)),
                "Note should be linked to the parent nodes 1 and 2"
            );

            n1.delete();
            assert.notOk(models["note.note"].read(n1.id), "Note should be deleted");
            assert.notOk(n3.parent_ids.includes(n1), "Note 1 should be unlinked from note 3");
        });
    });
});

QUnit.module("models without backlinks", () => {
    QUnit.module("many2one/one2many field relations to other models", (hooks) => {
        let models;

        hooks.beforeEach(() => {
            models = createRelatedModels({
                "product.product": {
                    category_id: { type: "many2one", relation: "product.category" },
                },
                "product.category": {},
            }).models;
        });

        QUnit.test("create operation", (assert) => {
            const category = models["product.category"].create({});
            const product = models["product.product"].create({ category_id: category });
            assert.equal(product.category_id, category, "Product should belong to the category");
            assert.deepEqual(
                category["<-product.product.category_id"],
                [product],
                "Backlink should be updated"
            );
        });

        QUnit.test("read operation", (assert) => {
            const c1 = models["product.category"].create({});
            const p1 = models["product.product"].create({ category_id: c1 });
            const p2 = models["product.product"].create({ category_id: c1 });

            // Test reading back the categories directly
            const readC1 = models["product.category"].read(c1.id);
            assert.deepEqual(
                readC1,
                c1,
                "Category 1 should be found and match the created category"
            );
            const readP1 = models["product.product"].read(p1.id);
            assert.deepEqual(readP1, p1, "Product should be found");

            // Test the one2many relationship from category to products
            assert.deepEqual(
                readC1["<-product.product.category_id"],
                [p1, p2],
                "Category 1 should have a backlink to Product 1 and Product 2"
            );

            // Test the many2one relationship from products to category
            assert.equal(readP1.category_id, c1, "Product 3 should belong to Category 2");
        });

        QUnit.test("update operation, many2one", (assert) => {
            const p1 = models["product.product"].create({});
            const c1 = models["product.category"].create({});
            assert.notOk(p1.category_id, "product and category is not linked");
            p1.update({ category_id: c1 });
            assert.equal(p1.category_id, c1, "Product should be updated with new category");
            assert.deepEqual(
                c1["<-product.product.category_id"],
                [p1],
                "Product should be backlinked to the new category"
            );
        });

        QUnit.test("update operation, unlink many2one", (assert) => {
            const p1 = models["product.product"].create({ category_id: {} });
            const c1 = p1.category_id;
            assert.ok(c1, "Product should be linked to the category");
            assert.deepEqual(
                c1["<-product.product.category_id"],
                [p1],
                "Category should be linked to the product"
            );

            p1.update({ category_id: undefined });
            assert.equal(p1.category_id, undefined, "Product should be unlinked from the category");
            assert.notOk(
                c1["<-product.product.category_id"].length > 0,
                "Product should be unlinked from the category"
            );
        });

        QUnit.test("delete operation, many2one item", (assert) => {
            const p1 = models["product.product"].create({});
            const c1 = models["product.category"].create({});
            p1.update({ category_id: c1 });

            assert.deepEqual(
                c1["<-product.product.category_id"],
                [p1],
                "Product should be linked to the category"
            );

            c1.delete();
            assert.notOk(models["product.category"].read(c1.id), "Category should be deleted");
            assert.equal(p1.category_id, undefined, "Product should be unlinked from the category");
        });
    });

    QUnit.module("many2many relations", (hooks) => {
        let models;
        hooks.beforeEach(() => {
            models = createRelatedModels({
                "product.product": {
                    tag_ids: {
                        type: "many2many",
                        relation: "product.tag",
                        relation_table: "product_tag_product_product_rel",
                    },
                },
                "product.tag": {},
            }).models;
        });

        QUnit.test("create operation, link", (assert) => {
            const tag1 = models["product.tag"].create({ name: "Electronics" });
            const tag2 = models["product.tag"].create({ name: "New" });
            const product = models["product.product"].create({
                name: "Smartphone",
                tag_ids: [["link", tag1, tag2]],
            });
            assert.ok(product.tag_ids.includes(tag1), "tag1 should be linked with product");
            assert.ok(
                tag1["<-product.product.tag_ids"].includes(product),
                "Product should be linked with both tags"
            );
        });

        QUnit.test("read operation", (assert) => {
            const t1 = models["product.tag"].create({});
            const t2 = models["product.tag"].create({});
            const p1 = models["product.product"].create({ tag_ids: [["link", t1, t2]] });
            const p2 = models["product.product"].create({ tag_ids: [["link", t1, t2]] });
            const p3 = models["product.product"].create({ tag_ids: [["link", t1]] });
            // Test reading back the tags directly
            const readT1 = models["product.tag"].read(t1.id);
            assert.deepEqual(readT1, t1, "Tag 1 should be found and match the created tag");
            const readP1 = models["product.product"].read(p1.id);
            assert.deepEqual(readP1, p1, "Product should be found");
            // Test the many2many relationship
            assert.ok(
                [p1, p2, p3].every((p) => t1["<-product.product.tag_ids"].includes(p)),
                "Tag 1 should include Product 1, 2 and 3"
            );
            assert.ok(
                [t1, t2].every((t) => p1.tag_ids.includes(t)),
                "Product 1 should belong to Tag 1 and 2"
            );
            const readMany = models["product.product"].readMany([p2.id, p3.id]);
            assert.deepEqual(readMany, [p2, p3], "Multiple products should be found");
        });

        QUnit.test("update operation, link", (assert) => {
            const p1 = models["product.product"].create({});
            const p2 = models["product.product"].create({});
            const t1 = models["product.tag"].create({});
            p1.update({ tag_ids: [["link", t1]] });
            assert.ok(p1.tag_ids.includes(t1), "Product should be updated with new tag");
            assert.ok(
                t1["<-product.product.tag_ids"].includes(p1),
                "Product should be linked to the new tag"
            );
            assert.notOk(
                t1["<-product.product.tag_ids"].includes(p2),
                "Product should be unlinked from the old tag"
            );
            p2.update({ tag_ids: [["link", t1]] });
            assert.ok(
                t1["<-product.product.tag_ids"].includes(p2),
                "Product should be linked to the tag"
            );
        });

        QUnit.test("update operation, unlink", (assert) => {
            const p1 = models["product.product"].create({});
            const t1 = models["product.tag"].create({});

            p1.update({ tag_ids: [["link", t1]] });
            assert.ok(
                t1["<-product.product.tag_ids"].includes(p1),
                "Product should be linked to the tag"
            );
            assert.ok(p1.tag_ids.includes(t1), "Product should be linked to the tag");

            p1.update({ tag_ids: [["unlink", t1]] });
            assert.notOk(
                [t1["<-product.product.tag_ids"]].includes(p1),
                "Product should be unlinked from the tag"
            );
            assert.notOk(p1.tag_ids.length > 0, "Product should be unlinked from the tag");
        });

        QUnit.test("update operation, Clear", (assert) => {
            const tag1 = models["product.tag"].create({});
            const tag2 = models["product.tag"].create({});
            const product = models["product.product"].create({ tag_ids: [[tag1, tag2]] });
            models["product.product"].update(product, { tag_ids: [["clear"]] });
            const updatedproduct = models["product.product"].read(product.id);
            assert.equal(
                updatedproduct.tag_ids.length,
                0,
                "All tags should be unlinked from the product"
            );
            models["product.product"].update(product, { tag_ids: [["link", tag1, tag2]] });
            assert.ok(
                [tag1, tag2].every((t) => product.tag_ids.includes(t)),
                "Product should be linked to the tags"
            );
            models["product.product"].update(product, { tag_ids: [["clear"]] });
            assert.notOk(
                [tag1["<-product.product.tag_ids"]].includes(product),
                "All tags should be unlinked from the product"
            );
        });

        QUnit.test("delete operation", (assert) => {
            const p1 = models["product.product"].create({});
            const p2 = models["product.product"].create({});
            const t1 = models["product.tag"].create({});
            p1.update({ tag_ids: [["link", t1]] });
            p2.update({ tag_ids: [["link", t1]] });

            assert.ok(
                t1["<-product.product.tag_ids"].includes(p1),
                "Product should be linked to the tag"
            );

            p1.delete();
            assert.notOk(models["product.product"].read(p1.id), "Product should be deleted");
            assert.notOk(
                t1["<-product.product.tag_ids"].includes(p1),
                "Product should be unlinked from the tag"
            );
            t1.delete();
            assert.notOk(models["product.tag"].read(t1.id), "Tag should be deleted");
            assert.notOk(p1.tag_ids.length > 0, "Product should be unlinked from the tag");
        });
    });
});
