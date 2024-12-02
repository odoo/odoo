import { expect, test } from "@odoo/hoot";
import { click, queryFirst, queryOne, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    getSnippetStructure,
    invisiblePopup,
    setupWebsiteBuilder,
} from "./helpers";
import { unformat } from "@html_editor/../tests/_helpers/format";

defineWebsiteModels();

test("click on invisible elements in the invisible elements tab", async () => {
    await setupWebsiteBuilder(`${invisiblePopup}`);
    expect(queryOne(".o_we_invisible_el_panel .o_we_invisible_entry")).toHaveText("Popup");
    expect(queryOne(".o_we_invisible_el_panel .o_we_invisible_entry i")).toHaveClass(
        "fa-eye-slash"
    );
    await contains(".o_we_invisible_el_panel .o_we_invisible_entry").click();
    expect(queryOne(".o_we_invisible_el_panel .o_we_invisible_entry i")).toHaveClass("fa-eye");
    await contains(".o_we_invisible_el_panel .o_we_invisible_entry").click();
    expect(queryOne(".o_we_invisible_el_panel .o_we_invisible_entry i")).toHaveClass(
        "fa-eye-slash"
    );
});

test("Add an element on the invisible elements tab", async () => {
    const snippetsDescription = [
        {
            name: "Test",
            groupName: "a",
            content: unformat(
                `<div class="s_popup o_snippet_invisible" data-snippet="s_popup" data-name="Popup">
                    <div class="test_a">Hello</div>
                </div>`
            ),
        },
    ];

    await setupWebsiteBuilder(`${invisiblePopup} <section><p>Text</p></section>`, {
        snippets: {
            snippet_groups: [
                '<div name="A" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
            ],
            snippet_structure: snippetsDescription.map((snippetDesc) =>
                getSnippetStructure(snippetDesc)
            ),
        },
    });
    await click(queryFirst(`.o-snippets-menu [data-category="snippet_groups"] div`));
    await waitFor(".o_add_snippet_dialog iframe.show.o_add_snippet_iframe", { timeout: 500 });
    await contains(
        ".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap"
    ).click();
    expect(".o_we_invisible_el_panel .o_we_invisible_entry:contains('Test') .fa-eye").toHaveCount(
        1
    );
    expect(
        ".o_we_invisible_el_panel .o_we_invisible_entry:contains('Popup') .fa-eye-slash"
    ).toHaveCount(1);
});
