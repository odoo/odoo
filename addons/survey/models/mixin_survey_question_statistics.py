import collections
import itertools
import json
import operator
import re
from typing import Any

from odoo import models, tools


class MixinSurveyQuestionStatistics(models.AbstractModel):
    _name = "mixin.survey.question.statistics"
    _description = "Survey Question Statistics Mixin"

    def _prepare_question_statistics(
        self, user_input_lines: Any
    ) -> list[dict[str, Any]]:
        all_questions_data = []
        lines_by_question = user_input_lines.grouped("question_id")
        empty_lines = self.env["survey.user_input.line"]
        for question in self:
            question_data = {"question": question, "is_page": question.is_page}

            if question.is_page:
                all_questions_data.append(question_data)
                continue

            all_lines = lines_by_question.get(question, empty_lines)
            if question.question_type in [
                "simple_choice",
                "dropdown",
                "multiple_choice",
                "matrix",
                "likert",
            ]:
                answer_lines = all_lines.filtered(
                    lambda line, q=question: (
                        line.answer_type == "suggestion"
                        or (line.skipped and not line.answer_type)
                        or (
                            line.answer_type == "char_box" and q.comment_count_as_answer
                        )
                    )
                )
                comment_line_ids = all_lines.filtered(
                    lambda line: line.answer_type == "char_box"
                )
            else:
                answer_lines = all_lines
                comment_line_ids = self.env["survey.user_input.line"]
            skipped_lines = answer_lines.filtered(lambda line: line.skipped)
            done_lines = answer_lines - skipped_lines
            question_data.update(
                answer_line_ids=answer_lines,
                answer_line_done_ids=done_lines,
                answer_input_done_ids=done_lines.mapped("user_input_id"),
                answer_input_ids=answer_lines.mapped("user_input_id"),
                comment_line_ids=comment_line_ids,
            )
            question_data.update(question._get_stats_summary_data(answer_lines))

            table_data, graph_data, extra_data = question._get_stats_data(answer_lines)
            question_data["table_data"] = table_data
            question_data["graph_data"] = json.dumps(graph_data)
            if extra_data:
                question_data["extra_data"] = extra_data
            if question.question_type in [
                "text_box",
                "char_box",
                "numerical_box",
                "date",
                "datetime",
            ]:
                answers_data = [
                    [
                        input_line.id,
                        input_line._get_answer_value(),
                        input_line.user_input_id.get_print_url(),
                    ]
                    for input_line in table_data
                    if not input_line.skipped
                ]
                question_data["answers_data"] = json.dumps(answers_data, default=str)
            if question.question_type in ("text_box", "char_box"):
                question_data["text_analysis"] = question._get_text_analysis(
                    answer_lines
                )
            all_questions_data.append(question_data)
        return all_questions_data

    def _get_stats_data(
        self, user_input_lines: Any
    ) -> tuple[Any, list[dict[str, Any]], dict[str, Any] | None]:
        if self.question_type in ("simple_choice", "dropdown"):
            table_data, graph_data = self._get_stats_data_answers(user_input_lines)
            return table_data, graph_data, None
        elif self.question_type == "multiple_choice":
            table_data, graph_data = self._get_stats_data_answers(user_input_lines)
            return table_data, [{"key": self.title, "values": graph_data}], None
        elif self.question_type in ("matrix", "likert"):
            table_data, graph_data = self._get_stats_graph_data_matrix(user_input_lines)
            return table_data, graph_data, None
        elif self.question_type == "scale":
            table_data, graph_data = self._get_stats_data_scale(user_input_lines)
            return table_data, [{"key": self.title, "values": graph_data}], None
        elif self.question_type == "nps":
            return self._get_stats_data_nps(user_input_lines)
        elif self.question_type == "slider":
            return list(user_input_lines), [], None
        elif self.question_type == "rating":
            table_data, graph_data = self._get_stats_data_rating(user_input_lines)
            return table_data, [{"key": self.title, "values": graph_data}], None
        elif self.question_type in ("ranking", "constant_sum"):
            return self._get_stats_data_per_answer(user_input_lines)
        return list(user_input_lines), [], None

    def _get_stats_data_answers(
        self, user_input_lines: Any
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        suggested_answers = list(self.mapped("suggested_answer_ids"))
        if self.comment_count_as_answer:
            suggested_answers += [self.env["survey.question.answer"]]

        count_data = dict.fromkeys(suggested_answers, 0)
        for line in user_input_lines:
            if line.suggested_answer_id in count_data or (
                line.value_char_box and self.comment_count_as_answer
            ):
                count_data[line.suggested_answer_id] += 1

        table_data = [
            {
                "value": self.env._("Other (see comments)")
                if not suggested_answer
                else suggested_answer.value_label,
                "suggested_answer": suggested_answer,
                "count": count_data[suggested_answer],
                "count_text": self.env._("%s Votes", count_data[suggested_answer]),
            }
            for suggested_answer in suggested_answers
        ]
        graph_data = [
            {
                "text": self.env._("Other (see comments)")
                if not suggested_answer
                else suggested_answer.value_label,
                "count": count_data[suggested_answer],
            }
            for suggested_answer in suggested_answers
        ]

        return table_data, graph_data

    def _get_stats_graph_data_matrix(
        self, user_input_lines: Any
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        suggested_answers = self.mapped("suggested_answer_ids")
        matrix_rows = self.mapped("matrix_row_ids")

        count_data = dict.fromkeys(itertools.product(matrix_rows, suggested_answers), 0)
        for line in user_input_lines:
            cell = (line.matrix_row_id, line.suggested_answer_id)
            if cell in count_data:
                count_data[cell] += 1

        table_data = [
            {
                "row": row,
                "columns": [
                    {
                        "suggested_answer": suggested_answer,
                        "count": count_data[(row, suggested_answer)],
                    }
                    for suggested_answer in suggested_answers
                ],
            }
            for row in matrix_rows
        ]
        graph_data = [
            {
                "key": suggested_answer.value,
                "values": [
                    {"text": row.value, "count": count_data[(row, suggested_answer)]}
                    for row in matrix_rows
                ],
            }
            for suggested_answer in suggested_answers
        ]

        return table_data, graph_data

    def _get_stats_data_scale(
        self, user_input_lines: Any
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        suggested_answers = range(self.scale_min, self.scale_max + 1)

        count_data = dict.fromkeys(suggested_answers, 0)
        for line in user_input_lines:
            if not line.skipped and line.value_scale in count_data:
                count_data[line.value_scale] += 1

        table_data = []
        graph_data = []
        for sug_answer in suggested_answers:
            table_data.append(
                {
                    "value": str(sug_answer),
                    "suggested_answer": self.env["survey.question.answer"],
                    "count": count_data[sug_answer],
                    "count_text": self.env._("%s Votes", count_data[sug_answer]),
                }
            )
            graph_data.append(
                {"text": str(sug_answer), "count": count_data[sug_answer]}
            )

        return table_data, graph_data

    def _get_stats_data_nps(
        self, user_input_lines: Any
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
        count_data = dict.fromkeys(range(11), 0)
        for line in user_input_lines:
            if not line.skipped and 0 <= line.value_scale <= 10:
                count_data[line.value_scale] += 1

        total = sum(count_data.values())
        detractors = sum(count_data[v] for v in range(7))
        passives = sum(count_data[v] for v in range(7, 9))
        promoters = sum(count_data[v] for v in range(9, 11))
        nps_score = round((promoters - detractors) / total * 100) if total else 0

        table_data = []
        graph_data = []
        for value in range(11):
            color = "#dc3545" if value <= 6 else "#ffc107" if value <= 8 else "#28a745"
            table_data.append(
                {
                    "value": str(value),
                    "suggested_answer": self.env["survey.question.answer"],
                    "count": count_data[value],
                    "count_text": self.env._("%s Votes", count_data[value]),
                }
            )
            graph_data.append(
                {
                    "text": str(value),
                    "count": count_data[value],
                    "color": color,
                }
            )

        nps_graph_data = [{"key": self.title, "values": graph_data}]
        nps_summary = {
            "nps_score": nps_score,
            "detractors": detractors,
            "passives": passives,
            "promoters": promoters,
            "total": total,
            "detractors_pct": round(detractors / total * 100) if total else 0,
            "passives_pct": round(passives / total * 100) if total else 0,
            "promoters_pct": round(promoters / total * 100) if total else 0,
        }
        return table_data, nps_graph_data, nps_summary

    def _get_stats_data_rating(
        self, user_input_lines: Any
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        suggested_answers = range(1, self.rating_max + 1)
        count_data = dict.fromkeys(suggested_answers, 0)
        for line in user_input_lines:
            if not line.skipped and line.value_scale in count_data:
                count_data[line.value_scale] += 1

        table_data = []
        graph_data = []
        for value in suggested_answers:
            table_data.append(
                {
                    "value": str(value),
                    "suggested_answer": self.env["survey.question.answer"],
                    "count": count_data[value],
                    "count_text": self.env._("%s Votes", count_data[value]),
                }
            )
            graph_data.append({"text": str(value), "count": count_data[value]})
        return table_data, graph_data

    def _get_stats_data_per_answer(
        self, user_input_lines: Any
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], None]:
        table_data = []
        graph_data = []
        for answer in self.suggested_answer_ids:
            lines = user_input_lines.filtered(
                lambda ln, a=answer: ln.suggested_answer_id == a and not ln.skipped
            )
            values = [ln.value_numerical_box for ln in lines]
            avg_val = sum(values) / len(values) if values else 0
            table_data.append(
                {
                    "value": answer.value,
                    "suggested_answer": answer,
                    "count": len(values),
                    "count_text": self.env._("Avg: %s", round(avg_val, 1)),
                }
            )
            graph_data.append({"text": answer.value, "count": round(avg_val, 1)})
        return table_data, [{"key": self.title, "values": graph_data}], None

    _STOP_WORDS_BY_LANG = {
        "en": frozenset(
            [
                "a",
                "an",
                "the",
                "and",
                "or",
                "but",
                "in",
                "on",
                "at",
                "to",
                "for",
                "of",
                "is",
                "it",
                "was",
                "be",
                "are",
                "been",
                "have",
                "has",
                "had",
                "do",
                "does",
                "did",
                "will",
                "would",
                "could",
                "should",
                "may",
                "might",
                "all",
                "any",
                "each",
                "every",
                "some",
                "both",
                "few",
                "many",
                "how",
                "what",
                "when",
                "where",
                "which",
                "who",
                "whom",
                "why",
                "its",
                "his",
                "her",
                "there",
                "here",
                "then",
                "now",
                "only",
                "still",
                "already",
                "even",
                "again",
            ]
        ),
        "es": frozenset(
            [
                "el",
                "la",
                "los",
                "las",
                "un",
                "una",
                "unos",
                "unas",
                "y",
                "o",
                "pero",
                "en",
                "de",
                "del",
                "a",
                "al",
                "para",
                "por",
                "con",
                "sin",
                "que",
                "se",
                "lo",
                "su",
                "sus",
                "es",
                "son",
                "era",
                "eran",
                "ser",
                "estar",
                "este",
                "esta",
                "estos",
                "estas",
                "ese",
                "esa",
                "como",
                "cuando",
                "donde",
                "quien",
                "porque",
                "muy",
                "mas",
                "menos",
                "todo",
                "toda",
                "todos",
                "todas",
                "ya",
                "tambien",
                "solo",
                "aun",
                "otra",
                "otro",
            ]
        ),
    }

    def _stop_words(self) -> frozenset[str]:
        """Keyed by the answers' language, not hardcoded to one of them.

        A single English list applied to Spanish answers returns de/la/que/el as
        the most frequent words, which is the whole word cloud. An unlisted
        language filters nothing rather than filtering the wrong thing.
        """
        lang = (self.env.context.get("lang") or self.env.lang or "en").split("_")[0]
        return self._STOP_WORDS_BY_LANG.get(lang, frozenset())

    def _get_text_analysis(
        self, user_input_lines: Any
    ) -> dict[str, list[dict[str, Any]]]:
        self.check_singleton()
        field_name = (
            "value_text_box" if self.question_type == "text_box" else "value_char_box"
        )
        all_text = " ".join(
            getattr(line, field_name) or ""
            for line in user_input_lines
            if not line.skipped
        )
        if not all_text.strip():
            return {"word_cloud": [], "top_keywords": []}

        stop_words = self._stop_words()
        words = re.findall(r"\w{3,}", all_text.lower())
        words = [w for w in words if w not in stop_words and not w.isdigit()]
        counter = collections.Counter(words)

        top_50 = counter.most_common(50)
        max_count = top_50[0][1] if top_50 else 1
        word_cloud = [
            {"text": word, "weight": round(count / max_count * 100)}
            for word, count in top_50
        ]
        top_keywords = [
            {"word": word, "count": count} for word, count in counter.most_common(20)
        ]
        return {
            "word_cloud": word_cloud,
            "top_keywords": top_keywords,
        }

    def _get_stats_summary_data(self, user_input_lines: Any) -> dict[str, Any]:
        stats = {}
        if self.question_type in ["simple_choice", "dropdown", "multiple_choice"]:
            stats.update(self._get_stats_summary_data_choice(user_input_lines))
        elif self.question_type in ("numerical_box", "slider"):
            stats.update(self._get_stats_summary_data_numerical(user_input_lines))
        elif self.question_type in ("scale", "nps", "rating"):
            stats.update(
                self._get_stats_summary_data_numerical(user_input_lines, "value_scale")
            )

        if self.question_type in [
            "numerical_box",
            "slider",
            "date",
            "datetime",
            "scale",
            "nps",
            "rating",
        ]:
            stats.update(self._get_stats_summary_data_scored(user_input_lines))
        return stats

    def _get_stats_summary_data_choice(self, user_input_lines: Any) -> dict[str, Any]:
        right_inputs, partial_inputs = (
            self.env["survey.user_input"],
            self.env["survey.user_input"],
        )
        right_answers = self.suggested_answer_ids.filtered(
            lambda label: label.is_correct
        )
        if self.question_type == "multiple_choice":
            for user_input, lines in tools.groupby(
                user_input_lines, operator.itemgetter("user_input_id")
            ):
                input_lines = self.env["survey.user_input.line"].concat(*lines)
                all_selected = input_lines.mapped("suggested_answer_id")
                correct_selected = input_lines.filtered(
                    lambda l: l.answer_is_correct
                ).mapped("suggested_answer_id")
                if (
                    correct_selected
                    and correct_selected == right_answers
                    and all_selected == right_answers
                ):
                    right_inputs += user_input
                elif correct_selected:
                    partial_inputs += user_input
        else:
            right_inputs = user_input_lines.filtered(
                lambda line: line.answer_is_correct
            ).mapped("user_input_id")
        return {
            "right_answers": right_answers,
            "right_inputs_count": len(right_inputs),
            "partial_inputs_count": len(partial_inputs),
        }

    def _get_stats_summary_data_numerical(
        self, user_input_lines: Any, fname: str = "value_numerical_box"
    ) -> dict[str, float]:
        all_values = user_input_lines.filtered(lambda line: not line.skipped).mapped(
            fname
        )
        lines_sum = sum(all_values)
        return {
            "numerical_max": max(all_values, default=0),
            "numerical_min": min(all_values, default=0),
            "numerical_average": round(lines_sum / (len(all_values) or 1), 2),
        }

    _VALUE_FIELD_ALIAS = {"nps": "scale", "slider": "numerical_box", "rating": "scale"}

    def _get_stats_summary_data_scored(self, user_input_lines: Any) -> dict[str, Any]:
        value_field_type = self._VALUE_FIELD_ALIAS.get(
            self.question_type, self.question_type
        )
        return {
            "common_lines": collections.Counter(
                user_input_lines.filtered(lambda line: not line.skipped).mapped(
                    f"value_{value_field_type}"
                )
            ).most_common(5),
            "right_inputs_count": len(
                user_input_lines.filtered(lambda line: line.answer_is_correct).mapped(
                    "user_input_id"
                )
            ),
        }

    def _get_correct_answers(self) -> dict[int, Any]:
        correct_answers = {}

        choices_questions = self.filtered(
            lambda q: (
                q.question_type in ["simple_choice", "dropdown", "multiple_choice"]
            )
        )
        if choices_questions:
            suggested_answers_data = self.env["survey.question.answer"].search_read(
                [
                    ("question_id", "in", choices_questions.ids),
                    ("is_correct", "=", True),
                ],
                ["question_id", "id"],
                load="",
            )
            for data in suggested_answers_data:
                if not data.get("id"):
                    continue
                correct_answers.setdefault(data["question_id"], []).append(data["id"])

        for question in self - choices_questions:
            if question.question_type not in ["numerical_box", "date", "datetime"]:
                continue
            answer = question[f"answer_{question.question_type}"]
            if not question.is_scored_question:
                continue
            if question.question_type == "date":
                answer = tools.format_date(self.env, answer)
            elif question.question_type == "datetime":
                answer = tools.format_datetime(
                    self.env, answer, tz="UTC", dt_format=False
                )
            correct_answers[question.id] = answer

        return correct_answers
