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
