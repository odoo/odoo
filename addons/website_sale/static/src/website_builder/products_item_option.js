import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { onWillStart, onMounted, useState, useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class ProductsItemOption extends BaseOptionComponent {
    static template = "website_sale.ProductsItemOptionPlugin";
    static dependencies = ["productsItemOptionPlugin"];
    static selector = "#products_grid .oe_product";
    static title = _t("Product");
    static groups = ["website.group_website_designer"];
    static editableOnly = false;

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.tableRef = useRef("table");

        const { loadInfo, getItemSize, getCount } = this.dependencies.productsItemOptionPlugin;

        this.state = useState({
            itemSize: getItemSize(),
            count: getCount(),
        });

        this.productsGridTableEl = this.env.getEditingElement().closest(".o_wsale_products_grid_table");

        this.domState = useDomState(() => {

            // If /shop page layout is list, do not display Size option
            const displaySizeOption = !this.productsGridTableEl?.classList.contains("o_wsale_products_opt_layout_list");

            if(displaySizeOption && this.state.itemSize) {
                this.addClassToTableCells(this.state.itemSize.x, this.state.itemSize.y, "selected");
            }

            return {
                displaySizeOption,
            }
        });

        onWillStart(async () => {
            this.defaultSort = await loadInfo();

            // need to display "re-order" option only if shop_default_sort is 'website_sequence asc'
            this.displayReOrder = this.defaultSort[0].shop_default_sort === "website_sequence asc";
            const pprValue = this.productsGridTableEl.style.getPropertyValue('--o-wsale-ppr').trim();
            this.maxWidth = parseInt(pprValue) || 5;
        });

        onMounted(() => {
            if (this.domState.displaySizeOption) {
                this.addClassToTableCells(this.state.itemSize.x, this.state.itemSize.y, "selected");
            }
        });
    }

    addClassToTableCells(x, y, className) {
        const table = this.tableRef.el;

        // By default, this.domState.displaySizeOption is undefined, so the table is not displayed
        // We need to check if the table is visible before adding classes to the cells
        if(!table) { return; }

        const rows = table.rows;

        for (let row = 0; row < y; row++) {
            const cells = rows[row].cells;
            for (let col = 0; col < x; col++) {
                cells[col].classList.add(className);
            }
        }
    }

    _onTableMouseEnter(ev) {
        ev.currentTarget.classList.add("oe_hover");
    }

    _onTableMouseLeave(ev) {
        ev.currentTarget.classList.remove("oe_hover");
    }

    _onTableCellMouseOver(i, j) {
        const allCells = this.tableRef.el.querySelectorAll("td.select");

        for (const cell of allCells) {
            cell.classList.remove("select");
        }

        this.addClassToTableCells(j + 1, i + 1, "select");
    }

    _onTableCellMouseClick(i, j) {
        const allCells = this.tableRef.el.querySelectorAll("td.selected");

        for (const cell of allCells) {
            cell.classList.remove("selected");
        }

        this.addClassToTableCells(j + 1, i + 1, "selected");
    }
}
