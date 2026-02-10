import { addBuilderOption, setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { refreshSublevelLines } from "@html_builder/core/building_blocks/builder_row";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { describe, expect, test } from "@odoo/hoot";
import {
    advanceTime,
    animationFrame,
    hover,
    queryAll,
    queryAllTexts,
    queryOne,
    waitFor,
} from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains, defineStyle } from "@web/../tests/web_test_helpers";
import { OPEN_DELAY } from "@web/core/tooltip/tooltip_service";

function reapplyCollapseTransition() {
    defineStyle(/* css */ `
        hoot-fixture:not(.allow-transitions) * .hb-collapse-content {
            transition: height 0.35s ease !important;
        }
    `);
}

describe.current.tags("desktop");

test("show row title", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderRow label="'my label'">row text</BuilderRow>`;
        }
    );
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeVisible();
    expect(".hb-row .text-nowrap").toHaveText("my label");
});
test("show row tooltip", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderRow label="'my label'" tooltip="'my tooltip'">row text</BuilderRow>`;
        }
    );
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeVisible();
    expect(".hb-row .text-nowrap").toHaveText("my label");
    expect(".o-tooltip").not.toHaveCount();
    await hover(".hb-row .text-nowrap");
    await advanceTime(OPEN_DELAY);
    await waitFor(".o-tooltip");
    expect(".o-tooltip").toHaveText("my tooltip");
    await contains(":iframe .test-options-target").hover();
    expect(".o-tooltip").not.toHaveCount();
});
test("hide empty row and display row with content", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".parent-target";
            static template = xml`<BuilderRow label="'Row 1'">
                        <BuilderButton applyTo="'.child-target'" classAction="'my-custom-class'"/>
                    </BuilderRow>`;
        }
    );
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".parent-target";
            static template = xml`<BuilderRow label="'Row 2'">
                        <BuilderButton applyTo="':not(.my-custom-class)'" classAction="'test'"/>
                    </BuilderRow>`;
        }
    );
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".parent-target";
            static template = xml`<BuilderRow label="'Row 3'">
                        <BuilderButton applyTo="'.my-custom-class'" classAction="'test'"/>
                    </BuilderRow>`;
        }
    );
    await setupHTMLBuilder(`<div class="parent-target"><div class="child-target">b</div></div>`);
    const selectorRowLabel = ".options-container .hb-row:not(.d-none) .hb-row-label";
    await contains(":iframe .parent-target").click();
    expect(queryAllTexts(selectorRowLabel)).toEqual(["Row 1", "Row 2"]);

    await contains("[data-class-action='my-custom-class']").click();
    expect(queryAllTexts(selectorRowLabel)).toEqual(["Row 1", "Row 3"]);
});

test("reconnects lines across mixed levels", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`
                <div class="options-container">
                    <BuilderRow label="'root-1'">root-1</BuilderRow>
                    <BuilderRow label="'level-1'" level="1">A</BuilderRow>
                    <BuilderRow label="'level-2'" level="2">B</BuilderRow>
                    <BuilderRow label="'level-1'" level="1">C</BuilderRow>
                    <BuilderRow label="'root-2'">root-2</BuilderRow>
                    <BuilderRow label="'level-1'" level="1">D</BuilderRow>
                    <BuilderRow label="'level-2'" level="2">E</BuilderRow>
                    <BuilderRow label="'level-2'" level="2">F</BuilderRow>
                    <BuilderRow label="'level-3'" level="3">G</BuilderRow>
                    <BuilderRow label="'level-3'" level="3">H</BuilderRow>
                    <BuilderRow label="'level-2'" level="2">I</BuilderRow>
                    <BuilderRow label="'level-1'" level="1">J</BuilderRow>
                </div>`;
        }
    );

    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    await waitFor(".options-container .hb-row-label");

    const labelEls = queryAll(".options-container .hb-row-label");
    const rowEls = queryAll(".options-container .hb-row");
    const rects = [
        { top: 0, bottom: 40 },
        { top: 40, bottom: 80 },
        { top: 80, bottom: 120 },
        { top: 120, bottom: 160 },
        { top: 160, bottom: 200 },
        { top: 200, bottom: 240 },
        { top: 240, bottom: 280 },
        { top: 280, bottom: 320 },
        { top: 320, bottom: 360 },
        { top: 360, bottom: 400 },
        { top: 400, bottom: 440 },
        { top: 440, bottom: 480 },
    ];
    labelEls.forEach((labelEl, index) => {
        labelEl.getBoundingClientRect = () => rects[index];
    });
    refreshSublevelLines(rowEls[10]);
    await animationFrame();

    const offsets = labelEls.map((labelEl) =>
        labelEl.style.getPropertyValue("--o-hb-row-sublevel-top")
    );
    expect(offsets).toEqual(["", "", "", "-40px", "", "", "", "", "", "", "-80px", "-200px"]);
});

/* ================= Collapse template ================= */
const collapseOptionTemplate = ({
    dependency = false,
    expand = false,
    observeCollapseContent = false,
} = {}) => xml`
        <BuilderRow label="'Test Collapse'" expand="${expand}" observeCollapseContent="${observeCollapseContent}">
            <BuilderButton classAction="'a'" ${
                dependency ? "id=\"'test_opt'\"" : ""
            }>A</BuilderButton>
            <t t-set-slot="collapse">
                <BuilderRow level="1" label="'B'" ${
                    dependency ? "t-if=\"isActiveItem('test_opt')\"" : ""
                }>
                    <BuilderButton classAction="'b'">B</BuilderButton>
                </BuilderRow>
            </t>
        </BuilderRow>`;

describe("BuilderRow with collapse content", () => {
    test("expand=false is collapsed by default", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = collapseOptionTemplate();
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeVisible();
        expect(".o_hb_collapse_toggler:not(.d-none)").not.toHaveClass("active");
    });

    test("expand=true is expanded by default", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = collapseOptionTemplate({ dependency: false, expand: true });
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeVisible();
        await animationFrame();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveClass("active");
    });

    test("Toggler button is not visible if no dependency is active", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = collapseOptionTemplate({
                    dependency: true,
                    observeCollapseContent: true,
                });
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeVisible();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveCount(0);
    });

    test("expand=true works when a dependency becomes active", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = collapseOptionTemplate({ dependency: true, expand: true });
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeVisible();
        await contains(".options-container button[data-class-action='a']").click();
        await animationFrame();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveCount(1);
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveClass("active");
        expect(".options-container button[data-class-action='b']").toBeVisible();
    });

    test("Collapse works with several dependencies", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`
                    <BuilderRow label="'Test Collapse'" expand="true">
                        <BuilderSelect>
                            <BuilderSelectItem classAction="'a'" id="'test_opt'">A</BuilderSelectItem>
                            <BuilderSelectItem classAction="'c'" id="'random_opt'">C</BuilderSelectItem>
                        </BuilderSelect>
                        <t t-set-slot="collapse">
                            <BuilderRow level="1" t-if="isActiveItem('test_opt')" label="'B'">
                                <BuilderButton classAction="'b'">B</BuilderButton>
                            </BuilderRow>
                            <BuilderRow level="1" t-if="isActiveItem('random_opt')" label="'D'">
                                <BuilderButton classAction="'d'">D</BuilderButton>
                            </BuilderRow>
                        </t>
                    </BuilderRow>`;
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeVisible();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveCount(0);
        await contains(".options-container .dropdown-toggle").click();
        await contains(".dropdown-menu [data-class-action='a']").click();
        await animationFrame();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveCount(1);
        expect(".options-container button[data-class-action='b']").toBeVisible();
        expect(".options-container button[data-class-action='d']").not.toHaveCount();
        await contains(".options-container .dropdown-toggle").click();
        await contains(".dropdown-menu [data-class-action='c']").click();
        await animationFrame();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveCount(1);
        expect(".options-container button[data-class-action='b']").not.toHaveCount();
        expect(".options-container button[data-class-action='d']").toBeVisible();
    });

    test("Click on toggler collapses / expands the BuilderRow", async () => {
        reapplyCollapseTransition();
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = collapseOptionTemplate();
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeVisible();
        expect(".o_hb_collapse_toggler:not(.d-none)").not.toHaveClass("active");
        expect(".options-container button[data-class-action='b']").toHaveCount(0);
        await contains(".o_hb_collapse_toggler:not(.d-none)").click();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveClass("active");
        expect(".options-container button[data-class-action='b']").toBeVisible();
        await contains(".o_hb_collapse_toggler:not(.d-none)").click();
        advanceTime(400); // wait for the collapse transition to be over
        await animationFrame();
        expect(".o_hb_collapse_toggler:not(.d-none)").not.toHaveClass("active");
        expect(".options-container button[data-class-action='b']").toHaveCount(0);
    });

    test("Click on toggler collapses / expands the BuilderRow (with observeCollapseContent)", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = collapseOptionTemplate({ observeCollapseContent: true });
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeVisible();
        expect(".o_hb_collapse_toggler:not(.d-none)").not.toHaveClass("active");
        expect(".options-container button[data-class-action='b']").not.toBeVisible();
        await contains(".o_hb_collapse_toggler:not(.d-none)").click();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveClass("active");
        expect(".options-container button[data-class-action='b']").toBeVisible();
        await contains(".o_hb_collapse_toggler:not(.d-none)").click();
        expect(".o_hb_collapse_toggler:not(.d-none)").not.toHaveClass("active");
        advanceTime(400); // wait for the collapse transition to be over
        await animationFrame();
        expect(".options-container button[data-class-action='b']").not.toBeVisible();
    });

    test("Click header row's label collapses / expands the BuilderRow", async () => {
        reapplyCollapseTransition();
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = collapseOptionTemplate();
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeVisible();
        expect(".o_hb_collapse_toggler:not(.d-none)").not.toHaveClass("active");
        expect(".options-container button[data-class-action='b']").toHaveCount(0);
        await contains("[data-label='Test Collapse'] span:contains('Test Collapse')").click();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveClass("active");
        expect(".options-container button[data-class-action='b']").toBeVisible();
        await contains("[data-label='Test Collapse'] span:contains('Test Collapse')").click();
        advanceTime(400); // wait for the collapse transition to be over
        await animationFrame();
        expect(".o_hb_collapse_toggler:not(.d-none)").not.toHaveClass("active");
        expect(".options-container button[data-class-action='b']").toHaveCount(0);
    });

    test("Click header row's label collapses / expands the BuilderRow (with observeCollapseContent)", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = collapseOptionTemplate({ observeCollapseContent: true });
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeVisible();
        expect(".o_hb_collapse_toggler:not(.d-none)").not.toHaveClass("active");
        expect(".options-container button[data-class-action='b']").not.toBeVisible();
        await contains("[data-label='Test Collapse'] span:contains('Test Collapse')").click();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveClass("active");
        expect(".options-container button[data-class-action='b']").toBeVisible();
        await contains("[data-label='Test Collapse'] span:contains('Test Collapse')").click();
        expect(".o_hb_collapse_toggler:not(.d-none)").not.toHaveClass("active");
        advanceTime(400); // wait for the collapse transition to be over
        await animationFrame();
        expect(".options-container button[data-class-action='b']").not.toBeVisible();
    });

    test("Two BuilderRows with collapse content on the same option are toggled independently", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = collapseOptionTemplate({ dependency: true, expand: true });
            }
        );
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = collapseOptionTemplate();
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeVisible();
        await animationFrame();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveCount(1);
        await contains(".options-container [data-class-action='a']:first").click();
        await animationFrame();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveCount(2);
        expect(".o_hb_collapse_toggler:not(.d-none):first").toHaveClass("active");
        expect(".o_hb_collapse_toggler:not(.d-none):not(.d-none):last").not.toHaveClass("active");
        await contains(".options-container .o_hb_collapse_toggler:not(.d-none):last").click();
        expect(".o_hb_collapse_toggler:not(.d-none):first").toHaveClass("active");
        expect(".o_hb_collapse_toggler:not(.d-none):last").toHaveClass("active");
        await contains(".options-container .o_hb_collapse_toggler:not(.d-none):first").click();
        expect(".o_hb_collapse_toggler:not(.d-none):first").not.toHaveClass("active");
        expect(".o_hb_collapse_toggler:not(.d-none):last").toHaveClass("active");
    });
});

describe.tags("desktop");
describe("HTML builder tests", () => {
    test("add tooltip when label is too long", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderRow label="'Supercalifragilisticexpalidocious'">Palais chatouille</BuilderRow>`;
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        await hover("[data-label='Supercalifragilisticexpalidocious'] .text-truncate");
        await advanceTime(OPEN_DELAY);
        await waitFor(".o-tooltip");
        const label = queryOne("[data-label='Supercalifragilisticexpalidocious'] .text-truncate");
        expect(label.scrollWidth).toBeGreaterThan(label.clientWidth); // the text is longer than the available width.
        expect(".o-tooltip").toHaveText("Supercalifragilisticexpalidocious");

        await contains(":iframe .test-options-target").hover();
        expect(".o-tooltip").toHaveCount(0);
    });
});
