import sys
sys.path.insert(0, r"C:\Odoo\odoo")
import odoo
from odoo.modules.registry import Registry
from odoo import api, SUPERUSER_ID

config_file = r"C:\Odoo\odoo\odoo.conf"
odoo.tools.config.parse_config(["-c", config_file])

registry = Registry("odoo")
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Test 1: Render Fee Invoice PDF
    fee_report = env.ref("school_management.action_report_university_fee_invoice")
    fee = env['university.fee'].browse(1209)
    print(f"Rendering Fee Invoice: {fee.name} for {fee.student_id.name}")
    
    html_inv = fee_report._render_qweb_html("school_management.action_report_university_fee_invoice", [fee.id])[0].decode("utf-8")
    print(f"HTML Invoice rendered, size: {len(html_inv)} characters")
    
    pdf_inv, _ = fee_report._render_qweb_pdf("school_management.action_report_university_fee_invoice", [fee.id])
    print(f"PDF Invoice rendered, size: {len(pdf_inv)} bytes")
    with open("scratch/invoice_1209.pdf", "wb") as f:
        f.write(pdf_inv)
        
    # Test 2: Render Draft Fee Invoice
    draft_fee = env['university.fee'].search([('state', '=', 'draft')], limit=1)
    if draft_fee:
        pdf_draft, _ = fee_report._render_qweb_pdf("school_management.action_report_university_fee_invoice", [draft_fee.id])
        print(f"Draft PDF Invoice rendered ({draft_fee.name}), size: {len(pdf_draft)} bytes")
        with open("scratch/invoice_draft.pdf", "wb") as f:
            f.write(pdf_draft)
            
    # Test 3: Render Payment Receipt PDF
    receipt_report = env.ref("school_management.action_report_university_payment_receipt")
    payment = env['university.payment'].search([('fee_id', '=', 1209)], limit=1) or env['university.payment'].search([], limit=1)
    if payment:
        print(f"Rendering Payment Receipt: {payment.name}")
        pdf_receipt, _ = receipt_report._render_qweb_pdf("school_management.action_report_university_payment_receipt", [payment.id])
        print(f"PDF Receipt rendered, size: {len(pdf_receipt)} bytes")
        with open("scratch/receipt_sample.pdf", "wb") as f:
            f.write(pdf_receipt)

    print("ALL INVOICE & RECEIPT REPORTS RENDERED CLEANLY!")
