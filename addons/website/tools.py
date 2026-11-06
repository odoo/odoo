# Part of Odoo. See LICENSE file for full copyright and licensing details.
import colorsys
import contextlib
import re
from collections import defaultdict
from urllib.parse import urlsplit

from lxml import etree, html
from markupsafe import Markup

from odoo.tools.misc import hash_sign
from odoo.tools.urls import urljoin

HAS_CLASS = 'contains(concat(" ", normalize-space(@class), " "), " %s ")'


def distance(s1="", s2="", limit=4):
    """
    Limited Levenshtein-ish distance (inspired from Apache text common)
    Note: this does not return quick results for simple cases (empty string, equal strings)
        those checks should be done outside loops that use this function.

    :param s1: first string
    :param s2: second string
    :param limit: maximum distance to take into account, return -1 if exceeded

    :return: number of character changes needed to transform s1 into s2 or -1 if this exceeds the limit
    """
    BIG = 100000  # never reached integer
    if len(s1) > len(s2):
        s1, s2 = s2, s1
    l1 = len(s1)
    l2 = len(s2)
    if l2 - l1 > limit:
        return -1
    boundary = min(l1, limit) + 1
    p = [i if i < boundary else BIG for i in range(0, l1 + 1)]
    d = [BIG for _ in range(0, l1 + 1)]
    for j in range(1, l2 + 1):
        j2 = s2[j - 1]
        d[0] = j
        range_min = max(1, j - limit)
        range_max = min(l1, j + limit)
        if range_min > 1:
            d[range_min - 1] = BIG
        for i in range(range_min, range_max + 1):
            if s1[i - 1] == j2:
                d[i] = p[i - 1]
            else:
                d[i] = 1 + min(d[i - 1], p[i], p[i - 1])
        p, d = d, p
    return p[l1] if p[l1] <= limit else -1


def similarity_score(s1, s2):
    """
    Computes a score that describes how much two strings are matching.

    :param s1: first string
    :param s2: second string

    :return: float score, the higher the more similar
        pairs returning non-positive scores should be considered non similar
    """
    dist = distance(s1, s2)
    if dist == -1:
        return -1
    set1 = set(s1)
    score = len(set1.intersection(s2)) / len(set1)
    score -= dist / len(s1)
    score -= len(set1.symmetric_difference(s2)) / (len(s1) + len(s2))
    return score


def text_from_html(html_fragment, collapse_whitespace=False):
    """
    Returns the plain non-tag text from an html

    :param html_fragment: document from which text must be extracted

    :return: text extracted from the html
    """
    # lxml requires one single root element
    tree = etree.fromstring('<p>%s</p>' % html_fragment, etree.XMLParser(recover=True))

    # Remove scripts or other technical elements that should not be converted
    # into text.
    xpath_filters = [
        '//script',
        '//style',
        '//svg',
        '//*[@class="css_non_editable_mode_hidden"]',
    ]
    for xpath_filter in xpath_filters:
        for element in tree.xpath(xpath_filter): element.getparent().remove(element)

    content = ' '.join(tree.itertext())
    if collapse_whitespace:
        content = re.sub(r'\s+', ' ', content).strip()
    return content


def _is_dark_rgb(red, green, blue, alpha, lightness_threshold):
    rgb = tuple(map(int, (red, green, blue)))
    _, lightness, _ = colorsys.rgb_to_hls(*(channel / 255 for channel in rgb))
    return (not alpha or float(alpha) > 0) and lightness < lightness_threshold


def adapt_dark_palette_content(root):
    """Keep text and carousel controls readable with dark palettes."""
    for element in root.iter():
        class_names = element.get('class', '').split()
        if 'carousel-dark' in class_names:
            class_names.remove('carousel-dark')
            element.set('class', ' '.join(class_names))
        # Blurred backgrounds inherit text colors from their closest preset.
        # Dark translucent backgrounds need `o_cc1` to keep text visible.
        if 'o_bg_blur_option' in class_names:
            color_match = re.search(
                r'background-color:\s*rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)'
                r'(?:\s*,\s*([\d.]+))?\s*\)',
                element.get('style', ''),
            )
            if color_match:
                red, green, blue, alpha = color_match.groups()
                if _is_dark_rgb(red, green, blue, alpha, 0.5):
                    color_preset_el = element
                    while color_preset_el is not None:
                        color_preset_classes = color_preset_el.get('class', '').split()
                        if 'o_cc' in color_preset_classes:
                            if 'o_cc5' in color_preset_classes:
                                color_preset_classes[color_preset_classes.index('o_cc5')] = 'o_cc1'
                                color_preset_el.set('class', ' '.join(color_preset_classes))
                            break
                        color_preset_el = color_preset_el.getparent()
        if 'o_cc1' not in class_names and 'o_cc5' not in class_names:
            continue
        for child_el in element:
            child_class_names = child_el.get('class', '').split()
            if 'o_we_bg_filter' not in child_class_names:
                continue
            # Current custom filters use gradients with a visible dark stop.
            has_dark_gradient = False
            for red, green, blue, alpha in re.findall(
                r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([\d.]+))?\s*\)',
                child_el.get('style', ''),
            ):
                # The 65% threshold keeps text light over all theme gradient
                # filters (e.g. the `s_cover` filter from `theme_monglia`,
                # which contains a color with 61% lightness).
                if _is_dark_rgb(red, green, blue, alpha, 0.65):
                    has_dark_gradient = True
                    break
            if any(name.startswith('bg-black-') for name in child_class_names) or has_dark_gradient:
                source_class, target_class = 'o_cc5', 'o_cc1'
            elif any(name.startswith('bg-white-') for name in child_class_names):
                source_class, target_class = 'o_cc1', 'o_cc5'
            else:
                continue
            if source_class in class_names:
                class_names[class_names.index(source_class)] = target_class
                element.set('class', ' '.join(class_names))
            break


def images_from_html(html_fragment, base_url):
    if not html_fragment or not html_fragment.strip():
        return []
    tree = html.fromstring(html_fragment)
    # urljoin only accepts URLs of base_url, but images may be hosted elsewhere
    seen = dict.fromkeys(
        src if urlsplit(src).netloc else urljoin(base_url, src)
        for img in tree.xpath('//img[@src]')
        if (src := img.get('src')) and not src.startswith('data:')
    )
    return list(seen)


def sign_website_forms(content, env_sudo, data_for=None):
    """ Sign the website forms of the rendered HTML content with what they can
    submit, to verify their submissions (see `_verify_website_form` on the
    `WebsiteForm` controller).

    :param str content: the rendered HTML content
    :param dict data_for: the values set in the forms by their `data-for`
        element (see `getParsedDataFor`)
    :rtype: markupsafe.Markup
    """
    # The content is already safe (rendered by QWeb), and lxml escapes it again
    # when serializing it, as done in the `ir.qweb.field.html` converter.
    body = html.fragment_fromstring(content, create_parent='body')
    for form in body.xpath('.//form[contains(@action, "/website/form/")]'):
        for signature_el in form.xpath('.//input[@name="website_form_signature"]'):
            signature_el.getparent().remove(signature_el)
        signature = hash_sign(env_sudo, 'website_form_signature', _get_website_form_structure(form, data_for or {}))
        form.insert(0, etree.Element('input', type='hidden', name='website_form_signature', value=signature))
    return Markup(etree.tostring(body, encoding='unicode', method='html')[6:-7])


def _get_website_form_structure(form, data_for):
    input_els_by_name = defaultdict(list)
    for input_el in form.xpath('.//input[@name!=""] | .//select[@name!=""] | .//textarea[@name!=""]'):
        input_els_by_name[input_el.get('name')].append(input_el)
    # form.js names the unnamed inputs when submitting (see `send`).
    unnamed_input_els = form.xpath(f'.//*[{HAS_CLASS % "s_website_form_input"}][not(@name) or @name=""]')
    for index, input_el in enumerate(unnamed_input_els, 1):
        input_els_by_name[f'unknown_field_{index}'].append(input_el)
    inputs = {
        name: _get_website_form_input_rules(name, input_els, data_for) for name, input_els in input_els_by_name.items()
    }
    # The inputs of the fields required by the model are always submitted.
    for field_el in form.xpath(f'.//*[@data-visibility-dependency][not({HAS_CLASS % "s_website_form_model_required"})]'):
        input_el = next(iter(field_el.xpath(f'.//*[{HAS_CLASS % "s_website_form_input"}]')), None)
        if input_el is not None and input_el.get('name') in inputs:
            # form.js compares a missing condition as an empty string (see `compareTo`).
            inputs[input_el.get('name')].setdefault('visibility', []).append(
                [field_el.get(f'data-visibility-{key}', '') for key in ('dependency', 'comparator', 'condition', 'between')]
            )
    # `StateFormField` disables the state select linked to the country, that
    # the browsers then do not check, when it has no state of the selected
    # country, or of any country of the form if none is selected.
    state_rules = inputs.get('state_id', {})
    if (
        state_rules.get('required') and 'country_id' in inputs
        and form.xpath('.//select[@name="state_id"][@data-link-state-to-country="true"]')
    ):
        country_ids = {_get_option_value(option) for option in form.xpath('.//select[@name="country_id"]//option')}
        state_country_ids = country_ids.intersection(form.xpath('.//select[@name="state_id"]//option/@data-country-id'))
        if state_country_ids:
            state_rules['data-country-id'] = sorted(state_country_ids)
        else:
            del state_rules['required']
    return {'model': form.get('data-force_action') or form.get('data-model_name'), 'inputs': inputs}


def _get_website_form_input_rules(name, input_els, data_for):
    """ Return the rules of the values of an input: its value if the visitor
    cannot change it, otherwise what form.js checks before submitting them (see
    `checkErrorFields`), named like the HTML attributes they come from.
    """
    input_attrs = input_els[0].attrib
    field_el = next(iter(input_els[0].xpath(f'ancestor::*[{HAS_CLASS % "s_website_form_field"}][1]')), None)
    field_attrs = {} if field_el is None else field_el.attrib
    field_classes = field_attrs.get('class', '').split()
    date_el = next(iter(input_els[0].xpath(f'ancestor::*[{HAS_CLASS % "s_website_form_date"} or {HAS_CLASS % "s_website_form_datetime"}]')), None)
    types = {input_el.get('type', input_el.tag) for input_el in input_els}
    rules = {}
    # form.js submits the dates of the model fields in the server format (see `send`).
    if date_el is not None and field_el is not None and 's_website_form_custom' not in field_classes:
        rules['server-format'] = True
    # The inputs of the fields with the "Hidden" visibility rule are submitted
    # too, while the values prefilled with the data of the visitor are unknown.
    is_hidden = types == {'hidden'} or 's_website_form_field_hidden' in field_classes
    if is_hidden and not input_attrs.get('data-fill-with'):
        rules['value'] = _get_website_form_value(name, input_els, data_for)
        # The date pickers display the default dates, given as timestamps (see `prepareDateFields`).
        if date_el is not None and not data_for.get(name):
            rules['date'] = 'datetime' if 's_website_form_datetime' in date_el.get('class').split() else 'date'
        return rules

    # The browsers do not check the disabled inputs, that scripts may enable.
    if any(input_el.get('required') is not None and input_el.get('disabled') is None for input_el in input_els):
        rules['required'] = True
    if 'checkbox' in types or 'multiple' in input_attrs:
        rules['multiple'] = True
    if types <= {'select', 'radio', 'checkbox'}:
        options = []
        for input_el in input_els:
            if input_el.tag == 'select':
                options += map(_get_option_value, input_el.iter('option'))
            else:
                options.append(input_el.get('value', 'on'))
        # The options of a select without any are loaded in the browser, and
        # the "Other" option lets the visitor type any value.
        if any(options) and not field_attrs.get('data-other-option-allowed'):
            rules['options'] = options
    elif input_attrs.get('type') in ('email', 'url', 'number', 'file'):
        rules['type'] = input_attrs['type']
    for attribute in ('minlength', 'maxlength', 'step', 'data-max-files-number', 'data-max-file-size'):
        with contextlib.suppress(TypeError, ValueError):  # the browsers ignore the invalid ones
            rules[attribute] = float(input_attrs.get(attribute))
    if input_attrs.get('accept'):
        rules['accept'] = input_attrs['accept']
    if field_attrs.get('data-requirement-comparator'):
        rules['requirement'] = [field_attrs.get(f'data-requirement-{key}') for key in ('comparator', 'condition', 'between')]
    return rules


def _get_website_form_value(name, input_els, data_for):
    # The `data-for` values replace the default values, except a set `email_to`
    # (see `prefillValues` in form.js).
    if data_for.get(name) and not (name == 'email_to' and input_els[0].get('value')):
        return str(data_for[name])
    values = []
    for input_el in input_els:
        if input_el.tag == 'select':
            options = list(input_el.iter('option'))
            selected_options = [option for option in options if option.get('selected') is not None]
            if not selected_options and input_el.get('multiple') is None:
                selected_options = options[:1]
            values += map(_get_option_value, selected_options)
        elif input_el.get('type') in ('checkbox', 'radio'):
            if input_el.get('checked') is not None:
                values.append(input_el.get('value', 'on'))
        else:
            values.append(input_el.text if input_el.tag == 'textarea' else input_el.get('value'))
    # Several values are submitted together, separated by commas (see `send` in form.js).
    return ','.join(filter(None, values))


def _get_option_value(option):
    # As in the browsers, an option without value has its text as value.
    return option.get('value', option.xpath('normalize-space()'))


def create_image_attachment(env, image_path, image_name):
    """
    Creates an image attachment.

    :param env: self.env
    :param image_path: the path to the image (e.g. '/web/image/website.s_banner_default_image')
    :param image_name: the name to give to the image (e.g. 's_banner_default_image.jpg')
    :return: the image attachment
    """
    Attachments = env['ir.attachment']
    img = Attachments.create({
        'public': True,
        'name': image_name,
        'type': 'url',
        'url': Attachments.get_base_url() + image_path,
    })
    return img


def add_seo_rels_to_links(html_template):
    """
    Add 'nofollow', 'noopener', 'noreferrer', and 'ugc' to anchor tags.
    This is useful to prevent users from harming SEO.

    :param html_template: the html code to edit
    :return: the updated html template
    """
    try:
        tree = html.fragment_fromstring(str(html_template), create_parent="template")
    except etree.ParserError:
        return html_template
    links = list(tree.iter('a'))
    if not links:
        return html_template
    for link in links:
        old_values = set(link.get("rel", "").split())
        old_values.update(('nofollow', 'noopener', 'noreferrer', 'ugc'))
        link.set("rel", " ".join(sorted(old_values)))
    result = html.tostring(tree, encoding="unicode")
    result = result[10:-11]
    return type(html_template)(result)
