# -*- coding: utf-8 -*-
"""掲示板カテゴリ・投稿モデル定義。

カテゴリは掲示板記事を整理するための階層のないシンプルなグルーピング。
投稿は公開期間、ピン留め情報、通知機能（mail.thread）を持つ。
"""

from odoo import fields, models


class EmployeeBoardCategory(models.Model):
    """掲示板カテゴリ。

    sequence で並び順を制御し、名前は必須。
    """

    _name = "employee.board.category"
    _description = "Employee Board Category"
    _order = "sequence, name"

    # カテゴリ名（必須）
    name = fields.Char(string="カテゴリ名", required=True)
    # 一覧での表示順を制御するシーケンス（昇順）
    sequence = fields.Integer(string="表示順", default=10)



class EmployeeBoardPost(models.Model):
    """掲示板投稿。

    mail.thread を継承し、フォロワーやアクティビティで通知できる。
    公開期間とピン留めで表示優先度を管理する。
    """

    _name = "employee.board.post"
    _description = "Employee Board Post"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "publish_from desc, create_date desc"

    # タイトル（必須、トラッキング対象）
    name = fields.Char(string="タイトル", required=True, tracking=True)
    # 所属カテゴリ
    category_id = fields.Many2one(
        "employee.board.category",
        string="カテゴリ",
        tracking=True,
    )
    # 種別：マニュアル／メニュー／告知
    type = fields.Selection(
        [
            ("manual", "マニュアル"),
            ("menu", "メニュー"),
            ("notice", "告知"),
        ],
        string="種別",
        tracking=True,
    )
    # 本文（HTML）
    body_html = fields.Html(string="内容")
    # 所属会社。マルチカンパニー対応のためデフォルトで現在会社をセット
    company_id = fields.Many2one(
        "res.company",
        string="会社",
        default=lambda self: self.env.company,
    )
    # 公開開始日
    publish_from = fields.Date(string="公開開始日")
    # 公開終了日
    publish_to = fields.Date(string="公開終了日")
    # ピン留めフラグ（優先表示）
    is_pinned = fields.Boolean(string="ピン留め")
    # アーカイブ用の標準 active フィールド
    active = fields.Boolean(string="有効", default=True)
