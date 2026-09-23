/** @odoo-module native */
import { Component, markup, onWillStart, useRef, useState } from "@odoo/owl";
import { useSetupAction } from "@web/core/action_hook";
import { download } from "@web/core/network";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { KeepLast } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { SelectCreateDialog } from "@web/views/view_dialogs";
import { standardActionServiceProps } from "@web/webclient/actions";

export class ProductPricelistReport extends Component {
    static props = { ...standardActionServiceProps };
    static components = { Layout };
    static template = "product.ProductPricelistReport";

    static MAX_QTY = 5;

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.notification = useService("notification");

        // Serialize report renders so a slow earlier request can't overwrite
        // the HTML of a later pricelist/quantity selection.
        this.renderKeepLast = new KeepLast();
        this.qtyInputRef = useRef("qtyInput");
        this.formatRef = useRef("format");

        const pastState = this.props.state || {};
        const activeModel =
            pastState.activeModel || this.props.action.context.active_model;
        const noProducts = activeModel === "product.pricelist";

        this.activeModel = noProducts ? "product.template" : activeModel;
        this.defaultPricelistId = noProducts
            ? this.props.action.context.active_id
            : false;

        this.state = useState({
            activeIds: noProducts
                ? []
                : pastState.activeIds || this.props.action.context.active_ids || [],
            displayPricelistTitle: pastState.displayPricelistTitle || false,
            html: "",
            noProducts,
            pricelists: [],
            quantities: pastState.quantities || [1, 5, 10],
            selectedPricelist: {},
        });

        onWillStart(async () => {
            this.state.pricelists = await this.getPricelists();
            this.state.selectedPricelist =
                (this.defaultPricelistId &&
                    this.pricelists.find((p) => p.id === this.defaultPricelistId)) ||
                (!this.defaultPricelistId && pastState.selectedPricelist) ||
                this.pricelists[0] ||
                {};
            if (this.noProducts) {
                this.onClickAddProducts();
            }
            await this.renderHtml();
        });

        this.env.config.setDisplayName(_t("Pricelist Report"));

        /*
        When following the link of a product and coming back we need to keep the
        precedent state:
            - if the pricelist was being showed
            - wich pricelist is selected at the moment
            - which quantities
        */
        useSetupAction({
            getLocalState: () => ({
                displayPricelistTitle: this.displayPricelistTitle,
                quantities: this.quantities,
                selectedPricelist: this.selectedPricelist,
                activeModel: this.activeModel,
                activeIds: this.activeIds,
            }),
        });
    }

    // getters

    get activeIds() {
        return this.state.activeIds;
    }

    get displayPricelistTitle() {
        return this.state.displayPricelistTitle;
    }

    get html() {
        return this.state.html;
    }

    get noProducts() {
        return this.state.noProducts;
    }

    get pricelists() {
        return this.state.pricelists;
    }

    get quantities() {
        return this.state.quantities;
    }

    get reportParams() {
        return {
            active_model: this.activeModel || "product.template",
            active_ids: this.activeIds,
            display_pricelist_title: this.displayPricelistTitle,
            pricelist_id: this.selectedPricelist.id || "",
            quantities: this.quantities.length ? this.quantities : [1],
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
        if (this.noProducts) {
            // do not make an rpc to get empty report data
            this.state.html = "";
            return;
        }
        const html = await this.renderKeepLast.add(
            this.orm.call("report.product.report_pricelist", "get_html", [], {
                data: this.reportParams,
            }),
        );
        this.state.html = markup(html);
    }

    // events

    onClickAddQty(ev) {
        ev.preventDefault(); // avoid automatic reloading of the page

        if (this.quantities.length >= this.constructor.MAX_QTY) {
            this.notification.add(
                _t(
                    "At most %s quantities can be displayed simultaneously. Remove a selected quantity to add others.",
                    this.constructor.MAX_QTY,
                ),
                { type: "warning" },
            );
            return;
        }

        const qty = parseInt(this.qtyInputRef.el?.value, 10);
        if (!Number.isInteger(qty) || qty <= 0) {
            this.notification.add(_t("Please enter a positive whole number."), {
                type: "info",
            });
            return;
        }
        if (this.quantities.includes(qty)) {
            this.notification.add(_t("Quantity already present (%s).", qty), {
                type: "info",
            });
            return;
        }
        this.state.quantities = [...this.quantities, qty].sort((a, b) => a - b);
        this.renderHtml();
    }

    onClickLink(ev) {
        ev.preventDefault();

        const parent = ev.target.parentElement;
        const classes = parent.getAttribute("class");
        const resModel = parent.getAttribute("data-model");
        const resId = parent.getAttribute("data-res-id");

        if (classes && classes.includes("o_action") && resModel && resId) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: resModel,
                res_id: parseInt(resId, 10),
                views: [[false, "form"]],
                target: "self",
            });
        }
    }

    async onClickPrint() {
        if (this.noProducts) {
            this.notification.add(_t("Please select some products first."), {
                type: "warning",
            });
            return;
        }
        const selectedFormat = this.formatRef.el?.value;
        if (selectedFormat === "pdf") {
            this.exportPdf();
        } else {
            await this.exportPricelist(selectedFormat);
        }
    }

    exportPdf() {
        this.action.doAction({
            type: "ir.actions.report",
            report_type: "qweb-pdf",
            report_name: "product.report_pricelist",
            report_file: "product.report_pricelist",
            data: this.reportParams,
        });
    }

    async exportPricelist(format) {
        try {
            await download({
                url: `/product/export/pricelist/`,
                data: {
                    report_data: JSON.stringify(this.reportParams),
                    export_format: format,
                },
            });
        } catch (error) {
            console.error(`Error exporting ${format.toUpperCase()} file:`, error);
            this.notification.add(_t("Error exporting file. Please try again."), {
                type: "danger",
            });
        }
    }

    onClickAddProducts() {
        this.dialog.add(SelectCreateDialog, {
            resModel: this.activeModel || "product.template",
            title: _t("Add Products to pricelist report"),
            noCreate: true,
            onSelected: async (resIds) => {
                const added = resIds.filter((id) => !this.activeIds.includes(id));
                if (added.length) {
                    this.state.activeIds = [...this.activeIds, ...added];
                }
                this.state.noProducts = false;
                await this.renderHtml();
            },
        });
    }

    onClickRemoveQty(qty) {
        if (this.quantities.length <= 1) {
            this.notification.add(_t("You must leave at least one quantity."), {
                type: "warning",
            });
            return;
        }
        this.state.quantities = this.quantities.filter((q) => q !== qty);
        this.renderHtml();
    }

    onSelectPricelist(ev) {
        const id = parseInt(ev.target.value, 10);
        this.state.selectedPricelist =
            this.pricelists.find((pricelist) => pricelist.id === id) || {};
        this.renderHtml();
    }

    onToggleDisplayPricelist() {
        this.state.displayPricelistTitle = !this.displayPricelistTitle;
        this.renderHtml();
    }
}

registry.category("actions").add("generate_pricelist_report", ProductPricelistReport);
