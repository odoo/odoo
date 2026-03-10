import { expect, test } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { LazyComponent } from "@web/core/lazy_component";

test("LazyComponent loads the required bundle", async () => {
    class Test extends Component {
        static template = xml`
            <LazyComponent bundle="'test_assetsbundle.lazy_test_component'" Component="'LazyTestComponent'" props="this.childProps"/>
        `;
        static components = { LazyComponent };
        static props = ["*"];
        get childProps() {
            return {
                onCreated: () => expect.step("Lazy test component created"),
            };
        }
    }

    await mountWithCleanup(Test);
    expect.verifySteps(["Lazy test component created"]);
    expect(".o_lazy_test_component").toHaveText("Lazy Component!");
    expect(".o_lazy_test_component:only").toHaveStyle({
        backgroundColor: "rgb(165, 94, 117)",
    });
});
