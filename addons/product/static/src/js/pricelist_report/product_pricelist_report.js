/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, markup, onRendered, onWillStart, useState } from "@odoo/owl";
import { Layout } from "@web/search/layout";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useSetupAction } from "@web/webclient/actions/action_hook";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";


function sendCustomNotification(type, message) {
    return {
        type: "ir.actions.client",
        tag: "display_notification",
        params: {
            "type": type,
            "message": message
        },
    }
}

export class ProductPricelistReport extends Component {
    static props = {
        action: { type: Object },
        "*": true,
    };
    static components = { Layout };
    static template = "product.ProductPricelistReport";

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.dialog = useService("dialog");

        this.MAX_QTY = 5;
        const pastState = this.props.state || {};

        this.activeIds = this.props.action.context.active_ids;
        this.activeModel = this.props.action.context.active_model;

        this.state = useState({
            displayPricelistTitle: pastState.displayPricelistTitle || false,
            html: "",
            pricelists: [],
            _quantities: pastState.quantities || [1, 5, 10],
            selectedPricelist: {},
        });

        onWillStart(async () => {
            this.state.pricelists = await this.getPricelists()
            this.state.selectedPricelist = pastState.selectedPricelist || this.pricelists[0];

            this.renderHtml();
        });

        onRendered(() => {
            this.env.config.setDisplayName(_t("Pricelist Report"));
        });

        /*
        When following the link of a product and coming back we need to keep the 
        precedent state:
            - if the pricelist was being showed
            - wich pricelist is selected at the moment
            - which quantities
        */
        useSetupAction({
            getLocalState: () => {
                return {
                    displayPricelistTitle: this.displayPricelistTitle,
                    quantities: this.quantities,
                    selectedPricelist: this.selectedPricelist,
              };
            },
        });
    }

    // getters and setters

    get displayPricelistTitle() {
        return this.state.displayPricelistTitle;
    }

    get html() {
        return this.state.html;
    }

    get pricelists() {
        return this.state.pricelists;
    }

    get quantities() {
        return this.state._quantities;
    }

    set quantities(value) {
        this.state._quantities = value;
    }

    get reportParams() {
        return {
            active_model: this.activeModel || 'product.template',
            active_ids: this.activeIds || [],
            display_pricelist_title: this.displayPricelistTitle || '',
            pricelist_id: this.selectedPricelist.id || '',
            quantities: this.quantities || [1],
        };
    }

    get selectedPricelist() {
        return this.state.selectedPricelist;
    }

    // orm calls

    getPricelists() {
        return this.orm.searchRead("product.pricelist", [], ["id", "name"]);
    }

    async renderHtml() {
        let html = await this.orm.call(
            "report.product.report_pricelist", "get_html", [], {data: this.reportParams}
        );
        this.state.html = markup(html);
    }

    // events

    async onClickAddQty(ev) {
        ev.preventDefault(); // avoid automatic reloading of the page

        if (this.quantities.length >= this.MAX_QTY) {
            let message = _t(
                "At most %s quantities can be displayed simultaneously. Remove a selected quantity to add others.",
                this.MAX_QTY
            );
            await this.action.doAction(sendCustomNotification("warning", message));
            return;
        }

        const qty = parseInt($("input.add-quantity-input")[0].value);
        if (qty && qty > 0) {
            // Check qty already exist.
            if (this.quantities.indexOf(qty) === -1) {
                this.quantities.push(qty);
                this.quantities = this.quantities.sort((a, b) => a - b);
                this.renderHtml();
            } else {
                let message = _t("Quantity already present (%s).", qty);
                await this.action.doAction(sendCustomNotification("info", message));
            }
        } else {
            await this.action.doAction(
                sendCustomNotification("info", _t("Please enter a positive whole number."))
            );
        }
    }

    onClickLink(ev) {
        ev.preventDefault();

        let classes = ev.target.getAttribute("class", "");
        let resModel = ev.target.getAttribute("data-model", "");
        let resId = ev.target.getAttribute("data-res-id", "");

        if (classes && classes.includes("o_action") && resModel && resId) {
            this.action.doAction({
                type: 'ir.actions.act_window',
                res_model: resModel,
                res_id: parseInt(resId),
                views: [[false, 'form']],
                target: 'self',
            });
        }
    }

    onClickPrint() {
        const selectedFormat = document.getElementById('formats').value;
        if (selectedFormat === 'pdf') {
            this.export_pdf();
        } else if (selectedFormat === 'csv') {
            this.export_csv();
        } else if (selectedFormat === 'xlsx') {
            this.export_xlsx();
        }
    }

    export_pdf() {
        this.action.doAction({
            type: 'ir.actions.report',
            report_type: 'qweb-pdf',
            report_name: 'product.report_pricelist',
            report_file: 'product.report_pricelist',
            data: this.reportParams,
        });
    }

    async export_csv() {
        // Fetch the product data from the server
        const csvData = await this.orm.call(
            "report.product.report_pricelist", "export_csv", [], { data: this.reportParams }
        );

        // Prepare CSV content
        const csvContent = "data:text/csv;charset=utf-8," + csvData;

        // Encode URI
        const encodedUri = encodeURI(csvContent);

        // Create and click the download link
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", "products.csv");
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    async export_xlsx() {
        // Fetch the product data from the server
        const xlsData = await this.orm.call(
            "report.product.report_pricelist", "export_xls", [], { data: this.reportParams }
        );

        // Convert base64 string to binary
        const binaryString = atob(xlsData);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }

        // Create a Blob with the correct MIME type
        const blob = new Blob([bytes.buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
        // Create and click the download link
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = "pricelist.xlsx";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    onClickAllProducts() {
        this.dialog.add(SelectCreateDialog, {
            resModel: this.activeModel || 'product.template',
            title: _t("All Products"),
            noCreate: true,
            onSelected: async (resIds) => {
                resIds.forEach(id => {
                    if (!this.activeIds.includes(id)) {
                        this.activeIds.push(id);
                    }
                });
                this.renderHtml();
            },
        });
    }

    async onClickRemoveQty(ev) {
        if (this.quantities.length <= 1) {
            await this.action.doAction(
                sendCustomNotification("warning", _t("You must leave at least one quantity."))
            );
            return;
        }

        const qty = parseInt(ev.srcElement.parentElement.childNodes[0].data);
        this.quantities = this.quantities.filter(q => q !== qty);
        this.renderHtml();
    }

    onSelectPricelist(ev) {
        this.state.selectedPricelist = this.pricelists.filter(pricelist => 
            pricelist.id === parseInt(ev.target.value)
        )[0];

        this.renderHtml();
    }

    onToggleDisplayPricelist() {
        this.state.displayPricelistTitle = !this.displayPricelistTitle;
        this.renderHtml();
    }
}

registry.category("actions").add("generate_pricelist_report", ProductPricelistReport);
