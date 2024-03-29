# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

from odoo.tests.common import BaseCase
from odoo.addons.web_editor.models.diff_utils import (
    generate_patch,
    generate_comparison,
    apply_patch,
)


@odoo.tests.tagged("post_install", "-at_install", "html_history")
class TestPatchUtils(BaseCase):
    def test_new_content_add_line(self):
        initial_content = "<p>foo</p><p>baz</p>"
        new_content = "<p>foo</p><p>bar</p><p>baz</p>"

        patch = generate_patch(new_content, initial_content)
        # Even if we added content in the new_content, we expect a remove
        # operation, because the patch would be used to restore the initial
        # content from the new content.
        self.assertEqual(patch, "-@3,4")

        restored_initial_content = apply_patch(new_content, patch)
        self.assertEqual(restored_initial_content, initial_content)

        comparison = generate_comparison(new_content, initial_content)
        self.assertEqual(
            comparison, "<p>foo</p><p><removed>bar</removed></p><p>baz</p>"
        )

    def test_new_content_remove_line(self):
        initial_content = "<p>foo</p><p>bar</p><p>baz</p>"
        new_content = "<p>foo</p><p>baz</p>"

        patch = generate_patch(new_content, initial_content)
        self.assertEqual(patch, "+@2:<p>bar</p>")

        restored_initial_content = apply_patch(new_content, patch)
        self.assertEqual(restored_initial_content, initial_content)

        comparison = generate_comparison(new_content, initial_content)
        self.assertEqual(comparison, "<p>foo</p><p><added>bar</added></p><p>baz</p>")

    def test_new_content_replace_line(self):
        initial_content = "<p>foo</p><p>bar</p><p>bor</p><p>bir</p><p>baz</p>"
        new_content = "<p>foo</p><p>buz</p><p>baz</p>"

        patch = generate_patch(new_content, initial_content)
        self.assertEqual(patch, "R@3:<p>bar</p><p>bor</p><p>bir")

        restored_initial_content = apply_patch(new_content, patch)
        self.assertEqual(restored_initial_content, initial_content)

        comparison = generate_comparison(new_content, initial_content)
        self.assertEqual(
            comparison,
            "<p>foo</p>"
            "<p><removed>buz</removed><added>bar</added></p>"
            "<p><added>bor</added></p><p><added>bir</added></p>"
            "<p>baz</p>",
        )

    def test_new_content_is_falsy(self):
        initial_content = "<p>foo</p><p>bar</p>"
        new_content = ""

        patch = generate_patch(new_content, initial_content)
        self.assertEqual(patch, "+@0:<p>foo</p><p>bar</p>")

        restored_initial_content = apply_patch(new_content, patch)
        self.assertEqual(restored_initial_content, initial_content)

        comparison = generate_comparison(new_content, initial_content)
        self.assertEqual(
            comparison, "<p><added>foo</added></p><p><added>bar</added></p>"
        )

    def test_new_content_is_equal(self):
        initial_content = "<p>foo</p><p>bar</p>"
        new_content = "<p>foo</p><p>bar</p>"

        patch = generate_patch(new_content, initial_content)
        self.assertEqual(patch, "")
        restored_initial_content = apply_patch(new_content, patch)
        self.assertEqual(restored_initial_content, initial_content)

        initial_content = ""
        new_content = ""

        patch = generate_patch(new_content, initial_content)
        self.assertEqual(patch, "")
        restored_initial_content = apply_patch(new_content, patch)
        self.assertEqual(restored_initial_content, initial_content)

    def test_new_content_multiple_operation(self):
        initial_content = "<p>foo</p><p>bar</p><p>baz</p><p>buz</p><p>boz</p>"
        new_content = (
            "<p>foo</p><div>new1<b>new2</b>new3</div>"
            "<p>bar</p><p>baz</p><p>boz</p><p>end</p>"
        )

        patch = generate_patch(new_content, initial_content)
        self.assertEqual(
            patch,
            """-@3,6
+@10:<p>buz</p>
-@13,14""",
        )

        restored_initial_content = apply_patch(new_content, patch)
        self.assertEqual(restored_initial_content, initial_content)

        comparison = generate_comparison(new_content, initial_content)
        self.assertEqual(
            comparison,
            "<p>foo</p>"
            "<div><removed>new1</removed>"
            "<b><removed>new2</removed></b>"
            "<removed>new3</removed></div>"
            "<p>bar</p><p>baz</p><p><added>buz</added></p>"
            "<p>boz</p><p><removed>end</removed></p>",
        )

    def test_multiple_revision(self):
        contents = [
            "<p>foo</p><p>bar</p>",
            "<p>foo</p>",
            "<p>f<b>u</b>i</p><p>baz</p>",
            "<p>fi</p><p>boz</p>",
            "<div><h1>something</h1><p>completely different</p></div>",
            "<p>foo</p><p>boz</p><p>buz</p>",
            "<p>buz</p>",
        ]
        patches = []
        for i in range(len(contents) - 1):
            patches.append(generate_patch(contents[i + 1], contents[i]))

        patches.reverse()
        reconstruct_content = contents[-1]
        for patch in patches:
            reconstruct_content = apply_patch(reconstruct_content, patch)

        self.assertEqual(reconstruct_content, contents[0])
