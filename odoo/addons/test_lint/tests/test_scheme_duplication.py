import base64
import logging
import re
from collections import Counter

from odoo.tests import tagged

from . import lint_case

_logger = logging.getLogger(__name__)

SOURCE_MARK_RE = re.compile(r"/\*\s*(/[^*]+?)\s*\*/")

VAR_RE = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,([^()]*(?:\([^()]*\)[^()]*)*))?\)")

DARK_SELECTOR_RE = re.compile(r':root\[data-color-scheme="?dark"?\]')

INERT_IN_URI_RE = re.compile(r"(?:var|color-mix)(?:\(|%28)")

DARK_SCOPE_RE = re.compile(r'(?:^|(?<= )):root\[data-color-scheme="?dark"?\] +')

COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\([^()]*\)")

_KEYWORDS = {
    "white": "#ffffff",
    "black": "#000000",
    "#000": "#000000",
    "#fff": "#ffffff",
}

SINGLE_BUNDLE_GAP_FLOOR = {
    "account": 4,
    "account_edi_ubl_cii": 1,
    "automation": 0,
    "base_import": 1,
    "calendar": 2,
    "document": 11,
    "event": 1,
    "google_address_autocomplete": 1,
    "hr_gamification": 1,
    "hr_recruitment": 1,
    "hr_skills_slides": 0,
    "html_editor": 17,
    "im_livechat": 4,
    "mail": 52,
    "mrp": 2,
    "onboarding": 1,
    "point_of_sale": 2,
    "product": 1,
    "project": 5,
    "sale": 11,
    "spreadsheet": 0,
    "spreadsheet_dashboard": 2,
    "stock": 1,
    "survey": 1,
    "web": 91,
    "web_tour": 0,
    "website": 13,
    "website_sale": 1,
}


def parse(css):
    out, buf, stack, source = [], "", [], "?"
    index, end = 0, len(css)

    def flush():
        nonlocal buf
        declaration, buf = buf.strip(), ""
        if ":" in declaration and stack:
            prop, _, value = declaration.partition(":")
            out.append((source, " ".join(stack), prop.strip(), value.strip()))

    while index < end:
        char = css[index]
        if char == "/" and css[index + 1 : index + 2] == "*":
            close = css.find("*/", index + 2)
            close = end if close < 0 else close + 2
            mark = SOURCE_MARK_RE.fullmatch(css[index:close])
            if mark and not stack:
                source = mark.group(1)
            index = close
            continue
        if char in "\"'":
            close = index + 1
            while close < end and css[close] != char:
                close += 2 if css[close] == "\\" else 1
            buf += css[index : close + 1]
            index = close + 1
            continue
        if char == "{":
            stack.append(buf.strip())
            buf = ""
        elif char == "}":
            flush()
            if stack:
                stack.pop()
        elif char == ";":
            flush()
        else:
            buf += char
        index += 1
    return out


def split_selector(selector):
    parts, depth, current = [], 0, ""
    for char in selector:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if char == "," and not depth:
            parts.append(current)
            current = ""
        else:
            current += char
    parts.append(current)
    return [part.strip() for part in parts if part.strip()]


def is_root(selector):
    return ":root" in split_selector(selector)


def unreachable(selector):
    parts = split_selector(selector)
    return bool(parts) and all("[data-bs-theme=" in part for part in parts)


ROOT = "\x00:root"


def settle(declarations):
    keep, order = {}, []
    for source, selector, prop, value in declarations:
        key = (
            (ROOT, prop)
            if prop.startswith("--") and is_root(selector)
            else (selector, prop)
        )
        if key not in keep:
            order.append(key)
        keep[key] = (source, value)
    return [(keep[key][0], key[0], key[1], keep[key][1]) for key in order]


def resolve(value, scope, depth=0):
    if depth > 12:
        return value

    def substitute(match):
        name, fallback = match.group(1), match.group(2)
        if name in scope:
            return resolve(scope[name], scope, depth + 1)
        return (
            resolve(fallback.strip(), scope, depth + 1) if fallback else match.group(0)
        )

    substituted = VAR_RE.sub(substitute, value)
    return value if substituted == value else resolve(substituted, scope, depth + 1)


def pick_dark(value):
    while True:
        start = value.lower().find("light-dark(")
        if start < 0:
            return value
        depth, index = 0, start + len("light-dark(") - 1
        while index < len(value):
            if value[index] == "(":
                depth += 1
            elif value[index] == ")":
                depth -= 1
                if not depth:
                    break
            index += 1
        inner = value[start + len("light-dark(") : index]
        halves = split_selector(inner)
        if len(halves) != 2:
            return value
        value = value[:start] + pick_dark(halves[1]) + value[index + 1 :]


def is_mask(prop):
    return bool(re.fullmatch(r"(?:-webkit-)?mask(?:-image)?", prop.strip().lower()))


def flatten_opaque(value):
    return COLOR_RE.sub(
        lambda match: "#000000" if _is_opaque(match.group(0)) else match.group(0),
        value,
    )


def _is_opaque(literal):
    literal = norm(literal)
    if literal.startswith("#"):
        return len(literal) == 7
    parts = literal[len("rgb(") : -1].split(",") if literal.startswith("rgb(") else []
    return len(parts) == 3


def norm(value):
    value = re.sub(r"\s+", " ", (value or "").strip().lower())
    value = _KEYWORDS.get(value, value)
    if re.fullmatch(r"#[0-9a-f]{3}", value):
        value = "#" + "".join(char * 2 for char in value[1:])
    match = re.fullmatch(r"rgba?\(([^()]*)\)", value)
    if match:
        parts = [part for part in re.split(r"[,\s/]+", match.group(1)) if part]
        if all(re.fullmatch(r"[\d.]+%?", part) for part in parts):
            parts = [f"{float(part.rstrip('%')):g}" for part in parts]
            if len(parts) == 4 and parts[3] == "1":
                parts = parts[:3]
            value = "rgb(" + ",".join(parts) + ")"
    return value


def measure(light_css, dark_css):
    light = settle(parse(light_css))
    dark = settle(parse(dark_css))

    light_root = {p: v for _, s, p, v in light if s == ROOT}
    dark_root = {p: v for _, s, p, v in dark if s == ROOT}
    attr_root = dict(light_root)
    attr_root.update(
        {p: v for _, s, p, v in light if DARK_SELECTOR_RE.fullmatch(s.strip())}
    )

    served = {(s, p): v for _, s, p, v in light}
    origin = {(s, p): f for f, s, p, _ in light}
    scoped = {}
    for _, selector, prop, value in light:
        parts = split_selector(selector)
        stripped = [DARK_SCOPE_RE.sub("", part) for part in parts]
        if parts and all(a != b for a, b in zip(parts, stripped, strict=True)):
            scoped[(",".join(stripped), prop)] = value

    dark_scoped = set()
    for _, selector, prop, _value in dark:
        parts = split_selector(selector)
        stripped = [DARK_SCOPE_RE.sub("", part) for part in parts]
        if parts and all(a != b for a, b in zip(parts, stripped, strict=True)):
            dark_scoped.add((",".join(stripped), prop))

    gap = []
    answered = 0
    for _, selector, prop, value in dark:
        key = (selector, prop)
        if key in dark_scoped:
            answered += 1
            continue
        if key not in served or served[key] == value:
            continue
        if unreachable(selector):
            continue
        if selector == ROOT:
            single, wanted = (
                attr_root.get(prop, served[key]),
                dark_root.get(prop, value),
            )
        else:
            single, wanted = scoped.get(key, served[key]), value
        single = pick_dark(resolve(single, attr_root))
        wanted = pick_dark(resolve(wanted, dark_root))
        if is_mask(prop):
            single, wanted = flatten_opaque(single), flatten_opaque(wanted)
        if norm(single) == norm(wanted):
            answered += 1
        else:
            gap.append((origin[key], selector, prop))
    return gap, answered, len(light), len(dark)


@tagged("post_install", "-at_install")
class TestSchemeDuplication(lint_case.LintCase):
    def _measure(self, env):
        return measure(
            self._css(env, "web.assets_web"), self._css(env, "web.assets_web_dark")
        )

    @staticmethod
    def _css(env, bundle):
        assets = env["ir.qweb"]._get_asset_bundle(bundle, css=True, js=False)
        return base64.b64decode(assets.css().datas).decode("utf-8", "replace")

    def test_no_svg_data_uri_reads_a_custom_property(self):
        offenders = []
        with self.superuser_env() as env:
            for bundle in ("web.assets_web", "web.assets_web_dark"):
                for source, selector, prop, value in parse(self._css(env, bundle)):
                    if "svg+xml" not in value:
                        continue
                    inert = INERT_IN_URI_RE.search(value)
                    if inert:
                        offenders.append(
                            f"{bundle} {source} {selector} {prop}: {inert.group(0)}"
                        )

        self.assertFalse(
            offenders,
            f"{len(offenders)} SVG data URI(s) name a custom property, which "
            f"cannot resolve there -- the icon will not be drawn. Keep the "
            f"variable the URI reads a colour, and restate the pair under the "
            f"scheme scope if it has to answer both:\n  " + "\n  ".join(offenders),
        )

    def test_the_single_bundle_gap_does_not_grow(self):
        with self.superuser_env() as env:
            self._require_the_floors_can_be_exercised(env)
            gap, answered, light, dark = self._measure(env)

        self.assertGreater(
            min(light, dark),
            12000,
            f"assets_web compiled {light} declarations and assets_web_dark "
            f"{dark}. Something did not compile -- every floor below is being "
            f"measured against a partial bundle and will pass for the wrong "
            f"reason.",
        )
        _logger.info(
            "assets_web %s declarations, assets_web_dark %s: %s declarations would "
            "still be wrong under one stylesheet, %s the attribute already answers",
            light,
            dark,
            len(gap),
            answered,
        )
        core = lint_case.core_module_names()
        by_module = Counter(
            module
            for source, _, _ in gap
            if (module := source.strip("/").split("/")[0]) in core
        )
        _logger.info("worst modules: %s", by_module.most_common(8))
        by_file = Counter(source for source, _, _ in gap)
        _logger.info("worst files: %s", by_file.most_common(6))

        offenders = []
        for module, count in sorted(by_module.items()):
            floor = SINGLE_BUNDLE_GAP_FLOOR.get(module)
            if floor is None:
                offenders.append(f"{module}: {count}, in a module that had none")
            elif count > floor:
                offenders.append(f"{module}: {count}, floor is {floor}")
        under = sorted(
            f"{module} {by_module.get(module, 0)}/{floor}"
            for module, floor in SINGLE_BUNDLE_GAP_FLOOR.items()
            if module in by_module and by_module[module] < floor
        )
        if under:
            _logger.info("under the floor on this install: %s", ", ".join(under))
        unreachable = sorted(set(SINGLE_BUNDLE_GAP_FLOOR) - set(by_module))
        _logger.info(
            "%s of %s floors were exercised on this install; %s were not: %s",
            len(SINGLE_BUNDLE_GAP_FLOOR) - len(unreachable),
            len(SINGLE_BUNDLE_GAP_FLOOR),
            len(unreachable),
            ", ".join(unreachable),
        )
        self.assertIn(
            "web",
            by_module,
            "no `web` declarations were measured, so every floor below passed "
            "for the wrong reason -- the bundles did not carry what they should",
        )
        self.assertFalse(
            offenders,
            f"{len(offenders)} module(s) put more between this fork and a single "
            f"stylesheet than the committed floor. A declaration counted here is "
            f'one a light bundle under `data-color-scheme="dark"` resolves '
            f"differently from what the dark bundle serves:\n  "
            + "\n  ".join(offenders),
        )

    def _require_the_floors_can_be_exercised(self, env):
        installed = set(
            env["ir.module.module"].search([("state", "=", "installed")]).mapped("name")
        )
        missing = sorted(set(SINGLE_BUNDLE_GAP_FLOOR) - installed)
        if missing:
            self.skipTest(
                f"{len(missing)} of {len(SINGLE_BUNDLE_GAP_FLOOR)} floored "
                f"module(s) are not installed, so their floors would pass by "
                f"describing an absence. Run this on a database that installs "
                f"every floored module. Missing: {', '.join(missing)}"
            )

    def test_every_floor_names_a_module_that_exists(self):
        self.assertFalse(
            sorted(set(SINGLE_BUNDLE_GAP_FLOOR) - lint_case.core_module_names()),
            "these floors name a module that is not in this repository",
        )

    def test_the_measurement_survives_a_brace_in_a_string(self):
        css = (
            '/* /a/x.scss */.fa-bracket-curly::before{content:"{"}'
            "/* /b/y.scss */.after{color:red}"
        )
        self.assertEqual(
            parse(css),
            [
                ("/a/x.scss", ".fa-bracket-curly::before", "content", '"{"'),
                ("/b/y.scss", ".after", "color", "red"),
            ],
        )

    def test_only_the_dark_half_of_light_dark_is_measured(self):
        self.assertEqual(
            pick_dark(
                "linear-gradient(light-dark(#fff, #000), light-dark(#eee, #111))"
            ),
            "linear-gradient(#000, #111)",
        )
        self.assertEqual(pick_dark("light-dark(a, light-dark(b, c))"), "c")
        self.assertEqual(pick_dark("#abc"), "#abc")

    def test_an_opaque_colour_inside_a_mask_is_not_a_scheme_difference(self):
        light = "linear-gradient(130deg, #000 55%, rgba(0, 0, 0, 0.8) 75%, #000 95%)"
        dark = light.replace("#000 ", "#E2E8F0 ")
        self.assertNotEqual(norm(light), norm(dark))
        self.assertEqual(norm(flatten_opaque(light)), norm(flatten_opaque(dark)))

        self.assertNotEqual(
            norm(flatten_opaque("linear-gradient(rgba(0, 0, 0, 0.8), #000)")),
            norm(flatten_opaque("linear-gradient(rgba(0, 0, 0, 0.4), #000)")),
        )
        self.assertEqual(flatten_opaque("var(--o-text)"), "var(--o-text)")

        self.assertTrue(is_mask("mask-image"))
        self.assertTrue(is_mask("-webkit-mask"))
        self.assertFalse(is_mask("mask-size"))
        self.assertFalse(is_mask("background-image"))

    def test_a_comma_inside_has_is_not_a_selector_boundary(self):
        selector = ':root[data-color-scheme="dark"] .a:has(.b, .c) .d, .e'
        self.assertEqual(
            split_selector(selector),
            [':root[data-color-scheme="dark"] .a:has(.b, .c) .d', ".e"],
        )

    def test_a_rule_scoped_to_the_attribute_answers_the_scheme(self):
        self.assertEqual(
            DARK_SCOPE_RE.sub("", ':root[data-color-scheme="dark"] .bg-primary-light'),
            ".bg-primary-light",
        )
        self.assertEqual(
            DARK_SCOPE_RE.sub("", ".bg-primary-light"), ".bg-primary-light"
        )
        self.assertEqual(
            DARK_SCOPE_RE.sub("", ':root[data-color-scheme="dark"]'),
            ':root[data-color-scheme="dark"]',
        )

    def test_bootstraps_own_colour_mode_is_not_counted(self):
        self.assertTrue(unreachable('[data-bs-theme="dark"]'))
        self.assertTrue(unreachable("[data-bs-theme=dark] .card"))
        self.assertFalse(unreachable(".navbar-dark,.navbar[data-bs-theme=dark]"))
        self.assertFalse(unreachable(":root"))

    def test_the_attribute_reading_is_what_is_compared(self):
        light = settle(
            parse(
                "/* /a/x.scss */:root{--o-bg:#fff;--other:1px}"
                '/* /a/x.scss */:root[data-color-scheme="dark"]{--o-bg:#000}'
            )
        )
        self.assertEqual(
            {p: v for _, s, p, v in light if s == ROOT},
            {"--o-bg": "#fff", "--other": "1px"},
        )
        self.assertTrue(DARK_SELECTOR_RE.fullmatch(':root[data-color-scheme="dark"]'))
        self.assertEqual(norm(resolve("var(--o-bg)", {"--o-bg": "black"})), "#000000")
