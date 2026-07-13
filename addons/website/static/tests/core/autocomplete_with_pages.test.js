import { describe, expect, test, getFixture } from "@odoo/hoot";
import { animationFrame, manuallyDispatchProgrammaticEvent } from "@odoo/hoot-dom";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { UrlAutoComplete } from "@website/components/autocomplete_with_pages/url_autocomplete";
import { AutoCompleteWithPages } from "@website/components/autocomplete_with_pages/autocomplete_with_pages";

defineMailModels();

describe.current.tags("desktop");

test("event on targetDropdown does not crash when the inner input ref is gone", async () => {
    // This component is mounted on a URL input living in a dialog (e.g. Edit
    // Menu), and binds its listeners to that external input, which outlives its
    // own hidden input. When the dialog closes, the input is removed while a
    // blur/change/click is still in flight, so a handler can run after
    // `inputRef.el` has been cleared. Here we force that state and fire those
    // events; without the guard the handlers crash reading `inputRef.el.value`.
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
            loadAnchors: () => [],
            targetDropdown,
        },
    });

    expect(component.inputRef.el).not.toBe(null);

    // Detach the inner input subtree, then force a render so OWL sweeps the
    // now-disconnected ref to null (component and its listeners stay alive).
    component.inputRef.el.closest(".o-autocomplete").remove();
    component.render(true);
    await animationFrame();
    expect(component.inputRef.el).toBe(null);

    manuallyDispatchProgrammaticEvent(targetDropdown, "change");
    manuallyDispatchProgrammaticEvent(targetDropdown, "click");
    manuallyDispatchProgrammaticEvent(targetDropdown, "blur");
    await animationFrame();

    expect(component.inputRef.el).toBe(null);
});
