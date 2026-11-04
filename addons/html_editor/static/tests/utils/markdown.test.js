import { isMarkdown } from "@html_editor/main/markdown/markdown_utils";
import { describe, expect, test } from "@odoo/hoot";

describe("isMarkdown", () => {
    test("should detect Markdown syntax", () => {
        for (const text of [
            "# Heading",
            "Some **bold** text",
            "Use `npm install`",
            "~~removed~~",
            "See [the docs](https://www.odoo.com)",
            "![image](https://www.odoo.com/logo.png)",
            "- first\n- second",
            "1. first\n2. second",
            "- [ ] task",
            "> quote",
            "```\ncode\n```",
            "| a | b |\n|---|---|",
        ]) {
            expect(isMarkdown(text)).toBe(true, { message: JSON.stringify(text) });
        }
    });

    test("should not detect regular text as Markdown", () => {
        for (const text of [
            "Hello world",
            "#hashtag",
            "- a single dash item",
            "my_variable_name and __init__.py",
            "2 * 3 * 4",
            "https://www.odoo.com",
            "a | b",
            "-----",
        ]) {
            expect(isMarkdown(text)).toBe(false, { message: JSON.stringify(text) });
        }
    });
});
