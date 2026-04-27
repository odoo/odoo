/** @odoo-module **/

    import { _t } from "@web/core/l10n/translation";
    import { registry } from "@web/core/registry";
    import { patch } from "@web/core/utils/patch";
    import { markup } from "@odoo/owl";
    import { accountTourSteps } from "@account/js/tours/account";

    patch(accountTourSteps, {
        newInvoice() {
            return [
                {
                    trigger: "button[name=action_create_new]",
                    content: _t("Now, we'll create your first invoice (accountant)"),
                    run: "click",
                }
            ]
        },
    });


    registry.category("web_tour.tours").add('account_accountant_tour', {
            url: "/odoo",
            steps: () => [
            ...accountTourSteps.goToAccountMenu('Let’s automate your bills, bank transactions and accounting processes.'),
            // The tour will stop here if there is at least 1 vendor bill in the database.
            // While not ideal, it is ok, since that means the user obviously knows how to create a vendor bill...
            {
                trigger: 'a[name="action_create_vendor_bill"]',
                content: markup(_t('Create your first vendor bill.<br/><br/><i>Tip: If you don’t have one on hand, use our sample bill.</i>')),
                tooltipPosition: 'bottom',
                run: "click",
            }, {
                trigger: 'button.btn-primary[name="action_post"]',
                content: _t('After the data extraction, check and validate the bill. If no vendor has been found, add one before validating.'),
                tooltipPosition: 'bottom',
                run: "click",
            }, {
                trigger: '.dropdown-item[data-menu-xmlid="account.menu_board_journal_1"]',
                content: _t('Let’s go back to the dashboard.'),
                tooltipPosition: 'bottom',
                run: "click",
            }, {
                trigger: 'a[name="open_action"] span:contains(bank)',
                content: _t('Connect your bank and get your latest transactions.'),
                tooltipPosition: 'bottom',
                run: "click",
            }, {
                trigger: 'button.o-kanban-button-new',
                content: _t('Create a new transaction.'),
                run: "click",
            }, {
                trigger: "div[name=amount] div input[id=amount_0]",
                content: _t("Set an amount."),
                tooltipPosition: "bottom",
                run: "edit -19250.00",
            }, {
                trigger: "div[name=payment_ref] input[id=payment_ref_0]",
                content: _t("Set the payment reference."),
                tooltipPosition: "bottom",
                run: "edit Payment Acme Corporation",
            }, {
                trigger: "button.o_kanban_edit",
                content: _t("Confirm the transaction."),
                tooltipPosition: "bottom",
                run: "click",
            }, {
                trigger: '.o_kanban_renderer:not(:has(.o_bank_rec_quick_create)) .o_bank_rec_st_line:not(.o_bank_rec_selected_st_line)',
                content: _t('Click on a fetched bank transaction to start the reconciliation process.'),
                run: "click",
            }, {
                isActive: ['auto'],
                trigger: '.dropdown-item[data-menu-xmlid="account.menu_board_journal_1"]',
                content: _t('Let’s go back to the dashboard.'),
                run: "click",
            },
        ]
    });
