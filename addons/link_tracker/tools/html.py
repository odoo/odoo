# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from typing import Iterable

import lxml

MAX_LABEL_LENGTH = 40  # arbitrary


def find_links_with_urls_and_labels(root_node, base_url, skip_regex=None, skip_prefix=None, skip_list=None):
    """Return lxml link nodes and respective matching urls (made absolute) and labels found in `root_node`.

    :param lxml.etree._Element root_node: The root node to process
    :param str base_url: base url to prefix relative hrefs
    :param str skip_regex: URL pattern to skip
    :param str skip_prefix: str prefix to skip
    :param Iterable[str] skip_list: URLS to skip

    :rtype: (list[lxml.etree._Element], list[dict])
    """
    link_nodes, urls_and_labels = [], []

    for link_node in root_node.iter(tag="a"):
        original_url = link_node.get("href")
        if not original_url:
            continue
        absolute_url = base_url + original_url if original_url.startswith(('/', '?', '#')) else original_url
        if (
            (skip_regex and re.search(skip_regex, absolute_url))
            or (skip_prefix and absolute_url.startswith(skip_prefix))
            or (skip_list and any(s in absolute_url for s in skip_list))
        ):
            continue

        if link_node.text and (stripped_text := link_node.text.strip()):
            label = stripped_text[:MAX_LABEL_LENGTH]
        else:
            children = link_node.getchildren()
            label = _get_label_from_elements(children)[:MAX_LABEL_LENGTH]

        link_nodes.append(link_node)
        urls_and_labels.append({'url': absolute_url, 'label': label})

    return link_nodes, urls_and_labels


def _get_label_from_elements(elements: Iterable[lxml.etree._Element], image_prefix: str = "[media] ") -> str:
    """Return the first label that can be extracted from a collection of elements"""
    for element in elements:
        if element.tag == "img":
            if img_alt := element.get("alt"):
                return f"{image_prefix}{img_alt}"
            if img_src := element.get("src"):
                img_src_tail = img_src.split("/")[-1]
                return f"{image_prefix}{img_src_tail}"
            return ""
        if isinstance(element, lxml.html.HtmlComment):  # A known "hack"
            continue
        if element.tag == "p" and element.get("class") == "o_outlook_hack":
            children = element.getchildren()
            if label := _get_label_from_elements(children):
                return label
    return ""
