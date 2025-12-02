# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

from odoo.tests.common import BaseCase
from odoo.addons.html_editor.models.diff_utils import (
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
        self.assertEqual(
            comparison, "<p>foo</p><p><added>bar</added></p><p>baz</p>"
        )

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
            "<p><added>bar</added></p>"
            "<p><added>bor</added></p>"
            "<p><added>bir</added><removed>buz</removed></p>"
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

    def test_replace_tag(self):
        initial_content = "<blockquote>foo</blockquote>"
        new_content = "<code>foo</code>"

        comparison = generate_comparison(new_content, initial_content)
        self.assertEqual(
            comparison,
            "<blockquote><added>foo</added></blockquote>"
            "<code><removed>foo</removed></code>",
        )

    def test_replace_complex(self):
        initial_content = (
            "<blockquote>foo</blockquote>"
            "<blockquote>bar</blockquote>"
            "<blockquote>baz</blockquote>"
            "<p>---<span>***</span>---</p>"
            "<blockquote>only content change</blockquote>"
            "<p>+++<span>~~~</span>+++</p>"
            "<blockquote>content and tag change</blockquote>"
            "<p>???<span>===</span>???</p>"
            "<blockquote>111</blockquote>"
            "<blockquote>222</blockquote>"
            "<blockquote>333</blockquote>"
        )
        new_content = (
            "<code>foo</code>"
            "<code>bar</code>"
            "<code>baz</code>"
            "<p>---<span>***</span>---</p>"
            "<blockquote>lorem ipsum</blockquote>"
            "<p>+++<span>~~~</span>+++</p>"
            "<code>dolor sit amet</code>"
            "<p>???<span>===</span>???</p>"
            "<blockquote>aaa</blockquote>"
            "<blockquote>bbb</blockquote>"
            "<blockquote>ccc</blockquote>"
        )

        comparison = generate_comparison(new_content, initial_content)
        self.assertEqual(
            comparison,
            "<blockquote><added>foo</added></blockquote>"
            "<blockquote><added>bar</added></blockquote>"
            "<blockquote><added>baz</added></blockquote>"
            "<code><removed>foo</removed></code>"
            "<code><removed>bar</removed></code>"
            "<code><removed>baz</removed></code>"
            "<p>---<span>***</span>---</p>"
            "<blockquote><added>only content change</added>"
            "<removed>lorem ipsum</removed></blockquote>"
            "<p>+++<span>~~~</span>+++</p>"
            "<blockquote><added>content and tag change</added></blockquote>"
            "<code><removed>dolor sit amet</removed></code>"
            "<p>???<span>===</span>???</p>"
            "<blockquote><added>111</added><removed>aaa</removed></blockquote>"
            "<blockquote><added>222</added><removed>bbb</removed></blockquote>"
            "<blockquote><added>333</added><removed>ccc</removed></blockquote>",
        )

    def test_replace_tag_multiline(self):
        initial_content = (
            "<blockquote>foo</blockquote>"
            "<code>bar lorem ipsum dolor</code>"
            "<blockquote>baz</blockquote>"
        )
        new_content = (
            "<code>foo</code>"
            "<blockquote>bar lorem ipsum dolor</blockquote>"
            "<code>baz</code>"
        )

        comparison = generate_comparison(new_content, initial_content)
        self.assertEqual(
            comparison,
            "<blockquote><added>foo</added></blockquote>"
            "<code><added>bar lorem ipsum dolor</added>"
            "<removed>foo</removed></code>"
            "<blockquote><added>baz</added>"
            "<removed>bar lorem ipsum dolor</removed></blockquote>"
            "<code><removed>baz</removed></code>",
        )

    def test_replace_nested_divs(self):
        initial_content = "<div class='A1'><div class='A2'><b>A</b></div></div>"
        new_content = "<div class='B1'><div class='B2'><i>B</i></div></div>"

        comparison = generate_comparison(new_content, initial_content)
        # This is a trade-off because of the limitation of the current
        # comparison system :
        # We can't easily generate comparison when only the tag parameters
        # changes, because the diff system will not contain the closing tags
        # in this case.
        #
        # This is why we choose to have the comparison below instead of :
        # <div class='A1'><div class='A2'>
        #     <b><removed>A</removed></b>
        # </div></div>
        # <div class='B1'><div class='B2'>
        #     <i><added>B</added></i>
        # </div></div>
        #
        # If we need to improve this in the future, we would probably have to
        # change drastically the comparison system to add a way to parse HTML.
        self.assertEqual(
            comparison,
            "<div class='A1'><div class='A2'>"
            "<b><added>A</added></b>"
            "<i><removed>B</removed></i>"
            "</div></div>",
        )

    def test_same_tag_replace_fixer(self):
        initial_content = "<div><p><b>A</b><b>B</b></p></div>"
        new_content = "<div>X<p><b>B</b></p></div>"

        comparison = generate_comparison(new_content, initial_content)
        # This is a trade-off, see explanation in test_replace_nested_divs.
        self.assertEqual(
            comparison,
            "<div><removed>X</removed>"
            "<p><b><added>A</added></b>"
            "<b>B</b></p></div>",
        )

    def test_simple_removal(self):
        initial_content = "<div><p>A</p></div>"
        new_content = "<div>X<p>A</p></div>"

        comparison = generate_comparison(new_content, initial_content)
        # This is a trade-off, see explanation in test_replace_nested_divs.
        self.assertEqual(
            comparison,
            "<div><removed>X</removed><p>A</p></div>",
        )

    def test_simple_addition(self):
        initial_content = "<div>X<p>A</p></div>"
        new_content = "<div><p>A</p></div>"

        comparison = generate_comparison(new_content, initial_content)
        # This is a trade-off, see explanation in test_replace_nested_divs.
        self.assertEqual(
            comparison,
            "<div><added>X</added><p>A</p></div>",
        )

    def test_replace_just_class(self):
        initial_content = "<div class='A1'>A</div>"
        new_content = "<div class='B1'>A</div>"

        comparison = generate_comparison(new_content, initial_content)
        # This is a trade-off, see explanation in test_replace_nested_divs.
        self.assertEqual(
            comparison,
            "<div class='A1'>A</div>",
        )

    def test_replace_twice_just_class(self):
        initial_content = (
            "<div class='A1'>A</div><p>abc</p><div class='D1'>D</div>"
        )
        new_content = "<div class='B1'>A</div><p>abc</p><div class='E1'>D</div>"

        comparison = generate_comparison(new_content, initial_content)
        # This is a trade-off, see explanation in test_replace_nested_divs.
        self.assertEqual(
            comparison,
            "<div class='A1'>A</div><p>abc</p><div class='D1'>D</div>",
        )

    def test_replace_with_just_class(self):
        initial_content = "<p>abc</p><div class='A1'>A</div>"
        new_content = "<p>def</p><div class='B1'>A</div>"

        comparison = generate_comparison(new_content, initial_content)
        # This is a trade-off, see explanation in test_replace_nested_divs.
        self.assertEqual(
            comparison,
            "<p><added>abc</added><removed>def</removed></p>"
            "<div class='A1'>A</div>",
        )

    def test_replace_class_and_content(self):
        initial_content = "<div class='A1'>A</div>"
        new_content = "<div class='B1'>B</div>"

        comparison = generate_comparison(new_content, initial_content)
        # This is a trade-off, see explanation in test_replace_nested_divs.
        self.assertEqual(
            comparison,
            "<div class='A1'><added>A</added><removed>B</removed></div>",
        )

    def test_replace_class_and_deep_content(self):
        initial_content = "<div class='A1'><p><i>A</i></p></div>"
        new_content = "<div class='B1'><p><i>B</i></p></div>"

        comparison = generate_comparison(new_content, initial_content)
        # This is a trade-off, see explanation in test_replace_nested_divs.
        self.assertEqual(
            comparison,
            "<div class='A1'><p><i>"
            "<added>A</added><removed>B</removed>"
            "</i></p></div>",
        )
