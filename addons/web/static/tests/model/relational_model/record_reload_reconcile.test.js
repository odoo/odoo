// @ts-check

import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import {
    defineModels,
    defineWebModels,
    fields,
    MockServer,
    models,
    mountView,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { RelationalModel } from "@web/model/relational_model/relational_model";

class Partner extends models.Model {
    name = fields.Char();
    tag_ids = fields.Many2many({ relation: "tag" });
    line_ids = fields.One2many({ relation: "line", relation_field: "partner_id" });
    _records = [{ id: 1, name: "p", tag_ids: [1, 2], line_ids: [1] }];
}
class Tag extends models.Model {
    name = fields.Char();
    _records = [
        { id: 1, name: "t1" },
        { id: 2, name: "t2" },
    ];
}
class Line extends models.Model {
    name = fields.Char();
    partner_id = fields.Many2one({ relation: "partner" });
    _records = [{ id: 1, name: "l1", partner_id: 1 }];
}
defineWebModels();
defineModels([Partner, Tag, Line]);

const ARCH = `
    <form>
        <field name="name"/>
        <field name="tag_ids" widget="many2many_tags"/>
        <field name="line_ids">
            <list editable="bottom"><field name="name"/></list>
        </field>
    </form>`;

/** @returns {Promise<RelationalModel>} */
async function mountFormAndGetModel() {
    /** @type {RelationalModel[]} */
    const instances = [];
    patchWithCleanup(RelationalModel.prototype, {
        setup(/** @type {any[]} */ ...args) {
            super.setup(...args);
            instances.push(/** @type {any} */ (this));
        },
    });
    await mountView({ resModel: "partner", type: "form", resId: 1, arch: ARCH });
    return /** @type {RelationalModel} */ (instances.at(-1));
}

test("a reload keeps an x2many the server sent unchanged and rebuilds one it did not", async () => {
    const model = await mountFormAndGetModel();
    const { tag_ids: tagsBefore, line_ids: linesBefore } = model.root.data;
    const dataBefore = model.root.data;

    await model.root.load();
    expect(model.root.data).toBe(dataBefore);
    expect(model.root.data.tag_ids).toBe(tagsBefore);
    expect(model.root.data.line_ids).toBe(linesBefore);

    MockServer.env["tag"].write([1], { name: "t1-renamed" });
    await model.root.load();
    await animationFrame();
    expect(model.root.data.tag_ids).not.toBe(tagsBefore);
    expect(model.root.data.line_ids).toBe(linesBefore);
    expect(".o_field_many2many_tags .o_tag:first").toHaveText("t1-renamed");
});

test("a reload rebuilds an x2many that carries a staged command or an edited row", async () => {
    const model = await mountFormAndGetModel();
    const record = model.root;

    const withCommand = record.data.line_ids;
    await withCommand.addNewRecord({ position: "bottom" });
    expect(withCommand.hasStagedCommands).toBe(true);
    await record.load();
    expect(record.data.line_ids).not.toBe(withCommand);
    expect(record.data.line_ids.records).toHaveLength(1);

    const withEdit = record.data.line_ids;
    await withEdit.records[0].update({ name: "l1-edited" });
    expect(withEdit.records[0].hasPendingChanges).toBe(true);
    await record.load();
    expect(record.data.line_ids).not.toBe(withEdit);
    expect(record.data.line_ids.records[0].data.name).toBe("l1");
});
