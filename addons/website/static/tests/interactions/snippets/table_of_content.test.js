import { expect, test } from "@odoo/hoot";
import { animationFrame, click, scroll } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { isElementVerticallyInViewportOf, startInteractions, setupInteractionWhiteList } from "../../core/helpers";

setupInteractionWhiteList("website.table_of_content");

// TODO Maybe recover from `website.s_table_of_content`.
const defaultToc = `
    <section class="s_table_of_content pt24 pb24 o_cc o_cc1">
        <div class="container">
            <div class="row s_nb_column_fixed">
                <div class="col-lg-3 s_table_of_content_navbar_wrap s_table_of_content_navbar_sticky s_table_of_content_vertical_navbar d-print-none d-none d-lg-block o_not_editable o_cc o_cc1" data-name="Navbar">
                    <div class="s_table_of_content_navbar list-group o_no_link_popover"
                        style="top: 76px; max-height: calc(100vh - 96px);"
                    >
                        <a href="#table_of_content_heading_1_1" class="table_of_content_link list-group-item list-group-item-action py-2 border-0 rounded-0 active">Intuitive system</a>
                        <a href="#table_of_content_heading_1_2" class="table_of_content_link list-group-item list-group-item-action py-2 border-0 rounded-0">Design features</a>
                    </div>
                </div>
                <div class="col-lg-9 s_table_of_content_main oe_structure oe_empty" data-name="Content">
                    <section class="s_text_block pt0 pb64" data-snippet="s_text_block" data-name="Section">
                        <div class="container s_allow_columns">
                            <h2 id="table_of_content_heading_1_1" class="h3" data-anchor="true">Intuitive system</h2>
                            <div class="s_hr pt8 pb24" data-snippet="s_hr" data-name="Separator">
                                <hr class="w-100 mx-auto"/>
                            </div>
                            <p class="lead">
                                Our intuitive system ensures effortless navigation for users of all skill levels. Its clean interface and logical organization make tasks easy to complete. With tooltips and contextual help, users quickly become productive, enjoying a smooth and efficient experience.
                            </p>
                            <br/>
                            <br/>
                            <h4 class="h5">What you see is what you get</h4>
                            <p>
                                Insert text styles like headers, bold, italic, lists, and fonts with a simple WYSIWYG editor. Flexible and easy to use, it lets you design and format documents in real time. No coding knowledge is needed, making content creation straightforward and enjoyable for everyone.
                            </p>
                            <br/>
                            <br/>
                            <h4 class="h5">Customization tool</h4>
                            <p>
                                Click and change content directly from the front-end, avoiding complex backend processes. This tool allows quick updates to text, images, and elements right on the page, streamlining your workflow and maintaining control over your content.
                            </p>
                        </div>
                    </section>
                    <section class="s_text_block pt0 pb64" data-snippet="s_text_block" data-name="Section">
                        <div class="container s_allow_columns">
                            <h2 id="table_of_content_heading_1_2" class="h3" data-anchor="true">Design features</h2>
                            <div class="s_hr pt8 pb24" data-snippet="s_hr" data-name="Separator">
                                <hr class="w-100 mx-auto"/>
                            </div>
                            <p class="lead">
                                Our design features offer a range of tools to create visually stunning websites. Utilize WYSIWYG editors, drag-and-drop building blocks, and Bootstrap-based templates for effortless customization. With professional themes and an intuitive system, you can design with ease and precision, ensuring a polished, responsive result.
                            </p>
                            <br/>
                            <br/>
                            <h4 class="h5">Building blocks system</h4>
                            <p>
                                Create pages from scratch by dragging and dropping customizable building blocks. This system simplifies web design, making it accessible to all skill levels. Combine headers, images, and text sections to build cohesive layouts quickly and efficiently.
                            </p>
                            <br/>
                            <br/>
                            <h4 class="h5">Bootstrap-Based Templates</h4>
                            <p>
                                Design Odoo templates easily with clean HTML and Bootstrap CSS. These templates offer a responsive, mobile-first design, making them simple to customize and perfect for any web project, from corporate sites to personal blogs.
                            </p>
                            <br/>
                            <br/>
                        </div>
                    </section>
                </div>
            </div>
        </div>
    </section>
`;

test("table of content does nothing if there is no s_table_of_content_navbar_sticky", async () => {
    const { core } = await startInteractions(`
      <div id="wrapwrap">
        <section id="somewhere" />
      </div>
    `);
    expect(core.interactions.length).toBe(0);
});

test("table of content scrolls to targetted location", async () => {
    const { core, el } = await startInteractions(`
        <div id="wrapwrap" style="overflow: scroll; max-height: 300px;">
            ${defaultToc}
        </div>
    `);
    expect(core.interactions.length).toBe(1);
    const wrapEl = el.querySelector("#wrapwrap");
    const aEls = el.querySelectorAll("a[href]");
    const h2Els = el.querySelectorAll("h2[id]");
    expect(aEls[0]).toHaveClass("active");
    expect(aEls[1]).not.toHaveClass("active");
    expect(isElementVerticallyInViewportOf(aEls[0], wrapEl)).toBe(true);
    expect(isElementVerticallyInViewportOf(aEls[0], wrapEl)).toBe(true);
    expect(isElementVerticallyInViewportOf(h2Els[0], wrapEl)).toBe(true);
    expect(isElementVerticallyInViewportOf(h2Els[1], wrapEl)).toBe(false);
    await click(aEls[1]);
    await animationFrame();
    expect(aEls[0]).not.toHaveClass("active");
    expect(aEls[1]).toHaveClass("active");
    expect(isElementVerticallyInViewportOf(aEls[0], wrapEl)).toBe(true);
    expect(isElementVerticallyInViewportOf(aEls[0], wrapEl)).toBe(true);
    expect(isElementVerticallyInViewportOf(h2Els[0], wrapEl)).toBe(false);
    expect(isElementVerticallyInViewportOf(h2Els[1], wrapEl)).toBe(true);
});

test("table of content highlights reached header", async () => {
    const { core, el } = await startInteractions(`
        <div id="wrapwrap" style="overflow: scroll; max-height: 300px;">
            ${defaultToc}
        </div>
    `);
    expect(core.interactions.length).toBe(1);
    const wrapEl = el.querySelector("#wrapwrap");
    const aEls = el.querySelectorAll("a[href]");
    const h2Els = el.querySelectorAll("h2[id]");
    expect(aEls[0]).toHaveClass("active");
    expect(aEls[1]).not.toHaveClass("active");
    expect(isElementVerticallyInViewportOf(aEls[0], wrapEl)).toBe(true);
    expect(isElementVerticallyInViewportOf(aEls[0], wrapEl)).toBe(true);
    expect(isElementVerticallyInViewportOf(h2Els[0], wrapEl)).toBe(true);
    expect(isElementVerticallyInViewportOf(h2Els[1], wrapEl)).toBe(false);
    await scroll(wrapEl, { top: h2Els[1].getBoundingClientRect().top });
    await animationFrame();
    expect(aEls[0]).not.toHaveClass("active");
    expect(aEls[1]).toHaveClass("active");
    expect(isElementVerticallyInViewportOf(aEls[0], wrapEl)).toBe(true);
    expect(isElementVerticallyInViewportOf(aEls[0], wrapEl)).toBe(true);
    expect(isElementVerticallyInViewportOf(h2Els[0], wrapEl)).toBe(false);
    expect(isElementVerticallyInViewportOf(h2Els[1], wrapEl)).toBe(true);
});
