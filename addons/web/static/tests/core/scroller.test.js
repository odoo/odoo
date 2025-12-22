import { expect, test } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { getService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { click, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { browser } from "@web/core/browser/browser";
import { scrollTo } from "@web/core/utils/scrolling";
import { WebClient } from "@web/webclient/webclient";
import { registry } from "@web/core/registry";
import { redirect } from "@web/core/utils/urls";

test("Ignore empty hrefs", async () => {
    class MyComponent extends Component {
        static template = xml/* xml */ `
            <div class="my_component">
                <a href="#" class="inactive_link">This link does nothing</a>
                <button class="btn btn-secondary">
                    <a href="#">
                        <i class="fa fa-trash"/>
                    </a>
                </button>
            </div>`;
        static props = ["*"];
    }

    await mountWithCleanup(MyComponent);

    browser.location.hash = "#testscroller";

    await click(".inactive_link");
    await animationFrame();

    await click(".fa.fa-trash");
    await animationFrame();

    expect(browser.location.hash).toBe("#testscroller");
});

test("Simple rendering with a scroll", async () => {
    class MyComponent extends Component {
        static template = xml/* xml */ `
            <div id="scroller" style="overflow: scroll; width: 400px; height: 150px">
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
            </div>
        `;
        static props = ["*"];
    }
    await mountWithCleanup(MyComponent);

    expect(queryOne("#scroller").scrollTop).toBe(0);
    await click(".btn.btn-primary");
    await animationFrame();
    expect(queryOne("#scroller").scrollTop).toBeGreaterThan(0);
});

test("clicking to scroll on a web client shouldn't open the default app", async (assert) => {
    expect.assertions(2);

    class MyComponent extends Component {
        static template = xml/* xml */ `
            <div class="o_content" style="overflow:scroll;height:150px;width:400px">
                <a href="#scrollToHere"  class="alert-link" role="button">sroll to ...</a>
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
        static props = ["*"];
        static path = "my_component";
    }
    registry.category("actions").add("my_component", MyComponent);
    await mountWithCleanup(WebClient);
    await getService("action").doAction("my_component");

    const scrollableParent = document.querySelector(".o_content");
    expect(scrollableParent.scrollTop).toBe(0);
    await click(".alert-link");
    expect(scrollableParent.scrollTop).not.toBe(0);
});

test("Rendering with multiple anchors and scrolls", async () => {
    class MyComponent extends Component {
        static template = xml/* xml */ `
            <div id="scroller" style="overflow: scroll; width: 400px; height: 150px">
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
            </div>
        `;
        static props = ["*"];
    }

    await mountWithCleanup(MyComponent);
    const scrollableParent = queryOne("#scroller");
    expect(scrollableParent.scrollTop).toBe(0);
    await click(".link1");

    // The element must be contained in the scrollable parent (top and bottom)
    const isVisible = (selector) => {
        const el = queryOne(selector);
        return (
            el.getBoundingClientRect().bottom <= scrollableParent.getBoundingClientRect().bottom &&
            el.getBoundingClientRect().top >= scrollableParent.getBoundingClientRect().top
        );
    };

    expect(isVisible("#anchor1")).toBe(true);
    await click(".link2");
    await animationFrame();
    expect(isVisible("#anchor2")).toBe(true);
    await click(".link3");
    await animationFrame();
    expect(isVisible("#anchor3")).toBe(true);
});

test("clicking anchor when no scrollable", async () => {
    class MyComponent extends Component {
        static template = xml/* xml */ `
            <div id="scroller" style="overflow: auto; width: 400px; height: 150px">
                <div class="o_content">
                    <a href="#scrollToHere"  class="btn btn-primary">scroll to ...</a>
                    <div class="active-container">
                        <p>There is no scrollable with only the height of this element</p>
                    </div>
                    <div class="inactive-container" style="max-height: 0; overflow: hidden">
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
            </div>
        `;
        static props = ["*"];
    }

    await mountWithCleanup(MyComponent);
    const scrollableParent = queryOne("#scroller");
    expect(scrollableParent.scrollTop).toBe(0);
    await click(".btn.btn-primary");
    await animationFrame();
    expect(scrollableParent.scrollTop).toBe(0, { message: "no scroll happened" });
    queryOne(".inactive-container").style.maxHeight = "unset";
    await click(".btn.btn-primary");
    await animationFrame();
    expect(scrollableParent.scrollTop).toBeGreaterThan(0, { message: "a scroll happened" });
});

test("clicking anchor when multi levels scrollables", async () => {
    class MyComponent extends Component {
        static template = xml/* xml */ `
        <div id="scroller" style="overflow: auto; width: 400px; height: 150px">
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
        </div>
        `;
        static props = ["*"];
    }

    await mountWithCleanup(MyComponent);
    const scrollableParent = queryOne("#scroller");

    const border = (selector) => {
        const el = queryOne(selector);
        // Returns the state of the element in relation to the borders
        const element = el.getBoundingClientRect();
        const scrollable = scrollableParent.getBoundingClientRect();
        return {
            top: parseInt(element.top - scrollable.top),
            bottom: parseInt(scrollable.bottom - element.bottom),
        };
    };

    expect(scrollableParent.scrollTop).toBe(0);
    await click(".btn1");
    await animationFrame();
    expect(border("#scroll1").top).toBeLessThan(10, {
        message: "the element must be near the top border",
    });
    await click(".btn2");
    await animationFrame();
    expect(border("#scroll2").top).toBeLessThan(10, {
        message: "the element must be near the top border",
    });
});

test("Simple scroll to HTML elements", async () => {
    class MyComponent extends Component {
        static template = xml/* xml */ `
            <div id="scroller" style="overflow: auto; width: 400px; height: 150px">
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
                    <div id="fake-scrollable">
                        <div id="o-div-3">A div is an HTML element</div>
                    </div>
                    <div id="sub-scrollable">
                        <p>
                            Aliquam convallis sollicitudin purus. Praesent aliquam, enim at fermentum mollis,
                            ligula massa adipiscing nisl, ac euismod nibh nisl eu lectus. Fusce vulputate sem
                            at sapien. Vivamus leo. Aliquam euismod libero eu enim. Nulla nec felis sed leo
                            placerat imperdiet. Aenean suscipit nulla in justo. Suspendisse cursus rutrum
                            augue.
                        </p>
                        <div id="o-div-4">A div is an HTML element</div>
                    </div>
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
                </div>
            </div>
        `;
        static props = ["*"];
    }

    await mountWithCleanup(MyComponent);
    const scrollableParent = queryOne("#scroller");

    // The element must be contained in the scrollable parent (top and bottom)
    const isVisible = (selector) => {
        const el = queryOne(selector);
        return (
            el.getBoundingClientRect().bottom <= scrollableParent.getBoundingClientRect().bottom &&
            el.getBoundingClientRect().top >= scrollableParent.getBoundingClientRect().top
        );
    };

    const border = (selector) => {
        const el = queryOne(selector);
        // Returns the state of the element in relation to the borders
        const element = el.getBoundingClientRect();
        const scrollable = scrollableParent.getBoundingClientRect();
        return {
            top: parseInt(element.top - scrollable.top),
            bottom: parseInt(scrollable.bottom - element.bottom),
        };
    };

    // When using scrollTo to an element, this should just scroll
    // until the element is visible in the scrollable parent
    const subScrollable = queryOne("#sub-scrollable");
    subScrollable.style.overflowY = "scroll";
    subScrollable.style.height = getComputedStyle(subScrollable)["line-height"];
    subScrollable.style.width = "300px";

    expect(isVisible("#o-div-1")).toBe(true);
    expect(isVisible("#o-div-2")).toBe(false);
    expect(border("#o-div-1").top).not.toBe(0);

    scrollTo(queryOne("#o-div-2"));
    expect(isVisible("#o-div-1")).toBe(false);
    expect(isVisible("#o-div-2")).toBe(true);
    expect(border("#o-div-2").bottom).toBe(0);

    scrollTo(queryOne("#o-div-1"));
    expect(isVisible("#o-div-3")).toBe(false);
    expect(isVisible("#o-div-4")).toBe(false);
    expect(border("#o-div-1").top).toBe(0);

    // Specify a scrollable which can not be scrolled, the effective scrollable
    // should be its closest actually scrollable parent.
    scrollTo(queryOne("#o-div-3"), { scrollable: queryOne("#fake-scrollable") });
    expect(isVisible("#o-div-3")).toBe(true);
    expect(isVisible("#o-div-4")).toBe(false);
    expect(border("#o-div-3").bottom).toBe(0);

    // Reset the position
    scrollTo(queryOne("#o-div-1"));
    expect(isVisible("#o-div-1")).toBe(true);
    expect(isVisible("#o-div-3")).toBe(false);
    expect(isVisible("#o-div-4")).toBe(false);

    // Scrolling should be recursive in case of a hierarchy of
    // scrollables, if `isAnchor` is set to `true`, and it must be scrolled
    // to the top even if it was positioned below the scroll view.
    scrollTo(queryOne("#o-div-4"), { isAnchor: true });
    expect(isVisible("#o-div-4")).toBe(true);
    expect(border("#o-div-4").top).toBe(0);
    expect(border("#sub-scrollable").top).toBe(0);
});

test("scroll to anchor from load", async () => {
    class MyComponent extends Component {
        static template = xml/* xml */ `
            <div class="o_content" style="overflow:scroll;height:150px;width:400px">
                <a href="#scrollToHere"  class="alert-link" role="button">sroll to ...</a>
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
        static props = ["*"];
        static path = "my_component";
    }
    registry.category("actions").add("my_component", MyComponent);
    redirect("/odoo/my_component#scrollToHere");
    await mountWithCleanup(WebClient);
    await animationFrame();

    const scrollableParent = document.querySelector(".o_content");
    expect(scrollableParent.scrollTop).not.toBe(0);
});
