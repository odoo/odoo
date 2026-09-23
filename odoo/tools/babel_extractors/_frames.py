from __future__ import annotations

from typing import Any

type Frame = dict[str, Any]
type TranslatorComments = list[tuple[int, str]]
type ExtractionResult = tuple[int, str, str | tuple[str, ...], list[str]]


def push_function_frame(
    function_stack: list[Frame],
    translator_comments: TranslatorComments,
    message_buffer: list[str],
    *,
    compare_lineno: int,
    function_lineno: int,
    function_name: str,
    message_lineno: int | None,
    messages: list,
) -> TranslatorComments:
    cur_translator_comments = translator_comments
    if function_stack and function_stack[-1]["function_lineno"] == compare_lineno:
        cur_translator_comments = function_stack[-1]["translator_comments"]

    function_stack.append(
        {
            "function_lineno": function_lineno,
            "function_name": function_name,
            "message_lineno": message_lineno,
            "messages": messages,
            "translator_comments": cur_translator_comments,
        }
    )
    message_buffer.clear()
    return []


def close_keyword_frame(
    function_stack: list[Frame], message_buffer: list[str]
) -> ExtractionResult:
    frame = function_stack[-1]
    messages = frame["messages"]
    lineno = frame["message_lineno"] or frame["function_lineno"]
    cur_translator_comments = frame["translator_comments"]

    if message_buffer:
        messages.append("".join(message_buffer))
        message_buffer.clear()
    else:
        messages.append(None)

    messages = tuple(messages) if len(messages) > 1 else messages[0]
    if cur_translator_comments and cur_translator_comments[-1][0] < lineno - 1:
        cur_translator_comments = []

    function_stack.pop()
    return (
        lineno,
        frame["function_name"],
        messages,
        [comment[1] for comment in cur_translator_comments],
    )


def handle_line_comment(
    value: str,
    lineno: int,
    comment_tags: Any,
    in_translator_comments: bool,
    translator_comments: TranslatorComments,
) -> tuple[bool, bool]:
    if in_translator_comments and translator_comments[-1][0] == lineno - 1:
        translator_comments.append((lineno, value))
        return True, True
    for comment_tag in comment_tags:
        if value.startswith(comment_tag):
            translator_comments.append((lineno, value))
            return True, False
    return in_translator_comments, False


def open_keyword_name(function_stack: list[Frame], keywords: Any) -> str:
    if function_stack and function_stack[-1]["function_name"] in keywords:
        return function_stack[-1]["function_name"]
    return ""
