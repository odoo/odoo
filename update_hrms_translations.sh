#!/bin/bash
# Script to update all HRMS modules and load Polish translations

echo "Updating all HRMS modules with Polish translations..."

# List of all HRMS modules
MODULES="ohrms_salary_advance,ohrms_loan,ohrms_loan_accounting,ohrms_core,oh_employee_documents_expiry,oh_employee_creation_from_user,hrms_dashboard,history_employee"

# Update modules (replace 'your_database' with your actual database name)
./odoo-bin -d your_database -u $MODULES --stop-after-init

echo "Done! All HRMS modules have been updated."
echo ""
echo "Next steps:"
echo "1. Start your Odoo server normally"
echo "2. Go to Settings > Translations > Load a Translation"
echo "3. Select Polish (pl / Polski)"
echo "4. Click 'Load'"
echo "5. Clear your browser cache (Ctrl+Shift+Delete)"
echo "6. Refresh the page"
echo "7. Change your user's language preference to Polish"
