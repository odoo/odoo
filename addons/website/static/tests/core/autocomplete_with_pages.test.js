import { describe, expect, test, getFixture } from "@odoo/hoot";
import {
    advanceTime,
    animationFrame,
    manuallyDispatchProgrammaticEvent,
    queryAllTexts,
} from "@odoo/hoot-dom";
import {
    contains,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { UrlAutoComplete } from "@website/components/autocomplete_with_pages/url_autocomplete";
import { AutoCompleteWithPages } from "@website/components/autocomplete_with_pages/autocomplete_with_pages";
import { render } from "@web/owl2/utils";
import wUtils from "@website/js/utils";

defineMailModels();

describe.current.tags("desktop");

test("event on targetDropdown does not crash when the inner input ref is gone", async () => {
    // This component is mounted on a URL input living in a dialog (e.g. Edit
    // Menu), and binds its listeners to that external input, which outlives its
    // own hidden input. When the dialog closes, the input is removed while a
    // blur/change/click is still in flight, so a handler can run after
    // `inputRef()` has been cleared. Here we force that state and fire those
    // events; without the guard the handlers crash reading `inputRef().value`.
    const targetDropdown = document.createElement("input");
    getFixture().appendChild(targetDropdown);

    let component;
    patchWithCleanup(AutoCompleteWithPages.prototype, {
        setup() {
            super.setup();
            component = this;
        },
    });

    await mountWithCleanup(UrlAutoComplete, {
        props: {
            options: {},
            loadOptionsSource: () => [],
            targetDropdown,
        },
    });

    expect(component.inputRef()).not.toBe(null);

    // Detach the inner input subtree, then force a render so OWL sweeps the
    // now-disconnected ref to null (component and its listeners stay alive).
    component.inputRef().closest(".o-autocomplete").remove();
    render(component, true);
    await animationFrame();
    expect(component.inputRef()).toBe(null);

    manuallyDispatchProgrammaticEvent(targetDropdown, "change");
    manuallyDispatchProgrammaticEvent(targetDropdown, "click");
    manuallyDispatchProgrammaticEvent(targetDropdown, "blur");
    await animationFrame();

    expect(component.inputRef()).toBe(null);
});

test("suggestions are rendered as a flat list of selectable urls", async () => {
    // The menu editor and the SEO dialog mount this component on their own URL
    // input: they have to display the same flat list as the link popover, i.e.
    // one selectable url per row, without the category titles and the app icons
    // the dropdown used to group its suggestions with.
    onRpc("/website/get_suggested_links", () => ({
        matching_pages: [{ value: "/page1", label: "/page1 (Page 1)" }],
        others: [
            {
                title: "Last modified pages",
                values: [{ value: "/page2", label: "/page2 (Page 2)" }],
            },
            {
                title: "Apps url",
                values: [
                    {
                        value: "/app1",
                        label: "/app1 (App 1)",
                        icon: "/website/static/description/icon.png",
                    },
                ],
            },
        ],
    }));

    const targetDropdown = document.createElement("input");
    targetDropdown.className = "o_test_url_input";
    getFixture().appendChild(targetDropdown);

    await mountWithCleanup(UrlAutoComplete, {
        props: {
            options: {},
            loadOptionsSource: wUtils.loadOptionsSource,
            targetDropdown,
        },
    });

    await contains(".o_test_url_input").edit("/page", { confirm: false });
    await advanceTime(250);

    // The last modified pages come first, then the matching pages, then the
    // apps urls.
    expect(queryAllTexts(".o-autocomplete--dropdown-item")).toEqual([
        "/page2 (Page 2)",
        "/page1 (Page 1)",
        "/app1 (App 1)",
    ]);
    expect(".ui-autocomplete-category").toHaveCount(0);
    expect(".o-autocomplete--dropdown-item img").toHaveCount(0);
    // Category titles had no `onSelect`, they were rendered as an unselectable
    // `span` instead of an `a`.
    expect(".o-autocomplete--dropdown-item > a").toHaveCount(3);
    expect(".o-autocomplete--dropdown-item > span").toHaveCount(0);
});
