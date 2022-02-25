/** @odoo-module **/

import { registry } from "@web/core/registry";
import { scrollerService } from "@web/core/scroller_service";
import { scrollTo } from "@web/core/utils/scrolling";
import { registerCleanup } from "../helpers/cleanup";
import { makeTestEnv } from "../helpers/mock_env";
import { click, getFixture, mount, nextTick } from "../helpers/utils";

const { Component, xml } = owl;
const serviceRegistry = registry.category("services");

let env;
let target;

QUnit.module("ScrollerService", {
    async beforeEach() {
        serviceRegistry.add("scroller", scrollerService);
        env = await makeTestEnv();
        target = getFixture();
    },
});

QUnit.test("Ignore empty hrefs", async (assert) => {
    assert.expect(1);

    class MyComponent extends Component {}
    MyComponent.template = xml/* xml */ `
        <div class="my_component">
            <a href="#" class="inactive_link">This link does nothing</a>
            <button class="btn btn-secondary">
                <a href="#">
                    <i class="fa fa-trash"/>
                </a>
            </button>
        </div>`;

    await mount(MyComponent, target, { env });

    /**
     * To determine whether the hash changed we need to use a custom hash for
     * this test. Note that changing the hash does not reload the page and is
     * rollbacked after the test so it should not not interfere with the test suite.
     */
    const initialHash = location.hash;
    const testHash = initialHash ? `${initialHash}&testscroller` : "#testscroller";
    location.hash = testHash;
    registerCleanup(() => (location.hash = initialHash));

    target.querySelector(".inactive_link").click();
    await nextTick();

    target.querySelector(".fa.fa-trash").click();
    await nextTick();

    assert.strictEqual(location.hash, testHash);
});

QUnit.test("Simple rendering with a scroll", async (assert) => {
    assert.expect(2);
    const scrollableParent = document.createElement("div");
    scrollableParent.style.overflow = "scroll";
    scrollableParent.style.height = "150px";
    scrollableParent.style.width = "400px";
    target.append(scrollableParent);

    class MyComponent extends Component {}
    MyComponent.template = xml/* xml */ `
        <div class="o_content">
            <a href="#scrollToHere"  class="btn btn-primary">sroll to ...</a>
            <p>
                Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed non risus.
                Suspendisse lectus tortor, dignissim sit amet, adipiscing nec, ultricies sed,
                dolor. Cras elementum ultrices diam. Maecenas ligula massa, varius a, semper
                congue, euismod non, mi. Proin porttitor, orci nec nonummy molestie, enim est
                eleifend mi, non fermentum diam nisl sit amet erat. Duis semper. Duis arcu
                massa, scelerisque vitae, consequat in, pretium a, enim. Pellentesque congue. Ut
                in risus volutpat libero pharetra tempor. Cras vestibulum bibendum augue. Praesent
                egestas leo in pede. Praesent blandit odio eu enim. Pellentesque sed dui ut augue
                blandit sodales. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices
                posuere cubilia Curae; Aliquam nibh. Mauris ac mauris sed pede pellentesque
                fermentum. Maecenas adipiscing ante non diam sodales hendrerit.
            </p>
            <p>
                Ut velit mauris, egestas sed, gravida nec, ornare ut, mi. Aenean ut orci vel massa
                suscipit pulvinar. Nulla sollicitudin. Fusce varius, ligula non tempus aliquam, nunc
                turpis ullamcorper nibh, in tempus sapien eros vitae ligula. Pellentesque rhoncus
                nunc et augue. Integer id felis. Curabitur aliquet pellentesque diam. Integer quis
                metus vitae elit lobortis egestas. Lorem ipsum dolor sit amet, consectetuer adipiscing
                elit. Morbi vel erat non mauris convallis vehicula. Nulla et sapien. Integer tortor
                tellus, aliquam faucibus, convallis id, congue eu, quam. Mauris ullamcorper felis
                vitae erat. Proin feugiat, augue non elementum posuere, metus purus iaculis lectus,
                et tristique ligula justo vitae magna.
            </p>
            <p>
                Aliquam convallis sollicitudin purus. Praesent aliquam, enim at fermentum mollis,
                ligula massa adipiscing nisl, ac euismod nibh nisl eu lectus. Fusce vulputate sem
                at sapien. Vivamus leo. Aliquam euismod libero eu enim. Nulla nec felis sed leo
                placerat imperdiet. Aenean suscipit nulla in justo. Suspendisse cursus rutrum
                augue. Nulla tincidunt tincidunt mi. Curabitur iaculis, lorem vel rhoncus faucibus,
                felis magna fermentum augue, et ultricies lacus lorem varius purus. Curabitur eu amet.
            </p>
            <div id="scrollToHere">sroll here!</div>
        </div>
    `;
    await mount(MyComponent, scrollableParent, { env });

    assert.strictEqual(scrollableParent.scrollTop, 0);
    await click(scrollableParent, ".btn.btn-primary");
    assert.ok(scrollableParent.scrollTop !== 0);
});

QUnit.test("Rendering with multiple anchors and scrolls", async (assert) => {
    assert.expect(4);
    const scrollableParent = document.createElement("div");
    scrollableParent.style.overflow = "scroll";
    scrollableParent.style.height = "150px";
    scrollableParent.style.width = "400px";
    target.append(scrollableParent);

    class MyComponent extends Component {}
    MyComponent.template = xml/* xml */ `
        <div class="o_content">
            <h2 id="anchor3">ANCHOR 3</h2>
            <a href="#anchor1" class="link1">sroll to ...</a>
            <p>
                Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed non risus.
                Suspendisse lectus tortor, dignissim sit amet, adipiscing nec, ultricies sed,
                dolor. Cras elementum ultrices diam. Maecenas ligula massa, varius a, semper
                congue, euismod non, mi. Proin porttitor, orci nec nonummy molestie, enim est
                eleifend mi, non fermentum diam nisl sit amet erat. Duis semper. Duis arcu
                massa, scelerisque vitae, consequat in, pretium a, enim. Pellentesque congue. Ut
                in risus volutpat libero pharetra tempor. Cras vestibulum bibendum augue. Praesent
                egestas leo in pede. Praesent blandit odio eu enim. 
            </p>
            <p>
                Ut velit mauris, egestas sed, gravida nec, ornare ut, mi. Aenean ut orci vel massa
                suscipit pulvinar. Nulla sollicitudin. Fusce varius, ligula non tempus aliquam, nunc
                turpis ullamcorper nibh, in tempus sapien eros vitae ligula. Pellentesque rhoncus
                nunc et augue. Integer id felis. Curabitur aliquet pellentesque diam. Integer quis
                metus vitae elit lobortis egestas. Lorem ipsum dolor sit amet, consectetuer adipiscing
                elit. Morbi vel erat non mauris convallis vehicula. Nulla et sapien. Integer tortor
                tellus, aliquam faucibus, convallis id, congue eu, quam. 
            </p>
            <table>
                <tbody>
                    <tr>
                        <td>
                            <h2 id="anchor2">ANCHOR 2</h2>
                            <a href="#anchor3" class="link3">TO ANCHOR 3</a>
                            <p>
                                The table forces you to get the precise position of the element.
                            </p>
                        </td>
                    </tr>
                </tbody>
            </table>
            <p>
                Aliquam convallis sollicitudin purus. Praesent aliquam, enim at fermentum mollis,
                ligula massa adipiscing nisl, ac euismod nibh nisl eu lectus. Fusce vulputate sem
                at sapien. Vivamus leo. Aliquam euismod libero eu enim. Nulla nec felis sed leo
                placerat imperdiet. Aenean suscipit nulla in justo. Suspendisse cursus rutrum
                augue.
            </p>
            <div id="anchor1">sroll here!</div>
            <a href="#anchor2" class="link2">TO ANCHOR 2</a>
        </div>
    `;
    await mount(MyComponent, scrollableParent, { env });
    assert.strictEqual(scrollableParent.scrollTop, 0);
    await click(scrollableParent, ".link1");

    // The element must be contained in the scrollable parent (top and bottom)
    const isVisible = (el) => {
        return (
            el.getBoundingClientRect().bottom <= scrollableParent.getBoundingClientRect().bottom &&
            el.getBoundingClientRect().top >= scrollableParent.getBoundingClientRect().top
        );
    };
    assert.ok(isVisible(scrollableParent.querySelector("#anchor1")));
    await click(scrollableParent, ".link2");
    assert.ok(isVisible(scrollableParent.querySelector("#anchor2")));
    await click(scrollableParent, ".link3");
    assert.ok(isVisible(scrollableParent.querySelector("#anchor3")));
});

QUnit.test("clicking anchor when no scrollable", async (assert) => {
    assert.expect(3);
    const scrollableParent = document.createElement("div");
    scrollableParent.style.overflow = "auto";
    scrollableParent.style.height = "150px";
    scrollableParent.style.width = "400px";
    target.append(scrollableParent);

    class MyComponent extends Component {}
    MyComponent.template = xml/* xml */ `
        <div class="o_content">
            <a href="#scrollToHere"  class="btn btn-primary">scroll to ...</a>
            <div class="active-container">
                <p>There is no scrollable with only the height of this element</p>
            </div>
            <div class="inactive-container" style="max-height: 0">
                <h2>There should be no scrollable if this element has 0 height</h2>
                <p>
                    Aliquam convallis sollicitudin purus. Praesent aliquam, enim at fermentum mollis,
                    ligula massa adipiscing nisl, ac euismod nibh nisl eu lectus. Fusce vulputate sem
                    at sapien. Vivamus leo. Aliquam euismod libero eu enim. Nulla nec felis sed leo
                    placerat imperdiet. Aenean suscipit nulla in justo. Suspendisse cursus rutrum
                    augue. Nulla tincidunt tincidunt mi. Curabitur iaculis, lorem vel rhoncus faucibus,
                    felis magna fermentum augue, et ultricies lacus lorem varius purus. Curabitur eu amet.
                </p>
                <div id="scrollToHere">should try to scroll here only if scrollable!</div>
            </div>
        </div>
    `;
    await mount(MyComponent, scrollableParent, { env });
    assert.strictEqual(scrollableParent.scrollTop, 0);
    await click(scrollableParent, ".btn.btn-primary");
    assert.ok(scrollableParent.scrollTop === 0, "no scroll happened");
    scrollableParent.querySelector(".inactive-container").style.maxHeight = "unset";
    await click(scrollableParent, ".btn.btn-primary");
    assert.ok(scrollableParent.scrollTop !== 0, "a scroll happened");
});

QUnit.test("clicking anchor when multi levels scrollables", async (assert) => {
    assert.expect(4);
    const scrollableParent = document.createElement("div");
    scrollableParent.style.overflow = "auto";
    scrollableParent.style.height = "150px";
    scrollableParent.style.width = "400px";
    target.append(scrollableParent);

    class MyComponent extends Component {}
    MyComponent.template = xml/* xml */ `
        <div class="o_content scrollable-1">
            <a href="#scroll1"  class="btn1 btn btn-primary">go to level 2 anchor</a>
            <div>
                <p>This is some content</p>
                <p>
                    Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed non risus.
                    Suspendisse lectus tortor, dignissim sit amet, adipiscing nec, ultricies sed,
                    dolor. Cras elementum ultrices diam. Maecenas
                </p>
            </div>
            <div class="scrollable-2" style="background: green; overflow: auto; height: 100px;">
                <h2>This is level 1 of scrollable</h2>
                <p>
                    Aliquam convallis sollicitudin purus. Praesent aliquam, enim at fermentum mollis,
                    ligula massa adipiscing nisl, ac euismod nibh nisl eu lectus. Fusce vulputate sem
                    at sapien. Vivamus leo. Aliquam euismod libero eu enim. Nulla nec felis sed leo
                    placerat imperdiet. Aenean suscipit nulla in justo. Suspendisse cursus rutrum
                    augue. Nulla tincidunt tincidunt mi. Curabitur iaculis, lorem vel rhoncus faucibus,
                    felis magna fermentum augue, et ultricies lacus lorem varius purus. Curabitur eu amet.
                </p>
                <div style="background: lime;">
                    <h2>This is level 2 of scrollable</h2>
                    <p>
                        Aliquam convallis sollicitudin purus. Praesent aliquam, enim at fermentum mollis,
                        ligula massa adipiscing nisl, ac euismod nibh nisl eu lectus. Fusce vulputate sem
                        at sapien. Vivamus leo. Aliquam euismod libero eu enim. Nulla nec felis sed leo
                        placerat imperdiet. Aenean suscipit nulla in justo. Suspendisse cursus rutrum
                        augue. Nulla tincidunt tincidunt mi. Curabitur iaculis, lorem vel rhoncus faucibus,
                        felis magna fermentum augue, et ultricies lacus lorem varius purus. Curabitur eu amet.
                    </p>
                    <div id="scroll1" style="background: orange;">this element is contained in a scrollable metaverse!</div>
                        <a href="#scroll2"  class="btn2 btn btn-primary">go to level 1 anchor</a>
                        <p>
                            Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed non risus.
                            Suspendisse lectus tortor, dignissim sit amet, adipiscing nec, ultricies sed,
                            dolor. Cras elementum ultrices diam. Maecenas ligula massa, varius a, semper
                            congue, euismod non, mi. Proin porttitor, orci nec nonummy molestie, enim est
                            eleifend mi, non fermentum diam nisl sit amet erat. Duis semper. Duis arcu
                            massa, scelerisque vitae, consequat in, pretium a, enim. Pellentesque congue. Ut
                            in risus volutpat libero pharetra tempor. Cras vestibulum bibendum augue. Praesent
                            egestas leo in pede. Praesent blandit odio eu enim. 
                        </p>
                </div>
            </div>
            <div id="scroll2" style="background: orange;">this is an anchor at level 1!</div>
            <p>
                    Aliquam convallis sollicitudin purus. Praesent aliquam, enim at fermentum mollis,
                    ligula massa adipiscing nisl, ac euismod nibh nisl eu lectus. Fusce vulputate sem
                    at sapien. Vivamus leo. Aliquam euismod libero eu enim. Nulla nec felis sed leo
                    at sapien. Vivamus leo. Aliquam euismod libero eu enim. Nulla nec felis sed leo
                    placerat imperdiet. Aenean suscipit nulla in justo. Suspendisse cursus rutrum
                    augue. Nulla tincidunt tincidunt mi. Curabitur iaculis, lorem vel rhoncus faucibus,
                    felis magna fermentum augue, et ultricies lacus lorem varius purus. Curabitur eu amet.
                </p>
        </div>
    `;
    await mount(MyComponent, scrollableParent, { env });

    const border = (el) => {
        // Returns the state of the element in relation to the borders
        const element = el.getBoundingClientRect();
        const scrollable = scrollableParent.getBoundingClientRect();
        return {
            top: parseInt(element.top - scrollable.top) < 10,
            bottom: parseInt(scrollable.bottom - element.bottom) < 10,
        };
    };

    assert.strictEqual(scrollableParent.scrollTop, 0);
    await click(scrollableParent, ".btn1");
    assert.ok(
        border(scrollableParent.querySelector("#scroll1")).top,
        "the element must be near the top border"
    );
    assert.ok(
        border(scrollableParent.querySelector("#scroll1")).top,
        "the scrollable inside level 1 must be near the top border"
    );
    await click(scrollableParent, ".btn2");
    assert.ok(
        border(scrollableParent.querySelector("#scroll2")).top,
        "the element must be near the top border"
    );
});

QUnit.test("Simple scroll to HTML elements", async (assert) => {
    assert.expect(6);
    const scrollableParent = document.createElement("div");
    scrollableParent.style.overflow = "scroll";
    scrollableParent.style.height = "150px";
    scrollableParent.style.width = "400px";
    target.append(scrollableParent);

    class MyComponent extends Component {}
    MyComponent.template = xml/* xml */ `
        <div class="o_content">
            <p>
                Aliquam convallis sollicitudin purus. 
            </p>
            <div id="o-div-1">A div is an HTML element</div>
            <p>
                Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed non risus.
                Suspendisse lectus tortor, dignissim sit amet, adipiscing nec, ultricies sed,
                dolor. Cras elementum ultrices diam. Maecenas ligula massa, varius a, semper
                congue, euismod non, mi. Proin porttitor, orci nec nonummy molestie, enim est
                eleifend mi, non fermentum diam nisl sit amet erat. Duis semper. Duis arcu
                massa, scelerisque vitae, consequat in, pretium a, enim. Pellentesque congue. Ut
                in risus volutpat libero pharetra tempor. Cras vestibulum bibendum augue. Praesent
                egestas leo in pede. Praesent blandit odio eu enim. 
            </p>
            <p>
                Ut velit mauris, egestas sed, gravida nec, ornare ut, mi. Aenean ut orci vel massa
                suscipit pulvinar. Nulla sollicitudin. Fusce varius, ligula non tempus aliquam, nunc
                turpis ullamcorper nibh, in tempus sapien eros vitae ligula. Pellentesque rhoncus
                nunc et augue. Integer id felis. Curabitur aliquet pellentesque diam. Integer quis
                metus vitae elit lobortis egestas. Lorem ipsum dolor sit amet, consectetuer adipiscing
                elit. Morbi vel erat non mauris convallis vehicula. Nulla et sapien. Integer tortor
                tellus, aliquam faucibus, convallis id, congue eu, quam. 
            </p>
            <div id="o-div-2">A div is an HTML element</div>
            <p>
                Aliquam convallis sollicitudin purus. Praesent aliquam, enim at fermentum mollis,
                ligula massa adipiscing nisl, ac euismod nibh nisl eu lectus. Fusce vulputate sem
                at sapien. Vivamus leo. Aliquam euismod libero eu enim. Nulla nec felis sed leo
                placerat imperdiet. Aenean suscipit nulla in justo. Suspendisse cursus rutrum
                augue.
            </p>
        </div>
    `;
    await mount(MyComponent, scrollableParent, { env });
    assert.strictEqual(scrollableParent.scrollTop, 0);

    // The element must be contained in the scrollable parent (top and bottom)
    const isVisible = (el) => {
        return (
            el.getBoundingClientRect().bottom <= scrollableParent.getBoundingClientRect().bottom &&
            el.getBoundingClientRect().top >= scrollableParent.getBoundingClientRect().top
        );
    };

    const border = (el) => {
        // Returns the state of the element in relation to the borders
        const element = el.getBoundingClientRect();
        const scrollable = scrollableParent.getBoundingClientRect();
        return {
            top: parseInt(element.top - scrollable.top) === 0,
            bottom: parseInt(scrollable.bottom - element.bottom) === 0,
        };
    };

    // When using scrollTo to an element, this should just scroll
    // until the element is visible in the scrollable parent
    const div_1 = scrollableParent.querySelector("#o-div-1");
    const div_2 = scrollableParent.querySelector("#o-div-2");
    assert.ok(isVisible(div_1) && !isVisible(div_2), "only the first div is visible");
    assert.ok(!border(div_1).top, "the element is not at the top border");
    scrollTo(div_2);
    assert.ok(!isVisible(div_1) && isVisible(div_2), "only the second div is visible");
    assert.ok(border(div_2).bottom, "the element must be at the bottom border");
    scrollTo(div_1);
    assert.ok(border(div_1).top, "the element must be at the top border");
});
