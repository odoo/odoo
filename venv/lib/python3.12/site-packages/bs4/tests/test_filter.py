import pytest
import re
import warnings

from . import (
    SoupTest,
)
from typing import (
    Callable,
    Optional,
    Tuple,
)
from bs4.element import Tag
from bs4.filter import (
    AttributeValueMatchRule,
    ElementFilter,
    MatchRule,
    SoupStrainer,
    StringMatchRule,
    TagNameMatchRule,
)
from bs4._typing import _RawAttributeValues


class TestElementFilter(SoupTest):
    def test_default_behavior(self):
        # An unconfigured ElementFilter matches absolutely everything.
        selector = ElementFilter()
        assert not selector.excludes_everything
        assert selector.includes_everything
        soup = self.soup("<a>text</a>")
        tag = soup.a
        string = tag.string
        assert True is selector.match(soup)
        assert True is selector.match(tag)
        assert True is selector.match(string)
        assert soup.find(selector).name == "a"

        # And allows any incoming markup to be turned into PageElements.
        assert True is selector.allow_tag_creation(None, "tag", None)
        assert True is selector.allow_string_creation("some string")

    def test_setup_with_match_function(self):
        # Configure an ElementFilter with a match function and
        # we can no longer state with certainty that it includes everything.
        selector = ElementFilter(lambda x: False)
        assert not selector.includes_everything

    def test_match(self):
        def m(pe):
            return pe.string == "allow" or (isinstance(pe, Tag) and pe.name == "allow")

        soup = self.soup("<allow>deny</allow>allow<deny>deny</deny>")
        allow_tag = soup.allow
        allow_string = soup.find(string="allow")
        deny_tag = soup.deny
        deny_string = soup.find(string="deny")

        selector = ElementFilter(match_function=m)
        assert True is selector.match(allow_tag)
        assert True is selector.match(allow_string)
        assert False is selector.match(deny_tag)
        assert False is selector.match(deny_string)

        # Since only the match function was provided, there is
        # no effect on tag or string creation.
        soup = self.soup("<a>text</a>", parse_only=selector)
        assert "text" == soup.a.string

    def test_allow_tag_creation(self):
        # By default, ElementFilter.allow_tag_creation allows everything.
        filter = ElementFilter()
        f = filter.allow_tag_creation
        assert True is f("allow", "ignore", {})
        assert True is f("ignore", "allow", {})
        assert True is f(None, "ignore", {"allow": "1"})
        assert True is f("no", "no", {"no": "nope"})

        # You can customize this behavior by overriding
        # allow_tag_creation in a subclass.
        class MyFilter(ElementFilter):
            def allow_tag_creation(
                self,
                nsprefix: Optional[str],
                name: str,
                attrs: Optional[_RawAttributeValues],
            ):
                return (
                    nsprefix == "allow"
                    or name == "allow"
                    or (attrs is not None and "allow" in attrs)
                )

        filter = MyFilter()
        f = filter.allow_tag_creation
        assert True is f("allow", "ignore", {})
        assert True is f("ignore", "allow", {})
        assert True is f(None, "ignore", {"allow": "1"})
        assert False is f("no", "no", {"no": "nope"})

        # Test the customized ElementFilter as a value for parse_only.
        soup = self.soup(
            "<deny>deny</deny> <allow>deny</allow> allow", parse_only=filter
        )

        # The <deny> tag was filtered out, but there was no effect on
        # the strings, since only allow_tag_creation_function was
        # overridden.
        assert "deny <allow>deny</allow> allow" == soup.decode()

        # Similarly, since match_function was not defined, this
        # ElementFilter matches everything.
        assert soup.find(filter) == "deny"

    def test_allow_string_creation(self):
        # By default, ElementFilter.allow_string_creation allows everything.
        filter = ElementFilter()
        f = filter.allow_string_creation
        assert True is f("allow")
        assert True is f("deny")
        assert True is f("please allow")

        # You can customize this behavior by overriding allow_string_creation
        # in a subclass.
        class MyFilter(ElementFilter):
            def allow_string_creation(self, s: str):
                return s == "allow"

        filter = MyFilter()
        f = filter.allow_string_creation
        assert True is f("allow")
        assert False is f("deny")
        assert False is f("please allow")

        # Test the customized ElementFilter as a value for parse_only.
        soup = self.soup(
            "<deny>deny</deny> <allow>deny</allow> allow", parse_only=filter
        )

        # All incoming strings other than "allow" (even whitespace)
        # were filtered out, but there was no effect on the tags,
        # since only allow_string_creation_function was defined.
        assert "<deny>deny</deny><allow>deny</allow>" == soup.decode()

        # Similarly, since match_function was not defined, this
        # ElementFilter matches everything.
        assert soup.find(filter).name == "deny"


class TestMatchRule(SoupTest):
    def _tuple(
        self, rule: MatchRule
    ) -> Tuple[Optional[str], Optional[str], Optional[Callable], Optional[bool]]:
        return (
            rule.string,
            rule.pattern.pattern if rule.pattern else None,
            rule.function,
            rule.present,
        )

    @staticmethod
    def tag_function(x: Tag) -> bool:
        return False

    @staticmethod
    def string_function(x: str) -> bool:
        return False

    @pytest.mark.parametrize(
        "constructor_args, constructor_kwargs, result",
        [
            # String
            ([], dict(string="a"), ("a", None, None, None)),
            (
                [],
                dict(string="\N{SNOWMAN}".encode("utf8")),
                ("\N{SNOWMAN}", None, None, None),
            ),
            # Regular expression
            ([], dict(pattern=re.compile("a")), (None, "a", None, None)),
            ([], dict(pattern="b"), (None, "b", None, None)),
            ([], dict(pattern=b"c"), (None, "c", None, None)),
            # Function
            ([], dict(function=tag_function), (None, None, tag_function, None)),
            ([], dict(function=string_function), (None, None, string_function, None)),
            # Boolean
            ([], dict(present=True), (None, None, None, True)),
            # With positional arguments rather than keywords
            (("a", None, None, None), {}, ("a", None, None, None)),
            ((None, "b", None, None), {}, (None, "b", None, None)),
            ((None, None, tag_function, None), {}, (None, None, tag_function, None)),
            ((None, None, None, True), {}, (None, None, None, True)),
        ],
    )
    def test_constructor(self, constructor_args, constructor_kwargs, result):
        rule = MatchRule(*constructor_args, **constructor_kwargs)
        assert result == self._tuple(rule)

    def test_empty_match_not_allowed(self):
        with pytest.raises(
            ValueError,
            match="Either string, pattern, function, present, or exclude_everything must be provided.",
        ):
            MatchRule()

    def test_full_match_not_allowed(self):
        with pytest.raises(
            ValueError,
            match="At most one of string, pattern, function, present, and exclude_everything must be provided.",
        ):
            MatchRule("a", "b", self.tag_function, True)

    @pytest.mark.parametrize(
        "rule_kwargs, match_against, result",
        [
            (dict(string="a"), "a", True),
            (dict(string="a"), "ab", False),
            (dict(pattern="a"), "a", True),
            (dict(pattern="a"), "ab", True),
            (dict(pattern="^a$"), "a", True),
            (dict(pattern="^a$"), "ab", False),
            (dict(present=True), "any random value", True),
            (dict(present=True), None, False),
            (dict(present=False), "any random value", False),
            (dict(present=False), None, True),
            (dict(function=lambda x: x.upper() == x), "UPPERCASE", True),
            (dict(function=lambda x: x.upper() == x), "lowercase", False),
            (dict(function=lambda x: x.lower() == x), "UPPERCASE", False),
            (dict(function=lambda x: x.lower() == x), "lowercase", True),
        ],
    )
    def test_matches_string(self, rule_kwargs, match_against, result):
        rule = MatchRule(**rule_kwargs)
        assert rule.matches_string(match_against) == result


class TestTagNameMatchRule(SoupTest):
    @pytest.mark.parametrize(
        "rule_kwargs, tag_kwargs, result",
        [
            (dict(string="a"), dict(name="a"), True),
            (dict(string="a"), dict(name="ab"), False),
            (dict(pattern="a"), dict(name="a"), True),
            (dict(pattern="a"), dict(name="ab"), True),
            (dict(pattern="^a$"), dict(name="a"), True),
            (dict(pattern="^a$"), dict(name="ab"), False),
            # This isn't very useful, but it will work.
            (dict(present=True), dict(name="any random value"), True),
            (dict(present=False), dict(name="any random value"), False),
            (
                dict(function=lambda t: t.name in t.attrs),
                dict(name="id", attrs=dict(id="a")),
                True,
            ),
            (
                dict(function=lambda t: t.name in t.attrs),
                dict(name="id", attrs={"class": "a"}),
                False,
            ),
        ],
    )
    def test_matches_tag(self, rule_kwargs, tag_kwargs, result):
        rule = TagNameMatchRule(**rule_kwargs)
        tag = Tag(**tag_kwargs)
        assert rule.matches_tag(tag) == result


# AttributeValueMatchRule and StringMatchRule have the same
# logic as MatchRule.


class TestSoupStrainer(SoupTest):

    def test_constructor_string_deprecated_text_argument(self):
        with warnings.catch_warnings(record=True) as w:
            strainer = SoupStrainer(text="text")
            assert strainer.text == "text"
            [w1, w2] = w
            msg = str(w1.message)
            assert w1.filename == __file__
            assert (
                msg
                == "As of version 4.11.0, the 'text' argument to the SoupStrainer constructor is deprecated. Use 'string' instead."
            )

            msg = str(w2.message)
            assert w2.filename == __file__
            assert (
                msg
                == "Access to deprecated property text. (Look at .string_rules instead) -- Deprecated since version 4.13.0."
            )

    def test_search_tag_deprecated(self):
        strainer = SoupStrainer(name="a")
        with warnings.catch_warnings(record=True) as w:
            assert False is strainer.search_tag("b", {})
            [w1] = w
            msg = str(w1.message)
            assert w1.filename == __file__
            assert (
                msg
                == "Call to deprecated method search_tag. (Replaced by allow_tag_creation) -- Deprecated since version 4.13.0."
            )

    def test_search_deprecated(self):
        strainer = SoupStrainer(name="a")
        soup = self.soup("<a></a><b></b>")
        with warnings.catch_warnings(record=True) as w:
            assert soup.a == strainer.search(soup.a)
            assert None is strainer.search(soup.b)
            [w1, w2] = w
            msg = str(w1.message)
            assert msg == str(w2.message)
            assert w1.filename == __file__
            assert (
                msg
                == "Call to deprecated method search. (Replaced by match) -- Deprecated since version 4.13.0."
            )

    # Dummy function used within tests.
    def _match_function(x):
        pass

    def test_constructor_default(self):
        # The default SoupStrainer matches all tags, and only tags.
        strainer = SoupStrainer()
        [name_rule] = strainer.name_rules
        assert True == name_rule.present
        assert 0 == len(strainer.attribute_rules)
        assert 0 == len(strainer.string_rules)

    def test_constructor(self):
        strainer = SoupStrainer(
            "tagname",
            {"attr1": "value"},
            string=self._match_function,
            attr2=["value1", False],
        )
        [name_rule] = strainer.name_rules
        assert name_rule == TagNameMatchRule(string="tagname")

        [attr1_rule] = strainer.attribute_rules.pop("attr1")
        assert attr1_rule == AttributeValueMatchRule(string="value")

        [attr2_rule1, attr2_rule2] = strainer.attribute_rules.pop("attr2")
        assert attr2_rule1 == AttributeValueMatchRule(string="value1")
        assert attr2_rule2 == AttributeValueMatchRule(present=False)

        assert not strainer.attribute_rules

        [string_rule] = strainer.string_rules
        assert string_rule == StringMatchRule(function=self._match_function)

    def test_scalar_attrs_becomes_class_restriction(self):
        # For the sake of convenience, passing a scalar value as
        # ``args`` results in a restriction on the 'class' attribute.
        strainer = SoupStrainer(attrs="mainbody")
        assert [] == strainer.name_rules
        assert [] == strainer.string_rules
        assert {"class": [AttributeValueMatchRule(string="mainbody")]} == (
            strainer.attribute_rules
        )

    def test_constructor_class_attribute(self):
        # The 'class' HTML attribute is also treated specially because
        # it's a Python reserved word. Passing in "class_" as a
        # keyword argument results in a restriction on the 'class'
        # attribute.
        strainer = SoupStrainer(class_="mainbody")
        assert [] == strainer.name_rules
        assert [] == strainer.string_rules
        assert {"class": [AttributeValueMatchRule(string="mainbody")]} == (
            strainer.attribute_rules
        )

        # But if you pass in "class_" as part of the ``attrs`` dict
        # it's not changed. (Otherwise there'd be no way to actually put
        # a restriction on an attribute called "class_".)
        strainer = SoupStrainer(attrs=dict(class_="mainbody"))
        assert [] == strainer.name_rules
        assert [] == strainer.string_rules
        assert {"class_": [AttributeValueMatchRule(string="mainbody")]} == (
            strainer.attribute_rules
        )

    def test_constructor_with_overlapping_attributes(self):
        # If you specify the same attribute in args and **kwargs, you end up
        # with two different AttributeValueMatchRule objects.

        # This happens whether you use the 'class' shortcut on attrs...
        strainer = SoupStrainer(attrs="class1", class_="class2")
        rule1, rule2 = strainer.attribute_rules["class"]
        assert rule1.string == "class1"
        assert rule2.string == "class2"

        # Or explicitly specify the same attribute twice.
        strainer = SoupStrainer(attrs={"id": "id1"}, id="id2")
        rule1, rule2 = strainer.attribute_rules["id"]
        assert rule1.string == "id1"
        assert rule2.string == "id2"

    @pytest.mark.parametrize(
        "obj, result",
        [
            ("a", MatchRule(string="a")),
            (b"a", MatchRule(string="a")),
            (True, MatchRule(present=True)),
            (False, MatchRule(present=False)),
            (re.compile("a"), MatchRule(pattern=re.compile("a"))),
            (_match_function, MatchRule(function=_match_function)),
            # Pass in a list and get back a list of rules.
            (["a", b"b"], [MatchRule(string="a"), MatchRule(string="b")]),
            (
                [re.compile("a"), _match_function],
                [
                    MatchRule(pattern=re.compile("a")),
                    MatchRule(function=_match_function),
                ],
            ),
            # Anything that doesn't fit is converted to a string.
            (100, MatchRule(string="100")),
        ],
    )
    def test__make_match_rules(self, obj, result):
        actual = list(SoupStrainer._make_match_rules(obj, MatchRule))
        # Helper to reduce the number of single-item lists in the
        # parameters.
        if len(actual) == 1:
            [actual] = actual
        assert result == actual

    @pytest.mark.parametrize(
        "cls, result",
        [
            (AttributeValueMatchRule, AttributeValueMatchRule(string="a")),
            (StringMatchRule, StringMatchRule(string="a")),
        ],
    )
    def test__make_match_rules_different_classes(self, cls, result):
        actual = cls(string="a")
        assert actual == result

    def test__make_match_rules_nested_list(self):
        # If you pass a nested list into _make_match_rules, it's
        # turned into a restriction that excludes everything, to avoid the
        # possibility of an infinite recursion.

        # Create a self-referential object.
        selfref = []
        selfref.append(selfref)

        with warnings.catch_warnings(record=True) as w:
            rules = SoupStrainer._make_match_rules(["a", selfref, "b"], MatchRule)
            assert list(rules) == [MatchRule(string="a"), MatchRule(exclude_everything=True), MatchRule(string="b")]

            [warning] = w
            # Don't check the filename because the stacklevel is
            # designed for normal use and we're testing the private
            # method directly.
            msg = str(warning.message)
            assert (
                msg
                == "Ignoring nested list [[...]] to avoid the possibility of infinite recursion."
            )

    def tag_matches(
        self,
        strainer: SoupStrainer,
        name: str,
        attrs: Optional[_RawAttributeValues] = None,
        string: Optional[str] = None,
        prefix: Optional[str] = None,
    ) -> bool:
        # Create a Tag with the given prefix, name and attributes,
        # then make sure that strainer.matches_tag and allow_tag_creation
        # both approve it.
        tag = Tag(prefix=prefix, name=name, attrs=attrs)
        if string:
            tag.string = string
        return strainer.matches_tag(tag) and strainer.allow_tag_creation(
            prefix, name, attrs
        )

    def test_matches_tag_with_only_string(self):
        # A SoupStrainer that only has StringMatchRules won't ever
        # match a Tag.
        strainer = SoupStrainer(string=["a string", re.compile("string")])
        tag = Tag(name="b", attrs=dict(id="1"))
        tag.string = "a string"
        assert not strainer.matches_tag(tag)

        # There has to be a TagNameMatchRule or an
        # AttributeValueMatchRule as well.
        strainer.name_rules.append(TagNameMatchRule(string="b"))
        assert strainer.matches_tag(tag)

        strainer.name_rules = []
        strainer.attribute_rules["id"] = [AttributeValueMatchRule("1")]
        assert strainer.matches_tag(tag)

    def test_matches_tag_with_prefix(self):
        # If a tag has an attached namespace prefix, the tag's name is
        # tested both with and without the prefix.
        kwargs = dict(name="a", prefix="ns")

        assert self.tag_matches(SoupStrainer(name="a"), **kwargs)
        assert self.tag_matches(SoupStrainer(name="ns:a"), **kwargs)
        assert not self.tag_matches(SoupStrainer(name="ns2:a"), **kwargs)

    def test_one_name_rule_must_match(self):
        # If there are TagNameMatchRule, at least one must match.
        kwargs = dict(name="b")

        assert self.tag_matches(SoupStrainer(name="b"), **kwargs)
        assert not self.tag_matches(SoupStrainer(name="c"), **kwargs)
        assert self.tag_matches(SoupStrainer(name=["c", "d", "d", "b"]), **kwargs)
        assert self.tag_matches(
            SoupStrainer(name=[re.compile("c-f"), re.compile("[ab]$")]), **kwargs
        )

    def test_one_attribute_rule_must_match_for_each_attribute(self):
        # If there is one or more AttributeValueMatchRule for a given
        # attribute, at least one must match that attribute's
        # value. This is true for *every* attribute -- just matching one
        # attribute isn't enough.
        kwargs = dict(name="b", attrs={"class": "main", "id": "1"})

        # 'class' and 'id' match
        assert self.tag_matches(
            SoupStrainer(
                class_=["other", "main"], id=["20", "a", re.compile("^[0-9]")]
            ),
            **kwargs,
        )

        # 'class' and 'id' are present and 'data' attribute is missing
        assert self.tag_matches(
            SoupStrainer(class_=True, id=True, data=False), **kwargs
        )

        # 'id' matches, 'class' does not.
        assert not self.tag_matches(SoupStrainer(class_=["other"], id=["2"]), **kwargs)

        # 'class' matches, 'id' does not
        assert not self.tag_matches(SoupStrainer(class_=["main"], id=["2"]), **kwargs)

        # 'class' and 'id' match but 'data' attribute is missing
        assert not self.tag_matches(
            SoupStrainer(class_=["main"], id=["1"], data=True), **kwargs
        )

    def test_match_against_multi_valued_attribute(self):
        # If an attribute has multiple values, only one of them
        # has to match the AttributeValueMatchRule.
        kwargs = dict(name="b", attrs={"class": ["main", "big"]})
        assert self.tag_matches(SoupStrainer(attrs="main"), **kwargs)
        assert self.tag_matches(SoupStrainer(attrs="big"), **kwargs)
        assert self.tag_matches(SoupStrainer(attrs=["main", "big"]), **kwargs)
        assert self.tag_matches(SoupStrainer(attrs=["big", "small"]), **kwargs)
        assert not self.tag_matches(SoupStrainer(attrs=["small", "smaller"]), **kwargs)

    def test_match_against_multi_valued_attribute_as_string(self):
        # If an attribute has multiple values, you can treat the entire
        # thing as one string during a match.
        kwargs = dict(name="b", attrs={"class": ["main", "big"]})
        assert self.tag_matches(SoupStrainer(attrs="main big"), **kwargs)

        # But you can't put them in any order; it's got to be the
        # order they are present in the Tag, which basically means the
        # order they were originally present in the document.
        assert not self.tag_matches(SoupStrainer(attrs=["big main"]), **kwargs)

    def test_one_string_rule_must_match(self):
        # If there's a TagNameMatchRule and/or an
        # AttributeValueMatchRule, then the StringMatchRule is _not_
        # ignored, and must match as well.
        tag = Tag(name="b", attrs=dict(id="1"))
        tag.string = "A string"

        assert SoupStrainer(name="b", string="A string").matches_tag(tag)
        assert not SoupStrainer(name="a", string="A string").matches_tag(tag)
        assert not SoupStrainer(name="a", string="Wrong string").matches_tag(tag)
        assert SoupStrainer(id="1", string="A string").matches_tag(tag)
        assert not SoupStrainer(id="2", string="A string").matches_tag(tag)
        assert not SoupStrainer(id="1", string="Wrong string").matches_tag(tag)

        assert SoupStrainer(name="b", id="1", string="A string").matches_tag(tag)

        # If there are multiple string rules, only one needs to match.
        assert SoupStrainer(
            name="b",
            id="1",
            string=["Wrong string", "Also wrong", re.compile("string")],
        ).matches_tag(tag)

    def test_allowing_tag_implies_allowing_its_contents(self):
        markup = "<a><b>one string<div>another string</div></b></a>"

        # Letting the <b> tag through implies parsing the <div> tag
        # and both strings, even though they wouldn't match the
        # SoupStrainer on their own.
        assert (
            "<b>one string<div>another string</div></b>"
            == self.soup(markup, parse_only=SoupStrainer(name="b")).decode()
        )

    @pytest.mark.parametrize(
        "soupstrainer",
        [
            SoupStrainer(name="b", string="one string"),
            SoupStrainer(name="div", string="another string"),
        ],
    )
    def test_parse_only_combining_tag_and_string(self, soupstrainer):
        # If you pass parse_only a SoupStrainer that contains both tag
        # restrictions and string restrictions, you get no results,
        # because the string restrictions can't be evaluated during
        # the parsing process, and the tag restrictions eliminate
        # any strings from consideration.
        #
        # We can detect this ahead of time, and warn about it,
        # thanks to SoupStrainer.excludes_everything
        markup = "<a><b>one string<div>another string</div></b></a>"

        with warnings.catch_warnings(record=True) as w:
            assert True, soupstrainer.excludes_everything
            assert "" == self.soup(markup, parse_only=soupstrainer).decode()
            [warning] = w
            str(warning.message)
            assert warning.filename == __file__
            assert str(warning.message).startswith(
                "The given value for parse_only will exclude everything:"
            )

        # The average SoupStrainer has excludes_everything=False
        assert not SoupStrainer().excludes_everything

    def test_documentation_examples(self):
        """Medium-weight real-world tests based on the Beautiful Soup
        documentation.
        """
        html_doc = """<html><head><title>The Dormouse's story</title></head>
<body>
<p class="title"><b>The Dormouse's story</b></p>

<p class="story">Once upon a time there were three little sisters; and their names were
<a href="http://example.com/elsie" class="sister" id="link1">Elsie</a>,
<a href="http://example.com/lacie" class="sister" id="link2">Lacie</a> and
<a href="http://example.com/tillie" class="sister" id="link3">Tillie</a>;
and they lived at the bottom of a well.</p>

<p class="story">...</p>
"""
        only_a_tags = SoupStrainer("a")
        only_tags_with_id_link2 = SoupStrainer(id="link2")

        def is_short_string(string):
            return string is not None and len(string) < 10

        only_short_strings = SoupStrainer(string=is_short_string)

        a_soup = self.soup(html_doc, parse_only=only_a_tags)
        assert (
            '<a class="sister" href="http://example.com/elsie" id="link1">Elsie</a><a class="sister" href="http://example.com/lacie" id="link2">Lacie</a><a class="sister" href="http://example.com/tillie" id="link3">Tillie</a>'
            == a_soup.decode()
        )

        id_soup = self.soup(html_doc, parse_only=only_tags_with_id_link2)
        assert (
            '<a class="sister" href="http://example.com/lacie" id="link2">Lacie</a>'
            == id_soup.decode()
        )
        string_soup = self.soup(html_doc, parse_only=only_short_strings)
        assert "\n\n\nElsie,\nLacie and\nTillie\n...\n" == string_soup.decode()
