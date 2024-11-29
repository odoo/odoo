import { expect, test } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { clearRegistry, mountWithCleanup, patchTranslations } from "@web/../tests/web_test_helpers";
import { renderService } from "@point_of_sale/app/services/render_service";

test("test the render service", async () => {
    class ComponentToBeRendered extends Component {
        static props = ["name"];
        static template = xml`
            <div> It's me, <t t-esc="props.name" />! </div>
        `;
    }
    clearRegistry(registry.category("services"));
    clearRegistry(registry.category("main_components"));
    registry.category("services").add("render", renderService);

    patchTranslations(); // this is needed because we are not loading the localization service
    const comp = await mountWithCleanup("none");
    const renderedComp = await comp.env.services.render.toHtml(ComponentToBeRendered, {
        name: "Mario",
    });
    expect(renderedComp).toHaveOuterHTML("<div> It's me, Mario! </div>");
});
