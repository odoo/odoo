import { addBuilderOption, setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { BuilderSlidingPanel } from "@html_builder/core/building_blocks/builder_sliding_panel";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";

test.tags("desktop");

test("sliding panel slot content is not rendered until the panel is opened", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-target";
            static components = { BuilderSlidingPanel };
            static template = xml`
                <BuilderSlidingPanel label="'Test Panel'">
                    <t t-set-slot="content">
                        <div class="panel-inner-content">Panel Content</div>
                    </t>
                </BuilderSlidingPanel>
            `;
        }
    );

    await setupHTMLBuilder(`<div class="test-target">Hello</div>`);
    await contains(":iframe .test-target").click();
    await animationFrame();

    // Slot content must not be compiled/rendered before the panel is opened.
    expect(".panel-inner-content").toHaveCount(0);

    // Open the panel.
    await contains(".we-bg-options-container .o-hb-btn").click();
    await animationFrame();

    // Now the slot content should be rendered.
    expect(".panel-inner-content").toHaveCount(1);
});

test("sliding panel slot content is rendered immediately when openByDefault is true", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-target";
            static components = { BuilderSlidingPanel };
            static template = xml`
                <BuilderSlidingPanel label="'Test Panel'" openByDefault="true">
                    <t t-set-slot="content">
                        <div class="panel-inner-content">Panel Content</div>
                    </t>
                </BuilderSlidingPanel>
            `;
        }
    );

    await setupHTMLBuilder(`<div class="test-target">Hello</div>`);
    await contains(":iframe .test-target").click();
    await animationFrame();

    // With openByDefault, content should be rendered right away.
    expect(".panel-inner-content").toHaveCount(1);
});
