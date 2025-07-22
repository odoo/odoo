import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { click, queryFirst } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

import { Notebook } from "@web/core/notebook/notebook";

test("not rendered if empty slots", async () => {
    await mountWithCleanup(Notebook);
    expect("div.o_notebook").toHaveCount(0);
});

test("notebook with multiple pages given as slots", async () => {
    class Parent extends Component {
        static template = xml`<Notebook>
                <t t-set-slot="page_about" title="'About'" isVisible="true">
                    <h3>About the bird</h3>
                    <p>Owls are birds from the order Strigiformes which includes over
                    200 species of mostly solitary and nocturnal birds of prey typified by an upright stance, ...</p>
                </t>
                <t t-set-slot="page_hunting" title="'Owl Activities'" isVisible="true">
                    <h3>Their favorite activity: hunting</h3>
                    <p>Owls are called raptors, or birds of prey, which means they use sharp talons and curved bills to hunt, kill, and eat other animals.</p>
                </t>
                <t t-set-slot="page_secret" title="'Secret about OWLs'" isVisible="false">
                    <p>TODO find a great secret about OWLs.</p>
                </t>
            </Notebook>`;
        static components = { Notebook };
        static props = ["*"];
    }

    await mountWithCleanup(Parent);
    expect("div.o_notebook").toHaveCount(1);
    expect(".o_notebook").toHaveClass("horizontal", {
        message: "default orientation is set as horizontal",
    });
    expect(".nav").toHaveClass("flex-row", {
        message: "navigation container uses the right class to display as horizontal tabs",
    });
    expect(".o_notebook_headers button.nav-link").toHaveCount(2, {
        message: "navigation link is present for each visible page",
    });
    expect(".o_notebook_headers .nav-item:first-child button").toHaveClass("active", {
        message: "first page is selected by default",
    });
    expect(".active h3").toHaveText("About the bird", {
        message: "first page content is displayed by the notebook",
    });

    await click(".o_notebook_headers .nav-item:nth-child(2) button");
    await animationFrame();
    expect(".o_notebook_headers .nav-item:nth-child(2) button").toHaveClass("active", {
        message: "second page is now selected",
    });
    expect(".active h3").toHaveText("Their favorite activity: hunting", {
        message: "second page content is displayed by the notebook",
    });
});

test("notebook with defaultPage props", async () => {
    class Parent extends Component {
        static template = xml`<Notebook defaultPage="'page_hunting'">
                <t t-set-slot="page_about" title="'About'" isVisible="true">
                    <h3>About the bird</h3>
                    <p>Owls are birds from the order Strigiformes which includes over
                    200 species of mostly solitary and nocturnal birds of prey typified by an upright stance, ...</p>
                </t>
                <t t-set-slot="page_hunting" title="'Owl Activities'" isVisible="true">
                    <h3>Their favorite activity: hunting</h3>
                    <p>Owls are called raptors, or birds of prey, which means they use sharp talons and curved bills to hunt, kill, and eat other animals.</p>
                </t>
                <t t-set-slot="page_secret" title="'Secret about OWLs'" isVisible="false">
                    <p>TODO find a great secret about OWLs.</p>
                </t>
            </Notebook>`;
        static components = { Notebook };
        static props = ["*"];
    }

    await mountWithCleanup(Parent);
    expect("div.o_notebook").toHaveCount(1);
    expect(".o_notebook_headers .nav-item:nth-child(2) button").toHaveClass("active", {
        message: "second page is selected by default",
    });
    expect(".active h3").toHaveText("Their favorite activity: hunting", {
        message: "second page content is displayed by the notebook",
    });
});

test("notebook with defaultPage set on invisible page", async () => {
    class Parent extends Component {
        static template = xml`<Notebook defaultPage="'page_secret'">
                    <t t-set-slot="page_about" title="'About'" isVisible="true">
                        <h3>About the bird</h3>
                        <p>Owls are birds from the order Strigiformes which includes over
                        200 species of mostly solitary and nocturnal birds of prey typified by an upright stance, ...</p>
                    </t>
                    <t t-set-slot="page_hunting" title="'Owl Activities'" isVisible="true">
                        <h3>Their favorite activity: hunting</h3>
                        <p>Owls are called raptors, or birds of prey, which means they use sharp talons and curved bills to hunt, kill, and eat other animals.</p>
                    </t>
                    <t t-set-slot="page_secret" title="'Secret about OWLs'" isVisible="false">
                        <h3>Oooops</h3>
                        <p>TODO find a great secret to reveal about OWLs.</p>
                    </t>
                </Notebook>`;
        static components = { Notebook };
        static props = ["*"];
    }

    await mountWithCleanup(Parent);
    expect(".o_notebook_headers .nav-item button.active").toHaveText("About", {
        message: "The first page is selected",
    });
});

test("notebook set vertically", async () => {
    class Parent extends Component {
        static template = xml`<Notebook orientation="'vertical'">
                <t t-set-slot="page_about" title="'About'" isVisible="true">
                    <h3>About the bird</h3>
                    <p>Owls are birds from the order Strigiformes which includes over
                    200 species of mostly solitary and nocturnal birds of prey typified by an upright stance, ...</p>
                </t>
                <t t-set-slot="page_hunting" title="'Owl Activities'" isVisible="true">
                    <h3>Their favorite activity: hunting</h3>
                    <p>Owls are called raptors, or birds of prey, which means they use sharp talons and curved bills to hunt, kill, and eat other animals.</p>
                </t>
            </Notebook>`;
        static components = { Notebook };
        static props = ["*"];
    }

    await mountWithCleanup(Parent);
    expect("div.o_notebook").toHaveCount(1);
    expect(".o_notebook").toHaveClass("vertical", {
        message: "orientation is set as vertical",
    });
    expect(".nav").toHaveClass("flex-column", {
        message: "navigation container uses the right class to display as vertical buttons",
    });
});

test("notebook pages rendered by a template component", async () => {
    class NotebookPageRenderer extends Component {
        static template = xml`
                <h3 t-esc="props.heading"></h3>
                <p t-esc="props.text" />
            `;
        static props = {
            heading: String,
            text: String,
        };
    }

    class Parent extends Component {
        static template = xml`<Notebook defaultPage="'page_three'" pages="pages">
                <t t-set-slot="page_one" title="'Page 1'" isVisible="true">
                    <h3>Page 1</h3>
                    <p>First page set directly as a slot</p>
                </t>
                <t t-set-slot="page_four" title="'Page 4'" isVisible="true">
                    <h3>Page 4</h3>
                </t>
            </Notebook>`;
        static components = { Notebook };
        static props = ["*"];
        setup() {
            this.pages = [
                {
                    Component: NotebookPageRenderer,
                    index: 1,
                    title: "Page 2",
                    props: {
                        heading: "Page 2",
                        text: "Second page rendered by a template component",
                    },
                },
                {
                    Component: NotebookPageRenderer,
                    id: "page_three", // required to be set as default page
                    index: 2,
                    title: "Page 3",
                    props: {
                        heading: "Page 3",
                        text: "Third page rendered by a template component",
                    },
                },
            ];
        }
    }

    await mountWithCleanup(Parent);
    expect("div.o_notebook").toHaveCount(1);
    expect(".o_notebook_headers .nav-item:nth-child(3) button").toHaveClass("active", {
        message: "third page is selected by default",
    });

    await click(".o_notebook_headers .nav-item:nth-child(2) button");
    await animationFrame();
    expect(".o_notebook_content p").toHaveText("Second page rendered by a template component", {
        message: "displayed content corresponds to the current page",
    });
});

test("each page is different", async () => {
    class Page extends Component {
        static template = xml`<h3>Coucou</h3>`;
        static props = ["*"];
    }

    class Parent extends Component {
        static template = xml`<Notebook pages="pages"/>`;
        static components = { Notebook };
        static props = ["*"];
        setup() {
            this.pages = [
                {
                    Component: Page,
                    index: 1,
                    title: "Page 1",
                },
                {
                    Component: Page,
                    index: 2,
                    title: "Page 2",
                },
            ];
        }
    }

    await mountWithCleanup(Parent);
    const firstPage = queryFirst("h3");
    expect(firstPage).toBeInstanceOf(HTMLElement);

    await click(".o_notebook_headers .nav-item:nth-child(2) button");
    await animationFrame();
    const secondPage = queryFirst("h3");
    expect(secondPage).toBeInstanceOf(HTMLElement);
    expect(firstPage).not.toBe(secondPage);
});

test("defaultPage recomputed when isVisible is dynamic", async () => {
    let defaultPageVisible = false;
    class Parent extends Component {
        static components = { Notebook };
        static template = xml`
                <Notebook defaultPage="'3'">
                    <t t-set-slot="1" title="'page1'" isVisible="true">
                        <div class="page1" />
                    </t>
                    <t t-set-slot="2" title="'page2'" isVisible="true">
                        <div class="page2" />
                    </t>
                    <t t-set-slot="3" title="'page3'" isVisible="defaultPageVisible">
                        <div class="page3" />
                    </t>
                </Notebook>`;
        static props = ["*"];
        get defaultPageVisible() {
            return defaultPageVisible;
        }
    }

    const parent = await mountWithCleanup(Parent);
    expect(".page1").toHaveCount(1);
    expect(".nav-link.active").toHaveText("page1");
    defaultPageVisible = true;
    parent.render(true);

    await animationFrame();
    expect(".page3").toHaveCount(1);
    expect(".nav-link.active").toHaveText("page3");

    await click(".o_notebook_headers .nav-item:nth-child(2) button");
    await animationFrame();
    expect(".page2").toHaveCount(1);
    expect(".nav-link.active").toHaveText("page2");

    parent.render(true);
    await animationFrame();
    expect(".page2").toHaveCount(1);
    expect(".nav-link.active").toHaveText("page2");
});

test("disabled pages are greyed out and can't be toggled", async () => {
    class Parent extends Component {
        static components = { Notebook };
        static template = xml`
            <Notebook defaultPage="'1'">
                <t t-set-slot="1" title="'page1'" isVisible="true">
                    <div class="page1" />
                </t>
                <t t-set-slot="2" title="'page2'" isVisible="true" isDisabled="true">
                    <div class="page2" />
                </t>
                <t t-set-slot="3" title="'page3'" isVisible="true">
                    <div class="page3" />
                </t>
            </Notebook>`;
        static props = ["*"];
    }

    await mountWithCleanup(Parent);
    expect(".page1").toHaveCount(1);
    expect(".nav-item:nth-child(2)").toHaveClass("disabled", {
        message: "tab of the disabled page is greyed out",
    });

    await click(".nav-item:nth-child(2) .nav-link");
    await animationFrame();
    expect(".page1").toHaveCount(1, {
        message: "the same page is still displayed",
    });

    await click(".nav-item:nth-child(3) .nav-link");
    await animationFrame();
    expect(".page3").toHaveCount(1, {
        message: "the third page is now displayed",
    });
});

test("icons can be given for each page tab", async () => {
    class Parent extends Component {
        static components = { Notebook };
        static template = xml`
            <Notebook defaultPage="'1'" icons="icons">
                <t t-set-slot="1" title="'page1'" isVisible="true">
                    <div class="page1" />
                </t>
                <t t-set-slot="2" title="'page2'" isVisible="true">
                    <div class="page2" />
                </t>
                <t t-set-slot="3" title="'page3'" isVisible="true">
                    <div class="page3" />
                </t>
            </Notebook>`;
        static props = ["*"];
        get icons() {
            return {
                1: "fa-trash",
                3: "fa-pencil",
            };
        }
    }

    await mountWithCleanup(Parent);
    expect(".nav-item:nth-child(1) i").toHaveClass("fa-trash");
    expect(".nav-item:nth-child(1)").toHaveText("page1");
    expect(".nav-item:nth-child(2) i").toHaveCount(0);
    expect(".nav-item:nth-child(2)").toHaveText("page2");
    expect(".nav-item:nth-child(3) i").toHaveClass("fa-pencil");
    expect(".nav-item:nth-child(3)").toHaveText("page3");
});
