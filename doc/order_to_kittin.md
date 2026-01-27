Codex にそのまま渡せる形で、モジュール名＋フォルダ構成＋__manifest__.py〜models/controllers のひな型 をまとめます。

今回はモジュール名を例として：

restaurant_self_order_kitchen

にします。
（名前はお好みで変えてOKですが、フォルダ名と __manifest__['name'] / depends は揃えてください）

1. フォルダ構成
restaurant_self_order_kitchen/
├─ __init__.py
├─ __manifest__.py
├─ models/
│   ├─ __init__.py
│   ├─ sale_order.py
│   └─ kitchen_ticket.py
├─ controllers/
│   ├─ __init__.py
│   └─ self_order.py
└─ views/
    ├─ kitchen_ticket_views.xml
    ├─ website_self_order_templates.xml
    └─ menu_items.xml


まずは Python 部分（__init__, __manifest__, models, controllers） を実装し、その後 view を追加していく流れでOKです。

2. __init__.py
# restaurant_self_order_kitchen/__init__.py

from . import models
from . import controllers

3. __manifest__.py

Odoo 19.0 用のざっくりした manifest です。細かい項目はあとで調整してください。

# restaurant_self_order_kitchen/__manifest__.py

{
    "name": "Restaurant Self Order & Kitchen Tickets",
    "summary": "Self-order from customer smartphones, kitchen tickets, and POS integration",
    "version": "19.0.1.0.0",
    "category": "Restaurant",
    "author": "Your Company",
    "website": "https://example.com",
    "license": "LGPL-3",
    "depends": [
        "base",
        "sale_management",   # sale.order を使う
        "point_of_sale",     # POS
        "website",           # self order の画面
        # 必要に応じて:
        # "pos_restaurant",  # テーブル管理を使う場合
        # "pos_sale",        # Sale Order -> POS連携を使う場合
    ],
    "data": [
        "views/menu_items.xml",
        "views/kitchen_ticket_views.xml",
        "views/website_self_order_templates.xml",
    ],
    "assets": {
        # 必要なら JS/CSS を指定（最初は空でもOK）
        # "web.assets_frontend": [
        #     "restaurant_self_order_kitchen/static/src/js/self_order.js",
        # ],
    },
    "application": True,
    "installable": True,
}

4. models/__init__.py
# restaurant_self_order_kitchen/models/__init__.py

from . import sale_order
from . import kitchen_ticket

5. models/sale_order.py（Sale Order にフィールド追加）
# restaurant_self_order_kitchen/models/sale_order.py

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # POSレストランのテーブルと紐付け（pos_restaurant 使用を想定）
    table_id = fields.Many2one(
        "pos.restaurant.table",
        string="Table",
        help="Restaurant table for this order (self-order).",
    )
    # スマホからのセルフオーダーかどうか
    is_self_order = fields.Boolean(
        string="Is Self Order",
        default=False,
        help="Flag to indicate this order was created from self-order site.",
    )
    kitchen_ticket_ids = fields.One2many(
        "restaurant.kitchen_ticket",
        "order_id",
        string="Kitchen Tickets",
    )

    @api.model
    def create_from_self_order(self, values):
        """
        スマホ注文から Sale Order を作成するためのヘルパー。
        Controller から呼び出す想定。
        """
        values = dict(values)
        values.setdefault("is_self_order", True)
        order = self.create(values)
        # 必要であればここで kitchen_ticket も作成しても良いが、
        # 一旦controller側で作る想定でもOK。
        return order

6. models/kitchen_ticket.py（キッチン伝票モデル）
# restaurant_self_order_kitchen/models/kitchen_ticket.py

from odoo import api, fields, models, _


class KitchenTicket(models.Model):
    _name = "restaurant.kitchen_ticket"
    _description = "Kitchen Ticket"
    _order = "create_date desc"

    name = fields.Char(
        string="Ticket No.",
        required=True,
        copy=False,
        default=lambda self: _("New"),
    )
    order_id = fields.Many2one(
        "sale.order",
        string="Sale Order",
        required=True,
        ondelete="cascade",
    )
    table_id = fields.Many2one(
        "pos.restaurant.table",
        string="Table",
        required=False,
        help="Table related to this ticket.",
    )
    state = fields.Selection(
        [
            ("new", "新規"),
            ("in_progress", "調理中"),
            ("done", "提供済"),
        ],
        string="Status",
        default="new",
        tracking=True,
    )
    line_ids = fields.One2many(
        "restaurant.kitchen_ticket_line",
        "ticket_id",
        string="Lines",
    )
    note = fields.Text(string="全体メモ")

    @api.model
    def create(self, vals):
        # name にシーケンスを割り当てる（必要なら ir.sequence を定義）
        if vals.get("name", _("New")) == _("New"):
            seq = self.env["ir.sequence"].next_by_code("restaurant.kitchen_ticket") or _("New")
            vals["name"] = seq
        return super().create(vals)


class KitchenTicketLine(models.Model):
    _name = "restaurant.kitchen_ticket_line"
    _description = "Kitchen Ticket Line"

    ticket_id = fields.Many2one(
        "restaurant.kitchen_ticket",
        string="Ticket",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        "product.product",
        string="メニュー",
        required=True,
    )
    qty = fields.Float(
        string="数量",
        default=1.0,
    )
    note = fields.Char(
        string="備考",
        help="辛さ、トッピング、抜き指定などのメモ。",
    )
    area = fields.Selection(
        [
            ("kitchen", "キッチン"),
            ("drink", "ドリンク"),
            ("dessert", "デザート"),
        ],
        string="担当エリア",
        default="kitchen",
    )


※ ir.sequence の定義は後ほど data/*.xml で追加できます。
ひとまず skeleton としてこのままでOK。

7. controllers/__init__.py
# restaurant_self_order_kitchen/controllers/__init__.py

from . import self_order

8. controllers/self_order.py（self order + kitchen screen のひな型）
# restaurant_self_order_kitchen/controllers/self_order.py

from odoo import http
from odoo.http import request


class SelfOrderController(http.Controller):
    """
    お客さんのスマホからの注文用 Controller と、
    厨房側の画面用 Controller のひな型。
    """

    # --- お客さん向け self order 画面 ---

    @http.route(["/self_order"], type="http", auth="public", website=True)
    def self_order_form(self, table=None, **kwargs):
        """
        QRコードからアクセスされる入口。
        /self_order?table=T001 などを想定。
        """
        # テーブルコードからテーブルを検索する例
        table_rec = None
        if table:
            table_rec = request.env["pos.restaurant.table"].sudo().search(
                [("name", "=", table)], limit=1
            )

        # 表示する商品（メニュー）を取得（とりあえず全商品にしておく）
        products = request.env["product.product"].sudo().search(
            [("sale_ok", "=", True)]
        )

        values = {
            "table_code": table,
            "table": table_rec,
            "products": products,
        }
        # QWeb テンプレート名は後で xml 側で定義
        return request.render(
            "restaurant_self_order_kitchen.self_order_page",
            values,
        )

    @http.route(
        ["/self_order/submit"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def self_order_submit(self, **post):
        """
        self order 画面の「注文する」から呼ばれる想定。
        post には product_id, qty, table_code などを含める。
        """
        # 1. テーブル情報
        table_code = post.get("table_code")
        table_rec = None
        if table_code:
            table_rec = request.env["pos.restaurant.table"].sudo().search(
                [("name", "=", table_code)], limit=1
            )

        # 2. ラインの組み立て（ここはPOSTの構造に合わせて後で実装）
        # 例：post から {product_id:qty} を取り出す
        order_lines = []
        for key, val in post.items():
            if key.startswith("product_"):
                try:
                    product_id = int(key.replace("product_", ""))
                    qty = float(val or 0)
                except Exception:
                    continue
                if qty <= 0:
                    continue
                order_lines.append((0, 0, {
                    "product_id": product_id,
                    "product_uom_qty": qty,
                    # price_unit は product のリスト価格に任せる or 明示的に指定
                }))

        # 3. Sale Order を作成
        so_vals = {
            "partner_id": request.website.user_id.partner_id.id,  # ゲスト的なパートナー
            "table_id": table_rec.id if table_rec else False,
            "is_self_order": True,
            "order_line": order_lines,
            "client_order_ref": table_code or "",
        }
        order = request.env["sale.order"].sudo().create_from_self_order(so_vals)

        # 4. Kitchen Ticket を作成
        ticket_vals = {
            "order_id": order.id,
            "table_id": table_rec.id if table_rec else False,
            "note": post.get("global_note") or "",
            "line_ids": [],
        }
        line_commands = []
        for line in order.order_line:
            line_commands.append((0, 0, {
                "product_id": line.product_id.id,
                "qty": line.product_uom_qty,
                "note": line.name,
                # area は product 側のカスタムフィールド等から決めても良い
                # "area": line.product_id.kitchen_area or "kitchen",
            }))
        ticket_vals["line_ids"] = line_commands

        request.env["restaurant.kitchen_ticket"].sudo().create(ticket_vals)

        # 5. 完了ページを表示
        return request.render(
            "restaurant_self_order_kitchen.self_order_thanks_page",
            {"order": order, "table": table_rec},
        )


class KitchenScreenController(http.Controller):
    """
    厨房側でキッチンチケットを一覧・更新するための Controller。
    """

    @http.route(
        ["/kitchen/screen"],
        type="http",
        auth="user",   # 社員アカウントでログインしている想定
        website=True,
    )
    def kitchen_screen(self, **kwargs):
        """
        新規・調理中のチケットを一覧表示する画面。
        """
        KitchenTicket = request.env["restaurant.kitchen_ticket"].sudo()
        tickets_new = KitchenTicket.search([("state", "=", "new")])
        tickets_in_progress = KitchenTicket.search([("state", "=", "in_progress")])

        values = {
            "tickets_new": tickets_new,
            "tickets_in_progress": tickets_in_progress,
        }
        return request.render(
            "restaurant_self_order_kitchen.kitchen_screen_page",
            values,
        )

    @http.route(
        ["/kitchen/ticket/set_state"],
        type="json",
        auth="user",
    )
    def set_ticket_state(self, ticket_id, state):
        """
        JS から呼んでステータスを変更する想定。
        例: new -> in_progress, in_progress -> done
        """
        ticket = request.env["restaurant.kitchen_ticket"].sudo().browse(int(ticket_id))
        if ticket.exists() and state in ["new", "in_progress", "done"]:
            ticket.state = state
        return {"result": "ok", "state": ticket.state if ticket else None}

9. view（XML）はざっくりこんなイメージで

ここは skeleton だけ置いておきます。あとで中身を書き足してOKです。

views/menu_items.xml
<!-- restaurant_self_order_kitchen/views/menu_items.xml -->
<odoo>
    <data>
        <!-- Kitchen Ticket 用メニュー -->
        <menuitem id="menu_restaurant_root"
                  name="Restaurant"
                  sequence="10"/>

        <menuitem id="menu_kitchen_ticket"
                  name="Kitchen Tickets"
                  parent="menu_restaurant_root"
                  action="action_kitchen_ticket_tree"/>

        <!-- action は kitchen_ticket_views.xml 側で定義 -->
    </data>
</odoo>

views/kitchen_ticket_views.xml
<!-- restaurant_self_order_kitchen/views/kitchen_ticket_views.xml -->
<odoo>
    <data>

        <record id="view_kitchen_ticket_tree" model="ir.ui.view">
            <field name="name">restaurant.kitchen_ticket.tree</field>
            <field name="model">restaurant.kitchen_ticket</field>
            <field name="arch" type="xml">
                <tree>
                    <field name="name"/>
                    <field name="table_id"/>
                    <field name="state"/>
                    <field name="create_date"/>
                </tree>
            </field>
        </record>

        <record id="view_kitchen_ticket_form" model="ir.ui.view">
            <field name="name">restaurant.kitchen_ticket.form</field>
            <field name="model">restaurant.kitchen_ticket</field>
            <field name="arch" type="xml">
                <form>
                    <sheet>
                        <group>
                            <field name="name" readonly="1"/>
                            <field name="order_id"/>
                            <field name="table_id"/>
                            <field name="state"/>
                            <field name="note"/>
                        </group>
                        <notebook>
                            <page string="Lines">
                                <field name="line_ids">
                                    <tree editable="bottom">
                                        <field name="product_id"/>
                                        <field name="qty"/>
                                        <field name="area"/>
                                        <field name="note"/>
                                    </tree>
                                </field>
                            </page>
                        </notebook>
                    </sheet>
                </form>
            </field>
        </record>

        <record id="action_kitchen_ticket_tree" model="ir.actions.act_window">
            <field name="name">Kitchen Tickets</field>
            <field name="res_model">restaurant.kitchen_ticket</field>
            <field name="view_mode">tree,form</field>
        </record>

    </data>
</odoo>

views/website_self_order_templates.xml
<!-- restaurant_self_order_kitchen/views/website_self_order_templates.xml -->
<odoo>
    <template id="self_order_page" name="Self Order Page" inherit_id="website.layout">
        <xpath expr="//main" position="inside">
            <section class="oe_structure">
                <div class="container">
                    <h1>セルフオーダー</h1>
                    <t t-if="table">
                        <p>テーブル: <t t-esc="table.name"/></p>
                    </t>
                    <!-- 簡易版：とりあえず product.id を hidden で投げるフォーム -->
                    <form action="/self_order/submit" method="post">
                        <input type="hidden" name="table_code" t-att-value="table_code"/>
                        <t t-foreach="products" t-as="p">
                            <div>
                                <span t-esc="p.display_name"/>
                                <input type="number"
                                       t-att-name="'product_%s' % p.id"
                                       min="0" step="1" value="0"/>
                            </div>
                        </t>
                        <div>
                            <label>全体メモ</label>
                            <textarea name="global_note"></textarea>
                        </div>
                        <button type="submit" class="btn btn-primary">注文する</button>
                    </form>
                </div>
            </section>
        </xpath>
    </template>

    <template id="self_order_thanks_page" name="Self Order Thanks Page" inherit_id="website.layout">
        <xpath expr="//main" position="inside">
            <section class="oe_structure">
                <div class="container">
                    <h1>ご注文ありがとうございました</h1>
                    <p>ご注文を受け付けました。</p>
                    <t t-if="table">
                        <p>テーブル: <t t-esc="table.name"/></p>
                    </t>
                </div>
            </section>
        </xpath>
    </template>

    <template id="kitchen_screen_page" name="Kitchen Screen Page" inherit_id="web.layout">
        <xpath expr="//main" position="inside">
            <section class="oe_structure">
                <div class="container">
                    <h1>Kitchen Screen</h1>
                    <div class="row">
                        <div class="col-6">
                            <h2>新規</h2>
                            <t t-foreach="tickets_new" t-as="tkt">
                                <div>
                                    <strong t-esc="tkt.name"/> -
                                    <span t-esc="tkt.table_id.name"/>
                                    <ul>
                                        <t t-foreach="tkt.line_ids" t-as="ln">
                                            <li>
                                                <t t-esc="ln.product_id.display_name"/> x
                                                <t t-esc="ln.qty"/>
                                            </li>
                                        </t>
                                    </ul>
                                </div>
                            </t>
                        </div>
                        <div class="col-6">
                            <h2>調理中</h2>
                            <t t-foreach="tickets_in_progress" t-as="tkt">
                                <div>
                                    <strong t-esc="tkt.name"/> -
                                    <span t-esc="tkt.table_id.name"/>
                                </div>
                            </t>
                        </div>
                    </div>
                </div>
            </section>
        </xpath>
    </template>
</odoo>

まとめ

ここまでで、

モジュール名

フォルダ構成

__manifest__.py

models（sale.order 継承 + kitchen_ticket / kitchen_ticket_line）

controllers（self order + kitchen screen のルート）

の「骨組み」はそろいました。