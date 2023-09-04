/** @odoo-module **/

    import makeTestEnvironment from "@web/../tests/legacy/helpers/test_env";
    import testUtils from "@web/../tests/legacy/helpers/test_utils";
    import { destroy, getFixture, mount } from "@web/../tests/helpers/utils";
    import { LegacyComponent } from "@web/legacy/legacy_component";

    const { xml } = owl;

    let target;
    QUnit.module("web", { beforeEach() { target = getFixture(); }}, function () {
        QUnit.module("Component Extension");

        QUnit.test("Component destroyed while performing successful RPC", async function (assert) {
            assert.expect(1);

            class Parent extends LegacyComponent {}
            Parent.template = xml`<div/>`;

            const env = makeTestEnvironment({}, () => Promise.resolve());

            const parent = await mount(Parent, target, { env });

            parent.rpc({}).then(() => { throw new Error(); });
            destroy(parent);

            await testUtils.nextTick();

            assert.ok(true, "Promise should still be pending");
        });

        QUnit.test("Component destroyed while performing failed RPC", async function (assert) {
            assert.expect(1);

            class Parent extends LegacyComponent {}
            Parent.template = xml`<div/>`;

            const env = makeTestEnvironment({}, () => Promise.reject());
            const parent = await mount(Parent, target, { env });

            parent.rpc({}).catch(() => { throw new Error(); });
            destroy(parent);

            await testUtils.nextTick();

            assert.ok(true, "Promise should still be pending");
        });
    });
