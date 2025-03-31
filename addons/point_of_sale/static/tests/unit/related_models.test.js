import { describe, expect, test } from "@odoo/hoot";
import { createRelatedModels } from "@point_of_sale/app/models/related_models";

describe("models with backlinks", () => {
    describe("many2one and one2many field relations to other models", () => {
        const getModels = () =>
            createRelatedModels({
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

        test("create operation", () => {
            const models = getModels();
            const category = models["product.category"].create({});
            const product = models["product.product"].create({ category_id: category });
            expect(product.category_id).toBe(category);
            expect(category.product_ids.includes(product)).toBe(true);
        });
        test("read operation", () => {
            const models = getModels();
            const c1 = models["product.category"].create({});
            const c2 = models["product.category"].create({});
            const p1 = models["product.product"].create({ category_id: c1 });
            const p2 = models["product.product"].create({ category_id: c1 });
            const p3 = models["product.product"].create({ category_id: c2 });

            // Test reading back the categories directly
            const readC1 = models["product.category"].read(c1.id);
            expect(readC1).toEqual(c1);

            const readP1 = models["product.product"].read(p1.id);
            expect(readP1).toEqual(p1);

            // Test the one2many relationship from category to products
            expect(readC1.product_ids.includes(p1)).toBe(true);
            expect(readC1.product_ids.includes(p2)).toBe(true);

            // Test the many2one relationship from products to category
            expect(readP1.category_id).toEqual(c1);

            // Additional checks for completeness
            const readMany = models["product.product"].readMany([p2.id, p3.id]);
            expect(readMany).toEqual([p2, p3]);

            const readNonExistent = models["product.product"].read(9999);
            expect(readNonExistent).toBe(undefined);

            const readNonExistentC = models["product.category"].read(9999);
            expect(readNonExistentC).toBe(undefined);
        });

        test("update operation, many2one", () => {
            const models = getModels();
            const p1 = models["product.product"].create({});
            const p2 = models["product.product"].create({});
            const c1 = models["product.category"].create({});

            p1.update({ category_id: c1 });
            expect(p1.category_id).toBe(c1);
            expect(c1.product_ids.includes(p1)).toBe(true);
            expect(c1.product_ids.includes(p2)).toBe(false);
        });

        test("update operation, one2many", () => {
            const models = getModels();
            const p1 = models["product.product"].create({});
            const p2 = models["product.product"].create({});
            const c1 = models["product.category"].create({});

            c1.update({ product_ids: [["link", p1, p2]] });
            expect(c1.product_ids.includes(p1)).toBe(true);
            expect(c1.product_ids.includes(p2)).toBe(true);
            expect(p1.category_id).toBe(c1);
        });

        test("update operation, unlink many2one", () => {
            const models = getModels();
            const p1 = models["product.product"].create({ category_id: {} });
            const c1 = p1.category_id;

            expect(c1.product_ids).toEqual([p1]);

            p1.update({ category_id: undefined });
            expect(p1.category_id).toBe(undefined);
            expect(c1.product_ids.includes(p1)).toBe(false);
        });

        test("update operation, unlink one2many", () => {
            const models = getModels();
            const p1 = models["product.product"].create({});
            const c1 = models["product.category"].create({});

            c1.update({ product_ids: [["link", p1]] });
            expect(c1.product_ids.includes(p1)).toBe(true);
            expect(p1.category_id).toBe(c1);

            c1.update({ product_ids: [["unlink", p1]] });
            expect(c1.product_ids.includes(p1)).toBe(false);
            expect(p1.category_id).toBe(undefined);
        });

        test("update operation, Clear one2many", () => {
            const models = getModels();
            const category = models["product.category"].create({});
            models["product.product"].create({ name: "Product 1", category_id: category });
            models["product.product"].create({ name: "Product 2", category_id: category });

            models["product.category"].update(category, { product_ids: [["clear"]] });
            const updatedCategory = models["product.category"].read(category.id);
            expect(updatedCategory.product_ids.length).toBe(0);
        });

        test("update operation, Clear many2one", () => {
            const models = getModels();
            const category = models["product.category"].create({});
            const product = models["product.product"].create({ category_id: category });

            models["product.product"].update(product, { category_id: undefined });
            const updatedCategory = models["product.category"].read(category.id);
            expect(updatedCategory.product_ids.length).toBe(0);
        });

        test("delete operation, one2many item", () => {
            const models = getModels();
            const p1 = models["product.product"].create({});
            const p2 = models["product.product"].create({});
            const c1 = models["product.category"].create({});

            c1.update({ product_ids: [["link", p1, p2]] });
            expect(c1.product_ids.includes(p1)).toBe(true);

            p1.delete();
            expect(models["product.product"].read(p1.id)).toBe(undefined);
            expect(c1.product_ids.includes(p1)).toBe(false);
        });

        test("delete operation, many2one item", () => {
            const models = getModels();
            const p1 = models["product.product"].create({});
            const c1 = models["product.category"].create({});

            p1.update({ category_id: c1 });
            expect(c1.product_ids.includes(p1)).toBe(true);

            c1.delete();
            expect(models["product.category"].read(c1.id)).toBe(undefined);
            expect(p1.category_id).toBe(undefined);
        });
    });
    describe("many2one/one2many field relations to own model", () => {
        const getModels = () =>
            createRelatedModels({
                "product.category": {
                    parent_id: { type: "many2one", relation: "product.category" },
                    child_ids: {
                        type: "one2many",
                        relation: "product.category",
                        inverse_name: "parent_id",
                    },
                },
            }).models;

        test("create operation", () => {
            const models = getModels();
            const c1 = models["product.category"].create({});
            const c2 = models["product.category"].create({ parent_id: c1 });

            expect(c2.parent_id).toBe(c1);
            expect(c1.child_ids.includes(c2)).toBe(true);
        });

        test("read operation", () => {
            const models = getModels();
            const c1 = models["product.category"].create({});
            const c2 = models["product.category"].create({ parent_id: c1 });

            const readC1 = models["product.category"].read(c1.id);
            expect(readC1.child_ids).toEqual([c2]);

            const readC2 = models["product.category"].read(c2.id);
            expect(readC2.parent_id).toEqual(c1);

            const readMany = models["product.category"].readMany([c1.id, c2.id]);
            expect(readMany).toEqual([c1, c2]);
        });

        test("update operation, many2one", () => {
            const models = getModels();
            const c1 = models["product.category"].create({});
            const c2 = models["product.category"].create({});
            const c3 = models["product.category"].create({ parent_id: c1 });

            expect(c3.parent_id).toBe(c1);
            c3.update({ parent_id: c2 });
            expect(c3.parent_id).toBe(c2);
            expect(c2.child_ids.includes(c3)).toBe(true);
            expect(c1.child_ids.includes(c3)).toBe(false);
        });

        test("update operation, one2many", () => {
            const models = getModels();
            const c1 = models["product.category"].create({});
            const c2 = models["product.category"].create({});

            expect(c1.parent_id).toBe(undefined);
            c1.update({ child_ids: [["link", c2]] });
            expect(c1.child_ids.includes(c2)).toBe(true);
            expect(c2.parent_id).toBe(c1);
        });

        test("update operation, unlink many2one", () => {
            const models = getModels();
            const c1 = models["product.category"].create({});
            const c2 = models["product.category"].create({});

            c2.update({ parent_id: c1 });
            expect(c2.parent_id).toBe(c1);

            c2.update({ parent_id: undefined });
            expect(c2.parent_id).toBe(undefined);
            expect(c1.child_ids.includes(c2)).toBe(false);
        });

        test("update operation, unlink one2many", () => {
            const models = getModels();
            const c1 = models["product.category"].create({});
            const c2 = models["product.category"].create({ parent_id: c1 });

            expect(c1.child_ids.includes(c2)).toBe(true);

            c1.update({ child_ids: [["unlink", c2]] });
            expect(c1.child_ids.includes(c2)).toBe(false);
            expect(c2.parent_id).toBe(undefined);
        });

        test("update operation, Clear one2many", () => {
            const models = getModels();
            const category = models["product.category"].create({});
            models["product.category"].create({ parent_id: category });
            models["product.category"].create({ parent_id: category });

            expect(category.child_ids.length).toBe(2);
            models["product.category"].update(category, { child_ids: [["clear"]] });
            expect(category.child_ids.length).toBe(0);
        });

        test("update operation, Clear many2one", () => {
            const models = getModels();
            const category = models["product.category"].create({});
            const category1 = models["product.category"].create({ parent_id: category });

            expect(category.child_ids.includes(category1)).toBe(true);
            models["product.category"].update(category1, { parent_id: undefined });
            expect(category.child_ids.includes(category1)).toBe(false);
        });

        test("delete operation, one2many item", () => {
            const models = getModels();
            const c1 = models["product.category"].create({});
            const c2 = models["product.category"].create({ parent_id: c1 });

            expect(c1.child_ids.includes(c2)).toBe(true);

            c2.delete();
            expect(models["product.category"].read(c2.id)).toBe(undefined);
            expect(c1.child_ids.includes(c2)).toBe(false);
        });

        test("delete operation, many2one item", () => {
            const models = getModels();
            const c1 = models["product.category"].create({});
            const c2 = models["product.category"].create({ parent_id: c1 });

            expect(c1.child_ids.includes(c2)).toBe(true);

            c1.delete();
            expect(models["product.category"].read(c1.id)).toBe(undefined);
            expect(c2.parent_id).toBe(undefined);
        });
    });
    describe("many2many field relations to other models", () => {
        const getModels = () =>
            createRelatedModels({
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
        test("create operation, create", () => {
            const models = getModels();
            const tag1 = { name: "Electronics" };
            const tag2 = { name: "New" };
            const product = models["product.product"].create({
                name: "Smartphone",
                tag_ids: [["create", tag1, tag2]],
            });
            expect(product.tag_ids[0].name).toBe(tag1.name);
        });

        test("create operation, link", () => {
            const models = getModels();
            const tag1 = models["product.tag"].create({ name: "Electronics" });
            const tag2 = models["product.tag"].create({ name: "New" });
            const product = models["product.product"].create({
                name: "Smartphone",
                tag_ids: [["link", tag1, tag2]],
            });
            expect(product.tag_ids.includes(tag1)).toBe(true);
            expect(tag1.product_ids.includes(product)).toBe(true);
        });

        test("read operation", () => {
            const models = getModels();
            const p1 = models["product.product"].create({});
            const p2 = models["product.product"].create({});
            const p3 = models["product.product"].create({});
            const t1 = models["product.tag"].create({ product_ids: [["link", p1, p2, p3]] });
            const t2 = models["product.tag"].create({ product_ids: [["link", p1, p2]] });

            const readT1 = models["product.tag"].read(t1.id);
            expect(readT1).toEqual(t1);
            const readP1 = models["product.product"].read(p1.id);
            expect(readP1).toEqual(p1);

            expect(readT1.product_ids.includes(p1)).toBe(true);
            expect(readT1.product_ids.includes(p2)).toBe(true);
            expect(readT1.product_ids.includes(p3)).toBe(true);
            expect(readP1.tag_ids.includes(t1)).toBe(true);
            expect(readP1.tag_ids.includes(t2)).toBe(true);

            const readMany = models["product.product"].readMany([p2.id, p3.id]);
            expect(readMany).toEqual([p2, p3]);
        });

        test("update operation, many2many", () => {
            const models = getModels();
            const p1 = models["product.product"].create({});
            const p2 = models["product.product"].create({});
            const t1 = models["product.tag"].create({});
            expect(p1.tag_ids.includes(t1)).toBe(false);

            p1.update({ tag_ids: [["link", t1]] });
            expect(p1.tag_ids.includes(t1)).toBe(true);
            expect(t1.product_ids.includes(p1)).toBe(true);
            expect(t1.product_ids.includes(p2)).toBe(false);

            t1.update({ product_ids: [["link", p2]] });
            expect(t1.product_ids.includes(p2)).toBe(true);
        });

        test("update operation, unlink many2many", () => {
            const models = getModels();
            const p1 = models["product.product"].create({});
            const t1 = models["product.tag"].create({});

            t1.update({ product_ids: [["link", p1]] });
            expect(t1.product_ids.includes(p1)).toBe(true);
            expect(p1.tag_ids.includes(t1)).toBe(true);

            t1.update({ product_ids: [["unlink", p1]] });
            expect(t1.product_ids.includes(p1)).toBe(false);
            expect(p1.tag_ids.length).toBe(0);
        });

        test("update operation, Clear many2many", () => {
            const models = getModels();
            const tag1 = models["product.tag"].create({});
            const tag2 = models["product.tag"].create({});
            const product = models["product.product"].create({ tag_ids: [["link", tag1, tag2]] });

            expect(product.tag_ids.length).toBe(2);

            product.update({ tag_ids: [["clear"]] });
            expect(product.tag_ids.length).toBe(0);
        });

        test("delete operation, many2many item", () => {
            const models = getModels();
            const p1 = models["product.product"].create({});
            const p2 = models["product.product"].create({});
            const t1 = models["product.tag"].create({});
            t1.update({ product_ids: [["link", p1, p2]] });

            expect(t1.product_ids.includes(p1)).toBe(true);

            p1.delete();
            expect(models["product.product"].read(p1.id)).toBe(undefined);
            expect(t1.product_ids.includes(p1)).toBe(false);
        });

        describe("many2many field relations to own model", () => {
            const getModels = () =>
                createRelatedModels({
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

            test("create operation, link", () => {
                const models = getModels();
                const note1 = models["note.note"].create({ name: "Emergency" });
                const note2 = models["note.note"].create({ name: "New" });
                const note = models["note.note"].create({
                    name: "To Serve",
                    child_ids: [["link", note1, note2]],
                });
                expect(note.child_ids.includes(note1)).toBe(true);
                expect(note1.parent_ids.includes(note)).toBe(true);
            });

            test("read operation", () => {
                const models = getModels();
                const n1 = models["note.note"].create({});
                const n2 = models["note.note"].create({});
                const n3 = models["note.note"].create({});
                const n4 = models["note.note"].create({ parent_ids: [["link", n1, n2, n3]] });
                const n5 = models["note.note"].create({ parent_ids: [["link", n1, n2]] });

                const readN1 = models["note.note"].read(n1.id);
                expect(readN1).toEqual(n1);

                const readN4 = models["note.note"].read(n4.id);
                expect(readN4).toEqual(n4);

                expect([n1, n2, n3].every((n) => readN4.parent_ids.includes(n))).toBe(true);
                expect([n4, n5].every((n) => readN1.child_ids.includes(n))).toBe(true);

                const readMany = models["note.note"].readMany([n2.id, n3.id]);
                expect(readMany).toEqual([n2, n3]);
            });

            test("update operation, many2many", () => {
                const models = getModels();
                const n1 = models["note.note"].create({});
                const n2 = models["note.note"].create({});
                const n3 = models["note.note"].create({});
                n1.update({ parent_ids: [["link", n3]] });
                expect(n1.parent_ids.includes(n3)).toBe(true);
                expect(n3.child_ids.includes(n1)).toBe(true);

                n3.update({ parent_ids: [["link", n2]] });
                expect(n3.parent_ids.includes(n2)).toBe(true);

                n3.update({ parent_ids: [["unlink", n2]] });
                expect(n3.parent_ids.includes(n2)).toBe(false);
                expect(n2.child_ids.includes(n3)).toBe(false);
            });

            test("update operation, unlink many2many", () => {
                const models = getModels();
                const n1 = models["note.note"].create({});
                const n2 = models["note.note"].create({});

                n2.update({ parent_ids: [["link", n1]] });
                expect(n2.parent_ids.includes(n1)).toBe(true);
                expect(n1.child_ids.includes(n2)).toBe(true);

                n2.update({ parent_ids: [["unlink", n1]] });
                expect(n2.parent_ids.includes(n1)).toBe(false);
                expect(n1.child_ids.length).toBe(0);
            });

            test("update operation, Clear many2many", () => {
                const models = getModels();
                const note = models["note.note"].create({});
                const note2 = models["note.note"].create({});
                const note3 = models["note.note"].create({ parent_ids: [["link", note, note2]] });

                expect(note3.parent_ids.length).toBe(2);

                models["note.note"].update(note3, { parent_ids: [["clear"]] });

                expect(note3.parent_ids.length).toBe(0);
                expect(note.child_ids.length).toBe(0);
            });

            test("delete operation, many2many item", () => {
                const models = getModels();
                const n1 = models["note.note"].create({});
                const n2 = models["note.note"].create({});
                const n3 = models["note.note"].create({});
                n3.update({ parent_ids: [["link", n1, n2]] });

                expect([n1, n2].every((n) => n3.parent_ids.includes(n))).toBe(true);

                n1.delete();
                expect(models["note.note"].read(n1.id)).toBe(undefined);
                expect(n3.parent_ids.includes(n1)).toBe(false);
            });
        });
    });
});

describe("models without backlinks", () => {
    describe("many2one and one2many field relations to other models", () => {
        const getModels = () =>
            createRelatedModels({
                "product.product": {
                    category_id: { type: "many2one", relation: "product.category" },
                },
                "product.category": {},
            }).models;

        test("create operation", () => {
            const models = getModels();
            const category = models["product.category"].create({});
            const product = models["product.product"].create({ category_id: category });
            expect(product.category_id).toBe(category);
            expect(category["<-product.product.category_id"]).toEqual([product]);
        });

        test("read operation", () => {
            const models = getModels();
            const c1 = models["product.category"].create({});
            const p1 = models["product.product"].create({ category_id: c1 });
            const p2 = models["product.product"].create({ category_id: c1 });

            const readC1 = models["product.category"].read(c1.id);
            expect(readC1).toEqual(c1);

            const readP1 = models["product.product"].read(p1.id);
            expect(readP1).toEqual(p1);

            expect(readC1["<-product.product.category_id"]).toEqual([p1, p2]);

            expect(readP1.category_id).toEqual(c1);
        });

        test("update operation, many2one", () => {
            const models = getModels();
            const p1 = models["product.product"].create({});
            const c1 = models["product.category"].create({});

            expect(p1.category_id).toBe(undefined);
            p1.update({ category_id: c1 });
            expect(p1.category_id).toBe(c1);
            expect(c1["<-product.product.category_id"]).toEqual([p1]);
        });

        test("update operation, unlink many2one", () => {
            const models = getModels();
            const p1 = models["product.product"].create({ category_id: {} });
            const c1 = p1.category_id;

            expect(c1["<-product.product.category_id"]).toEqual([p1]);

            p1.update({ category_id: undefined });
            expect(p1.category_id).toBe(undefined);
            expect(c1["<-product.product.category_id"].length).toBe(0);
        });

        test("delete operation, many2one item", () => {
            const models = getModels();
            const p1 = models["product.product"].create({});
            const c1 = models["product.category"].create({});

            p1.update({ category_id: c1 });
            expect(c1["<-product.product.category_id"]).toEqual([p1]);

            c1.delete();
            expect(models["product.category"].read(c1.id)).toBe(undefined);
            expect(p1.category_id).toBe(undefined);
        });
    });

    describe("many2many relations", () => {
        const getModels = () =>
            createRelatedModels({
                "product.product": {
                    tag_ids: {
                        type: "many2many",
                        relation: "product.tag",
                        relation_table: "product_tag_product_product_rel",
                    },
                },
                "product.tag": {},
            }).models;

        test("create operation, link", () => {
            const models = getModels();
            const tag1 = models["product.tag"].create({ name: "Electronics" });
            const tag2 = models["product.tag"].create({ name: "New" });
            const product = models["product.product"].create({
                name: "Smartphone",
                tag_ids: [["link", tag1, tag2]],
            });

            expect(product.tag_ids.includes(tag1)).toBe(true);
            expect(tag1["<-product.product.tag_ids"].includes(product)).toBe(true);
        });

        test("read operation", () => {
            const models = getModels();
            const t1 = models["product.tag"].create({});
            const t2 = models["product.tag"].create({});
            const p1 = models["product.product"].create({ tag_ids: [["link", t1, t2]] });
            const p2 = models["product.product"].create({ tag_ids: [["link", t1, t2]] });
            const p3 = models["product.product"].create({ tag_ids: [["link", t1]] });

            const readT1 = models["product.tag"].read(t1.id);
            expect(readT1).toEqual(t1);

            const readP1 = models["product.product"].read(p1.id);
            expect(readP1).toEqual(p1);

            expect([p1, p2, p3].every((p) => t1["<-product.product.tag_ids"].includes(p))).toBe(
                true
            );
            expect([t1, t2].every((t) => p1.tag_ids.includes(t))).toBe(true);

            const readMany = models["product.product"].readMany([p2.id, p3.id]);
            expect(readMany).toEqual([p2, p3]);
        });

        test("update operation, link", () => {
            const models = getModels();
            const p1 = models["product.product"].create({});
            const p2 = models["product.product"].create({});
            const t1 = models["product.tag"].create({});

            p1.update({ tag_ids: [["link", t1]] });
            expect(p1.tag_ids.includes(t1)).toBe(true);
            expect(t1["<-product.product.tag_ids"].includes(p1)).toBe(true);
            expect(t1["<-product.product.tag_ids"].includes(p2)).toBe(false);

            p2.update({ tag_ids: [["link", t1]] });
            expect(t1["<-product.product.tag_ids"].includes(p2)).toBe(true);
        });

        test("update operation, unlink", () => {
            const models = getModels();
            const p1 = models["product.product"].create({});
            const t1 = models["product.tag"].create({});

            p1.update({ tag_ids: [["link", t1]] });
            expect(t1["<-product.product.tag_ids"].includes(p1)).toBe(true);
            expect(p1.tag_ids.includes(t1)).toBe(true);

            p1.update({ tag_ids: [["unlink", t1]] });
            expect(t1["<-product.product.tag_ids"].includes(p1)).toBe(false);
            expect(p1.tag_ids.length).toBe(0);
        });

        test("update operation, Clear", () => {
            const models = getModels();
            const tag1 = models["product.tag"].create({});
            const tag2 = models["product.tag"].create({});
            const product = models["product.product"].create({ tag_ids: [[tag1, tag2]] });

            models["product.product"].update(product, { tag_ids: [["clear"]] });
            const updatedProduct = models["product.product"].read(product.id);
            expect(updatedProduct.tag_ids.length).toBe(0);

            models["product.product"].update(product, { tag_ids: [["link", tag1, tag2]] });
            expect([tag1, tag2].every((t) => product.tag_ids.includes(t))).toBe(true);

            models["product.product"].update(product, { tag_ids: [["clear"]] });
            expect(tag1["<-product.product.tag_ids"].includes(product)).toBe(false);
        });

        test("delete operation", () => {
            const models = getModels();
            const p1 = models["product.product"].create({});
            const p2 = models["product.product"].create({});
            const t1 = models["product.tag"].create({});

            p1.update({ tag_ids: [["link", t1]] });
            p2.update({ tag_ids: [["link", t1]] });

            expect(t1["<-product.product.tag_ids"].includes(p1)).toBe(true);

            p1.delete();
            expect(models["product.product"].read(p1.id)).toBe(undefined);
            expect(t1["<-product.product.tag_ids"].includes(p1)).toBe(false);

            t1.delete();
            expect(models["product.tag"].read(t1.id)).toBe(undefined);
            expect(p1.tag_ids.length).toBe(0);
        });
    });
});

describe("loadData function", () => {
    const getModels = () =>
        createRelatedModels(
            {
                "product.product": {
                    id: { type: "integer" },
                    uuid: { type: "char" },
                    category_ids: { type: "many2many", relation: "product.category" },
                },
                "product.category": {
                    id: { type: "integer" },
                    name: { type: "char" },
                },
            },
            {},
            {
                databaseIndex: { "product.product": ["uuid"], "product.category": ["id"] },
                databaseTable: {
                    "product.product": {
                        key: "uuid",
                        condition: (record) => true,
                    },
                    "product.category": {
                        key: "id",
                        condition: (record) => true,
                    },
                },
                dynamicModels: ["product.product", "product.category"],
            }
        ).models;

    test("loadData should load new data correctly", () => {
        const models = getModels();

        const rawData = {
            "product.category": [
                { id: 1, name: "Electronics" },
                { id: 2, name: "Accessories" },
            ],
            "product.product": [
                { id: 1, uuid: "prod-123", category_ids: [1] },
                { id: 2, uuid: "prod-456", category_ids: [2] },
            ],
        };

        models.loadData(rawData);

        const product1 = models["product.product"].read(1);
        const product2 = models["product.product"].read(2);
        const category1 = models["product.category"].read(1);
        const category2 = models["product.category"].read(2);

        expect(product1.uuid).toBe("prod-123");
        expect(product1.category_ids.includes(category1)).toBe(true);

        expect(product2.uuid).toBe("prod-456");
        expect(product2.category_ids.includes(category2)).toBe(true);

        expect(category1.name).toBe("Electronics");
        expect(category2.name).toBe("Accessories");
    });

    test("loadData should update existing data when loading the same UUID", () => {
        const models = getModels();

        const initialRawData = {
            "product.category": [{ id: 1, name: "Electronics" }],
            "product.product": [{ id: 1, uuid: "prod-123", category_ids: [1] }],
        };

        models.loadData(initialRawData);

        const updatedRawData = {
            "product.category": [{ id: 2, name: "Updated Category" }], // New category
            "product.product": [{ id: 1, uuid: "prod-123", category_ids: [2] }],
        };

        models.loadData(updatedRawData);

        const updatedProduct = models["product.product"].read(1);
        const updatedCategory = models["product.category"].read(2);

        expect(updatedProduct.uuid).toBe("prod-123");
        expect(updatedProduct.category_ids.includes(updatedCategory)).toBe(true);
    });
    test("replace string-based ID records when loading integer-based IDs", () => {
        const models = getModels();

        models["product.category"].create({
            id: "product.category_1",
            name: "Electronics",
        });
        models["product.product"].create({
            id: "product.product_1",
            uuid: "prod-123",
            category_ids: ["product.category_1"],
        });

        const updatedRawData = {
            "product.category": [{ id: 1, name: "Updated Electronics" }],
            "product.product": [{ id: 1, uuid: "prod-123", category_ids: [1] }],
        };

        models.loadData(updatedRawData);

        const updatedCategory = models["product.category"].read(1);
        const updatedProduct = models["product.product"].read(1);

        expect(updatedCategory).not.toBeEmpty();
        expect(updatedCategory.name).toBe("Updated Electronics");

        expect(updatedProduct).not.toBeEmpty();
        expect(updatedProduct.uuid).toBe("prod-123");
        expect(updatedProduct.category_ids.includes(updatedCategory)).toBe(true);
        expect(updatedProduct.category_ids.length).toBe(1);
    });
});
