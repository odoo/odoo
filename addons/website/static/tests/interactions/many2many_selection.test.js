import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { contains, onRpc } from "@web/../tests/web_test_helpers";

setupInteractionWhiteList(["website.form", "website.many2many_selection"]);

describe.current.tags("interaction_dev");

const RECORDS = [
    { id: 1, label: "One" },
    { id: 2, label: "Two" },
];

function m2mFormHTML(selectedIds) {
    const isSelected = (record) => selectedIds.includes(record.id);
    const hasSelection = selectedIds.length > 0;
    return /* html */ `
        <section class="s_website_form">
            <form action="/website/form/" data-model_name="mail.mail">
                <div class="s_website_form_m2m_selection dropdown">
                    <select multiple="multiple" class="s_website_form_input" name="m2m_field">
                        ${RECORDS.map(
                            (r) => `
                        <option value="${r.id}"${isSelected(r) ? " selected='selected'" : ""}>${
                                r.label
                            }</option>`
                        ).join("")}
                    </select>
                    <div class="s_website_form_m2m_pills_container">
                        <span class="s_website_form_m2m_placeholder${
                            hasSelection ? " d-none" : ""
                        }">Pick</span>
                        ${RECORDS.map(
                            (r) => `
                        <span class="s_website_form_m2m_pill${
                            isSelected(r) ? "" : " d-none"
                        }" data-value="${r.id}">${
                                r.label
                            }<button type="button" class="s_website_form_m2m_pill_remove"></button></span>`
                        ).join("")}
                        <button type="button" class="s_website_form_m2m_remove_all${
                            hasSelection ? "" : " d-none"
                        }"></button>
                        <button type="button" data-bs-toggle="dropdown" data-bs-auto-close="outside"></button>
                        <div class="dropdown-menu">
                            <button type="button" class="s_website_form_m2m_toggle_all dropdown-item" aria-checked="${
                                selectedIds.length === RECORDS.length
                            }">Select all</button>
                            ${RECORDS.map(
                                (r) => `
                            <button type="button" class="dropdown-item" aria-checked="${isSelected(
                                r
                            )}" data-value="${r.id}">${r.label}</button>`
                            ).join("")}
                        </div>
                    </div>
                </div>
                <span id="s_website_form_result"></span>
                <a href="#" class="s_website_form_send">Submit</a>
            </form>
        </section>
    `;
}

async function startM2mForm(selectedIds) {
    const { core } = await startInteractions(m2mFormHTML(selectedIds));
    expect(core.interactions).toHaveLength(2);
    return core;
}

const openDropdown = () => contains("button[data-bs-toggle='dropdown']").click();
const clickItem = (id) => contains(`.dropdown-item[data-value='${id}']`).click();

/**
 * Asserts the state of the whole widget against the expected selection.
 *
 * @param {number[]} selectedIds ids of the expected selected records.
 */
function expectSelection(selectedIds) {
    const expectHidden = (selector, hidden) => {
        const matcher = expect(queryOne(selector));
        (hidden ? matcher : matcher.not).toHaveClass("d-none");
    };
    for (const { id } of RECORDS) {
        const selected = selectedIds.includes(id);
        expect(queryOne(`option[value='${id}']`).selected).toBe(selected);
        expect(queryOne(`.dropdown-item[data-value='${id}']`)).toHaveAttribute(
            "aria-checked",
            String(selected)
        );
        expectHidden(`.s_website_form_m2m_pill[data-value='${id}']`, !selected);
    }
    const hasSelection = selectedIds.length > 0;
    expectHidden(".s_website_form_m2m_placeholder", hasSelection);
    expectHidden(".s_website_form_m2m_remove_all", !hasSelection);
    const areAllSelected = selectedIds.length === RECORDS.length;
    expect(queryOne(".s_website_form_m2m_toggle_all")).toHaveAttribute(
        "aria-checked",
        String(areAllSelected)
    );
    expect(queryOne(".s_website_form_m2m_toggle_all")).toHaveText(
        areAllSelected ? "Deselect all" : "Select all"
    );
}

test("initial state reflects pre-selected options", async () => {
    await startM2mForm([1]);
    expectSelection([1]);
});

test("clicking a dropdown option toggles its selection and matching pill", async () => {
    await startM2mForm([1]);
    await openDropdown();
    await clickItem(2);
    expectSelection([1, 2]);
    await clickItem(1);
    expectSelection([2]);
});

test("removing a pill deselects only that option", async () => {
    await startM2mForm([1, 2]);
    await contains(
        ".s_website_form_m2m_pill[data-value='1'] .s_website_form_m2m_pill_remove"
    ).click();
    expectSelection([2]);
});

test("'Select all' selects every option & 'Deselect all' clears them", async () => {
    await startM2mForm([1]);
    await openDropdown();
    await contains(".s_website_form_m2m_toggle_all").click();
    expectSelection([1, 2]);
    await contains(".s_website_form_m2m_toggle_all").click();
    expectSelection([]);
});

test("'Remove all' deselects every option", async () => {
    await startM2mForm([1, 2]);
    await contains(".s_website_form_m2m_remove_all").click();
    expectSelection([]);
});

test("cleanup restores the initial selection", async () => {
    const core = await startM2mForm([1]);
    await openDropdown();
    await clickItem(1);
    core.stopInteractions();
    expectSelection([1]);
});

test("form reset restores the saved selection", async () => {
    await startM2mForm([1]);
    await openDropdown();
    await clickItem(2);
    await clickItem(1);
    expectSelection([2]);
    queryOne("form").reset();
    await animationFrame();
    expectSelection([1]);
});

test("form submits the selected values", async () => {
    onRpc("/website/form/mail.mail", async (request) => {
        expect((await request.formData()).getAll("m2m_field")).toEqual(["1,2"]);
        expect.step("submitted");
    });
    await startM2mForm([1]);
    await openDropdown();
    await clickItem(2);
    await contains(".s_website_form_send").click();
    expect.verifySteps(["submitted"]);
});

test("selection changes dispatch a bubbling input event on the select", async () => {
    await startM2mForm([]);
    const selectEl = queryOne("select.s_website_form_input");
    const inputTargets = [];
    queryOne("form").addEventListener("input", (ev) => inputTargets.push(ev.target));
    await openDropdown();
    await clickItem(1);
    expect(inputTargets).toHaveLength(1);
    expect(inputTargets[0]).toBe(selectEl);
    await contains(".s_website_form_m2m_remove_all").click();
    expect(inputTargets).toHaveLength(2);
});
