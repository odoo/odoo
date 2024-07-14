/** @odoo-module **/

    import { _t } from "@web/core/l10n/translation";
    import { registry } from "@web/core/registry";
    import { stepUtils } from "@web_tour/tour_service/tour_utils";
    import { patch } from "@web/core/utils/patch";
    import { markup } from "@odoo/owl";

    // Update the invoicing tour as the menu items have changed, but we want the test to still work
    patch(registry.category("web_tour.tours").get("account_tour"), {
        steps() {
            const originalSteps = super.steps();
            originalSteps.splice(0, 3,
                ...stepUtils
                    .goToAppSteps("account_accountant.menu_accounting", _t("Go to invoicing"))
                    .map((step) => Object.assign(step, { auto: true })),
                {
                    trigger: 'button[data-menu-xmlid="account.menu_finance_receivables"]',
                    content: _t('Go to invoicing'),
                    auto: true,
                }, {
                    trigger: '.dropdown-item[data-menu-xmlid="account.menu_action_move_out_invoice_type"]',
                    content: _t('Go to invoicing'),
                    auto: true,
                });
            return originalSteps;
        }
    });

    registry.category("web_tour.tours").add('account_accountant_tour', {
            rainbowManMessage: function({ isTourConsumed }) {
                var message = markup(_t('<strong><b>Good job!</b> You went through all steps of this tour.</strong>'));
                if (!isTourConsumed('account_tour')) {
                    message += markup(_t('<br>See how to manage your customer invoices in the <b>Customers/Invoices</b> menu'));
                }
                return markup(message);
            },
            url: "/web",
            sequence: 50,
            steps: () => [
            ...stepUtils.goToAppSteps('account_accountant.menu_accounting', _t('Let’s automate your bills, bank transactions and accounting processes.')),
            // The tour will stop here if there is at least 1 vendor bill in the database.
            // While not ideal, it is ok, since that means the user obviously knows how to create a vendor bill...
            {
                trigger: 'button.btn-primary[name="action_create_vendor_bill"]',
                content: markup(_t('Create your first vendor bill.<br/><br/><i>Tip: If you don’t have one on hand, use our sample bill.</i>')),
                position: 'bottom',
            }, {
                trigger: 'button[name="apply"]',
                content: markup(_t('Great! Let’s continue.<br/><br/><i>Tip: If you choose to upload your bill, don’t forget to attach it.</i>')),
                position: 'top',
            }, {
                trigger: '.o_data_cell',
                extra_trigger: 'tr:not(.o_sample_data_disabled)>td:has(div[name="state"])',
                content: _t('Let’s see how a bill looks like in form view.'),
                position: 'bottom',
                skip_trigger: 'button.btn-primary[name="action_post"]',
            }, {
                trigger: 'button.btn-primary[name="action_post"]',
                content: _t('After the data extraction, check and validate the bill. If no vendor has been found, add one before validating.'),
                position: 'bottom',
            }, {
                trigger: '.dropdown-item[data-menu-xmlid="account.menu_board_journal_1"]',
                extra_trigger: 'button[data-value="posted"].btn',
                content: _t('Let’s go back to the dashboard.'),
                position: 'bottom',
            }, {
                trigger: 'a[data-method="action_open_step_bank_account"].o_onboarding_step_action',
                content: _t('Connect your bank and get your latest transactions.'),
                position: 'bottom',
                run: function () {
                    // Close the modal
                    // We can't test bank sync in the tour
                    $('button[name="action_open_reconcile"]').click();
                }
            }, {
                trigger: '.o_bank_rec_st_line:not(.o_bank_rec_selected_st_line)',
                content: _t('Click on a fetched bank transaction to start the reconciliation process.'),
            }
        ]
    });
