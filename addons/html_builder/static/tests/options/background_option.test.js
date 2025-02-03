import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "../helpers";
import { BackgroundComponent } from "@html_builder/plugins/background_option/background_option";

defineWebsiteModels();

test("show and leave the 'BackgroundShapeComponent'", async () => {
    await setupWebsiteBuilder(
        `<section data-oe-shape-data='{"shape":"web_editor/Connections/01","flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'>AAAA</section>`
    );
    await contains(":iframe section").click();
    await contains("[data-label='Change Shapes'] button").click();
    await contains("button.o_pager_nav_angle").click();
    expect("[data-label='Change Shapes'] button").toBeVisible();
});

test("change the background shape of elements", async () => {
    addOption({
        selector: "section",
        applyTo: "div",
        Component: BackgroundComponent,
        props: {
            getShapeData: () => ({
                shape: "web_editor/Connections/01",
                flip: [],
                showOnMobile: false,
                shapeAnimationSpeed: "0",
            }),
            getShapeStyleUrl: () => "",
        },
    });
    await setupWebsiteBuilder(`
        <section>
            <div id="first" data-oe-shape-data='{"shape":"web_editor/Connections/01","flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'>
                AAAA
            </div>
            <div id="second" data-oe-shape-data='{"shape":"web_editor/Connections/01","flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'>
                BBBB
            </div>
        </section>`);
    await contains(":iframe section").click();
    await contains("[data-label='Change Shapes'] button").click();
    await contains(
        ".o_pager_container .button_shape:nth-child(2) [data-action-id='applyShape']"
    ).click();
    expect(":iframe section div#first").toHaveAttribute(
        "data-oe-shape-data",
        '{"shape":"web_editor/Connections/02","flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'
    );
    expect(":iframe section div#second").toHaveAttribute(
        "data-oe-shape-data",
        '{"shape":"web_editor/Connections/02","flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'
    );
});
