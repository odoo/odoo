import {
    advanceTime,
    animationFrame,
    beforeEach,
    describe,
    expect,
    leave,
    queryAll,
    queryOne,
    queryRect,
    test,
    waitFor,
} from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { contains, mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { pointerState } from "@web_tutorial/pointer/pointer_state";
import { TutorialPointer } from "@web_tutorial/pointer/tutorial_pointer";

describe.current.tags("desktop");

class Root extends Component {
    static components = { TutorialPointer };
    static template = xml`
        <div class="o_scroller" style="overflow: auto; width: 400px; height: 300px;">
            <div style="position: relative; width: 2000px; height: 2000px;">
                <button class="o_foo" style="position: absolute; left: 100px; top: 50px;">Foo</button>
                <button class="o_bar" style="position: absolute; left: 100px; top: 50px;">Bar</button>
                <button class="o_far" style="position: absolute; left: 1500px; top: 1500px;">Far</button>
            </div>
        </div>
        <button class="o_edge" style="position: fixed; left: 0; top: 0;">Edge</button>
        <TutorialPointer/>
    `;
}

beforeEach(() => {
    patchWithCleanup(pointerState, {
        alwaysOpen: false,
        ballHidden: false,
        chapterSizes: "",
        content: "",
        invalid: false,
        onNext: undefined,
        onSkip: undefined,
        progress: "",
        stepIndex: -1,
        trigger: undefined,
        triggerRect: "",
    });
});

test("the ball follows its trigger, and hides without one", async () => {
    await mountWithCleanup(Root);
    expect(".o_tutorial_pointer").toHaveCount(0);

    pointerState.trigger = queryOne(".o_foo");
    await animationFrame();
    const fooRect = queryRect(".o_foo");
    const ballRect = queryRect(".o_tutorial_pointer");
    expect(ballRect.top).toBeGreaterThan(fooRect.bottom - 1);

    queryOne(".o_foo").remove();
    pointerState.trigger = queryOne(".o_bar");
    await animationFrame();
    expect(queryRect(".o_tutorial_pointer")).toEqual(ballRect);

    pointerState.trigger = undefined;
    await animationFrame();
    expect(".o_tutorial_pointer").toHaveCount(0);
});

test("the ball follows its trigger moved by a change of the layout", async () => {
    await mountWithCleanup(Root);
    pointerState.trigger = queryOne(".o_foo");
    await animationFrame();
    const ballRect = queryRect(".o_tutorial_pointer");

    queryOne(".o_foo").style.top = "150px";
    pointerState.triggerRect = "moved";
    await animationFrame();
    expect(queryRect(".o_tutorial_pointer").top).toBe(ballRect.top + 100);
});

test("the bubble opens while hovered if it has a help, and shortly after", async () => {
    await mountWithCleanup(Root);
    pointerState.trigger = queryOne(".o_foo");
    await animationFrame();
    await contains(".o_tutorial_pointer").hover();
    expect(".o_tutorial_pointer_content").toHaveCount(0);

    pointerState.content = "Click Foo";
    await leave();
    await contains(".o_tutorial_pointer").hover();
    expect(".o_tutorial_pointer_content span").toHaveText("Click Foo");

    await contains(".o_tutorial_pointer_content").hover();
    await advanceTime(TutorialPointer.closeDelay);
    expect(".o_tutorial_pointer_content").toHaveCount(1);

    await leave();
    await advanceTime(TutorialPointer.closeDelay - 100);
    await contains(".o_tutorial_pointer").hover();
    await leave();
    await advanceTime(TutorialPointer.closeDelay - 100);
    expect(".o_tutorial_pointer_content").toHaveCount(1);
    await advanceTime(100);
    expect(".o_tutorial_pointer_content").toHaveCount(0);
});

test("the bubble is shown alone, next to its trigger, once the ball is hidden", async () => {
    await mountWithCleanup(Root);
    Object.assign(pointerState, {
        alwaysOpen: true,
        ballHidden: true,
        content: "Click Foo",
        trigger: queryOne(".o_foo"),
    });
    await waitFor(".o_tutorial_pointer_content:contains(Click Foo)");
    expect(".o_tutorial_pointer_tip").toHaveCount(0);
    expect(queryRect(".o_tutorial_pointer_content").top).toBeGreaterThan(
        queryRect(".o_foo").bottom - 1
    );
});

test("the bubble is below the ball, its arrow pointing at the ball", async () => {
    await mountWithCleanup(Root);
    Object.assign(pointerState, {
        alwaysOpen: true,
        content: "Click Foo",
        trigger: queryOne(".o_foo"),
    });
    await waitFor(".o_tutorial_pointer_content");
    const ballRect = queryRect(".o_tutorial_pointer_tip");
    const arrowRect = queryRect(".o_tutorial_pointer_content .popover-arrow");
    expect(".o_tutorial_pointer_tip").toHaveClass("o_bottom");
    expect(queryRect(".o_tutorial_pointer_content").top).toBeGreaterThan(ballRect.bottom - 1);
    expect(Math.round(arrowRect.left + arrowRect.width / 2)).toBe(
        Math.round(ballRect.left + ballRect.width / 2)
    );
});

test("the bubble shows the progress, and its buttons call back", async () => {
    await mountWithCleanup(Root);
    Object.assign(pointerState, {
        alwaysOpen: true,
        content: "Click Foo",
        onNext: () => expect.step("next"),
        onSkip: () => expect.step("skip"),
        progress: "Step 1/3",
        trigger: queryOne(".o_foo"),
    });
    await animationFrame();
    expect(".o_tutorial_progress").toHaveText("Step 1/3");
    expect(".o_tutorial_pointer_content").not.toHaveClass("o_tutorial_invalid");

    await contains(".o_tutorial_next").click();
    await contains(".o_tutorial_skip").click();
    expect.verifySteps(["next", "skip"]);

    pointerState.invalid = true;
    await animationFrame();
    expect(".o_tutorial_pointer_content").toHaveClass("o_tutorial_invalid");
});

test("the bubble shows the progress bar of the tutorial, by chapter", async () => {
    await mountWithCleanup(Root);
    Object.assign(pointerState, {
        alwaysOpen: true,
        content: "Click Foo",
        trigger: queryOne(".o_foo"),
    });
    await animationFrame();
    expect(".o_tutorial_progress_bar").toHaveCount(0);

    Object.assign(pointerState, { chapterSizes: "2,3,1", progress: "Step 3/6", stepIndex: 2 });
    await animationFrame();
    expect(
        queryAll(".o_tutorial_progress_chapter").map((chapter) =>
            [...chapter.children].map((step) => step.className.match(/o_(done|current|todo)/)[1])
        )
    ).toEqual([["done", "done"], ["current", "todo", "todo"], ["todo"]]);
});

test("the ball waits on the edge of the scroll parent of a trigger out of view, on both axes", async () => {
    await mountWithCleanup(Root);
    Object.assign(pointerState, {
        alwaysOpen: true,
        content: "Click Far",
        onNext: () => {},
        trigger: queryOne(".o_far"),
    });
    const scroller = queryOne(".o_scroller");
    const cases = [
        [0, 1300, "o_top", "Scroll down to reach the next step."],
        [1700, 1300, "o_bottom", "Scroll up to reach the next step."],
        [1400, 0, "o_left", "Scroll right to reach the next step."],
        [1400, 1600, "o_right", "Scroll left to reach the next step."],
    ];
    for (const [scrollTop, scrollLeft, sideClass, hint] of cases) {
        scroller.scrollTo({ top: scrollTop, left: scrollLeft });
        await waitFor(
            `.o_tutorial_pointer.${sideClass} .o_tutorial_pointer_content:contains(${hint})`
        );
        expect(".o_tutorial_next").toHaveCount(0);
        const ballRect = queryRect(".o_tutorial_pointer");
        const scrollerRect = queryRect(scroller);
        expect(ballRect.top).toBeGreaterThan(scrollerRect.top - 1);
        expect(ballRect.bottom).toBeLessThan(scrollerRect.bottom + 1);
    }

    await contains(".o_tutorial_pointer_content").click();
    await waitFor(".o_tutorial_pointer_content:contains(Click Far)");
    expect(".o_tutorial_next").toHaveCount(1);
});

test("the bubble is shifted not to overflow the window", async () => {
    await mountWithCleanup(Root);
    Object.assign(pointerState, {
        alwaysOpen: true,
        content: "A help long enough to overflow the window if centered on the ball",
        trigger: queryOne(".o_edge"),
    });
    await animationFrame();
    expect(queryRect(".o_tutorial_pointer_content").left).toBeGreaterThan(
        TutorialPointer.margin - 1
    );
});
