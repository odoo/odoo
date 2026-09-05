# Part of Odoo. See LICENSE file for full copyright and licensing details.
import colorsys
import re

from lxml import etree, html

from odoo.tools.misc import hmac
from odoo.tools.urls import urljoin


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


def adapt_dark_palette_content(root):
    """Keep text and carousel controls readable with dark palettes."""
    for element in root.iter():
        class_names = element.get('class', '').split()
        if 'carousel-dark' in class_names:
            class_names.remove('carousel-dark')
            element.set('class', ' '.join(class_names))
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
                rgb = tuple(map(int, (red, green, blue)))
                _, lightness, _ = colorsys.rgb_to_hls(*(channel / 255 for channel in rgb))
                if (not alpha or float(alpha) > 0) and lightness < 0.5:
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
    seen = dict.fromkeys(
        urljoin(base_url, src)
        for img in tree.xpath('//img[@src]')
        if (src := img.get('src')) and not src.startswith('data:')
    )
    return list(seen)


def add_form_signature(html_fragment, env_sudo):
    for form in html_fragment.iter('form'):
        if '/website/form/' not in form.attrib.get('action', ''):
            continue

        existing_hash_node = form.find('.//input[@type="hidden"][@name="website_form_signature"]')
        if existing_hash_node is not None:
            existing_hash_node.getparent().remove(existing_hash_node)
        input_nodes = form.xpath('.//input[contains(@name, "email_")]')
        form_values = {input_node.attrib['name']: input_node for input_node in input_nodes}
        # if this form does not send an email, ignore. But at this stage,
        # the value of email_to can still be None in case of default value
        if 'email_to' not in form_values:
            continue

        email_to_value = form_values['email_to'].attrib.get('value')
        if not email_to_value:
            email_to_value = env_sudo.company.email or ''

        has_cc = {'email_cc', 'email_bcc'} & form_values.keys()
        value = email_to_value + (':email_cc' if has_cc else '')
        hash_value = hmac(env_sudo, 'website_form_signature', value)
        if has_cc:
            hash_value += ':email_cc'
        hash_node = etree.Element('input', attrib={'type': "hidden", 'value': hash_value, 'class': "form-control s_website_form_input s_website_form_custom", 'name': "website_form_signature"})
        form_values['email_to'].addnext(hash_node)


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
