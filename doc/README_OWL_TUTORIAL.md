思考時間: 21s

Odoo 19 の JS（OWL）拡張、ここから触れると分かりやすいよ、という**「基礎チュートリアル」を md 形式でまとめます**。
OWL_TUTORIAL.md みたいな名前で保存して使える想定です 👍

# Odoo 19 OWL（JS）拡張・基礎チュートリアル

このドキュメントでは、Odoo 19 のフロントエンドフレームワーク **OWL** を使って、

- 自作の OWL コンポーネントを作成し
- バックエンド画面（web クライアント）に表示し
- 将来的に既存画面を拡張できるようになる

までの **最小構成サンプル** を解説します。

---

## 0. 前提

- Odoo 19 が Docker で起動済み  
  （`http://localhost:8069` でログインできる）
- custom_addons に `module_template` などのカスタムモジュールがある
- `docker-compose.yml` で以下のようにマウントしている：

```yaml
volumes:
  - ./custom_addons:/mnt/extra-addons


このチュートリアルでは、既存の module_template に JS/OWL を追加していきます。

1. OWL とは何か（ざっくり）

Odoo 16 以降のフロントエンドは OWL (Odoo Web Library) という React ライクなフレームワークで書かれている

概念は「コンポーネント + テンプレート（XML）」

JS は ES モジュール形式で書き、ファイル先頭に /** @odoo-module **/ を付ける

Odoo の画面（リストビュー、フォームビュー、ヘッダーバー、systray など）は、OWL コンポーネントの集合体

この OWL コンポーネントを自作して、Odoo に「埋め込む」のが拡張の基本です。

2. 今回作るもの

画面右上のヘッダー部分（ユーザーアイコンの近く）に、簡単なボタンを追加します。

ボタンをクリックすると、小さなカウンターが増えていく

フロント側で動くだけなので、DB には影響しない

OWL コンポーネントの基本（state, event, template）を体験できる

3. ディレクトリ構成を追加

custom_addons/module_template に、OWL 用のディレクトリを追加します：

custom_addons/
└─ module_template/
   ├─ __init__.py
   ├─ __manifest__.py
   ├─ models/
   ├─ views/
   ├─ security/
   └─ static/
       └─ src/
           ├─ js/
           │   └─ sample_systray.js
           └─ xml/
               └─ sample_systray.xml


※ static/src/js, static/src/xml の構成は Odoo 標準のパターンです。

4. OWL コンポーネントの JS を書く

module_template/static/src/js/sample_systray.js

/** @odoo-module **/

// OWL の Component, useState
import { Component, useState } from "@odoo/owl";
// ヘッダ右上の「Systray」領域に登録するための registry
import { registry } from "@web/core/registry";

// systray 用のカテゴリを取得
const systrayRegistry = registry.category("systray");

// ===============================
// OWL コンポーネント本体
// ===============================
export class SampleSystray extends Component {
    setup() {
        // コンポーネント内の状態（state）を定義
        this.state = useState({
            count: 0,
        });
    }

    // ボタン押下時に呼ばれるメソッド
    increment() {
        this.state.count++;
    }
}

// ===============================
// テンプレート名を紐づける
// （後ほど XML で定義する）
// ===============================
SampleSystray.template = "module_template.SampleSystray";

// ===============================
// systray にコンポーネントを登録
// ===============================
// 第1引数: 一意なキー
// 第2引数: { Component } オブジェクト
systrayRegistry.add("module_template.SampleSystray", {
    Component: SampleSystray,
});


ポイント：

/** @odoo-module **/ を必ず先頭に書く

registry.category("systray") に Component を登録すると、ヘッダー右上（通知アイコンなどの領域）に表示される

SampleSystray.template にテンプレートの技術名を設定
→ 後で書く XML と一致させる

5. テンプレート(XML)を書く

module_template/static/src/xml/sample_systray.xml

<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <!--
        template の name は JS 側で指定した
        SampleSystray.template に対応する
        "module_template.SampleSystray"
    -->
    <templates xml:space="preserve">
        <t t-name="module_template.SampleSystray">
            <!--
                systray 用のボタン（シンプルな例）
                - t-on-click で JS メソッドを呼び出す
                - t-esc="state.count" で state 表示
            -->
            <button type="button"
                    class="btn btn-link o_systray_item"
                    t-on-click="increment">
                <span>Sample: <t t-esc="state.count"/></span>
            </button>
        </t>
    </templates>
</odoo>


ポイント：

<templates> 配下に <t t-name="..."> で OWL テンプレートを定義

JS の SampleSystray.template = "module_template.SampleSystray"; と一致していること

t-on-click="increment" により、JS クラス内の increment() が呼ばれる

6. アセットバンドルへの登録（manifest 修正）

この JS/XML を Odoo の web クライアントが読み込めるように、__manifest__.py に asset 定義を追加します。

module_template/__manifest__.py（既存の内容に追記）

# -*- coding: utf-8 -*-
{
    "name": "Module Template Sample",
    "summary": "Sample module for Odoo 19 development & debugging",
    "description": """
Module Template Sample
======================

Odoo 19 向けの開発・デバッグ用サンプルモジュールです。
    """,
    "author": "Kazuaki Watanabe",
    "website": "https://github.com/KazuakiWatanabe",
    "category": "Tools",
    "version": "19.0.1.0.0",
    "depends": [
        "base",
        "web",  # ← フロントエンド拡張には web モジュールへの依存が必要
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/sample_item_views.xml",
        "views/sample_item_menu.xml",
    ],
    # ==============================
    # ここから asset 定義
    # ==============================
    "assets": {
        # バックエンド画面（管理画面）で読み込むアセット
        "web.assets_backend": [
            "module_template/static/src/js/sample_systray.js",
            "module_template/static/src/xml/sample_systray.xml",
        ],
    },
    "application": True,
}


ポイント：

"depends" に "web" を追加

"assets" → "web.assets_backend" に JS/XML を指定

パスは addons/module_name/ を省いた相対パスで書く

7. Odoo を再起動 → アセット更新
7-1. Docker のコンテナを再起動
cd ./odoo_dev
docker compose restart odoo

7-2. アセットキャッシュのクリア（推奨）

Odoo はアセットをバンドル・キャッシュするので、ブラウザ側で Ctrl+F5 などでリロードする。

必要なら Odoo の開発者モードの debug=assets を使って：

http://localhost:8069/web?debug=assets


としてアクセスすると、アセットの再読み込みが強制されて開発時に便利です。

8. 画面を確認する

ブラウザで http://localhost:8069 にアクセス

ログイン

画面右上のヘッダーバー（ユーザー名の近く）に
「Sample: 0」 というテキスト付きボタンが表示されていることを確認

クリックするたびに Sample: 1, 2, 3 ... と増えていけば成功 🎉

9. OWL コンポーネントをデバッグする
9-1. ブラウザの DevTools

Chrome の DevTools（F12）を開く

Sources タブで module_template/static/src/js/sample_systray.js を探し、ブレークポイントを置ける

※ Odoo 19 では Vite などと組み合わせている可能性がありますが、基本的にはビルド後 JS にもソースマップがつくので、元ファイルに近い形でブレークが可能です。

9-2. ログ出力
increment() {
    console.log("SampleSystray clicked, current count:", this.state.count);
    this.state.count++;
}


のように console.log を仕込むのも有効です。

10. 応用の入口

このサンプルが動けば、次のような拡張に進めます。

✔ 特定モデルのフォームビューをカスタムウィジェットで拡張する
→ registry.category("fields") にコンポーネントを登録して、widget="..." で使う

✔ 既存コンポーネントを patch して挙動を変える

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

patch(ListController.prototype, "module_template_list_patch", {
    // メソッドをオーバーライド or 追加
});


✔ ダイアログを表示するカスタムボタン
→ useService("dialog") で OWL コンポーネントからダイアログを出す

11. まとめ

このチュートリアルでは：

custom_addons 内に OWL 用の static/src/js / static/src/xml を追加

__manifest__.py の assets に登録

registry.systray に OWL コンポーネントを追加

画面右上のヘッダーにボタンを表示

という ”最小の OWL 拡張” を実装しました。

12. 次のステップの例

sample.item モデルのフォームに、OWL で作ったカスタムウィジェットを組み込む

Kanban ボードやリストビューにボタンを追加して、OWL コンポーネント側で制御

REST API と組み合わせて、外部サービスと連携する画面を作る

具体的に「この画面にこういうボタンを出したい」という要望があれば、
その場所に合わせた OWL の拡張パターン（fields, view, controller, systray, action など）を一緒に設計できます。
