import { describe, expect, test } from "@odoo/hoot";
import { click, edit, press, queryAll, queryOne, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { setupEditor } from "./_helpers/editor";
import { getContent } from "./_helpers/selection";
import { expectElementCount } from "./_helpers/ui_expectations";
import { insertText, undo } from "./_helpers/user_actions";

const ICON = `\ufeff<span class="oi" data-icon="check" contenteditable="false">\u200b</span>\ufeff`;

async function openIconPicker(editor) {
    await insertText(editor, "/icon");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Icon");
    await press("enter");
    await waitFor(".o-IconPicker");
}

async function search(term) {
    await edit(term);
    await animationFrame();
}

function displayedIcons() {
    return queryAll(".o-IconPicker-icon").map((iconEl) =>
        iconEl.classList.contains("oi-filled")
            ? `${iconEl.dataset.icon} (filled)`
            : iconEl.dataset.icon
    );
}

describe.tags("desktop");
describe("icon picker", () => {
    test("insert an icon with the powerbox", async () => {
        const { el, editor } = await setupEditor("<p>ab[]</p>");
        await openIconPicker(editor);
        expect(".o-IconPicker input").toBeFocused();
        expect(".o-IconPicker-upload").toHaveCount(0, { message: "no image upload to insert" });
        expect(getContent(el)).toBe("<p>ab</p>");

        await click(".o-IconPicker-icon[data-icon='check']");
        await animationFrame();
        await expectElementCount(".o-IconPicker", 0);
        expect(getContent(el)).toBe(`<p>ab${ICON}[]</p>`);

        undo(editor);
        expect(getContent(el)).toBe("<p>ab[]</p>");
    });

    test("insert a filled icon", async () => {
        const { el, editor } = await setupEditor("<p>ab[]</p>");
        await openIconPicker(editor);
        await click(".o-IconPicker-icon[data-icon='favorite'].oi-filled");
        await animationFrame();
        expect(el.querySelector("span.oi")).toHaveClass("oi-filled");
        expect(el.querySelector("span.oi")).toHaveAttribute("data-icon", "favorite");
    });

    test("display the filled variant right after the outlined one", async () => {
        const { editor } = await setupEditor("<p>[]</p>");
        await openIconPicker(editor);
        expect(displayedIcons()).toEqual([
            "check",
            "close",
            "diamond",
            "diamond (filled)",
            "favorite",
            "favorite (filled)",
            "home",
            "home (filled)",
            "search",
            "mail",
            "mail (filled)",
            "local_bar",
            "bug_report",
            "bug_report (filled)",
            "oi_view-kanban",
        ]);
    });

    test("search icons by name and tags", async () => {
        const { editor } = await setupEditor("<p>[]</p>");
        await openIconPicker(editor);
        await search("heart");
        expect(displayedIcons()).toEqual(["favorite", "favorite (filled)"]);

        await search("local bar");
        expect(displayedIcons()).toEqual(["local_bar"]);

        await search("COEUR");
        expect(displayedIcons()).toEqual(["favorite", "favorite (filled)"]);

        await search("zzzz");
        expect(displayedIcons()).toEqual([]);
        expect(".o-IconPicker-empty").toHaveText("No icons match your search");

        await click(".o-IconPicker button[title='Clear search']");
        await animationFrame();
        expect(displayedIcons()).toHaveLength(15);
        expect(".o-IconPicker input").toBeFocused();
    });

    test("navigate with the arrows and pick with enter", async () => {
        const { el, editor } = await setupEditor("<p>[]</p>");
        await openIconPicker(editor);
        expect(".o-IconPicker-icon.o-active").toHaveAttribute("data-icon", "check");

        await press("ArrowRight");
        await animationFrame();
        expect(".o-IconPicker-icon.o-active").toHaveAttribute("data-icon", "close");
        expect(".o-IconPicker input").toHaveAttribute("placeholder", "close");

        // 7 icons per row
        await press("ArrowDown");
        await animationFrame();
        expect(".o-IconPicker-icon.o-active").toHaveAttribute("data-icon", "search");

        await press("ArrowLeft");
        await animationFrame();
        expect(".o-IconPicker-icon.o-active").toHaveAttribute("data-icon", "home");
        expect(".o-IconPicker-icon.o-active").toHaveClass("oi-filled");
        await press("ArrowUp");
        await animationFrame();
        expect(".o-IconPicker-icon.o-active").toHaveAttribute("data-icon", "check");

        await press("ArrowRight");
        await press("Enter");
        await animationFrame();
        await expectElementCount(".o-IconPicker", 0);
        expect(el.querySelector("span.oi")).toHaveAttribute("data-icon", "close");
    });

    test("pick the first result of a search with enter", async () => {
        const { el, editor } = await setupEditor("<p>[]</p>");
        await openIconPicker(editor);
        await search("insect");
        await press("Enter");
        await animationFrame();
        expect(el.querySelector("span.oi")).toHaveAttribute("data-icon", "bug_report");
    });

    test("close the icon picker with escape", async () => {
        const { el, editor } = await setupEditor("<p>ab[]</p>");
        await openIconPicker(editor);
        await press("Escape");
        await animationFrame();
        await expectElementCount(".o-IconPicker", 0);
        expect(getContent(el)).toBe("<p>ab[]</p>");
    });

    test("list the frequently used icons first", async () => {
        const { editor } = await setupEditor("<p>[]</p>");
        await openIconPicker(editor);
        expect(".o-IconPicker-section").toHaveCount(0);
        await click(".o-IconPicker-icon[data-icon='mail'].oi-filled");
        await animationFrame();

        await openIconPicker(editor);
        await click(".o-IconPicker-icon[data-icon='home']:not(.oi-filled)");
        await animationFrame();

        await openIconPicker(editor);
        await click(".o-IconPicker-icon[data-icon='home']:not(.oi-filled)");
        await animationFrame();

        await openIconPicker(editor);
        expect(queryAll(".o-IconPicker-section").map((el) => el.textContent.trim())).toEqual([
            "Frequently used",
            "All icons",
        ]);
        expect(displayedIcons().slice(0, 3)).toEqual(["home", "mail (filled)", "check"]);

        // While searching, the frequent icons matching the search come first,
        // and are not repeated.
        await search("mail");
        expect(".o-IconPicker-section").toHaveCount(0);
        expect(displayedIcons().slice(0, 2)).toEqual(["mail (filled)", "mail"]);
        expect(displayedIcons().filter((icon) => icon === "mail (filled)")).toHaveLength(1);
    });

    test("expose the picker to assistive technologies", async () => {
        const { editor } = await setupEditor("<p>[]</p>");
        await openIconPicker(editor);
        expect(".o-IconPicker").toHaveAttribute("role", "dialog");
        expect(".o-IconPicker").toHaveAttribute("aria-label", "Insert an icon");

        const input = queryOne(".o-IconPicker input");
        expect(input).toHaveAttribute("role", "combobox");
        expect(input).toHaveAttribute("aria-label", "Search an icon");
        const listbox = queryOne(`#${input.getAttribute("aria-controls")}`);
        expect(listbox).toHaveAttribute("role", "listbox");
        expect(".o-IconPicker-search [data-icon='search']").toHaveAttribute("aria-hidden", "true");

        // Every icon is an option named after its readable name
        expect(queryAll(".o-IconPicker-icon").every((el) => el.role === "option")).toBe(true);
        expect(".o-IconPicker-icon[data-icon='local_bar']").toHaveAttribute(
            "aria-label",
            "local bar"
        );
        expect(".o-IconPicker-icon[data-icon='home'].oi-filled").toHaveAttribute(
            "aria-label",
            "home (filled)"
        );
        expect(".o-IconPicker-icon[data-icon='oi_view-kanban']").toHaveAttribute(
            "aria-label",
            "view kanban"
        );

        // The active option follows the keyboard navigation
        const activeOption = () => queryOne(`#${input.getAttribute("aria-activedescendant")}`);
        expect(activeOption()).toHaveAttribute("data-icon", "check");
        expect(activeOption()).toHaveAttribute("aria-selected", "true");
        await press("ArrowRight");
        await animationFrame();
        expect(activeOption()).toHaveAttribute("data-icon", "close");
        expect(".o-IconPicker-icon[data-icon='check']").toHaveAttribute("aria-selected", "false");

        await search("zzzz");
        expect(input).not.toHaveAttribute("aria-activedescendant");
        expect(".o-IconPicker-empty").toHaveAttribute("role", "status");

        await click(".o-IconPicker button[title='Clear search']");
        await animationFrame();
        expect(activeOption()).toHaveAttribute("data-icon", "check");
    });

    test("name the sections of the listbox", async () => {
        const { editor } = await setupEditor("<p>[]</p>");
        await openIconPicker(editor);
        expect(".o-IconPicker [role='group']").toHaveCount(0);
        await click(".o-IconPicker-icon[data-icon='mail']:not(.oi-filled)");
        await animationFrame();

        await openIconPicker(editor);
        const groups = queryAll(".o-IconPicker [role='listbox'] > [role='group']");
        expect(groups).toHaveLength(2);
        expect(
            groups.map((group) =>
                queryOne(`#${group.getAttribute("aria-labelledby")}`).textContent.trim()
            )
        ).toEqual(["Frequently used", "All icons"]);
    });

    test("the clear search button is an accessible button", async () => {
        const { editor } = await setupEditor("<p>[]</p>");
        await openIconPicker(editor);
        await search("heart");
        const button = ".o-IconPicker button[title='Clear search']";
        expect(button).toHaveAttribute("type", "button");
        expect(button).toHaveAttribute("aria-label", "Clear search");
        expect(`${button} .oi`).toHaveAttribute("aria-hidden", "true");
    });

    test("pick an icon for another purpose than inserting it", async () => {
        const { el, editor } = await setupEditor("<p>ab[]</p>");
        let promise = editor.shared.icon.pickIcon({ target: el.querySelector("p") });
        await waitFor(".o-IconPicker");
        expect(".o-IconPicker").toHaveAttribute("aria-label", "Select an icon");
        await click(".o-IconPicker-icon[data-icon='favorite'].oi-filled");
        const iconEl = await promise;
        await expectElementCount(".o-IconPicker", 0);
        expect(iconEl.outerHTML).toBe(`<span class="oi oi-filled" data-icon="favorite"></span>`);
        expect(getContent(el)).toBe("<p>ab[]</p>", { message: "nothing is inserted" });

        promise = editor.shared.icon.pickIcon();
        await waitFor(".o-IconPicker");
        await press("Escape");
        expect(await promise).toBe(undefined, { message: "closed without picking" });

        // Opening a picker closes the open one
        const firstPromise = editor.shared.icon.pickIcon();
        await waitFor(".o-IconPicker");
        promise = editor.shared.icon.pickIcon();
        expect(await firstPromise).toBe(undefined);
        await animationFrame();
        await expectElementCount(".o-IconPicker", 1);
        await click(".o-IconPicker-icon[data-icon='home']:not(.oi-filled)");
        expect((await promise).dataset.icon).toBe("home");
    });

    test("highlight the current icon when picking one", async () => {
        const { editor } = await setupEditor("<p>[]</p>");
        const iconEl = document.createElement("i");
        iconEl.className = "oi";
        iconEl.dataset.icon = "mail";
        editor.shared.icon.pickIcon({ iconEl });
        await waitFor(".o-IconPicker");
        expect(".o-IconPicker-icon.o-selected").toHaveAttribute("data-icon", "mail");
        expect(".o-IconPicker-icon.o-selected").not.toHaveClass("oi-filled");
    });
});
