import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { click, edit, keyDown, keyUp, queryOne } from "@odoo/hoot-dom";
import { Deferred, advanceTime, animationFrame, runAllTimers } from "@odoo/hoot-mock";
import {
    contains,
    defineWebModels,
    getService,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { WebClient } from "@web/webclient/webclient";
import { TourRecorder } from "@web_tour_recorder/tour_recorder/tour_recorder";
import { TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY } from "@web_tour_recorder/tour_recorder/tour_recorder_service";

describe.current.tags("desktop");

let tourRecorder;
beforeEach(async () => {
    serverState.debug = "1";
    browser.localStorage.setItem(TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY, "1");
    patchWithCleanup(TourRecorder.prototype, {
        setup() {
            tourRecorder = this;
            return super.setup(...arguments);
        },
    });

    defineWebModels();
    await mountWithCleanup(WebClient);
});

const checkTourSteps = (expected) => {
    expect(tourRecorder.state.steps.map((s) => s.trigger)).toEqual(expected);
};

test("Click on element with unique odoo class", async () => {
    await mountWithCleanup(
        `
        <div class="o_parent">
            <div class="o_child_1 click"></div>
            <div class="o_child_2"></div>
            <div class="o_child_3"></div>
        </div>
    `,
        { noMainContainer: true }
    );

    expect(".o_tour_recorder").toHaveCount(1);
    await click(".o_button_record");
    await animationFrame();
    await click(".click");
    await animationFrame();
    checkTourSteps([".o_child_1"]);

    await click(".o_child_2");
    await animationFrame();
    checkTourSteps([".o_child_1", ".o_child_2"]);
});

test("Click on element with no unique odoo class", async () => {
    await mountWithCleanup(
        `
        <div class="o_parent">
            <div class="o_child_1 click"></div>
            <div class="o_child_1"></div>
            <div class="o_child_1"></div>
        </div>
    `,
        { noMainContainer: true }
    );

    expect(".o_tour_recorder").toHaveCount(1);
    await click(".o_button_record");
    await animationFrame();
    await click(".click");
    await animationFrame();
    checkTourSteps([".o_child_1:nth-child(1)"]);
});

test("Find the nearest odoo class", async () => {
    await mountWithCleanup(`<a class="click"></a>`, { noMainContainer: true });

    expect(".o_tour_recorder").toHaveCount(1);
    await click(".o_button_record");
    await animationFrame();
    await click(".click");
    await animationFrame();
    checkTourSteps([".o_web_client > a"]);
});

test("Click on elements with 'data-menu-xmlid' attribute", async () => {
    await mountWithCleanup(
        `
        <div>
            <div></div>
            <div data-menu-xmlid="my_menu_1" class="click_1"></div>
            <div data-menu-xmlid="my_menu_2" class="click_2 o_div"></div>
            <div></div>
        </div>
    `,
        { noMainContainer: true }
    );

    expect(".o_tour_recorder").toHaveCount(1);
    await click(".o_button_record");
    await animationFrame();
    await click(".click_1");
    await click(".click_2");
    await animationFrame();
    checkTourSteps([
        ".o_web_client div[data-menu-xmlid='my_menu_1']",
        ".o_div[data-menu-xmlid='my_menu_2']",
    ]);
});

test("Click on elements with 'name' attribute", async () => {
    await mountWithCleanup(
        `
        <div>
            <div></div>
            <div name="sale_id" class="click_1"></div>
            <div name="partner_id" class="click_2 o_div"></div>
            <div></div>
        </div>
    `,
        { noMainContainer: true }
    );

    expect(".o_tour_recorder").toHaveCount(1);
    await click(".o_button_record");
    await animationFrame();
    await click(".click_1");
    await click(".click_2");
    await animationFrame();
    checkTourSteps([".o_web_client div[name='sale_id']", ".o_div[name='partner_id']"]);
});

test("Click on element that have a link or button has parent", async () => {
    await mountWithCleanup(
        `
        <div>
            <button class="o_button"><i class="click_1">icon</i></button>
            <a class="o_link"><span class="click_2">This is my link</span></a>
        </div>
    `,
        { noMainContainer: true }
    );

    expect(".o_tour_recorder").toHaveCount(1);
    await click(".o_button_record");
    await animationFrame();
    await click(".click_1");
    await click(".click_2");
    await animationFrame();
    checkTourSteps([".o_button", ".o_link"]);
});

test("Click on element with path that can be reduced", async () => {
    await mountWithCleanup(
        `
        <div class=".o_parent">
            <div name="field_name">
                <div class="o_div_2">
                    <div class="o_div_3 click"></div>
                </div>
            </div>
            <div name="field_partner_id">
                <div class="o_div_2">
                    <div class="o_div_3"></div>
                </div>
            </div>
        </div>
    `,
        { noMainContainer: true }
    );

    expect(".o_tour_recorder").toHaveCount(1);
    await click(".o_button_record");
    await animationFrame();
    await click(".click");
    await animationFrame();
    checkTourSteps(["div[name='field_name'] .o_div_3"]);
});

test("Click on input", async () => {
    await mountWithCleanup(
        `
        <div class=".o_parent">
            <input type="text" class="click o_input"/>
        </div>
    `,
        { noMainContainer: true }
    );

    expect(".o_tour_recorder").toHaveCount(1);
    await click(".o_button_record");
    await animationFrame();
    await click(".click");
    await animationFrame();
    expect(".o_button_record").toHaveText("Record (recording keyboard)");
    checkTourSteps([".o_input"]);
});

test("Click on tag that is inside a contenteditable", async () => {
    await mountWithCleanup(
        `
        <div class=".o_parent">
            <div class="o_editor" contenteditable="true">
                <p class="click oe-hint oe-command-temporary-hint" placeholder="My placeholder..."></p>
            </div>
        </div>
    `,
        { noMainContainer: true }
    );

    expect(".o_tour_recorder").toHaveCount(1);
    await click(".o_button_record");
    await animationFrame();
    await click(".click");
    await animationFrame();
    expect(".o_button_record").toHaveText("Record (recording keyboard)");
    checkTourSteps([".o_editor[contenteditable='true']"]);
});

test("Remove step during recording", async () => {
    await mountWithCleanup(
        `
        <div class="o_parent">
            <div class="o_child click"></div>
        </div>
    `,
        { noMainContainer: true }
    );

    expect(".o_tour_recorder").toHaveCount(1);
    await click(".o_button_record");
    await animationFrame();
    await click(".click");
    await animationFrame();
    checkTourSteps([".o_child"]);
    await click(".o_button_steps");
    await animationFrame();
    contains(".o_button_delete_step").click();
    await click(".o_button_steps");
    await animationFrame();
    checkTourSteps([]);
});

test("Edit input", async () => {
    await mountWithCleanup(
        `
        <div class="o_parent">
            <input type="text" class="click o_input"/>
        </div>
    `,
        { noMainContainer: true }
    );

    expect(".o_tour_recorder").toHaveCount(1);
    await click(".o_button_record");
    await animationFrame();
    await click(".click");
    await animationFrame();
    expect(".o_button_record").toHaveText("Record (recording keyboard)");
    expect(".click").toBeFocused();
    edit("Bismillah");
    await animationFrame();
    checkTourSteps([".o_input"]);
    expect(tourRecorder.state.steps.map((s) => s.run)).toEqual(["edit Bismillah"]);
});

test("Save a custom tour in the localStorage", async () => {
    await mountWithCleanup(
        `
        <div class="o_parent">
            <div class="click"></div>
        </div>
    `,
        { noMainContainer: true }
    );

    expect(".o_tour_recorder").toHaveCount(1);
    await click(".o_button_record");
    await animationFrame();
    await click(".click");
    await animationFrame();
    checkTourSteps([".o_parent > div"]);

    await click(".o_button_save");
    await animationFrame();
    await contains("input[name='name']").click();
    edit("tour_name");
    await animationFrame();
    await click(".o_button_save_confirm");
    await animationFrame();

    const customToursString = browser.localStorage.getItem("custom_tours");
    const customTours = JSON.parse(customToursString);
    expect(customTours).toEqual([
        {
            name: "tour_name",
            url: "/",
            test: true,
            steps: [
                {
                    trigger: ".o_parent > div",
                    run: "click",
                },
            ],
        },
    ]);
});

test("Save a custom tour and check the tour dialog", async () => {
    await mountWithCleanup(
        `
        <div class="o_parent">
            <div class="click"></div>
        </div>
    `,
        { noMainContainer: true }
    );

    expect(".o_tour_recorder").toHaveCount(1);
    await click(".o_button_record");
    await animationFrame();
    await click(".click");
    await animationFrame();
    checkTourSteps([".o_parent > div"]);

    await click(".o_button_save");
    await animationFrame();
    await contains("input[name='name']").click();
    edit("tour_name");
    await animationFrame();
    await click(".o_button_save_confirm");
    await animationFrame();
    expect(".o_notification_manager .o_notification_body").toHaveText(
        "Custom tour 'tour_name' has been added."
    );

    await click(".o_debug_manager > button");
    await contains(".o-dropdown-item:contains('Start Tour')").click();

    expect("table tr td:contains('tour_name')").toHaveCount(1);
});

test("Delete saved custom tour and check the tour dialog", async () => {
    await mountWithCleanup(
        `
        <div class="o_parent">
            <div class="click"></div>
        </div>
    `,
        { noMainContainer: true }
    );

    expect(".o_tour_recorder").toHaveCount(1);
    await click(".o_button_record");
    await animationFrame();
    await click(".click");
    await animationFrame();
    checkTourSteps([".o_parent > div"]);

    await click(".o_button_save");
    await animationFrame();
    await contains("input[name='name']").click();
    edit("tour_name");
    await animationFrame();
    await click(".o_button_save_confirm");
    await runAllTimers(); // Wait that the save notification disappear

    await click(".o_debug_manager > button");
    await contains(".o-dropdown-item:contains('Start Tour')").click();

    expect("table tr td:contains('tour_name')").toHaveCount(1);

    await click(".o_button_extra");
    await contains(".o-dropdown-item:contains('Delete')").click();

    expect(".o_notification_manager .o_notification_body").toHaveText(
        "Tour 'tour_name' correctly deleted."
    );
    expect("table tr td:contains('tour_name')").toHaveCount(0);

    const customToursString = browser.localStorage.getItem("custom_tours");
    const customTours = JSON.parse(customToursString);
    expect(customTours).toEqual([]);
});

test("Drag and drop", async () => {
    await mountWithCleanup(
        `
        <div class="o_parent">
            <div>
                <div class="o_drag">drag me</div>
            </div>
            <div class="o_drop"></div>
        </div>
    `,
        { noMainContainer: true }
    );

    expect(".o_tour_recorder").toHaveCount(1);
    await click(".o_button_record");
    await animationFrame();
    await contains(".o_drag").dragAndDrop(".o_drop");
    await animationFrame();
    checkTourSteps([".o_drag"]);
    expect(tourRecorder.state.steps.map((s) => s.run)).toEqual(["drag_and_drop .o_drop"]);
});

test("Edit contenteditable", async () => {
    await mountWithCleanup(
        `
        <div class="o_parent">
            <div class="o_editor click" contenteditable="true" style="width: 50px; height: 50px">
            </div>
        </div>
    `,
        { noMainContainer: true }
    );

    expect(".o_tour_recorder").toHaveCount(1);
    await click(".o_button_record");
    await animationFrame();
    await click(".click");
    await animationFrame();
    expect(".o_editor").toBeFocused();
    expect(".o_button_record").toHaveText("Record (recording keyboard)");
    keyDown("B");
    await animationFrame();
    queryOne(".o_editor").appendChild(document.createTextNode("Bismillah"));
    keyUp("B");
    await animationFrame();
    checkTourSteps([".o_editor[contenteditable='true']"]);
    expect(tourRecorder.state.steps.map((s) => s.run)).toEqual(["editor Bismillah"]);
});

test("Run custom tour", async () => {
    await mountWithCleanup(
        `
        <div class="o_parent">
            <div class="click">Bishmillah</div>
        </div>
    `,
        { noMainContainer: true }
    );

    expect(".o_tour_recorder").toHaveCount(1);
    await click(".o_button_record");
    await animationFrame();
    await click(".click");
    await animationFrame();
    checkTourSteps([".o_parent > div"]);

    await click(".o_button_save");
    await animationFrame();
    await contains("input[name='name']").click();
    edit("tour_name");
    await animationFrame();
    await click("input[name='url']");
    await animationFrame();
    edit("");
    await animationFrame();
    await click(".o_button_save_confirm");
    await animationFrame();
    expect(".o_notification_manager .o_notification_body").toHaveText(
        "Custom tour 'tour_name' has been added."
    );

    const divElement = queryOne(".click");
    divElement.addEventListener("click", () => {
        expect.step("Clicked on div");
    });

    const def = new Deferred();
    getService("tour_service").bus.addEventListener("TOUR-FINISHED", () => {
        def.resolve();
    });

    await click(".o_debug_manager > button");
    await contains(".o-dropdown-item:contains('Start Tour')").click();

    expect("table tr td:contains('tour_name')").toHaveCount(1);
    await click(".o_test_tour");

    // Max timeout before triggering an error from tour compiler
    await advanceTime(9999);
    await def;

    expect.verifySteps(["Clicked on div"]);
});

test("Run a custom tour twice doesn't trigger traceback", async () => {
    onRpc("/web/dataset/call_kw/web_tour.tour/consume", async () => {
        return Promise.resolve(true);
    });

    await mountWithCleanup(
        `
        <div class="o_parent">
            <div class="click">Bishmillah</div>
        </div>
    `,
        { noMainContainer: true }
    );

    expect(".o_tour_recorder").toHaveCount(1);
    await click(".o_button_record");
    await animationFrame();
    await click(".click");
    await animationFrame();
    checkTourSteps([".o_parent > div"]);

    await click(".o_button_save");
    await animationFrame();
    await contains("input[name='name']").click();
    edit("tour_name");
    await animationFrame();
    await click("input[name='url']");
    await animationFrame();
    edit("");
    await animationFrame();
    await click(".o_button_save_confirm");
    await animationFrame();
    expect(".o_notification_manager .o_notification_body").toHaveText(
        "Custom tour 'tour_name' has been added."
    );

    await click(".o_debug_manager > button");
    await contains(".o-dropdown-item:contains('Start Tour')").click();

    expect("table tr td:contains('tour_name')").toHaveCount(1);
    await click(".o_start_tour");
    await animationFrame();

    await click(".o_debug_manager > button");
    await contains(".o-dropdown-item:contains('Start Tour')").click();

    expect("table tr td:contains('tour_name')").toHaveCount(2);
    await click(".o_start_tour:eq(1)");
    await animationFrame();
    await advanceTime(100);

    await click(".o_parent > div");
    await advanceTime(100);
    await animationFrame();
});
