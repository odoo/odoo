/** @odoo-module */

import { loadBundle, LazyComponent } from "@web/core/assets";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";

const { Component, App, xml } = owl;

QUnit.module("utils", () => {
    QUnit.module("Assets");

    QUnit.test("LazyComponent loads the required bundle", async function (assert) {
        class Test extends Component {
            get childProps() {
                return {
                    onCreated: () => assert.step("Lazy test component created"),
                };
            }
        }
        Test.template = xml`
            <LazyComponent bundle="'test_assetsbundle.lazy_test_component'" Component="'LazyTestComponent'" props="childProps"/>
        `;
        Test.components = { LazyComponent };

        const target = getFixture();
        const app = new App(Test, {
            test: true,
            env: makeTestEnv(),
        });
        registerCleanup(() => app.destroy());
        patchWithCleanup(loadBundle, { app });

        assert.verifySteps([]);
        await app.mount(target);
        assert.verifySteps(["Lazy test component created"]);
        assert.strictEqual(
            target.innerHTML,
            `<div class="o_lazy_test_component">Lazy Component!</div>`
        );
        assert.strictEqual(
            window.getComputedStyle(target.querySelector(".o_lazy_test_component")).backgroundColor,
            "rgb(165, 94, 117)",
            "scss file was loaded"
        );
    });
});
