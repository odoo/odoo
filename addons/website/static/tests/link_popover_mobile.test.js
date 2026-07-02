import { setupEditor } from "@html_editor/../tests/_helpers/editor";
import { cleanLinkArtifacts } from "@html_editor/../tests/_helpers/format";
import { getContent } from "@html_editor/../tests/_helpers/selection";
import {
    advanceTime,
    animationFrame,
    click,
    expect,
    mockUserAgent,
    press,
    test,
    waitFor,
} from "@odoo/hoot";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { contains, onRpc } from "@web/../tests/web_test_helpers";

defineMailModels();

test.tags("mobile");
test("URL input of the link popover has no autocomplete in a bottom sheet (mobile)", async () => {
    mockUserAgent("android");
    onRpc("/website/get_suggested_links", () => {
        expect.step("/website/get_suggested_links");
        return {
            matching_pages: [{ value: "/contactus", label: "/contactus (Contact Us)" }],
            others: [],
        };
    });
    onRpc("/html_editor/link_preview_internal", () => ({}));

    const { el } = await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
    await waitFor(".o_bottom_sheet .o-we-linkpopover");
    await click(".o_we_edit_link");
    await animationFrame();
    await contains(".o_we_href_input_link").focus();
    await press(["ctrl", "a"]);
    await press("/");
    await press("c");
    await advanceTime(1000); // more than the autocomplete debounce delay
    await animationFrame();
    expect(".o-autocomplete--dropdown-menu").toHaveCount(0);
    await animationFrame();
    // Enter applies the link: no hidden suggestion list blocks it
    await press("Enter");
    await animationFrame();
    expect(cleanLinkArtifacts(getContent(el))).toBe('<p>this is a <a href="/c">li[]nk</a></p>');
    expect(".o-autocomplete").toHaveCount(0);
    expect.verifySteps([]);
});
