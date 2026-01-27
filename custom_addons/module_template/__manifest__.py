# -*- coding: utf-8 -*-
# -----------------------------------------------------------
# Module Template Sample
# Odoo 19 開発用のサンプルモジュール
# - Pythonモデル
# - ビュー（フォーム/リスト）
# - メニュー
# - OWL（JSフロントエンド）拡張
# これらをすべて含む、学習・開発用テンプレート
# -----------------------------------------------------------

{
    # モジュール名（Odoo のアプリ一覧に表示される）
    "name": "Module Template Sample",

    # モジュール概要（短い説明）
    "summary": "Sample module for Odoo 19 development & debugging including OWL systray component",

    # 詳細説明（複数行記述可能）
    "description": """
Module Template Sample
======================

This module contains:

- Basic Python model (sample.item)
- Tree & Form views
- Menu entries
- OWL Systray Component (sample_systray)
- Web asset integration example
- Debugging support when developing locally

Useful as a starting point for custom Odoo 19 development.
    """,

    # 作者情報（任意）
    "author": "Kazuaki Watanabe",
    "website": "https://github.com/KazuakiWatanabe",

    # モジュールカテゴリ（Odoo 上の分類）
    "category": "Tools",

    # バージョン (Odoo-Major.Minor.Revision.Build)
    "version": "19.0.1.0.0",

    # -----------------------------------------------------------
    # このモジュールが依存する Odoo の基本アドオン
    # -----------------------------------------------------------
    "depends": [
        "base",   # モデル定義に必要な Odoo 基盤モジュール
        "web",    # OWL（JS拡張）を使う場合は絶対に必要
    ],

    # -----------------------------------------------------------
    # XML・CSV で読み込むデータファイル
    # 読み込み順に注意（アクセス権 → ビュー → メニュー）
    # -----------------------------------------------------------
    "data": [
        "security/ir.model.access.csv",   # モデルへのアクセス権定義
        "views/sample_item_views.xml",    # ツリー / フォームビュー
        "views/sample_item_menu.xml",     # メニュー
    ],

    # -----------------------------------------------------------
    # Web クライアントで読み込むアセット（JS / XML）
    # Odoo 19 では Vite + OWL ベースの AssetBundle を使用
    # "web.assets_backend" = 管理画面に読み込まれるアセット
    # -----------------------------------------------------------
    "assets": {
        "web.assets_backend": [
            # OWL コンポーネント（JavaScript）
            "module_template/static/src/js/sample_systray.js",

            # OWL テンプレート（XML）
            "module_template/static/src/xml/sample_systray.xml",
        ],
    },

    # -----------------------------------------------------------
    # このモジュールを「アプリ一覧」に表示するかどうか
    # True にすると Apps にカード表示される
    # -----------------------------------------------------------
    "application": True,
}
