#!/bin/bash
# Script to test Polish translations in HRMS modules

echo "============================================"
echo "HRMS Modules Translation Test"
echo "============================================"
echo ""

# Check if translation files exist and are valid
echo "Checking translation files..."
echo ""

for module in ohrms_salary_advance ohrms_loan ohrms_loan_accounting ohrms_core oh_employee_documents_expiry oh_employee_creation_from_user hrms_dashboard history_employee
do
    echo "=== $module ==="
    if [ -f "addons/$module/i18n/pl.po" ]; then
        # Count translated strings
        translated=$(grep -c "^msgstr \"[^\"]\+\"" addons/$module/i18n/pl.po)
        total=$(grep -c "^msgid \"" addons/$module/i18n/pl.po)

        # Validate PO file format
        if command -v msgfmt &> /dev/null; then
            if msgfmt -c addons/$module/i18n/pl.po 2>&1 | grep -q "translated messages"; then
                echo "  ✓ Polish translation file exists and is valid"
            else
                echo "  ⚠ Polish translation file has format errors"
            fi
        else
            echo "  ✓ Polish translation file exists"
        fi

        echo "    Translated strings: $translated / $total"
    else
        echo "  ✗ No Polish translation file found"
    fi
    echo ""
done

echo "============================================"
echo "To apply these translations:"
echo "============================================"
echo "1. Update all HRMS modules:"
echo "   ./odoo-bin -d your_database -u ohrms_salary_advance,ohrms_loan,ohrms_loan_accounting,ohrms_core,oh_employee_documents_expiry,oh_employee_creation_from_user,hrms_dashboard,history_employee --stop-after-init"
echo ""
echo "2. In Odoo UI:"
echo "   Settings > Translations > Load a Translation"
echo "   Select 'Polish / Polski (pl)' and click Load"
echo ""
echo "3. Clear browser cache (Ctrl+Shift+Delete)"
echo ""
echo "4. Change user language to Polish:"
echo "   User avatar > My Profile > Language > Polish"
echo ""
echo "5. Log out and log back in"
echo "============================================"
