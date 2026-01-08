import pytest

from bs4.element import Tag
from bs4.formatter import (
    Formatter,
    HTMLFormatter,
    XMLFormatter,
)
from . import SoupTest


class TestFormatter(SoupTest):
    def test_default_attributes(self):
        # Test the default behavior of Formatter.attributes().
        formatter = Formatter()
        tag = Tag(name="tag")
        tag["b"] = "1"
        tag["a"] = "2"

        # Attributes come out sorted by name. In Python 3, attributes
        # normally come out of a dictionary in the order they were
        # added.
        assert [("a", "2"), ("b", "1")] == formatter.attributes(tag)

        # This works even if Tag.attrs is None, though this shouldn't
        # normally happen.
        tag.attrs = None
        assert [] == formatter.attributes(tag)

        assert " " == formatter.indent

    def test_sort_attributes(self):
        # Test the ability to override Formatter.attributes() to,
        # e.g., disable the normal sorting of attributes.
        class UnsortedFormatter(Formatter):
            def attributes(self, tag):
                self.called_with = tag
                for k, v in sorted(tag.attrs.items()):
                    if k == "ignore":
                        continue
                    yield k, v

        soup = self.soup('<p cval="1" aval="2" ignore="ignored"></p>')
        formatter = UnsortedFormatter()
        decoded = soup.decode(formatter=formatter)

        # attributes() was called on the <p> tag. It filtered out one
        # attribute and sorted the other two.
        assert formatter.called_with == soup.p
        assert '<p aval="2" cval="1"></p>' == decoded

    def test_empty_attributes_are_booleans(self):
        # Test the behavior of empty_attributes_are_booleans as well
        # as which Formatters have it enabled.

        for name in ("html", "minimal", None):
            formatter = HTMLFormatter.REGISTRY[name]
            assert False is formatter.empty_attributes_are_booleans

        formatter = XMLFormatter.REGISTRY[None]
        assert False is formatter.empty_attributes_are_booleans

        formatter = HTMLFormatter.REGISTRY["html5"]
        assert True is formatter.empty_attributes_are_booleans

        # Verify that the constructor sets the value.
        formatter = Formatter(empty_attributes_are_booleans=True)
        assert True is formatter.empty_attributes_are_booleans

        # Now demonstrate what it does to markup.
        for markup in ("<option selected></option>", '<option selected=""></option>'):
            soup = self.soup(markup)
            for formatter in ("html", "minimal", "xml", None):
                assert b'<option selected=""></option>' == soup.option.encode(
                    formatter="html"
                )
                assert b"<option selected></option>" == soup.option.encode(
                    formatter="html5"
                )

    @pytest.mark.parametrize(
        "indent,expect",
        [
            (None, "<a>\n<b>\ntext\n</b>\n</a>\n"),
            (-1, "<a>\n<b>\ntext\n</b>\n</a>\n"),
            (0, "<a>\n<b>\ntext\n</b>\n</a>\n"),
            ("", "<a>\n<b>\ntext\n</b>\n</a>\n"),
            (1, "<a>\n <b>\n  text\n </b>\n</a>\n"),
            (2, "<a>\n  <b>\n    text\n  </b>\n</a>\n"),
            ("\t", "<a>\n\t<b>\n\t\ttext\n\t</b>\n</a>\n"),
            ("abc", "<a>\nabc<b>\nabcabctext\nabc</b>\n</a>\n"),
            # Some invalid inputs -- the default behavior is used.
            (object(), "<a>\n <b>\n  text\n </b>\n</a>\n"),
            (b"bytes", "<a>\n <b>\n  text\n </b>\n</a>\n"),
        ],
    )
    def test_indent(self, indent, expect):
        # Pretty-print a tree with a Formatter set to
        # indent in a certain way and verify the results.
        soup = self.soup("<a><b>text</b></a>")
        formatter = Formatter(indent=indent)
        assert soup.prettify(formatter=formatter) == expect

        # Pretty-printing only happens with prettify(), not
        # encode().
        assert soup.encode(formatter=formatter) != expect

    def test_default_indent_value(self):
        formatter = Formatter()
        assert formatter.indent == " "

    @pytest.mark.parametrize("formatter,expect",
        [
            (HTMLFormatter(indent=1), "<p>\n a\n</p>\n"),
            (HTMLFormatter(indent=2), "<p>\n  a\n</p>\n"),
            (XMLFormatter(indent=1), "<p>\n a\n</p>\n"),
            (XMLFormatter(indent="\t"), "<p>\n\ta\n</p>\n"),
        ]                             )
    def test_indent_subclasses(self, formatter, expect):
        soup = self.soup("<p>a</p>")
        assert expect == soup.p.prettify(formatter=formatter)

    @pytest.mark.parametrize(
        "s,expect_html,expect_html5",
        [
            # The html5 formatter is much less aggressive about escaping ampersands
            # than the html formatter.
            ("foo & bar", "foo &amp; bar", "foo & bar"),
            ("foo&", "foo&amp;", "foo&"),
            ("foo&&& bar", "foo&amp;&amp;&amp; bar", "foo&&& bar"),
            ("x=1&y=2", "x=1&amp;y=2", "x=1&y=2"),
            ("&123", "&amp;123", "&123"),
            ("&abc", "&amp;abc", "&abc"),
            ("foo &0 bar", "foo &amp;0 bar", "foo &0 bar"),
            ("foo &lolwat bar", "foo &amp;lolwat bar", "foo &lolwat bar"),
            # But both formatters escape what the HTML5 spec considers ambiguous ampersands.
            ("&nosuchentity;", "&amp;nosuchentity;", "&amp;nosuchentity;"),
        ],
    )
    def test_entity_substitution(self, s, expect_html, expect_html5):
        assert HTMLFormatter.REGISTRY["html"].substitute(s) == expect_html
        assert HTMLFormatter.REGISTRY["html5"].substitute(s) == expect_html5
        assert HTMLFormatter.REGISTRY["html5-4.12"].substitute(s) == expect_html

    def test_entity_round_trip(self):
        # This is more an explanatory test and a way to avoid regressions than a test of functionality.

        markup = "<p>Some division signs: ÷ &divide; &#247; &#xf7;. These are made with: ÷ &amp;divide; &amp;#247;</p>"
        soup = self.soup(markup)
        assert (
            "Some division signs: ÷ ÷ ÷ ÷. These are made with: ÷ &divide; &#247;"
            == soup.p.string
        )

        # Oops, I forgot to mention the entity.
        soup.p.string = soup.p.string + " &#xf7;"

        assert (
            "Some division signs: ÷ ÷ ÷ ÷. These are made with: ÷ &divide; &#247; &#xf7;"
            == soup.p.string
        )

        expect = "<p>Some division signs: &divide; &divide; &divide; &divide;. These are made with: &divide; &amp;divide; &amp;#247; &amp;#xf7;</p>"
        assert expect == soup.p.decode(formatter="html")
        assert expect == soup.p.decode(formatter="html5")

        markup = "<p>a & b</p>"
        soup = self.soup(markup)
        assert "<p>a &amp; b</p>" == soup.p.decode(formatter="html")
        assert "<p>a & b</p>" == soup.p.decode(formatter="html5")
