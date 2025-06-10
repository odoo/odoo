import { InputPlugin } from "@html_editor/core/input_plugin";
import { SuggestionPlugin } from "@mail/core/web/plugins/suggestion_plugin";
import { describe, expect, test } from "@odoo/hoot";

describe("Implicit plugin dependencies", () => {
    test("position as an implicit dependency", async () => {
        for (const P of [SuggestionPlugin]) {
            // input dependency through the "beforeinput_handlers" and
            // "input_handlers" resources. This dependency was added because the
            // plugin is heavily dependent on inputs handling and will appear
            // broken without the appropriate handlers.
            expect(P.dependencies).toInclude(InputPlugin.id);
        }
    });
});
