import { getFixture, click } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let makeViewParams, target;

QUnit.module("Project", (hooks) => {
    hooks.beforeEach(() => {
        makeViewParams = {
            type: "kanban",
            resModel: "project.project",
            serverData: {
                models: {
                    "project.project": {
                        fields: {
                            id: { string: "Id", type: "integer" },
                            name: { string: "Name", type: "string" },
                            is_favorite: { string: "Favorite", type: "boolean" },
                        },
                        records: [{ id: 1, name: "Project A" }],
                    },
                },
            },
            arch: `
                <kanban class="o_kanban_test" edit="0">
                    <template>
                        <t t-name="kanban-box">
                            <div>
                                <field name="is_favorite" widget="project_is_favorite" nolabel="1"/>
                                <field name="name"/>
                            </div>
                        </t>
                    </template>
                </kanban>`,
        };
        target = getFixture();
        setupViewRegistries();
    });
    QUnit.module("Components", (hooks) => {
        QUnit.module("project_is_favorite");
        QUnit.test(
            "Check is_favorite field is still editable even if the field is in readonly",
            async function (assert) {
                await makeView({
                    ...makeViewParams,
                    async mockRPC(route, { method, args }) {
                        if (method === "web_save") {
                            const [ids, vals] = args;
                            if ("is_favorite" in vals) {
                                assert.deepEqual(ids, [1]);
                                assert.strictEqual(vals.is_favorite, true);
                                assert.step(method);
                            }
                        }
                    },
                });

                assert.containsOnce(
                    target,
                    'div[name="is_favorite"] .o_favorite',
                    "The is_favorite field should be displayed"
                );
                await click(target, 'div[name="is_favorite"] .o_favorite');
                assert.verifySteps(["web_save"]);
            }
        );

        QUnit.test(
            "Check is_favorite field is readonly if the field is readonly",
            async function (assert) {
                makeViewParams.arch = makeViewParams.arch.replace(
                    'widget="project_is_favorite"',
                    'widget="project_is_favorite" readonly="1"'
                );
                await makeView({
                    ...makeViewParams,
                    async mockRPC(route, { method, args }) {
                        if (method === "web_save") {
                            const [ids, vals] = args;
                            if ("is_favorite" in vals) {
                                assert.deepEqual(ids, [1]);
                                assert.strictEqual(vals.is_favorite, true);
                                assert.step(method);
                            }
                        }
                    },
                });
                assert.containsOnce(
                    target,
                    'div[name="is_favorite"] .o_favorite',
                    "The is_favorite field should be displayed"
                );
                await click(target, 'div[name="is_favorite"] .o_favorite');
                assert.verifySteps([]);
            }
        );
    });
});
