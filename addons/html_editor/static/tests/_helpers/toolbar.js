import { expect } from "@odoo/hoot";
import { queryAll, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";

export async function expandToolbar() {
    await contains(".o-we-toolbar .btn[name='expand_toolbar'").click();
    await waitFor(".o-we-toolbar[data-namespace='expanded']");
}

/**
 * Checks the `aria-pressed` and `aria-expanded` attributes of every button
 * currently displayed in the toolbar, based on the toolbar items declared by
 * the plugins:
 * - buttons opening a popup (dropdowns, color selectors) rely on
 *   `aria-expanded` instead of `aria-pressed`: it must match whether the popup
 *   is open (`show` class for dropdowns, `active` class for color selectors),
 *   they must have `aria-haspopup`, and `aria-controls` must reference the
 *   popup while it is open, whose role must match `aria-haspopup`,
 * - buttons whose item defines `isActive` are toggle buttons: they must have
 *   `aria-pressed` matching their `active` state,
 * - other buttons are not toggle buttons and must not have `aria-pressed`.
 *
 * @param {import("@html_editor/editor").Editor} editor
 * @param {Object} [options]
 * @param {(el: HTMLElement) => boolean} [options.isPopupOpen] whether the popup
 *   of the given button is open, for buttons whose `active` class has another
 *   meaning (e.g. an applied text effect)
 */
export function expectConsistentAriaStates(editor, { isPopupOpen } = {}) {
    const toggleButtonIds = new Set(
        editor
            .getResource("toolbar_items")
            .filter((item) => !item.Component && "isActive" in item)
            .map((item) => item.id)
    );
    const buttons = queryAll(".o-we-toolbar .btn");
    expect(buttons.length).toBeGreaterThan(0, { message: "toolbar should have buttons" });
    for (const el of buttons) {
        const name = el.getAttribute("name");
        const label = name || el.className;
        if (el.hasAttribute("aria-expanded")) {
            const isOpen = isPopupOpen
                ? isPopupOpen(el)
                : el.classList.contains("show") || el.classList.contains("active");
            expect(el).toHaveAttribute("aria-expanded", isOpen ? "true" : "false", {
                message: `"${label}" popup should be ${isOpen ? "open" : "closed"}`,
            });
            expect(el).not.toHaveAttribute("aria-pressed", undefined, {
                message: `"${label}" opens a popup and is not a toggle button`,
            });
            expect(el).toHaveAttribute("aria-haspopup", undefined, {
                message: `"${label}" should announce its popup`,
            });
            if (isOpen) {
                const popupId = el.getAttribute("aria-controls");
                const popupEl = popupId && document.getElementById(popupId);
                expect(!!popupEl).toBe(true, {
                    message: `"${label}" aria-controls should reference its open popup`,
                });
                expect(popupEl).toHaveAttribute("role", el.getAttribute("aria-haspopup"), {
                    message: `"${label}" popup role should match its aria-haspopup`,
                });
                if (popupEl.role === "dialog") {
                    expect(popupEl).toHaveAttribute("aria-label", el.getAttribute("aria-label"), {
                        message: `"${label}" dialog should be named after its button`,
                    });
                }
            } else {
                expect(el).not.toHaveAttribute("aria-controls", undefined, {
                    message: `"${label}" should not reference a closed popup`,
                });
            }
        } else if (toggleButtonIds.has(name)) {
            expect(el).toHaveAttribute(
                "aria-pressed",
                el.classList.contains("active") ? "true" : "false",
                { message: `"${label}" is a toggle button` }
            );
        } else {
            expect(el).not.toHaveAttribute("aria-pressed", undefined, {
                message: `"${label}" is not a toggle button`,
            });
        }
    }
}

/**
 * Checks that every button currently displayed in the toolbar has an
 * `aria-label`:
 * - it is the same as the button's `title`, which possibly includes its
 *   current value (e.g. "Select text style: Paragraph"), so that screen
 *   readers do not read it twice (as the name, then as the description),
 * - it contains the button's visible text, if any (text hidden from screen
 *   readers excepted),
 * - the button's icons are hidden from screen readers.
 * Every iframe of the toolbar (e.g. the font size input) must also have a
 * `title`, which names the input it contains, and every button of the
 * toolbar and of its open dropdowns must have the `button` type.
 */
export function expectAccessibleLabels() {
    const buttons = queryAll(".o-we-toolbar .btn");
    expect(buttons.length).toBeGreaterThan(0, { message: "toolbar should have buttons" });
    for (const el of buttons) {
        const label = el.getAttribute("name") || el.className;
        const ariaLabel = el.getAttribute("aria-label");
        expect(!!ariaLabel).toBe(true, { message: `"${label}" should have an aria-label` });
        expect(el).toHaveAttribute("title", ariaLabel, {
            message: `"${label}" title should be the same as its aria-label "${ariaLabel}"`,
        });
        // Text hidden from screen readers (e.g. an SVG icon drawn with text)
        // is not part of the label
        const visibleEl = el.cloneNode(true);
        for (const hiddenEl of visibleEl.querySelectorAll("[aria-hidden='true']")) {
            hiddenEl.remove();
        }
        const text = visibleEl.textContent.trim();
        expect(ariaLabel.includes(text)).toBe(true, {
            message: `"${label}" aria-label "${ariaLabel}" should contain its text "${text}"`,
        });
        for (const icon of el.querySelectorAll(".oi, svg")) {
            expect(icon).toHaveAttribute("aria-hidden", "true", {
                message: `"${label}" icon should be hidden from screen readers`,
            });
        }
    }
    for (const el of queryAll(".o-we-toolbar button, .o-we-toolbar-dropdown button")) {
        expect(el).toHaveAttribute("type", "button", {
            message: `"${el.getAttribute("name") || el.className}" should have the button type`,
        });
    }
    for (const iframe of queryAll(".o-we-toolbar iframe")) {
        const label = iframe.className;
        const title = iframe.getAttribute("title");
        expect(!!title).toBe(true, { message: `"${label}" iframe should have a title` });
        const input = iframe.contentDocument.querySelector("input");
        if (input) {
            expect(input).toHaveAttribute("aria-label", title, {
                message: `"${label}" iframe input should be named after its title`,
            });
        }
    }
}
