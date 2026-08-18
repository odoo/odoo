import os
import asyncio
import xmlrpc.client
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

# 1. إنشاء خادم MCP الأساسي
app = Server("Odoo Integration Server")

# 2. قراءة متغيرات البيئة
ODOO_URL = os.getenv("ODOO_URL", "http://localhost:8069")
ODOO_DB = os.getenv("ODOO_DB", "odoo")
ODOO_USER = os.getenv("ODOO_USER", "odoo@odoo.odoo")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "odoo")


def _get_odoo_client():
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    if not uid:
        raise ValueError("فشل الاتصال بـ Odoo: بيانات الاعتماد غير صحيحة.")
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    return uid, models


# 3. تعريف الأدوات المتاحة للذكاء الاصطناعي
@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="test_odoo_connection",
            description="اختبار الاتصال بسيرفر Odoo",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="search_invoices",
            description="البحث عن الفواتير في Odoo بناءً على حالتها",
            inputSchema={
                "type": "object",
                "properties": {
                    "state": {
                        "type": "string",
                        "description": "حالة الفاتورة (draft, posted, cancel)",
                        "default": "draft",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "عدد الفواتير المطلوبة",
                        "default": 5,
                    },
                },
            },
        ),
    ]


# 4. تنفيذ الأدوات عند الاستدعاء
@app.call_tool()
async def call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    arguments = arguments or {}

    if name == "test_odoo_connection":
        try:
            common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
            version = common.version()
            msg = f"تم الاتصال بنجاح بـ Odoo! الإصدار: {version.get('server_version')}"
        except Exception as e:
            msg = f"فشل الاتصال بـ Odoo: {str(e)}"
        return [types.TextContent(type="text", text=msg)]

    elif name == "search_invoices":
        state = arguments.get("state", "draft")
        limit = arguments.get("limit", 5)
        try:
            uid, models = _get_odoo_client()
            domain = [
                ("move_type", "in", ["in_invoice", "out_invoice"]),
                ("state", "=", state),
            ]
            invoice_ids = models.execute_kw(
                ODOO_DB,
                uid,
                ODOO_PASSWORD,
                "account.move",
                "search",
                [domain],
                {"limit": limit},
            )

            if not invoice_ids:
                return [
                    types.TextContent(
                        type="text", text="لا يوجد فواتير بهاتين الحالتين."
                    )
                ]

            invoices = models.execute_kw(
                ODOO_DB,
                uid,
                ODOO_PASSWORD,
                "account.move",
                "read",
                [invoice_ids],
                {
                    "fields": [
                        "id",
                        "name",
                        "partner_id",
                        "amount_total",
                        "state",
                    ]
                },
            )
            return [types.TextContent(type="text", text=str(invoices))]
        except Exception as e:
            return [types.TextContent(type="text", text=f"خطأ: {str(e)}")]

    raise ValueError(f"الأداة غير معروفة: {name}")


# 5. تشغيل السيرفر عبر stdio
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
