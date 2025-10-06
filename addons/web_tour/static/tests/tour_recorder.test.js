import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { click, edit, keyDown, keyUp, press, queryOne } from "@odoo/hoot-dom";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";
import {
    contains,
    defineWebModels,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { browser } from "@web/core/browser/browser";
import { TourRecorder } from "@web_tour/js/tour_recorder/tour_recorder";
import {
    TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY,
    tourRecorderState,
} from "@web_tour/js/tour_recorder/tour_recorder_state";
import { Component, xml } from "@odoo/owl";
import { useAutofocus } from "@web/core/utils/hooks";
import { WebClient } from "@web/webclient/webclient";

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
    await edit("Bismillah");
    await animationFrame();
    checkTourSteps([".o_input"]);
    expect(tourRecorder.state.steps.map((s) => s.run)).toEqual(["edit Bismillah"]);
});

test("Save custom tour", async () => {
    onRpc("web_tour.tour", "create", ({ args }) => {
        const tour = args[0][0];
        expect.step(tour.name);
        expect.step(tour.url);
        expect.step(tour.step_ids.length);
        return true;
    });

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
    await edit("tour_name");
    await animationFrame();
    await click(".o_button_save_confirm");
    await runAllTimers(); // Wait that the save notification disappear

    expect.verifySteps(["tour_name", "/", 1]);
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
    await keyDown("B");
    await animationFrame();
    queryOne(".o_editor").appendChild(document.createTextNode("Bismillah"));
    await keyUp("B");
    await animationFrame();
    checkTourSteps([".o_editor[contenteditable='true']"]);
    expect(tourRecorder.state.steps.map((s) => s.run)).toEqual(["editor Bismillah"]);
});

test("Selecting item in autocomplete field through Enter", async () => {
    class Dummy extends Component {
        static components = { AutoComplete };
        static template = xml`<AutoComplete id="'autocomplete'" value="'World'" sources="sources"/>`;
        static props = ["*"];

        sources = [
            {
                options: [
                    { label: "World", onSelect() {} },
                    { label: "Hello", onSelect() {} },
                ],
            },
        ];
    }

    expect(".o_tour_recorder").toHaveCount(1);
    await click(".o_button_record");
    await animationFrame();

    await mountWithCleanup(Dummy);
    await click("#autocomplete");
    await animationFrame();
    await press("Enter");
    checkTourSteps([
        ".o-autocomplete--input",
        ".o-autocomplete--dropdown-item > a:contains('World'), .fa-circle-o-notch",
    ]);
    expect(tourRecorder.state.steps.map((s) => s.run)).toEqual(["click", "click"]);
});

test("Edit input after autofocus", async () => {
    class Dummy extends Component {
        static components = {};
        static template = xml/*html*/ `
            <t>
                <div class="container">
                    <input type="text" class="o_input" t-ref="input"/>
                </div>
            </t>
        `;
        static props = ["*"];

        setup() {
            useAutofocus({ refName: "input" });
        }
    }

    expect(".o_tour_recorder").toHaveCount(1);
    await click(".o_button_record");
    await animationFrame();

    await mountWithCleanup(Dummy);

    expect(".o_input").toBeFocused();
    expect(".o_button_record").toHaveText("Record");
    await edit("Bismillah");
    await animationFrame();
    expect(".o_button_record").toHaveText("Record (recording keyboard)");
    checkTourSteps([".o_input"]);
    expect(tourRecorder.state.steps.map((s) => s.run)).toEqual(["edit Bismillah"]);
});

test("Check Tour Recorder State", async () => {
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
    expect(tourRecorderState.isRecording()).toBe("0");
    await click(".o_button_record");
    await animationFrame();
    expect(tourRecorderState.isRecording()).toBe("1");
    expect(tourRecorderState.getCurrentTourRecorder()).toEqual([]);
    await click(".click");
    await animationFrame();
    checkTourSteps([".o_child_1"]);

    await click(".o_child_2");
    await animationFrame();
    checkTourSteps([".o_child_1", ".o_child_2"]);
    expect(tourRecorderState.getCurrentTourRecorder()).toEqual([
        { trigger: ".o_child_1", run: "click" },
        { trigger: ".o_child_2", run: "click" },
    ]);

    await click(".o_button_record");
    await animationFrame();
    await click(".o_tour_recorder_close_button");
    await animationFrame();
    expect(tourRecorderState.getCurrentTourRecorder()).toEqual([]);
    expect(tourRecorderState.isRecording()).toBe("0");
});
