import { describe, expect, test } from "@odoo/hoot";
import { getRelatedModelsInstance } from "../data/get_model_definitions";
import { makeMockServer } from "@web/../tests/web_test_helpers";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

describe("models with backlinks", () => {
    describe("many2one and one2many field relations to other models", () => {
        test("create operation", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const category = models["pos.category"].create({});
            const product = models["product.template"].create({ pos_categ_ids: [category] });
            expect(product.pos_categ_ids).toInclude(category);
            expect(category.backLink("product.template.pos_categ_ids")).toInclude(product);
        });
        test("read operation 1", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const c1 = models["pos.category"].create({});
            const c2 = models["pos.category"].create({});
            const p1 = models["product.template"].create({ pos_categ_ids: [c1] });
            const p2 = models["product.template"].create({ pos_categ_ids: [c1] });
            const p3 = models["product.template"].create({ pos_categ_ids: [c2] });

            // Test reading back the categories directly
            const readC1 = models["pos.category"].read(c1.id);
            expect(readC1).toEqual(c1);

            const readP1 = models["product.template"].read(p1.id);
            expect(readP1).toEqual(p1);

            // Test the many2one relationship from products to category
            expect(readP1.pos_categ_ids).toEqual([c1]);

            // Additional checks for completeness
            const readMany = models["product.template"].readMany([p2.id, p3.id]);
            expect(readMany).toEqual([p2, p3]);

            const readNonExistent = models["product.template"].read(9999);
            expect(readNonExistent).toBe(undefined);

            const readNonExistentC = models["pos.category"].read(9999);
            expect(readNonExistentC).toBe(undefined);
        });

        test("update operation, many2one", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const p1 = models["product.template"].create({});
            const c1 = models["product.category"].create({});

            p1.update({ categ_id: c1 });
            expect(p1.categ_id).toBe(c1);
        });

        test("update operation, one2many", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const l1 = models["pos.order.line"].create({});
            const l2 = models["pos.order.line"].create({});
            const order1 = models["pos.order"].create({});

            order1.update({ lines: [["link", l1, l2]] });
            expect(order1.lines).toInclude(l1);
            expect(order1.lines).toInclude(l2);
            expect(l1.order_id).toBe(order1);
        });

        test("update operation, unlink many2one", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const o1 = models["pos.order"].create({ lines: [] });
            const l1 = models["pos.order.line"].create({
                order_id: o1,
            });

            expect(l1.order_id).toEqual(o1);

            o1.update({ lines: [] });
            expect(l1.order_id).toBe(undefined);
        });

        test("update operation, unlink one2many", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const o1 = models["pos.order"].create({ lines: [] });
            const l1 = models["pos.order.line"].create({
                order_id: o1,
            });

            o1.update({ lines: [["link", l1]] });
            expect(o1.lines).toInclude(l1);
            expect(l1.order_id).toBe(o1);

            o1.update({ lines: [["unlink", l1]] });
            expect(o1.lines).not.toInclude(l1);
            expect(l1.order_id).toBe(undefined);
        });

        test("update operation, Clear one2many", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const o1 = models["pos.order"].create({});
            const l1 = models["pos.order.line"].create({
                order_id: o1,
            });
            o1.update({ lines: [["link", l1]] });
            expect(o1.lines).toInclude(l1);
            expect(l1.order_id).toBe(o1);

            o1.update({ lines: [["unlink", l1]] });
            expect(o1.lines).not.toInclude(l1);
            expect(l1.order_id).toBe(undefined);
        });

        test("update operation, Clear many2one", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const o1 = models["pos.order"].create({ lines: [] });
            models["pos.order.line"].create({
                order_id: o1,
            });

            models["pos.order"].update(o1, { lines: [] });
            expect(o1.lines).toHaveLength(0);
        });

        test("delete operation, one2many item", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const l1 = models["pos.order.line"].create({});
            const l2 = models["pos.order.line"].create({});
            const o1 = models["pos.order"].create({});

            o1.update({ lines: [["link", l1, l2]] });
            expect(o1.lines).toInclude(l1);

            l1.delete();
            expect(models["pos.order.line"].read(l1.id)).toBe(undefined);
            expect(o1.lines).not.toInclude(l1);
        });

        test("delete operation, many2one item", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const o1 = models["pos.order"].create({});
            const l1 = models["pos.order.line"].create({});

            o1.update({ lines: [["link", l1]] });
            expect(l1.order_id).toBe(o1);

            l1.delete();
            expect(models["pos.order.line"].read(l1.id)).toBe(undefined);
            expect(o1.lines).not.toInclude(l1);
        });
    });
    describe("many2one/one2many field relations to own model", () => {
        test("create operation", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const o1 = models["pos.order"].create({});
            const l2 = models["pos.order.line"].create({ order_id: o1 });

            expect(l2.order_id).toBe(o1);
            expect(o1.lines).toInclude(l2);
        });

        test("read operation 2", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const c1 = models["pos.category"].create({});
            const c2 = models["pos.category"].create({ parent_id: c1 });

            const readC1 = models["pos.category"].read(c1.id);
            expect(readC1.child_ids).toEqual([c2]);

            const readC2 = models["pos.category"].read(c2.id);
            expect(readC2.parent_id).toEqual(c1);

            const readMany = models["pos.category"].readMany([c1.id, c2.id]);
            expect(readMany).toEqual([c1, c2]);
        });

        test("update operation, many2one", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const o1 = models["pos.order"].create({});
            const l1 = models["pos.order.line"].create({});
            const l2 = models["pos.order.line"].create({ order_id: o1 });

            expect(l2.order_id).toBe(o1);
            o1.update({ lines: [l1] });
            expect(o1.lines).not.toInclude(l2);
        });

        test("update operation, one2many", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const o1 = models["pos.order"].create({});
            const l1 = models["pos.order.line"].create({ order_id: o1 });
            const l2 = models["pos.order.line"].create({});

            expect(o1.lines).toInclude(l1);
            l2.update({ order_id: o1 });
            expect(o1.lines).toInclude(l2);
        });

        test("update operation, unlink many2one", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const c1 = models["pos.category"].create({});
            const c2 = models["pos.category"].create({});

            c2.update({ parent_id: c1 });
            expect(c2.parent_id).toBe(c1);

            c2.update({ parent_id: undefined });
            expect(c2.parent_id).toBe(undefined);
            expect(c1.child_ids).not.toInclude(c2);
        });

        test("update operation, unlink one2many", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const c1 = models["pos.category"].create({});
            const c2 = models["pos.category"].create({ parent_id: c1 });

            expect(c1.child_ids).toInclude(c2);

            c1.update({ child_ids: [["unlink", c2]] });
            expect(c1.child_ids).not.toInclude(c2);
            expect(c2.parent_id).toBe(undefined);
        });

        test("update operation, Clear one2many", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const category = models["pos.category"].create({});
            models["pos.category"].create({ parent_id: category });
            models["pos.category"].create({ parent_id: category });

            expect(category.child_ids).toHaveLength(2);
            models["pos.category"].update(category, { child_ids: [["clear"]] });
            expect(category.child_ids).toHaveLength(0);
        });

        test("update operation, Clear many2one", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const category = models["pos.category"].create({});
            const category1 = models["pos.category"].create({ parent_id: category });

            expect(category.child_ids).toInclude(category1);
            models["pos.category"].update(category1, { parent_id: undefined });
            expect(category.child_ids).not.toInclude(category1);
        });

        test("delete operation, one2many item", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const c1 = models["pos.category"].create({});
            const c2 = models["pos.category"].create({ parent_id: c1 });

            expect(c1.child_ids).toInclude(c2);

            c2.delete();
            expect(models["pos.category"].read(c2.id)).toBe(undefined);
            expect(c1.child_ids).not.toInclude(c2);
        });

        test("delete operation, many2one item", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const c1 = models["pos.category"].create({});
            const c2 = models["pos.category"].create({ parent_id: c1 });

            expect(c1.child_ids).toInclude(c2);

            c1.delete();
            expect(models["pos.category"].read(c1.id)).toBe(undefined);
            expect(c2.parent_id).toBe(undefined);
        });
    });
    describe("many2many field relations to other models", () => {
        test("create operation, create", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const line1 = { id: 2 };
            const line2 = { name: 4 };
            const product = models["pos.order"].create({
                name: "Smartphone",
                lines: [["create", line1, line2]],
            });
            expect(product.lines).toHaveLength(2);
        });

        test("create operation, link", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const line1 = models["pos.order.line"].create({ id: 1 });
            const line2 = models["pos.order.line"].create({ id: 2 });
            const product = models["pos.order"].create({
                name: "Smartphone",
                lines: [["link", line1, line2]],
            });
            expect(product.lines).toInclude(line1);
            expect(product.lines).toInclude(line2);
        });

        test("read operation 3", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const c1 = models["pos.category"].create({});
            const c2 = models["pos.category"].create({});
            const c3 = models["pos.category"].create({});
            const t1 = models["product.template"].create({ pos_categ_ids: [["link", c1, c2, c3]] });
            const t2 = models["product.template"].create({ pos_categ_ids: [["link", c1, c2]] });

            const readT1 = models["product.template"].read(t1.id);
            expect(readT1).toEqual(t1);
            const readP1 = models["product.template"].read(t2.id);
            expect(readP1).toEqual(t2);

            expect(readT1.pos_categ_ids).toInclude(c1);
            expect(readT1.pos_categ_ids).toInclude(c2);
            expect(readT1.pos_categ_ids).toInclude(c3);
            expect(readP1.pos_categ_ids).toInclude(c1);
            expect(readP1.pos_categ_ids).toInclude(c2);

            const readMany = models["product.template"].readMany([t1.id, t2.id]);
            expect(readMany[0]).toBe(t1);
            expect(readMany[1]).toBe(t2);
        });

        test("update operation, many2many", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const c1 = models["pos.category"].create({});
            const c2 = models["pos.category"].create({});
            const t1 = models["product.template"].create({ pos_categ_ids: [] });
            expect(t1.pos_categ_ids).not.toInclude(c1);

            t1.update({ pos_categ_ids: [["link", c1]] });
            expect(t1.pos_categ_ids).toInclude(c1);
            expect(t1.pos_categ_ids).not.toInclude(c2);

            t1.update({ pos_categ_ids: [["link", c2]] });
            expect(t1.pos_categ_ids).toInclude(c2);
        });

        test("update operation, unlink many2many", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const c1 = models["pos.category"].create({});
            const t1 = models["product.template"].create({ pos_categ_ids: [] });

            t1.update({ pos_categ_ids: [["link", c1]] });
            expect(t1.pos_categ_ids).toInclude(c1);

            t1.update({ pos_categ_ids: [["unlink", c1]] });
            expect(t1.pos_categ_ids).not.toInclude(c1);
        });

        test("update operation, Clear many2many", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const c1 = models["pos.category"].create({});
            const c2 = models["pos.category"].create({});
            const t1 = models["product.template"].create({ pos_categ_ids: [c1, c2] });

            expect(t1.pos_categ_ids).toHaveLength(2);

            t1.update({ pos_categ_ids: [["clear"]] });
            expect(t1.pos_categ_ids).toHaveLength(0);
        });

        test("delete operation, many2many item", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const c1 = models["pos.category"].create({});
            const c2 = models["pos.category"].create({});
            const t1 = models["product.template"].create({ pos_categ_ids: [] });
            t1.update({ pos_categ_ids: [["link", c1, c2]] });

            expect(t1.pos_categ_ids).toInclude(c1);

            c1.delete();
            expect(models["pos.category"].read(c1.id)).toBe(undefined);
            expect(t1.pos_categ_ids).not.toInclude(c1);
            expect(t1.pos_categ_ids).toInclude(c2);
        });

        describe("many2many field relations to own model", () => {
            test("create operation, link", async () => {
                await makeMockServer();
                const models = getRelatedModelsInstance(false);
                const l1 = models["pos.order.line"].create({ id: 1 });
                const l2 = models["pos.order.line"].create({ id: 2, combo_parent_id: l1 });
                expect(l1.combo_line_ids).toInclude(l2);
                expect(l2.combo_parent_id).toBe(l1);
            });

            test("read operation 4", async () => {
                await makeMockServer();
                const models = getRelatedModelsInstance(false);
                const l1 = models["pos.order.line"].create({});
                const l2 = models["pos.order.line"].create({});
                const l3 = models["pos.order.line"].create({});
                const l4 = models["pos.order.line"].create({ combo_line_ids: [l1, l2, l3] });

                const readL1 = models["pos.order.line"].read(l1.id);
                expect(readL1).toEqual(l1);

                const readL4 = models["pos.order.line"].read(l4.id);
                expect(readL4).toEqual(l4);

                expect([l1, l2, l3].every((n) => readL4.combo_line_ids.includes(n))).toBe(true);

                const readMany = models["pos.order.line"].readMany([l2.id, l3.id]);
                expect(readMany[0]).toBe(l2);
                expect(readMany[1]).toBe(l3);
            });

            test("update operation, many2many", async () => {
                await makeMockServer();
                const models = getRelatedModelsInstance(false);
                const l1 = models["pos.order.line"].create({});
                const l2 = models["pos.order.line"].create({});
                const l3 = models["pos.order.line"].create({});
                l1.update({ combo_line_ids: [["link", l3]] });
                expect(l1.combo_line_ids).toInclude(l3);
                expect(l3.combo_parent_id).toBe(l1);

                l3.update({ combo_line_ids: [["link", l2]] });
                expect(l3.combo_line_ids).toInclude(l2);

                l3.update({ combo_line_ids: [["unlink", l2]] });
                expect(l3.combo_line_ids).not.toInclude(l2);
                expect(l2.combo_line_ids).not.toInclude(l3);
            });

            test("update operation, unlink many2many", async () => {
                await makeMockServer();
                const models = getRelatedModelsInstance(false);
                const l1 = models["pos.order.line"].create({});
                const l2 = models["pos.order.line"].create({});

                l2.update({ combo_line_ids: [["link", l1]] });
                expect(l2.combo_line_ids).toInclude(l1);
                expect(l1.combo_parent_id).toBe(l2);

                l2.update({ combo_line_ids: [["unlink", l1]] });
                expect(l2.combo_line_ids).not.toInclude(l1);
                expect(l1.combo_parent_id).toBeEmpty();
            });

            test("update operation, Clear many2many", async () => {
                await makeMockServer();
                const models = getRelatedModelsInstance(false);
                const l1 = models["pos.order.line"].create({});
                const l2 = models["pos.order.line"].create({});
                const l3 = models["pos.order.line"].create({});
                const l4 = models["pos.order.line"].create({ combo_line_ids: [l1, l2, l3] });

                expect(l4.combo_line_ids).toHaveLength(3);

                models["pos.order.line"].update(l4, { combo_line_ids: [["clear"]] });

                expect(l4.combo_line_ids).toHaveLength(0);
                expect(l1.combo_parent_id).toBeEmpty();
            });

            test("delete operation, many2many item", async () => {
                await makeMockServer();
                const models = getRelatedModelsInstance(false);
                const l1 = models["pos.order.line"].create({});
                const l2 = models["pos.order.line"].create({});
                const l3 = models["pos.order.line"].create({});
                l3.update({ combo_line_ids: [["link", l1, l2]] });

                expect([l1, l2].every((n) => l3.combo_line_ids.includes(n))).toBe(true);

                l1.delete();
                expect(models["pos.order.line"].read(l1.id)).toBe(undefined);
                expect(l3.combo_line_ids).not.toInclude(l1);
            });
        });
    });
});

describe("models without backlinks", () => {
    describe("many2one and one2many field relations to other models", () => {
        test("create operation", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const category = models["pos.category"].create({ id: 1 });
            const product = models["product.template"].create({ pos_categ_ids: [category] });
            expect(product.pos_categ_ids).toEqual([category]);
            expect(category.backLink("<-product.template.pos_categ_ids")).toEqual([product]);
        });

        test("read operation 5", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const c1 = models["pos.category"].create({});
            const p1 = models["product.template"].create({ pos_categ_ids: [c1] });
            const p2 = models["product.template"].create({ pos_categ_ids: [c1] });

            const readC1 = models["pos.category"].read(c1.id);
            expect(readC1).toEqual(c1);

            const readP1 = models["product.template"].read(p1.id);
            expect(readP1).toEqual(p1);

            expect(readC1.backLink("product.template.pos_categ_ids")).toEqual([p1, p2]);

            expect(readP1.pos_categ_ids).toEqual([c1]);
        });

        test("update operation, many2one", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const p1 = models["product.template"].create({});
            const c1 = models["pos.category"].create({});

            p1.update({ pos_categ_ids: [c1] });
            expect(p1.pos_categ_ids).toInclude(c1);
        });

        test("update operation, unlink many2one", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const categ = models["pos.category"].create({});
            const p1 = models["product.template"].create({ pos_categ_ids: [categ] });

            p1.update({ pos_categ_ids: [] });
            expect(p1.pos_categ_ids).toHaveLength(0);
            expect(categ.backLink("product.template.pos_categ_ids")).toHaveLength(0);
        });

        test("delete operation, many2one item", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const p1 = models["product.template"].create({});
            const c1 = models["pos.category"].create({});

            p1.update({ pos_categ_ids: [c1] });
            expect(c1.backLink("<-product.template.pos_categ_ids")).toEqual([p1]);

            c1.delete();
            expect(models["pos.category"].read(c1.id)).toBe(undefined);
            expect(p1.pos_categ_ids).toHaveLength(0);
        });
    });

    describe("many2many relations", () => {
        test("create operation, link", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const l1 = models["pos.order.line"].create({});
            const l2 = models["pos.order.line"].create({});
            const l3 = models["pos.order.line"].create({});
            const o1 = models["pos.order"].create({
                lines: [["link", l1, l2, l3]],
            });

            expect(o1.lines).toInclude(l1);
        });

        test("read operation 6", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const c1 = models["pos.category"].create({});
            const c2 = models["pos.category"].create({});
            const p1 = models["product.template"].create({
                pos_categ_ids: [["link", c1, c2]],
            });
            const p2 = models["product.template"].create({
                pos_categ_ids: [["link", c1, c2]],
            });
            const p3 = models["product.template"].create({ pos_categ_ids: [["link", c1]] });

            const readT1 = models["product.template"].read(p1.id);
            expect(readT1).toEqual(p1);

            const readP1 = models["product.template"].read(p2.id);
            expect(readP1).toEqual(p2);

            const readMany = models["product.template"].readMany([p2.id, p3.id]);
            expect(readMany).toEqual([p2, p3]);
        });

        test("update operation, link", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const p1 = models["product.template"].create({});
            const p2 = models["product.template"].create({});
            const t1 = models["pos.category"].create({});

            p1.update({ pos_categ_ids: [["link", t1]] });
            expect(p1.pos_categ_ids).toInclude(t1);
            expect(t1.backLink("<-product.template.pos_categ_ids")).toInclude(p1);
            expect(t1.backLink("<-product.template.pos_categ_ids")).not.toInclude(p2);

            p2.update({ pos_categ_ids: [["link", t1]] });
            expect(t1.backLink("<-product.template.pos_categ_ids")).toInclude(p2);
        });

        test("update operation, unlink", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const p1 = models["product.template"].create({});
            const t1 = models["pos.category"].create({});

            p1.update({ pos_categ_ids: [["link", t1]] });
            expect(t1.backLink("<-product.template.pos_categ_ids")).toInclude(p1);
            expect(p1.pos_categ_ids).toInclude(t1);

            p1.update({ pos_categ_ids: [["unlink", t1]] });
            expect(t1.backLink("<-product.template.pos_categ_ids")).not.toInclude(p1);
            expect(p1.pos_categ_ids).toHaveLength(0);
        });

        test("update operation, Clear", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const tag1 = models["pos.category"].create({});
            const tag2 = models["pos.category"].create({});
            const product = models["product.template"].create({ pos_categ_ids: [tag1, tag2] });
            models["product.template"].update(product, { pos_categ_ids: [["clear"]] });
            const updatedProduct = models["product.template"].read(product.id);
            expect(updatedProduct.pos_categ_ids).toHaveLength(0);

            models["product.template"].update(product, { pos_categ_ids: [["link", tag1, tag2]] });
            expect([tag1, tag2].every((t) => product.pos_categ_ids.includes(t))).toBe(true);
            models["product.template"].update(product, { pos_categ_ids: [["clear"]] });
            expect(tag1.backLink("<-product.template.pos_categ_ids")).not.toInclude(product);
        });

        test("delete operation", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const p1 = models["product.template"].create({});
            const p2 = models["product.template"].create({});
            const t1 = models["pos.category"].create({});

            p1.update({ pos_categ_ids: [["link", t1]] });
            p2.update({ pos_categ_ids: [["link", t1]] });

            expect(t1.backLink("<-product.template.pos_categ_ids")).toInclude(p1);

            p1.delete();
            expect(models["product.template"].read(p1.id)).toBe(undefined);
            expect(t1.backLink("<-product.template.pos_categ_ids")).not.toInclude(p1);

            t1.delete();
            expect(models["pos.category"].read(t1.id)).toBe(undefined);
            expect(p1.pos_categ_ids).toHaveLength(0);
        });
    });
});
