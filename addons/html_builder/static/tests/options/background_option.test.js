import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";
import { BackgroundComponent } from "@html_builder/plugins/background_option/background_option";

defineWebsiteModels();

test("show and leave the 'BackgroundShapeComponent'", async () => {
    await setupWebsiteBuilder(`<section>AAAA</section>`);
    await contains(":iframe section").click();
    await contains("button[data-action-id='toggleBgShape']").click();
    await contains("button.o_pager_nav_angle").click();
    expect("button[data-action-id='toggleBgShape']").toBeVisible();
});

test("change the background shape of elements", async () => {
    const shapesInfo = {
        connectionShapes: [
            {
                shapeUrl: "web_editor/Connections/01",
                label: "Connections 01",
            },
            {
                shapeUrl: "web_editor/Connections/02",
                label: "Connections 02",
            },
        ],
        originShapes: [],
        boldShapes: [],
        blobShapes: [],
        airyAndZigShapes: [],
        wavyShapes: [],
        blockAndRainyShapes: [],
        floatingShapes: [],
        allPossiblesShapes: [
            {
                shapeUrl: "",
                label: "",
            },
            {
                shapeUrl: "web_editor/Connections/01",
                label: "Connections 01",
            },
            {
                shapeUrl: "web_editor/Connections/02",
                label: "Connections 02",
            },
        ],
    };
    addOption({
        selector: ".selector",
        applyTo: ".applyTo",
        Component: BackgroundComponent,
        props: {
            getShapeData: () => ({
                shape: "web_editor/Connections/01",
                flip: [],
                showOnMobile: false,
                shapeAnimationSpeed: "0",
            }),
            getShapeStyleUrl: () => "",
            withColors: true,
            withImages: true,
            // todo: handle with_videos
            withShapes: true,
            withGradient: false,
            withColorCombinations: false,
            shapesInfo: shapesInfo,
        },
    });
    await setupWebsiteBuilder(`
        <div class="selector">
            <div id="first" class="applyTo" data-oe-shape-data='{"shape":"web_editor/Connections/01","flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'>
                AAAA
            </div>
            <div id="second" class="applyTo" data-oe-shape-data='{"shape":"web_editor/Connections/01","flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'>
                BBBB
            </div>
        </div>`);
    await contains(":iframe .selector").click();
    await contains("[data-label='Shape'] button").click();
    await contains(
        ".o_pager_container .button_shape:nth-child(2) [data-action-id='applyShape']"
    ).click();
    expect(":iframe .selector div#first").toHaveAttribute(
        "data-oe-shape-data",
        '{"shape":"web_editor/Connections/02","flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'
    );
    expect(":iframe .selector div#second").toHaveAttribute(
        "data-oe-shape-data",
        '{"shape":"web_editor/Connections/02","flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'
    );
});

test("remove background shape", async () => {
    await setupWebsiteBuilder(`
        <section data-oe-shape-data='{"shape":"web_editor/Connections/01","flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'>
            AAAA
        </section>`);
    await contains(":iframe section").click();
    await contains("button[data-action-id='applyShape']").click();
    expect(":iframe section").not.toHaveAttribute("data-oe-shape-data");
    expect("button[data-action-id='applyShape']").not.toBeVisible();
});

test("toggle Show/Hide on mobile of the shape background", async () => {
    await setupWebsiteBuilder(`
        <section data-oe-shape-data='{"shape":"web_editor/Connections/01","flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'>
            <div class="o_we_shape o_web_editor_Connections_01">
                AAAA
            </div>
        </section>`);
    await contains(":iframe section").click();
    await contains("button[data-action-id='showOnMobile']").click();
    expect(":iframe section .o_we_shape").toHaveClass("o_shape_show_mobile");
    await contains("button[data-action-id='showOnMobile']").click();
    expect(":iframe section .o_we_shape").not.toHaveClass("o_shape_show_mobile");
});
