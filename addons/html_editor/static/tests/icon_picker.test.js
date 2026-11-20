import { describe, expect, test } from "@odoo/hoot";
import { click, edit, press, queryAll, waitFor } from "@odoo/hoot-dom";
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
});
