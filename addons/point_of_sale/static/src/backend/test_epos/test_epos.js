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
        this.orm = useService("orm");
    }

    _getReceipt(printer_name) {
        return `
        <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
            <s:Body>
                <epos-print xmlns="http://www.epson-pos.com/schemas/2011/03/epos-print">
                    <feed line="1" />
                    <text align="center">Test print for printer ${printer_name}&#10;</text>
                    <feed line="3" />
                    <cut type="feed" />
                </epos-print>
            </s:Body>
        </s:Envelope>`;
    }

    async getPrinterDataEPos(printer_id) {
        if (printer_id) {
            const response = await this.orm.read(
                "pos.printer",
                [printer_id],
                ["epson_printer_ip", "name", "printer_type"]
            );
            return response[0];
        } else {
            const data = this.props.record.data;
            return {
                id: this.props.record.resId || null,
                name: data.name,
                epson_printer_ip: data.epson_printer_ip,
                printer_type: data.printer_type,
            };
        }
    }

    async _testSinglePrinter() {
        try {
            await this._printTo();
        } catch {
            this.notification.add(
                _t("You need to add an IP address or choose an IoT device before testing."),
                {
                    type: "warning",
                }
            );
            return;
        }
    }

    async _testAllPrinters() {
        const config_id = this.props.record.resId;

        if (!config_id) {
            this.notification.add(_t("Save the configuration before testing"), {
                type: "warning",
            });
            return;
        }
        const config_data = await this.orm.read("pos.config", [config_id], ["receipt_printer_ids"]);

        const printers_id = config_data[0].receipt_printer_ids;

        if (!printers_id.length) {
            this.notification.add(_t("No receipt printers configured for this POS."), {
                type: "warning",
            });
            return;
        }

        for (const p_id of printers_id) {
            await this._printTo(p_id);
        }
    }

    async _printTo(printer_id = null) {
        const printer = await this.getPrinterDataEPos(printer_id);
        if (printer.printer_type === "epson_epos") {
            try {
                const url = window.location.protocol + "//" + printer.epson_printer_ip;
                const address = url + "/cgi-bin/epos/service.cgi?devid=local_printer";

                const result = await fetch(address, {
                    method: "POST",
                    body: this._getReceipt(printer.name),
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
                    this.notification.add(
                        `${printer.name} (${printer.epson_printer_ip}): ${errorMessage}`,
                        {
                            type: "warning",
                        }
                    );
                }
            } catch {
                this.notification.add(
                    `${printer.name} (${printer.epson_printer_ip}): ${_t(
                        "Cannot reach the printer."
                    )}`,
                    { type: "danger" }
                );
            }
        }
    }

    async onClick() {
        const model = this.props.record.resModel;
        if (model === "pos.printer") {
            await this._testSinglePrinter();
        } else if (model === "pos.config") {
            await this._testAllPrinters();
        }
    }
}

export const TestEPosWidget = {
    component: TestEPos,
};
registry.category("view_widgets").add("point_of_sale_test_epos", TestEPosWidget);
