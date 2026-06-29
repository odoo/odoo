"""Tests of classes in element.py.

The really big classes -- Tag, PageElement, and NavigableString --
are tested in separate files.
"""

import pytest
from bs4.element import (
    HTMLAttributeDict,
    XMLAttributeDict,
    CharsetMetaAttributeValue,
    ContentMetaAttributeValue,
    NamespacedAttribute,
    ResultSet,
)

class TestNamedspacedAttribute:
    def test_name_may_be_none_or_missing(self):
        a = NamespacedAttribute("xmlns", None)
        assert a == "xmlns"

        a = NamespacedAttribute("xmlns", "")
        assert a == "xmlns"

        a = NamespacedAttribute("xmlns")
        assert a == "xmlns"

    def test_namespace_may_be_none_or_missing(self):
        a = NamespacedAttribute(None, "tag")
        assert a == "tag"

        a = NamespacedAttribute("", "tag")
        assert a == "tag"

    def test_attribute_is_equivalent_to_colon_separated_string(self):
        a = NamespacedAttribute("a", "b")
        assert "a:b" == a

    def test_attributes_are_equivalent_if_prefix_and_name_identical(self):
        a = NamespacedAttribute("a", "b", "c")
        b = NamespacedAttribute("a", "b", "c")
        assert a == b

        # The actual namespace is not considered.
        c = NamespacedAttribute("a", "b", None)
        assert a == c

        # But name and prefix are important.
        d = NamespacedAttribute("a", "z", "c")
        assert a != d

        e = NamespacedAttribute("z", "b", "c")
        assert a != e


class TestAttributeValueWithCharsetSubstitution:
    """Certain attributes are designed to have the charset of the
    final document substituted into their value.
    """

    def test_charset_meta_attribute_value(self):
        # The value of a CharsetMetaAttributeValue is whatever
        # encoding the string is in.
        value = CharsetMetaAttributeValue("euc-jp")
        assert "euc-jp" == value
        assert "euc-jp" == value.original_value
        assert "utf8" == value.substitute_encoding("utf8")
        assert "ascii" == value.substitute_encoding("ascii")

        # If the target encoding is a Python internal encoding,
        # no encoding will be mentioned in the output HTML.
        assert "" == value.substitute_encoding("palmos")

    def test_content_meta_attribute_value(self):
        value = ContentMetaAttributeValue("text/html; charset=euc-jp")
        assert "text/html; charset=euc-jp" == value
        assert "text/html; charset=euc-jp" == value.original_value
        assert "text/html; charset=utf8" == value.substitute_encoding("utf8")
        assert "text/html; charset=ascii" == value.substitute_encoding("ascii")

        # If the target encoding is a Python internal encoding, the
        # charset argument will be omitted altogether.
        assert "text/html" == value.substitute_encoding("palmos")


class TestAttributeDicts:
    def test_xml_attribute_value_handling(self):
        # Verify that attribute values are processed according to the
        # XML spec's rules.
        d = XMLAttributeDict()
        d["v"] = 100
        assert d["v"] == "100"
        d["v"] = 100.123
        assert d["v"] == "100.123"

        # This preserves Beautiful Soup's old behavior in the absence of
        # guidance from the spec.
        d["v"] = False
        assert d["v"] is False

        d["v"] = True
        assert d["v"] is True

        d["v"] = None
        assert d["v"] == ""

    def test_html_attribute_value_handling(self):
        # Verify that attribute values are processed according to the
        # HTML spec's rules.
        d = HTMLAttributeDict()
        d["v"] = 100
        assert d["v"] == "100"
        d["v"] = 100.123
        assert d["v"] == "100.123"

        d["v"] = False
        assert "v" not in d

        d["v"] = None
        assert "v" not in d

        d["v"] = True
        assert d["v"] == "v"

        attribute = NamespacedAttribute("prefix", "name", "namespace")
        d[attribute] = True
        assert d[attribute] == "name"


class TestResultSet:
    def test_getattr_exception(self):
        rs = ResultSet(None)
        with pytest.raises(AttributeError) as e:
            rs.name
        assert (
            """ResultSet object has no attribute "name". You're probably treating a list of elements like a single element. Did you call find_all() when you meant to call find()?"""
            == str(e.value)
        )
