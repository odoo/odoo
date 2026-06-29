# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SampleItem(models.Model):
    """
    Odoo で1テーブルを表すクラス。
    _name の値がテーブル名（sample_item）になる。

    このクラスで定義した fields.* が DB カラムとして作成される。
    """
    _name = "sample.item"
    _description = "Sample Item for Development"

    # ===========================
    # フィールド定義（DBのカラム）
    # ===========================

    # 文字列フィールド（必須項目）
    name = fields.Char(string="Name", required=True)

    # テキストフィールド
    description = fields.Text(string="Description")

    # 論理値（ON/OFF）
    active = fields.Boolean(string="Active", default=True)

    # 整数値
    value = fields.Integer(string="Value")

    # 日付
    date = fields.Date(string="Date")

    # 選択項目（状態管理に便利）
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("done", "Done"),
        ],
        string="Status",
        default="draft",
    )

    # ===========================
    # オーバーライド：create()
    # ===========================
    @api.model
    def create(self, vals):
        """
        レコード作成時に必ず通る処理。
        デバッグポイントを置くのに最適。

        - vals: 入力された値の辞書
        """
        # ★ブレークポイント候補①
        return super().create(vals)

    # ===========================
    # ボタン用のヘルパー関数
    # ===========================
    def action_confirm(self):
        """
        Confirm ボタンを押したときに呼ばれる処理。
        """
        # ★ブレークポイント候補②
        for rec in self:
            rec.state = "confirmed"

    def action_done(self):
        """
        Done ボタンを押したときに呼ばれる処理。
        """
        # ★ブレークポイント候補③
        for rec in self:
            rec.state = "done"
