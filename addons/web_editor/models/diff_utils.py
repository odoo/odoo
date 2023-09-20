# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from difflib import SequenceMatcher


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

HTML_ATTRIBUTES_TO_REMOVE = [
    "data-last-history-steps",
]


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


HTML_TAG_ISOLATION_REGEX = r"^([^>]*>)(.*)$"
ADDITION_COMPARISON_REGEX = r"\1<added>\2</added>"
ADDITION_1ST_REPLACE_COMPARISON_REGEX = r"added>\2</added>"
DELETION_COMPARISON_REGEX = r"\1<removed>\2</removed>"
EMPTY_OPERATION_TAG = r"<(added|removed)><\/(added|removed)>"


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
                    comparison[index] = re.sub(
                        HTML_TAG_ISOLATION_REGEX,
                        DELETION_COMPARISON_REGEX,
                        comparison[index],
                    )

        if operation_type == PATCH_OPERATION_ADD:
            for line in patch_content_line:
                comparison.insert(
                    start_index + 1,
                    re.sub(
                        HTML_TAG_ISOLATION_REGEX,
                        ADDITION_COMPARISON_REGEX,
                        line,
                    ),
                )

        if operation_type == PATCH_OPERATION_REPLACE:
            for i, line in enumerate(patch_content_line):
                # We need to remove the first tag of a replace operation
                # to avoid having a duplicate opening tag in the middle of a
                # line.
                replace_regex = (
                    ADDITION_1ST_REPLACE_COMPARISON_REGEX
                    if i == len(patch_content_line) - 1
                    else ADDITION_COMPARISON_REGEX
                )
                comparison.insert(
                    start_index + 1,
                    re.sub(HTML_TAG_ISOLATION_REGEX, replace_regex, line),
                )

        if operation_type in [PATCH_OPERATION_REMOVE, PATCH_OPERATION_REPLACE]:
            comparison[start_index] = re.sub(
                HTML_TAG_ISOLATION_REGEX,
                DELETION_COMPARISON_REGEX,
                comparison[start_index],
            )

    comparison = [re.sub(EMPTY_OPERATION_TAG, "", line) for line in comparison]
    return LINE_SEPARATOR.join(comparison)


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
        return "{}{}".format(PATCH_OPERATION_LINE_AT, start)
    return "{}{},{}".format(PATCH_OPERATION_LINE_AT, start, start + length - 1)


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
            r' {}="[^"]*"'.format(attribute), "", html_content
        )

    return html_content
