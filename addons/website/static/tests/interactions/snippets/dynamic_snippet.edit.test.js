import { describe, expect, test } from "@odoo/hoot";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { switchToEditMode } from "../../helpers";

setupInteractionWhiteList("website.dynamic_snippet");

describe.current.tags("interaction_dev");

const snippetWithoutFilter = `
    <section data-snippet="s_dynamic_snippet" class="s_dynamic_snippet s_dynamic pt32 pb32" data-name="Dynamic Snippet"
            data-template-key="website.dynamic_filter_template_test_item"
            data-number-of-records="16">
        <div class="container">
            <div class="row s_nb_column_fixed">
                <section class="s_dynamic_snippet_content oe_unremovable oe_unmovable o_not_editable col">
                    <div class="dynamic_snippet_template"></div>
                </section>
            </div>
        </div>
    </section>
`;

test("misconfigured dynamic snippet: warning only rendered in edit mode", async () => {
    const { core } = await startInteractions(snippetWithoutFilter);
    expect(core.interactions).toHaveLength(1);
    expect(".s_dynamic_snippet .missing_option_warning").toHaveCount(0);

    await switchToEditMode(core);
    expect(".s_dynamic_snippet_content > .missing_option_warning").toHaveCount(1);

    core.stopInteractions();
    expect(".s_dynamic_snippet .missing_option_warning").toHaveCount(0);
});
