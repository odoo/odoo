/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import {
    SaleDetailsButton,
    handleSaleDetails,
} from "@point_of_sale/app/components/navbar/sale_details_button/sale_details_button";
import { DailySalesReportPopup } from "@pos_hr/app/components/popups/daily_sales_report_popup/daily_sales_report_popup";
import { patch } from "@web/core/utils/patch";
import { renderToElement } from "@web/core/utils/render";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { formatDateTime } from "@web/core/l10n/dates";

const { DateTime } = luxon;

async function printEmployeeSaleDetails(pos, hardwareProxy, employeeId) {
    const saleDetails = await pos.data.call(
        "report.pos_hr.single_employee_sales_report",
        "get_sale_details",
        [false, false, false, [pos.session.id], employeeId]
    );
    const report = renderToElement(
        "point_of_sale.SaleDetailsReport",
        Object.assign({}, saleDetails, {
            date: formatDateTime(DateTime.now()),
            pos: pos,
            formatCurrency: pos.env.utils.formatCurrency,
        })
    );
    return hardwareProxy.printer.printReceipt(report);
}

export async function handleSaleDetailsWithEmployees(pos, hardwareProxy, dialog) {
    const payload = await makeAwaitable(dialog, DailySalesReportPopup, {
        title: _t("Session Report"),
    });

    if (!payload) {
        return;
    }

    // Print global report
    const { successful } = await handleSaleDetails(pos, hardwareProxy, dialog);
    if (!successful) {
        return;
    }

    // Print employee reports
    if (payload.add_report_per_employee) {
        const employeeIds =
            (await pos.data.call("pos.session", "get_session_employee_ids", [[pos.session.id]])) ||
            [];

        for (let i = 0; i < employeeIds.length; i++) {
            const result = await printEmployeeSaleDetails(pos, hardwareProxy, employeeIds[i]);
            if (!result.successful) {
                const remaining = employeeIds.length - i - 1;
                dialog.add(AlertDialog, {
                    title: result.message.title,
                    body: remaining
                        ? _t("%(body)s\n\n%(count)s employee report(s) were not printed.", {
                              body: result.message.body,
                              count: remaining,
                          })
                        : result.message.body,
                });
                break;
            }
        }
    }
}

async function dispatchSaleDetails(pos, hardwareProxy, dialog, printDefault) {
    if (pos.config.module_pos_hr) {
        await handleSaleDetailsWithEmployees(pos, hardwareProxy, dialog);
    } else {
        await printDefault();
    }
}

patch(Navbar.prototype, {
    async showSaleDetails() {
        await dispatchSaleDetails(this.pos, this.hardwareProxy, this.dialog, () =>
            super.showSaleDetails()
        );
    },
});

patch(SaleDetailsButton.prototype, {
    async onClick() {
        await dispatchSaleDetails(this.pos, this.hardwareProxy, this.dialog, () => super.onClick());
    },
});
