from odoo.tests.common import BaseCase
from odoo.tools.urls import parse_query, parse_query_list, parse_url, urlencode, urljoin


class TestUrlsTool(BaseCase):
    def test_urljoin(self):
        self.assertEqual(
            urljoin('https://api.example.com/v1/?bar=fiz', '/users/42?bar=bob'),
            'https://api.example.com/v1/users/42?bar=bob',
        )
        self.assertEqual(
            urljoin('https://api.example.com/data/', '/?lang=fr'),
            'https://api.example.com/data/?lang=fr',
        )

        with self.assertRaises(ValueError):
            urljoin('https://example.com/foo', 'http://8.8.8.8/foo')

        with self.assertRaises(ValueError):
            urljoin('https://example.com/foo', '/foo/../bar')

    def test_parse_url(self):
        self.assertEqual(tuple(parse_url(None)), (None,) * 7)
        self.assertEqual(tuple(parse_url("")), (None,) * 7)
        self.assertEqual(parse_url("").url, "")

        self.assertEqual(parse_url("/?foo=bar").decode_query(), {"foo": ["bar"]})
        self.assertEqual(parse_url("/?foo=bar&foo=baz").decode_query(), {"foo": ["bar", "baz"]})

        self.assertEqual(
            parse_url('https://api.example.com/data/').join('/?lang=fr').url,
            'https://api.example.com/data/?lang=fr',
        )

    def test_urlencode(self):
        self.assertEqual(urlencode(parse_query("foo=bar&foo=baz")), "foo=bar&foo=baz")
        self.assertEqual(urlencode(parse_query_list("foo=bar&foo=baz")), "foo=bar&foo=baz")

        self.assertEqual(urlencode({"foo": "bar"}), "foo=bar")
        self.assertEqual(urlencode({"foo": ["bar"]}), "foo=bar")
        self.assertEqual(urlencode({"foo": ["bar", "baz"]}), "foo=bar&foo=baz")

        # None values are removed
        self.assertEqual(urlencode({"foo": "bar", "baz": None}), "foo=bar")
        self.assertEqual(urlencode({"foo": ["bar", None]}), "foo=bar")  # type: ignore # accepted, but would complexify the type definition

        # automatic string conversion
        self.assertEqual(urlencode({"foo": 1}), "foo=1")  # type: ignore # While it's not in the type definition, we still supports it

        # quoting
        self.assertEqual(urlencode({"foo": "="}), "foo=%3D")
        self.assertEqual(urlencode({"=": "bar"}), "%3D=bar")
        self.assertEqual(urlencode({"foo": "/"}, safe="/"), "foo=/")
        self.assertEqual(urlencode({"foo": "bar"}, quote_via=lambda x, *a: x[0]), "f=b")

        # iterators
        self.assertEqual(urlencode(("x", str(i)) for i in range(2)), "x=0&x=1")
