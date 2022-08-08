/** @odoo-module **/

import { Notebook } from "@web/core/notebook/notebook";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { click, getFixture, mount, nextTick } from "@web/../tests/helpers/utils";

const { Component, xml } = owl;
let target;

QUnit.module("Components", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
    });

    QUnit.module("Notebook");

    QUnit.test("not rendered if empty slots", async (assert) => {
        const env = await makeTestEnv();
        await mount(Notebook, target, { env, props: {} });
        assert.containsNone(target, "div.o_notebook");
    });

    QUnit.test("notebook with multiple pages given as slots", async (assert) => {
        const env = await makeTestEnv();

        class Parent extends Component {}
        Parent.template = xml`<Notebook>
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
        Parent.components = { Notebook };

        await mount(Parent, target, { env });
        assert.containsOnce(target, "div.o_notebook");
        assert.hasClass(
            target.querySelector(".o_notebook"),
            "horizontal",
            "default orientation is set as horizontal"
        );
        assert.hasClass(
            target.querySelector(".nav"),
            "nav-tabs",
            "navigation container uses the right class to display as horizontal tabs"
        );
        assert.containsN(
            target,
            ".o_notebook_headers a.nav-link",
            2,
            "navigation link is present for each visible page"
        );
        assert.hasClass(
            target.querySelector(".o_notebook_headers .nav-item:first-child a"),
            "active",
            "first page is selected by default"
        );
        assert.strictEqual(
            target.querySelector(".tab-pane.active").firstElementChild.textContent,
            "About the bird",
            "first page content is displayed by the notebook"
        );

        await click(target, ".o_notebook_headers .nav-item:nth-child(2) a");
        assert.hasClass(
            target.querySelector(".o_notebook_headers .nav-item:nth-child(2) a"),
            "active",
            "second page is now selected"
        );
        assert.strictEqual(
            target.querySelector(".tab-pane.active").firstElementChild.textContent,
            "Their favorite activity: hunting",
            "second page content is displayed by the notebook"
        );
    });

    QUnit.test("notebook with defaultPage props", async (assert) => {
        const env = await makeTestEnv();

        class Parent extends Component {}
        Parent.template = xml`<Notebook defaultPage="'page_hunting'">
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
        Parent.components = { Notebook };

        await mount(Parent, target, { env });
        assert.containsOnce(target, "div.o_notebook");
        assert.hasClass(
            target.querySelector(".o_notebook_headers .nav-item:nth-child(2) a"),
            "active",
            "second page is selected by default"
        );
        assert.strictEqual(
            target.querySelector(".tab-pane.active").firstElementChild.textContent,
            "Their favorite activity: hunting",
            "second page content is displayed by the notebook"
        );
    });

    QUnit.test("notebook with defaultPage set on invisible page", async (assert) => {
        const env = await makeTestEnv();

        class Parent extends Component {}
        Parent.template = xml`<Notebook defaultPage="'page_secret'">
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
        Parent.components = { Notebook };

        await mount(Parent, target, { env });
        assert.containsOnce(target, "div.o_notebook");
        assert.strictEqual(
            target.querySelector(".o_notebook_headers .nav-item a.active").textContent,
            "About",
            "The first page is selected"
        );

        assert.containsN(
            target,
            ".o_notebook_headers a.nav-link",
            2,
            "navigation link is only present for visible pages"
        );
        assert.strictEqual(
            target.querySelector(".tab-pane.active").firstElementChild.textContent,
            "About the bird",
            "third page content is displayed by the notebook"
        );
    });

    QUnit.test("notebook set vertically", async (assert) => {
        const env = await makeTestEnv();

        class Parent extends Component {}
        Parent.template = xml`<Notebook orientation="'vertical'">
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
        Parent.components = { Notebook };

        await mount(Parent, target, { env });
        assert.containsOnce(target, "div.o_notebook");
        assert.hasClass(
            target.querySelector(".o_notebook"),
            "vertical",
            "orientation is set as vertical"
        );
        assert.hasClass(
            target.querySelector(".nav"),
            "nav-pills",
            "navigation container uses the right class to display as vertical buttons"
        );
    });

    QUnit.test("notebook pages rendered by a template component", async (assert) => {
        const env = await makeTestEnv();

        class NotebookPageRenderer extends Component {}
        NotebookPageRenderer.template = xml`
                <h3 t-esc="props.heading"></h3>
                <p t-esc="props.text" />
            `;
        NotebookPageRenderer.props = {
            heading: String,
            text: String,
        };

        class Parent extends Component {
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
        Parent.template = xml`<Notebook defaultPage="'page_three'" pages="pages">
                <t t-set-slot="page_one" title="'Page 1'" isVisible="true">
                    <h3>Page 1</h3>
                    <p>First page set directly as a slot</p>
                </t>
                <t t-set-slot="page_four" title="'Page 4'" isVisible="true">
                    <h3>Page 4</h3>
                </t>
            </Notebook>`;
        Parent.components = { Notebook };

        await mount(Parent, target, { env });

        assert.containsOnce(target, "div.o_notebook");
        assert.hasClass(
            target.querySelector(".o_notebook_headers .nav-item:nth-child(3) a"),
            "active",
            "third page is selected by default"
        );

        await click(target.querySelector(".o_notebook_headers .nav-item:nth-child(2) a"));
        assert.strictEqual(
            target.querySelector(".o_notebook_content p").textContent,
            "Second page rendered by a template component",
            "displayed content corresponds to the current page"
        );
    });

    QUnit.test("each page is different", async (assert) => {
        const env = await makeTestEnv();

        class Page extends Component {}
        Page.template = xml`<h3>Coucou</h3>`;

        class Parent extends Component {
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
        Parent.template = xml`<Notebook pages="pages"/>`;
        Parent.components = { Notebook };

        await mount(Parent, target, { env });

        const firstPage = target.querySelector("h3");
        assert.ok(firstPage instanceof HTMLElement);

        await click(target.querySelector(".o_notebook_headers .nav-item:nth-child(2) a"));

        const secondPage = target.querySelector("h3");
        assert.ok(firstPage instanceof HTMLElement);

        assert.notEqual(firstPage, secondPage);
    });

    QUnit.test("defaultPage recomputed when isVisible is dynamic", async (assert) => {
        let defaultPageVisible = false;
        class Parent extends Component {
            get defaultPageVisible() {
                return defaultPageVisible;
            }
        }
        Parent.components = { Notebook };
        Parent.template = xml`
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

        const env = await makeTestEnv();
        const parent = await mount(Parent, target, { env });
        assert.containsOnce(target, ".page1");
        assert.strictEqual(target.querySelector(".nav-link.active").textContent, "page1");

        defaultPageVisible = true;
        parent.render(true);
        await nextTick();
        assert.containsOnce(target, ".page3");
        assert.strictEqual(target.querySelector(".nav-link.active").textContent, "page3");

        await click(target.querySelectorAll(".nav-link")[1]);
        assert.containsOnce(target, ".page2");
        assert.strictEqual(target.querySelector(".nav-link.active").textContent, "page2");

        parent.render(true);
        await nextTick();
        assert.containsOnce(target, ".page2");
        assert.strictEqual(target.querySelector(".nav-link.active").textContent, "page2");
    });
});
