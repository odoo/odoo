import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

const EPSON_ERRORS = {
    DeviceNotFound: _t(
        "Check the printer configuration for the 'Device ID' setting.\nIt should be set to: 'local_printer'"
    ),
    EPTR_AUTOMATICAL: _t(
        "Continuous printing of high-density printing caused a printing error. Please retry later"
    ),
    EPTR_COVER_OPEN: _t("Printer cover is open, please close it before printing"),
    EPTR_CUTTER: _t("The cutter has a foreign matter, please check the cutter mechanism"),
    EPTR_MECHANICAL: _t("Mechanical error, please check the printer"),
    EPTR_REC_EMPTY: _t("The paper is empty, please load paper into the printer"),
    EPTR_UNRECOVERABLE: _t("Low voltage unrecoverable error occured, please check the printer"),
    EX_BADPORT: _t("The device is not connected, please check the printer power / connection"),
    EX_TIMEOUT: _t("Timeout occured, please try again"),
};

export class TestEPos extends Component {
    static template = `point_of_sale.TestEPosButton`;
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        super.setup();
        this.notification = useService("notification");
    }

    _getReceipt() {
        return `
        <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
            <s:Body>
                <epos-print xmlns="http://www.epson-pos.com/schemas/2011/03/epos-print">
                    <feed line="1" />
                    <text align="center">This is a test receipt&#10;</text>
                    <feed line="3" />
                    <cut type="feed" />
                </epos-print>
            </s:Body>
        </s:Envelope>`;
    }

    async onClick() {
        try {
            const data = this.props.record.data;
            const printer_ip =
                data.epson_printer_ip !== undefined
                    ? data.epson_printer_ip
                    : data.pos_epson_printer_ip;
            if (!printer_ip) {
                this.notification.add(
                    _t("Please configure a valid ePoS url in order to test the printer"),
                    { type: "danger" }
                );
                return;
            }
            const url = window.location.protocol + "//" + printer_ip;
            this.address = url + "/cgi-bin/epos/service.cgi?devid=local_printer";
            // Parse response
            const result = await fetch(this.address, {
                method: "POST",
                body: this._getReceipt(),
                signal: AbortSignal.timeout(15000),
            });
            const body = await result.text();
            const parser = new DOMParser();
            const parsedBody = parser.parseFromString(body, "application/xml");
            const response = parsedBody.querySelector("response");
            const success = response.getAttribute("success") === "true";
            const errorCode = response.getAttribute("code");
            if (!success || errorCode !== "") {
                const errorMessage =
                    EPSON_ERRORS[errorCode] ||
                    _t("Failed to print a test receipt. Check your printer.");
                this.notification.add(errorMessage, { type: "warning" });
            } else {
                this.notification.add(_t("Succesfully printed a test receipt"), { type: "info" });
            }
        } catch {
            this.notification.add(
                _t(
                    "Failed to reach the printer. Check the configured url. Make sure that the printer is online and you are on the same network."
                ),
                { type: "danger" }
            );
        }
    }
}

export const TestEPosWidget = {
    component: TestEPos,
};
registry.category("view_widgets").add("point_of_sale_test_epos", TestEPosWidget);
