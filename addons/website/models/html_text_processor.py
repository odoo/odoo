import logging
import re
import uuid

from lxml import etree, html

from odoo import api, models
from odoo.tools import xml_translate

_logger = logging.getLogger(__name__)


class WebsiteHTMLTextProcessor(models.AbstractModel):
    """
    Abstract model for HTML text processing functionality. It can be inherited by
    website configurator, ai_website, and other modules that need
    HTML text processing capabilities.
    """
    _name = 'website.html.text.processor'
    _description = 'HTML Text Processor Abstract Model'

    @api.model
    def _with_processing_context(self, IrQweb, cta_data, text_generation_target_lang, text_must_be_translated_for_openai=False):
        """
        Initialize HTML processing context similar to website.with_context() pattern
        :param IrQweb: QWeb rendering environment
        :param cta_data: Call-to-action data for rendering
        :param text_generation_target_lang: Target language code
        :param text_must_be_translated_for_openai: Whether translation is required
        :return: WebsiteHTMLTextProcessor instance with processing context
        """
        return self.with_context(
            html_processing=True,
            html_IrQweb=IrQweb,
            html_cta_data=cta_data,
            html_text_generation_target_lang=text_generation_target_lang,
            html_text_must_be_translated_for_openai=text_must_be_translated_for_openai,
            html_snippets_cache={},
            html_translated_content={},
            html_hashes_to_tags_and_attributes={},
            html_string_to_wrapping_tags={},
        )

    def _get_processing_cache(self, cache_key):
        """Get cached data from context, similar to website._get_cached() pattern
        :param cache_key: Key to get cached data from context
        :return: Cached data from context
        :rtype: dict
        """
        return dict(self.env.context.get(cache_key, {}))

    def _update_processing_cache(self, cache_key, updates):
        """Update cached data in context, returning new context
        :param cache_key: Key to update cached data in context
        :param updates: Updates to add to cached data
        :return: WebsiteHTMLTextProcessor instance with updated context
        """
        current_cache = self._get_processing_cache(cache_key)
        current_cache.update(updates)
        return self.with_context(**{cache_key: current_cache})

    @api.model
    def _get_snippet_content(self, snippet_key):
        """
        Get the content of a list of snippets as a list of placeholders and their translations
        :param snippet_key: Snippet key
        :return: (updated_processor (self), generated_content, translated_content)
        :rtype: tuple
        """
        generated_content = {}
        updated_processor = self
        # Generate content for all snippets to collect placeholders
        updated_processor, _dummy, placeholders = updated_processor._render_snippet(snippet_key)
        for placeholder in placeholders:
            # Update the cached generated content instead of local dict
            generated_content[placeholder] = ''
        translated_content = updated_processor._get_processing_cache('html_translated_content')
        return (updated_processor, generated_content, translated_content)

    @api.model
    def _get_rendered_snippets_content(self, snippets):
        """
        Process rendered snippets
        :param snippets: Dict of snippet_id keys mapping to the snippet HTML
        string and the English snippet HTML string
        :type snippets: dict
        :return: (updated_processor, generated_content, translated_content)
        :rtype: tuple
        """
        generated_content = {}
        updated_processor = self
        snippets_cache = self._get_processing_cache('html_snippets_cache')
        for key, snippet in snippets.items():
            data = snippets_cache.get(key)
            if data:
                placeholders = data[1]
                for placeholder in placeholders:
                    generated_content[placeholder] = ''
            else:
                snippet_html = snippet['section']
                snippet_html_en = snippet['translated_section']
                updated_processor, placeholders = updated_processor._process_snippet(snippet_html, snippet_html_en)
                render_data = (snippet_html, placeholders)
                # Update cache in context
                updated_processor = updated_processor._update_processing_cache('html_snippets_cache', {key: render_data})
                for placeholder in placeholders:
                    generated_content[placeholder] = ''
        translated_content = updated_processor._get_processing_cache('html_translated_content')
        return updated_processor, generated_content, translated_content

    def _process_snippet(self, snippet, snippet_en):
        """
        Process a snippet and its translation
        :param snippet: Snippet HTML string
        :param snippet_en: English snippet HTML string
        :type snippet_en: str
        :return: (updated_processor, placeholders)
        :rtype: tuple
        """
        text_generation_target_lang = self.env.context['html_text_generation_target_lang']
        text_must_be_translated_for_openai = self.env.context['html_text_must_be_translated_for_openai']
        terms = []
        xml_translate(terms.append, snippet)
        placeholders = []
        updated_processor = self
        for term in terms:
            updated_processor, placeholder = updated_processor._compute_placeholder(term)
            placeholders.append(placeholder)
        if text_must_be_translated_for_openai:
            # Check if terms are translated.
            translation_dictionary = self.env['website.page']._fields['arch_db'].get_translation_dictionary(
                snippet_en,
                {text_generation_target_lang: snippet},
            )
            # Remove all numeric keys.
            translation_dictionary = {
                k: v
                for k, v in translation_dictionary.items()
                if not xml_translate.get_text_content(k).strip().isnumeric()
            }
            # Update translated content in context
            translated_updates = {}
            for from_lang_term, to_lang_terms in translation_dictionary.items():
                translated_updates[from_lang_term] = to_lang_terms[text_generation_target_lang]

            if translated_updates:
                updated_processor = updated_processor._update_processing_cache('html_translated_content', translated_updates)
        return updated_processor, placeholders

    def _render_snippet(self, snippet_key):
        """
        Handle the rendering of a snippet and its translation
        :param snippet_key: Snippet key
        :return: (updated_processor, render, placeholders)
        :rtype: tuple
        """
        # Get processing state from context
        snippets_cache = self._get_processing_cache('html_snippets_cache')
        IrQweb = self.env.context['html_IrQweb']
        cta_data = self.env.context['html_cta_data']

        # Using this avoids rendering the same snippet multiple times
        data = snippets_cache.get(snippet_key)
        if data:
            return self, data[0], data[1]

        render = IrQweb._render(snippet_key, cta_data)
        render_en = IrQweb._render(snippet_key, cta_data, lang="en_US")
        updated_processor = self
        updated_processor, placeholders = updated_processor._process_snippet(render, render_en)
        data = (render, placeholders)
        # Update cache in context
        updated_processor = updated_processor._update_processing_cache('html_snippets_cache', {snippet_key: data})

        return updated_processor, render, placeholders

    @api.model
    def _calculate_translation_ratio(self, generated_content, translated_content):
        """
        Calculate the translation ratio between generated and translated content.
        :param generated_content: Generated content
        :param translated_content: Translated content
        :return: Translation ratio
        :rtype: float
        """
        text_must_be_translated_for_openai = self.env.context.get('html_text_must_be_translated_for_openai', False)
        if text_must_be_translated_for_openai:
            nb_terms_translated = len([k for k, v in translated_content.items() if k != v])
            nb_terms_total = len(translated_content)
        else:
            nb_terms_translated = len(generated_content)
            nb_terms_total = len(generated_content)

        translated_ratio = nb_terms_translated / nb_terms_total if nb_terms_total > 0 else 0
        _logger.debug("Ratio of translated content: %s%% (%s/%s)", translated_ratio * 100, nb_terms_translated, nb_terms_total)
        return translated_ratio

    @api.model
    def _update_snippet_content(self, generated_content, snippet_key, snippet_html=''):
        """
        Update the content of a snippet with the generated content
        :param generated_content: Generated content to update
        :type generated_content: dict
        :param snippet_key: Snippet key
        :type snippet_key: str
        :param snippet_html: Snippet HTML string
        :type snippet_html: str
        :return: Updated HTML element with snippet data
        :rtype: lxml.html.HtmlElement
        """
        if not snippet_html:
            updated_processor, render, _dummy = self._render_snippet(snippet_key)
        else:
            updated_processor = self
            render = snippet_html
        render = xml_translate(lambda html_string: updated_processor._format_replacement(html_string, generated_content), render)
        el = html.fromstring(render)
        return el

    def _compute_placeholder(self, html_string):
        """
        Transforms an HTML string by converting specific HTML tags into a custom
        pseudo-markdown format using context-stored state.
        :param html_string: The input HTML string to be transformed.
        :type html_string: str
        :return: (updated_processor, transformed_string) - The updated processor instance
                and the transformed string with HTML tags replaced by pseudo-markdown.
        :rtype: tuple
        """
        if not html_string or not html_string.strip():
            return self, html_string

        tree = etree.fromstring(f'<div>{html_string}</div>')

        # Identifying one or more wrapping tags that enclose the entire HTML
        # content e.g., <strong><em>text ...</em></strong>. Store them to
        # reapply them after processing with AI.
        wrapping_html = []
        for element in tree.iter():
            wrapping_html.append({"tag": element.tag, "attr": element.attrib})
            if len(element) != 1 \
                    or (element.text and element.text.strip()) \
                    or (element[-1].tail and element[-1].tail.strip()):
                break
        # Remove the wrapping element used for parsing into a tree
        wrapping_html = wrapping_html[1:]

        # Loop through all nodes, ignoring wrapping ones, to mark them with
        # a pseudo-markdown identifier if they are leaf nodes.
        nb_tags_to_skip = len(wrapping_html) + 1
        hash_updates = {}

        for cursor, element in enumerate(tree.iter()):
            if cursor < nb_tags_to_skip or len(element) > 0:
                continue

            # Generate a unique hash based on the element's text, tag
            # and attributes.
            attrib_string = ','.join(f'{key}={value}' for key, value in sorted(element.attrib.items()))
            combined_string = f'{element.text or ""}-{element.tag}-{attrib_string}'
            unique_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, combined_string)
            hash_value = unique_uuid.hex[:12]

            hash_updates[hash_value] = {"tag": element.tag, "attr": element.attrib}
            element.text = f'#[{element.text or "0"}]({hash_value})'

        # Start with current processor
        updated_processor = self

        # Update context with new hashes
        if hash_updates:
            updated_processor = updated_processor._update_processing_cache('html_hashes_to_tags_and_attributes', hash_updates)

        res = tree.xpath('string()')

        # If there is at least one wrapping tag, save the way it needs to
        # be re-applied.
        if wrapping_html:
            tags = [
                (
                    f'<{tag}{" " if attrs else ""}{attrs}>',
                    f'</{tag}>',
                )
                for el in wrapping_html
                for tag, attrs in [(el["tag"], " ".join([f'{k}="{v}"' for k, v in el["attr"].items()]))]
            ]
            opening_tags, closing_tags = zip(*tags)
            wrapping_pattern = f'{"".join(opening_tags)}$0{"".join(closing_tags[::-1])}'

            # Update context with wrapping tags
            updated_processor = updated_processor._update_processing_cache('html_string_to_wrapping_tags', {html_string: wrapping_pattern})

        # Note that `get_text_content` here is still needed despite the use
        # of `string()` in the XPath expression above. Indeed, it allows to
        # strip newlines and double-spaces, which would confuse IAP (without
        # this, it does not perform any replacement for some reason).
        result = xml_translate.get_text_content(res.strip())
        return updated_processor, result

    def _format_replacement(self, html_string, generated_content):
        """
        Reapplies original HTML formatting by replacing pseudo-markdown with
        corresponding HTML tags using context-stored state.
        :param html_string: The source HTML whose replacement has to
            receive original formatting
        :type html_string: str
        :param generated_content: Dictionary mapping placeholders to generated content
        :type generated_content: dict
        :return: The text with HTML tags re-applied.
        :rtype: str
        """
        replacement = generated_content.get(self._compute_placeholder(html_string)[1])
        if not replacement:
            return html_string

        # Get state from context
        hashes_to_tags_and_attributes = self._get_processing_cache('html_hashes_to_tags_and_attributes')
        html_string_to_wrapping_tags = self._get_processing_cache('html_string_to_wrapping_tags')

        # Replace #[string](hash) with <tag>...</tag> based on stored tag
        # and attribute information
        def _replace_tag(match):
            content = match.group(1)  # The string inside the square brackets
            hash_value = match.group(2)  # The hash value inside the parentheses
            if hash_value not in hashes_to_tags_and_attributes:
                return content

            tag = hashes_to_tags_and_attributes[hash_value]['tag']
            attr = hashes_to_tags_and_attributes[hash_value]['attr']
            attr_string = (" " + " ".join([f'{key}="{value}"' for key, value in attr.items()])) if attr else ''

            # Handle self-closing tag if content is "0"
            if content == "0":
                return f'<{tag}{attr_string}/>'

            return f'<{tag}{attr_string}>{content}</{tag}>'

        # Use regular expression to find instances of #[string](hash) and
        # replace them
        tag_pattern = r'#\[([^\]]+)\]\(([^)]+)\)'
        replacement = re.sub(tag_pattern, _replace_tag, replacement)

        # Handle possible wrapping tags identified
        if html_string in html_string_to_wrapping_tags:
            replacement = html_string_to_wrapping_tags[html_string].replace('$0', replacement)

        return replacement
