# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from difflib import SequenceMatcher, unified_diff
from bs4 import BeautifulSoup


# ------------------------------------------------------------
# Patch and comparison functions
# ------------------------------------------------------------


OPERATION_SEPARATOR = "\n"
LINE_SEPARATOR = "<"

PATCH_OPERATION_LINE_AT = "@"
PATCH_OPERATION_CONTENT = ":"

PATCH_OPERATION_ADD = "+"
PATCH_OPERATION_REMOVE = "-"
PATCH_OPERATION_REPLACE = "R"

PATCH_OPERATIONS = dict(
    insert=PATCH_OPERATION_ADD,
    delete=PATCH_OPERATION_REMOVE,
    replace=PATCH_OPERATION_REPLACE,
)

HTML_ATTRIBUTES_TO_REMOVE = ["data-last-history-steps"]
HTML_TAG_ISOLATION_REGEX = r"^([^>]*>)(.*)$"
ADDITION_COMPARISON_REGEX = r"\1<added>\2</added>"
ADDITION_1ST_REPLACE_COMPARISON_REGEX = r"added>\2</added>"
DELETION_COMPARISON_REGEX = r"\1<removed>\2</removed>"
EMPTY_OPERATION_TAG = r"<(added|removed)><\/(added|removed)>"
SAME_TAG_REPLACE_FIXER = r"<\/added><(?:[^\/>]|(?:><))+><removed>"
UNNECESSARY_REPLACE_FIXER = (
    r"<added>([^<](?!<\/added>)*)<\/added>"
    r"<removed>([^<](?!<\/removed>)*)<\/removed>"
)


def apply_patch(initial_content, patch):
    """Apply a patch (multiple operations) on a content.
    Each operation is a string with the following format:
    <operation_type>@<start_index>[,<end_index>][:<patch_text>*]
    patch format example:
        +@4:<p>ab</p><p>cd</p>
        +@4,15:<p>ef</p><p>gh</p>
        -@32
        -@125,129
        R@523:<b>sdf</b>

    :param string initial_content: the initial content to patch
    :param string patch: the patch to apply

    :return: string: the patched content
    """
    if not patch:
        return initial_content

    # Replace break line in initial content to ensure they don't interfere with
    # operations
    initial_content = initial_content.replace("\n", "")
    initial_content = _remove_html_attribute(
        initial_content, HTML_ATTRIBUTES_TO_REMOVE
    )

    content = initial_content.split(LINE_SEPARATOR)
    patch_operations = patch.split(OPERATION_SEPARATOR)
    # Apply operations in reverse order to preserve the indexes integrity.
    patch_operations.reverse()

    for operation in patch_operations:
        metadata, *patch_content_line = operation.split(LINE_SEPARATOR)

        metadata_split = metadata.split(PATCH_OPERATION_LINE_AT)
        operation_type = metadata_split[0]
        lines_index_range = metadata_split[1] if len(metadata_split) > 1 else ""
        # We need to remove PATCH_OPERATION_CONTENT char from lines_index_range.
        lines_index_range = lines_index_range.split(PATCH_OPERATION_CONTENT)[0]
        indexes = lines_index_range.split(",")
        start_index = int(indexes[0])
        end_index = int(indexes[1]) if len(indexes) > 1 else start_index

        # We need to insert lines from last to the first
        # to preserve the indexes integrity.
        patch_content_line.reverse()

        if end_index > start_index:
            for index in range(end_index, start_index, -1):
                if operation_type in [
                    PATCH_OPERATION_REMOVE,
                    PATCH_OPERATION_REPLACE,
                ]:
                    del content[index]

        if operation_type in [PATCH_OPERATION_ADD, PATCH_OPERATION_REPLACE]:
            for line in patch_content_line:
                content.insert(start_index + 1, line)
        if operation_type in [PATCH_OPERATION_REMOVE, PATCH_OPERATION_REPLACE]:
            del content[start_index]

    return LINE_SEPARATOR.join(content)


def generate_comparison(new_content, old_content):
    """Compare a content to an older content
    and generate a comparison html between both content.

    :param string new_content: the current content
    :param string old_content: the old content

    :return: string: the comparison content
    """
    new_content = _remove_html_attribute(new_content, HTML_ATTRIBUTES_TO_REMOVE)
    old_content = _remove_html_attribute(old_content, HTML_ATTRIBUTES_TO_REMOVE)

    if new_content == old_content:
        return new_content

    patch = generate_patch(new_content, old_content)
    comparison = new_content.split(LINE_SEPARATOR)
    patch_operations = patch.split(OPERATION_SEPARATOR)
    # We need to apply operation from last to the first
    # to preserve the indexes integrity.
    patch_operations.reverse()

    for operation in patch_operations:
        metadata, *patch_content_line = operation.split(LINE_SEPARATOR)

        metadata_split = metadata.split(PATCH_OPERATION_LINE_AT)
        operation_type = metadata_split[0]
        lines_index_range = metadata_split[1] if len(metadata_split) > 1 else ""
        lines_index_range = lines_index_range.split(PATCH_OPERATION_CONTENT)[0]
        indexes = lines_index_range.split(",")
        start_index = int(indexes[0])
        end_index = int(indexes[1]) if len(indexes) > 1 else start_index

        # If the operation is a replace, we need to flag the changes that
        # will generate ghost opening tags if we don't ignore
        # them.
        # this can append when:
        # * A change concerning only html parameters.
        #   <p class="x">a</p> => <p class="y">a</p>
        # * An addition in a previously empty element opening tag
        #   <p></p> => <p>a</p>
        if operation_type == PATCH_OPERATION_REPLACE:
            for i, line in enumerate(patch_content_line):
                current_index = start_index + i
                if current_index > end_index:
                    break

                current_line = comparison[current_index]
                current_line_tag = current_line.split(">")[0]
                line_tag = line.split(">")[0]
                if current_line[-1] == ">" and (
                    current_line_tag == line_tag
                    or current_line_tag.split(" ")[0] == line_tag.split(" ")[0]
                ):
                    comparison[start_index + i] = "delete_me>"

        # We need to insert lines from last to the first
        # to preserve the indexes integrity.
        patch_content_line.reverse()

        for index in range(end_index, start_index - 1, -1):
            if operation_type in [
                PATCH_OPERATION_REMOVE,
                PATCH_OPERATION_REPLACE,
            ]:
                deletion_flagged_comparison = re.sub(
                    HTML_TAG_ISOLATION_REGEX,
                    DELETION_COMPARISON_REGEX,
                    comparison[index],
                )
                # Only use this line if it doesn't generate an empty
                # <removed> tag
                if not re.search(
                    EMPTY_OPERATION_TAG, deletion_flagged_comparison
                ):
                    comparison[index] = deletion_flagged_comparison

        if operation_type == PATCH_OPERATION_ADD:
            for line in patch_content_line:
                addition_flagged_line = re.sub(
                    HTML_TAG_ISOLATION_REGEX, ADDITION_COMPARISON_REGEX, line
                )

                if not re.search(EMPTY_OPERATION_TAG, addition_flagged_line):
                    comparison.insert(start_index + 1, addition_flagged_line)
                else:
                    comparison.insert(start_index + 1, line)

        if operation_type == PATCH_OPERATION_REPLACE:
            for line in patch_content_line:
                addition_flagged_line = re.sub(
                    HTML_TAG_ISOLATION_REGEX, ADDITION_COMPARISON_REGEX, line
                )
                if not re.search(EMPTY_OPERATION_TAG, addition_flagged_line):
                    comparison.insert(start_index, addition_flagged_line)
                elif (
                    line.split(">")[0] != comparison[start_index].split(">")[0]
                    or line.startswith("/")
                ):
                    comparison.insert(start_index, line)

    final_comparison = LINE_SEPARATOR.join(comparison)
    # We can remove all the opening tags which are located between the end of an
    # added tag and the start of a removed tag, because this should never happen
    # as the added and removed tags should always be near each other.
    # This can happen when the new container tag had a parameter change.
    final_comparison = re.sub(
        SAME_TAG_REPLACE_FIXER, "</added><removed>", final_comparison
    )

    # Remove al the <delete_me> tags
    final_comparison = final_comparison.replace(r"<delete_me>", "")

    # This fix the issue of unnecessary replace tags.
    # ex: <added>abc</added><removed>abc</removed> -> abc
    # This can occur when the new content is the same as the old content and
    # their container tags are the same but the tags parameters are different
    for match in re.finditer(UNNECESSARY_REPLACE_FIXER, final_comparison):
        if match.group(1) == match.group(2):
            final_comparison = final_comparison.replace(
                match.group(0), match.group(1)
            )

    return final_comparison


def _format_line_index(start, end):
    """Format the line index to be used in a patch operation.

    :param start: the start index
    :param end: the end index
    :return: string
    """
    length = end - start
    if not length:
        start -= 1
    if length <= 1:
        return "%s%s" % (PATCH_OPERATION_LINE_AT, start)
    return "%s%s,%s" % (PATCH_OPERATION_LINE_AT, start, start + length - 1)


def _patch_generator(new_content, old_content):
    """Generate a patch (multiple operations) between two contents.
    Each operation is a string with the following format:
    <operation_type>@<start_index>[,<end_index>][:<patch_text>*]
    patch format example:
        +@4:<p>ab</p><p>cd</p>
        +@4,15:<p>ef</p><p>gh</p>
        -@32
        -@125,129
        R@523:<b>sdf</b>

    :param string new_content: the new content
    :param string old_content: the old content

    :return: string: the patch containing all the operations to reverse
                     the new content to the old content
    """
    # remove break line in contents to ensure they don't interfere with
    # operations
    new_content = new_content.replace("\n", "")
    old_content = old_content.replace("\n", "")

    new_content_lines = new_content.split(LINE_SEPARATOR)
    old_content_lines = old_content.split(LINE_SEPARATOR)

    for group in SequenceMatcher(
        None, new_content_lines, old_content_lines, False
    ).get_grouped_opcodes(0):
        patch_content_line = []
        first, last = group[0], group[-1]
        patch_operation = _format_line_index(first[1], last[2])

        if any(tag in {"replace", "delete"} for tag, _, _, _, _ in group):
            for tag, _, _, _, _ in group:
                if tag not in {"insert", "equal", "replace"}:
                    patch_operation = PATCH_OPERATIONS[tag] + patch_operation

        if any(tag in {"replace", "insert"} for tag, _, _, _, _ in group):
            for tag, _, _, j1, j2 in group:
                if tag not in {"delete", "equal"}:
                    patch_operation = PATCH_OPERATIONS[tag] + patch_operation
                    for line in old_content_lines[j1:j2]:
                        patch_content_line.append(line)

        if patch_content_line:
            patch_content = LINE_SEPARATOR + LINE_SEPARATOR.join(
                patch_content_line
            )
            yield str(patch_operation) + PATCH_OPERATION_CONTENT + patch_content
        else:
            yield str(patch_operation)


def generate_patch(new_content, old_content):
    new_content = _remove_html_attribute(new_content, HTML_ATTRIBUTES_TO_REMOVE)
    old_content = _remove_html_attribute(old_content, HTML_ATTRIBUTES_TO_REMOVE)

    return OPERATION_SEPARATOR.join(
        list(_patch_generator(new_content, old_content))
    )


def _remove_html_attribute(html_content, attributes_to_remove):
    for attribute in attributes_to_remove:
        html_content = re.sub(
            r' %s="[^"]*"' % attribute, "", html_content
        )

    return html_content


def _indent(content):
    """Indent the content using BeautifulSoup.

    :param string content: the content to indent

    :return: string: the indented content
    """
    content = "<document>" + _remove_html_attribute(content, HTML_ATTRIBUTES_TO_REMOVE) + "</document>"
    soup = BeautifulSoup(content, 'html.parser')
    return soup.prettify()


def generate_unified_diff(new_content, old_content):
    """Generate a unified diff between two contents.

    :param string new_content: the current content
    :param string old_content: the old content

    :return: string: the unified diff content
    """
    new_content = _indent(new_content)
    old_content = _indent(old_content)

    return OPERATION_SEPARATOR.join(
        list(unified_diff(
            old_content.split(OPERATION_SEPARATOR),
            new_content.split(OPERATION_SEPARATOR),
            fromfile='old',
            tofile='new'
        ))
    )
