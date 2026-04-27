import { PositionPlugin } from "@html_editor/main/position_plugin";
import { KnowledgeCommentsPlugin } from "@knowledge/editor/plugins/comments_plugin/comments_plugin";
import { describe, expect, test } from "@odoo/hoot";

describe("Implicit plugin dependencies", () => {
    test("position as an implicit dependency", async () => {
        for (const P of [KnowledgeCommentsPlugin]) {
            // position dependency through the "layout_geometry_change_handlers"
            // resource. This dependency was added because the plugin is
            // heavily dependent on layout changes and will appear broken
            // without the appropriate handler.
            expect(P.dependencies).toInclude(PositionPlugin.id);
        }
    });
});
