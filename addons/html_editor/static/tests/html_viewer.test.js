import { HtmlViewer } from "@html_editor/components/html_viewer/html_viewer";
import { expect, test } from "@odoo/hoot";
import { dblclick, queryOne, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { markup } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { WebClient } from "@web/webclient/webclient";
import { base64Img } from "./_helpers/editor";
import { expectElementCount } from "./_helpers/ui_expectations";

test(`XML-like self-closing elements are fixed in a standalone HtmlViewer`, async () => {
    await mountWithCleanup(WebClient);

    registry.category("main_components").add("mycomponent", {
        Component: HtmlViewer,
        props: {
            config: {
                value: markup(`<a href="#"/>outside<a href="#">inside</a>`),
            },
        },
    });
    await animationFrame();
    expect(".o_readonly").toHaveInnerHTML(
        `<a href="#" target="_blank" rel="noreferrer noopener"></a>outside<a href="#" target="_blank" rel="noreferrer noopener">inside</a>`
    );
});

test(`tables are wrapped in a scroll container in a standalone HtmlViewer`, async () => {
    await mountWithCleanup(WebClient);

    registry.category("main_components").add("mycomponent", {
        Component: HtmlViewer,
        props: {
            config: {
                value: markup(
                    `<table class="o_table"><tbody><tr><td><table class="o_table"><tbody><tr><td>a</td></tr></tbody></table></td></tr></tbody></table>`
                ),
            },
        },
    });
    await animationFrame();
    expect(".o_readonly > .o_table_wrapper > table").toHaveCount(1);
    expect("td .o_table_wrapper").toHaveCount(0);
});

test(`copy from HtmlViewer must support application/vnd.odoo.odoo-editor`, async () => {
    await mountWithCleanup(WebClient);

    registry.category("main_components").add("mycomponent", {
        Component: HtmlViewer,
        props: {
            config: {
                value: markup(`
                    <p>before</p>
                    <table class="table table-bordered o_table">
                        <tbody>
                            <tr style="height: 49.1875px;">
                                <td style="background-color: rgba(214, 239, 214, 0.6); color: rgb(55, 65, 81);">
                                    <p>A</p>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                    <p>after</p>
                `),
            },
        },
    });
    await animationFrame();
    const beforeNode = await waitFor("p:contains('before')");
    const afterNode = await waitFor("p:contains('after')");
    const range = new Range();
    range.setStart(beforeNode, 1);
    range.setEnd(afterNode, 0);
    getSelection().addRange(range);
    await animationFrame();

    const clipboardData = new DataTransfer();
    const ev = new ClipboardEvent("copy", { bubbles: true, clipboardData });
    beforeNode.dispatchEvent(ev);

    expect(clipboardData.getData("text/plain").trim()).toBe("A");
    expect(clipboardData.getData("text/html")).toInclude("background-color");
    expect(clipboardData.getData("application/vnd.odoo.odoo-editor")).toBe(
        clipboardData.getData("text/html")
    );
});

test(`copy from HtmlViewer should copy all the selection`, async () => {
    await mountWithCleanup(WebClient);

    registry.category("main_components").add("mycomponent", {
        Component: HtmlViewer,
        props: {
            config: {
                value: markup(`
                    <table class="table table-bordered o_table">
                        <tbody>
                            <tr style="height: 49.1875px;">
                                <td style="background-color: rgba(214, 239, 214, 0.6); color: rgb(55, 65, 81);">
                                    <p>A</p>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                `),
            },
        },
    });
    await animationFrame();
    const tableParent = (await waitFor("table")).parentElement;
    const range = new Range();
    range.setStart(tableParent, 0);
    range.setEnd(tableParent, 1);
    getSelection().addRange(range);
    await animationFrame();
    const clipboardData = new DataTransfer();
    tableParent.dispatchEvent(new ClipboardEvent("copy", { bubbles: true, clipboardData }));

    expect(clipboardData.getData("text/html")).toInclude("table");
    expect(clipboardData.getData("application/vnd.odoo.odoo-editor")).toBe(
        clipboardData.getData("text/html")
    );
});

test.tags("desktop");
test("double-clicking a readonly image opens its preview", async () => {
    await mountWithCleanup(WebClient);
    registry.category("main_components").add("mycomponent", {
        Component: HtmlViewer,
        props: {
            config: {
                value: markup(`<img src="${base64Img}">`),
            },
        },
    });
    await expectElementCount(".o_readonly img", 1);
    const image = queryOne(".o_readonly img");
    await dblclick(image);
    await expectElementCount(".o-FileViewer-viewImage", 1);
    expect(".o-FileViewer-viewImage").toHaveAttribute("data-src", image.src);
});

test.tags("desktop");
test("double-clicking an image of an embedded component only opens its preview in an editable part", async () => {
    await mountWithCleanup(WebClient);
    registry.category("main_components").add("mycomponent", {
        Component: HtmlViewer,
        props: {
            config: {
                value: markup(
                    `<div data-embedded="toggle"><img src="${base64Img}"><div data-embedded-editable="content"><img src="${base64Img}"></div></div>`
                ),
            },
        },
    });
    await expectElementCount(".o_readonly img", 2);
    await dblclick(queryOne("[data-embedded] > img"));
    await animationFrame();
    expect(".o-FileViewer").toHaveCount(0);

    const image = queryOne("[data-embedded-editable] img");
    await dblclick(image);
    await expectElementCount(".o-FileViewer-viewImage", 1);
    expect(".o-FileViewer-viewImage").toHaveAttribute("data-src", image.src);
});
