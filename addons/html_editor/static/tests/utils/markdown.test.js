import { isMarkdown } from "@html_editor/main/markdown/markdown_utils";
import { describe, expect, test } from "@odoo/hoot";

describe("isMarkdown", () => {
    test("should detect Markdown syntax", () => {
        for (const text of [
            "# Heading",
            "## Heading\n\nSome text",
            "#\tHeading\n",
            "Some **bold** text",
            "Use `npm install`",
            "~~removed~~",
            "See [the docs](https://www.odoo.com)",
            "![image](https://www.odoo.com/logo.png)",
            "- a single dash item",
            "- first\n- second",
            "1. first\n2. second",
            "- [ ] task",
            "-\t[x] task",
            "1. [ ] task",
            "> quote",
            ">\tquote after a tab",
            "```\ncode\n```",
            "Some code:\n```js\nconst a = 1;\n```",
            "````\nclosed by a shorter delimiter\n```",
            "| a | b |\n|---|---|\n| 1 | 2 |",
            "Some text\n\na | b\n--|--\n1 | 2",
        ]) {
            expect(isMarkdown(text)).toBe(true, { message: JSON.stringify(text) });
        }
    });

    test("should not detect regular text as Markdown", () => {
        for (const text of [
            "Hello world",
            "#hashtag",
            "   # indented",
            "```\nnot closed",
            "1) first\n2) second",
            "my_variable_name and __init__.py",
            "2 * 3 * 4",
            "https://www.odoo.com",
            "a | b",
            "| a | b |\n|---|---|",
            "Some text\n| a | b |\n|---|---|\n| 1 | 2 |",
            "-----",
        ]) {
            expect(isMarkdown(text)).toBe(false, { message: JSON.stringify(text) });
        }
    });
});
