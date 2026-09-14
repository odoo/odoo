import { expect, getFixture, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { SelectMenuWrapper } from "@l10n_latam_base/components/select_menu_wrapper/select_menu_wrapper";
import { editSelectMenu, mountWithCleanup } from "@web/../tests/web_test_helpers";

async function mountSelect(attributes = "multiple") {
    getFixture().innerHTML = `<form><select name="obligations" ${attributes}>
        <option value="1" selected="selected">One</option>
        <option value="2" selected="selected">Two</option>
        <option value="3">Three</option>
    </select></form>`;
    const select = queryOne("select");
    const wrapper = await mountWithCleanup(SelectMenuWrapper, {
        props: { el: select },
    });
    return { select, wrapper };
}

test("multiple selection displays every saved obligation", async () => {
    await mountSelect();
    expect(".o_tag_badge_text").toHaveCount(2);
    expect(new FormData(queryOne("form")).getAll("obligations")).toEqual(["1", "2"]);
});

test("choosing another obligation preserves existing selections in FormData", async () => {
    const { select } = await mountSelect();
    select.addEventListener("change", () => expect.step("change"));
    await editSelectMenu(".o_select_menu_toggler", { value: "Three" });
    expect(new FormData(queryOne("form")).getAll("obligations")).toEqual([
        "1",
        "2",
        "3",
    ]);
    expect.verifySteps(["change"]);
});

test("a multiple selection callback updates every native selected option", async () => {
    const { wrapper } = await mountSelect();
    wrapper.onSelect(["2", "3"]);
    expect(new FormData(queryOne("form")).getAll("obligations")).toEqual(["2", "3"]);
    wrapper.onSelect([]);
    expect(new FormData(queryOne("form")).getAll("obligations")).toEqual([]);
});

test("unmount restores a previously visible native select", async () => {
    const { select, wrapper } = await mountSelect("");
    expect(select).toHaveClass("d-none");
    wrapper.__owl__.app.destroy();
    expect(select).not.toHaveClass("d-none");
});

test("single selection keeps the external selection event and bubbling change", async () => {
    const { select, wrapper } = await mountSelect("");
    queryOne("form").addEventListener("change", () => expect.step("change"));
    select.dispatchEvent(new CustomEvent("select", { detail: { value: "3" } }));
    expect(select).toHaveValue("3");
    expect(wrapper.state.value).toBe("3");
    expect.verifySteps(["change"]);
    wrapper.onSelect(null);
    expect(select).toHaveValue("");
    expect.verifySteps(["change"]);
});

test("teardown preserves a native select that was already hidden", async () => {
    const { select, wrapper } = await mountSelect('class="d-none"');
    wrapper.__owl__.app.destroy();
    expect(select).toHaveClass("d-none");
});
