# -*- coding: utf-8 -*-
"""タスクテンプレートと従業員タスクのモデル。

テンプレートは日次・週次・月次の定期タスクを表し、cron により実タスクが生成される。
タスクは従業員と日付で一意となるよう重複作成を防止する。
"""

import logging
from calendar import monthrange
from datetime import date as pydate

from odoo import fields, models

# モジュール内で cron のスキップ理由等をログ出力するためのロガー
_logger = logging.getLogger(__name__)



class EmployeeTaskTemplate(models.Model):
    """タスクテンプレート。

    frequency/weekday/month_day で発生頻度を定義し、employee_ids に紐付く従業員へ展開する。
    """

    _name = "employee.task.template"
    _description = "Employee Task Template"
    _order = "name"

    # テンプレート名称（必須）
    name = fields.Char(string="テンプレート名", required=True)
    # 補足説明
    description = fields.Text(string="説明")
    # 発生頻度（日次／週次／月次）
    frequency = fields.Selection(
        [
            ("daily", "日次"),
            ("weekly", "週次"),
            ("monthly", "月次"),
        ],
        string="頻度",
        default="daily",
        required=True,
    )
    # 週次タスクの曜日。0=Monday 〜 6=Sunday
    weekday = fields.Selection(
        [
            ("0", "月曜日"),
            ("1", "火曜日"),
            ("2", "水曜日"),
            ("3", "木曜日"),
            ("4", "金曜日"),
            ("5", "土曜日"),
            ("6", "日曜日"),
        ],
        string="曜日",
        help="週次タスクを生成する曜日。",
    )
    # 月次タスクの実行日（1〜31。31超は月末に丸める）
    month_day = fields.Integer(
        string="実行日（毎月）",
        help="1〜31で指定。月末を超える場合は末日に丸めます。",
    )
    # 対象従業員のMany2many
    employee_ids = fields.Many2many("hr.employee", string="従業員")
    # マルチカンパニー対応。未指定時は現在会社。
    company_id = fields.Many2one(
        "res.company",
        string="会社",
        default=lambda self: self.env.company,
    )
    # 標準のアクティブフラグ
    active = fields.Boolean(string="有効", default=True)



class EmployeeTask(models.Model):
    """従業員タスク。

    テンプレートから生成されることを想定し、status で進捗を管理する。
    """

    _name = "employee.task"
    _description = "Employee Task"
    _order = "date desc, id desc"

    # タスク名（通常はテンプレート名を引き継ぐ）
    name = fields.Char(string="タスク名", required=True)
    # 担当従業員（必須）
    employee_id = fields.Many2one("hr.employee", string="従業員", required=True)
    # 実施日（タスク生成対象日）
    date = fields.Date(string="日付", required=True)
    # 任意の締切日時
    deadline = fields.Datetime(string="期限")
    # ステータス（未実施／完了／キャンセル）
    status = fields.Selection(
        [
            ("todo", "未実施"),
            ("done", "完了"),
            ("cancel", "キャンセル"),
        ],
        string="ステータス",
        default="todo",
        required=True,
    )
    # 元となったテンプレート。更新しないので読み取り専用
    template_id = fields.Many2one(
        "employee.task.template",
        string="テンプレート",
        readonly=True,
    )
    # マルチカンパニー用の会社
    company_id = fields.Many2one(
        "res.company",
        string="会社",
        default=lambda self: self.env.company,
    )
    # 参考となる掲示板投稿へのリンク
    board_post_id = fields.Many2one("employee.board.post", string="関連掲示板")
    # 任意メモ
    note = fields.Text(string="メモ")

    def action_mark_done(self):
        """タスクを完了状態にする簡易アクション。"""
        for task in self:
            # 個別に done をセットすることで複数レコードでも動作
            task.status = "done"
        return True

    def cron_generate_tasks(self):
        """アクティブなテンプレートから日々のタスクを生成する。

        - daily: 毎日生成
        - weekly: 曜日が一致する場合のみ
        - monthly: month_day と当月日付が一致する場合のみ（末日丸め対応）
        同一日付・同一テンプレート・同一従業員のタスクが既にある場合は作成しない。
        """
        # 今日の日付（コンテキスト考慮）。何度も呼ばないようローカル変数に保持。
        today = fields.Date.context_today(self)
        # Python date に変換して曜日や年/月/日を求める
        today_dt = pydate.fromisoformat(str(today))
        weekday = str(today_dt.weekday())  # 0〜6の文字列
        year, month, day = today_dt.year, today_dt.month, today_dt.day

        # アクティブなテンプレートを全件取得（多人数展開のため sudo）
        templates = (
            self.env["employee.task.template"]
            .sudo()
            .search([("active", "=", True)])
        )
        for template in templates:
            if not template.employee_ids:
                # 従業員未割当の場合は生成をスキップ
                _logger.warning(
                    "Employee Task Template '%s' has no employees assigned; "
                    "skipping.",
                    template.display_name,
                )
                continue

            # 週次：曜日が一致しない場合スキップ
            if (
                template.frequency == "weekly"
                and template.weekday
                and template.weekday != weekday
            ):
                continue
            # 月次：指定日が無効（<=0）ならスキップ、31超は月末に丸めて比較
            if template.frequency == "monthly" and template.month_day:
                month_day = int(template.month_day or 0)  # 月次ターゲット日
                if month_day <= 0:
                    _logger.warning(
                        "Employee Task Template '%s' has invalid month_day=%s; "
                        "skipping.",
                        template.display_name,
                        template.month_day,
                    )
                    continue
                # 対象月の末日を取得し、指定日を丸める
                last_day = monthrange(year, month)[1]
                target_day = min(month_day, last_day)
                if target_day != day:
                    continue

            for employee in template.employee_ids:
                # 重複作成防止のためのドメイン
                domain = [
                    ("template_id", "=", template.id),
                    ("employee_id", "=", employee.id),
                    ("date", "=", today),
                ]
                exists = self.sudo().search_count(domain)  # 既存タスクの有無
                if exists:
                    continue
                # company_id はテンプレート優先、未設定なら従業員の会社
                self.sudo().create(
                    {
                        "name": template.name,
                        "employee_id": employee.id,
                        "date": today,
                        "status": "todo",
                        "template_id": template.id,
                        "company_id": template.company_id.id or employee.company_id.id,
                    }
                )
