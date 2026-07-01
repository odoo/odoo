import { describe, expect, test } from "@odoo/hoot";
import { queryAll, queryOne } from "@odoo/hoot-dom";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { contains, onRpc } from "@web/../tests/web_test_helpers";

setupInteractionWhiteList(["website.many2many_selection", "website.form"]);

describe.current.tags("interaction_dev");

const many2manySelectionHTML = /* html */ `
    <section class="s_website_form">
        <form action="/website/form/" method="post" enctype="multipart/form-data" data-model_name="mail.mail">
            <div class="s_website_form_m2m_selection dropdown">
                <select multiple="multiple" class="s_website_form_input d-none" name="m2m_field">
                    <option value="1" selected="selected">One</option>
                    <option value="2">Two</option>
                </select>
                <div class="s_website_form_m2m_pills_container form-select d-flex flex-wrap align-items-center gap-1">
                    <button id="m2m_sel" type="button" data-bs-toggle="dropdown" data-bs-auto-close="outside" data-bs-display="static" aria-haspopup="menu" aria-expanded="false" aria-label="Toggle options"></button>
                    <span class="s_website_form_m2m_placeholder d-none">Pick</span>
                    <span class="s_website_form_m2m_pill badge rounded-pill text-bg-primary" data-value="1">One<button type="button" class="s_website_form_m2m_pill_remove" aria-label="Remove"><i class="fa fa-times"></i></button></span>
                    <span class="s_website_form_m2m_pill badge rounded-pill text-bg-primary d-none" data-value="2">Two<button type="button" class="s_website_form_m2m_pill_remove" aria-label="Remove"><i class="fa fa-times"></i></button></span>
                    <div class="dropdown-menu w-100">
                        <button type="button" class="dropdown-item" role="menuitemcheckbox" aria-checked="true" data-value="1">One</button>
                        <button type="button" class="dropdown-item" role="menuitemcheckbox" aria-checked="false" data-value="2">Two</button>
                    </div>
                </div>
            </div>
            <div class="s_website_form_submit" data-name="Submit Button">
                <span id="s_website_form_result"></span>
                <a href="#" role="button" class="btn btn-primary s_website_form_send">Submit</a>
            </div>
        </form>
    </section>
`;

const VISIBLE_PILL = ".s_website_form_m2m_pill:not(.d-none)";

test("initial state reflects pre-selected options", async () => {
    const { core } = await startInteractions(many2manySelectionHTML);
    expect(core.interactions).toHaveLength(2);

    const selectEl = queryOne("select.s_website_form_input");
    const item1El = queryOne(".dropdown-item[data-value='1']");
    const item2El = queryOne(".dropdown-item[data-value='2']");

    expect(selectEl.querySelector("option[value='1']").selected).toBe(true);
    expect(item1El).toHaveAttribute("aria-checked", "true");

    expect(selectEl.querySelector("option[value='2']").selected).toBe(false);
    expect(item2El).toHaveAttribute("aria-checked", "false");

    expect(queryAll(VISIBLE_PILL)).toHaveLength(1);
});

test("clicking a dropdown option toggles its selection and matching pill", async () => {
    const { core } = await startInteractions(many2manySelectionHTML);
    expect(core.interactions).toHaveLength(2);

    await contains("button[data-bs-toggle='dropdown']").click();

    // Selecting an unselected option shows its pill.
    await contains(".dropdown-item[data-value='2']").click();
    expect(queryOne("select.s_website_form_input option[value='2']").selected).toBe(true);
    expect(queryOne(".dropdown-item[data-value='2']")).toHaveAttribute("aria-checked", "true");
    expect(queryAll(VISIBLE_PILL)).toHaveLength(2);

    // Clicking a selected option deselects it and hides its pill.
    await contains(".dropdown-item[data-value='1']").click();
    expect(queryOne("select.s_website_form_input option[value='1']").selected).toBe(false);
    expect(queryOne(".dropdown-item[data-value='1']")).toHaveAttribute("aria-checked", "false");
    expect(queryAll(VISIBLE_PILL)).toHaveLength(1);
});

test("removing a pill deselects the option, hides the pill and shows the placeholder", async () => {
    const { core } = await startInteractions(many2manySelectionHTML);
    expect(core.interactions).toHaveLength(2);

    const placeholderEl = queryOne(".s_website_form_m2m_placeholder");
    expect(placeholderEl).toHaveClass("d-none");

    await contains(".s_website_form_m2m_pill_remove").click();
    expect(queryOne("select.s_website_form_input option[value='1']").selected).toBe(false);
    expect(queryOne(".dropdown-item[data-value='1']")).toHaveAttribute("aria-checked", "false");
    expect(queryAll(VISIBLE_PILL)).toHaveLength(0);
    expect(placeholderEl).not.toHaveClass("d-none");
});

test("cleanup restores initial selected state", async () => {
    const { core } = await startInteractions(many2manySelectionHTML);
    expect(core.interactions).toHaveLength(2);

    await contains("button[data-bs-toggle='dropdown']").click();
    await contains(".dropdown-item[data-value='2']").click();
    await contains(".dropdown-item[data-value='1']").click();

    const selectEl = queryOne("select.s_website_form_input");
    expect(selectEl.querySelector("option[value='1']").selected).toBe(false);
    expect(selectEl.querySelector("option[value='2']").selected).toBe(true);

    core.stopInteractions();

    expect(selectEl.querySelector("option[value='1']").selected).toBe(true);
    expect(selectEl.querySelector("option[value='2']").selected).toBe(false);
    expect(queryAll(VISIBLE_PILL)).toHaveLength(1);
    expect(queryOne(".dropdown-item[data-value='1']")).toHaveAttribute("aria-checked", "true");
    expect(queryOne(".dropdown-item[data-value='2']")).toHaveAttribute("aria-checked", "false");
});

test("form sends the selected pills values on submit", async () => {
    onRpc("/website/form/mail.mail", async (request) => {
        const formData = await request.formData();
        expect(formData.getAll("m2m_field")).toEqual(["1,2"]);
        expect.step("submitted");
    });

    const { core } = await startInteractions(many2manySelectionHTML);
    expect(core.interactions).toHaveLength(2);

    await contains("button[data-bs-toggle='dropdown']").click();
    await contains(".dropdown-item[data-value='2']").click();
    await contains(".s_website_form_send").click();
    expect.verifySteps(["submitted"]);
});
