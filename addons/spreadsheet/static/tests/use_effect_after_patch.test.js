import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { helpers, hooks } from "@odoo/o-spreadsheet";
import { Component, signal, xml } from "@odoo/owl";
import {
    createCarousel,
    createSheet,
    deleteSheet,
    setCellContent,
} from "@spreadsheet/../tests/helpers/commands";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { createModelAndMountSpreadsheet } from "@spreadsheet/../tests/helpers/ui";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { unPatchRenderer } from "./hoot_override";

/**
    In o-spreadsheet, when using canvas we cannot use a simple `useEffect`
    to replace the old `useLayoutEffect`.

    We cannot use an `useEffect` because it would trigger before the owl
    render. So if we do a change that'd destroy the component, first
    we'd trigger the useEffect (on a wrong state, crashing), then the component
    parent would be rendered and destroy the child component with the canvas.

    We cannot use `onPatched` either as for simple components with only a
    canvas and no reactive value in the template, it is never triggered.

    Our solution is a hook `useEffectAfterPatch`, that has an effect that
    triggers `component.render(false)`, and runs the callback in an
    `onPatched`.
 */

const { useEffectAfterPatch } = hooks;
const { toZone } = helpers;

describe.current.tags("desktop");
defineSpreadsheetModels();

unPatchRenderer(); // use real renderer plugin for those tests

describe("useEffectAfterPatch", () => {
    test("a tracked signal re-runs the callback, with the DOM already patched", async () => {
        const value = signal("a");
        class Comp extends Component {
            static template = xml`<div class="target" t-ref="this.ref" t-out="this.value()"/>`;
            value = value;
            ref = signal.ref();
            setup() {
                useEffectAfterPatch(() => {
                    this.value(); // tracked dependency
                    expect.step(`run with text:${this.ref().textContent}`);
                });
            }
        }
        await mountWithCleanup(Comp);
        expect.verifySteps(["run with text:a"]);

        value.set("b");
        await animationFrame();

        expect(".target").toHaveText("b");
        expect.verifySteps(["run with text:b"]);
    });

    test("the callback re-runs even when the dependency is not used by the template", async () => {
        let drawCount = 0;
        const value = signal("a");
        class Comp extends Component {
            static template = xml`<canvas class="target"/>`;
            setup() {
                useEffectAfterPatch(() => {
                    value(); // tracked dependency
                    expect.step(`draw:${drawCount++}`);
                });
            }
        }
        await mountWithCleanup(Comp);
        expect.verifySteps(["draw:0"]);

        value.set("b");
        await animationFrame();
        expect.verifySteps(["draw:1"]);
    });
});

describe("useEffectAfterPatch is used in a carousel", () => {
    test("deleting the sheet a carousel data view points to does not crash", async () => {
        const { model } = await createModelAndMountSpreadsheet();
        const dataSheetId = "dataSheet";
        createSheet(model, { sheetId: dataSheetId });
        setCellContent(model, "A1", "10", dataSheetId);
        createCarousel(
            model,
            {
                items: [
                    {
                        type: "carouselDataView",
                        rangeData: model.getters.getRangeDataFromZone(dataSheetId, toZone("A1:B5")),
                    },
                ],
            },
            "carouselFigureId"
        );
        await animationFrame();
        expect(".o-standalone-viewport").toHaveCount(1);

        // If we draw the carousel data view in a simple useEffect, it would run before the DOM is patched. That means
        // that we'd try to draw a sheet that does not exist anymore, and only in the next owl render would the canvas
        // be removed
        deleteSheet(model, dataSheetId);
        await animationFrame();

        expect(".o-standalone-viewport").toHaveCount(0);
        expect(".o-carousel").toHaveCount(1);
    });
});
