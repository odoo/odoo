import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart, onMounted, useState, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ProductsItemOption extends BaseOptionComponent {
    static template = "website_sale.ProductsItemOptionPlugin";
    static props = {
        loadInfo: Function,
        itemSize: Object,
        count: Object,
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.tableRef = useRef("table");

        this.state = useState({
            ribbons: [],
            ribbonEditMode: false,
            itemSize: this.props.itemSize,
        });

        onWillStart(async () => {
            const [ribbons, defaultSort] = await this.props.loadInfo();
            this.state.ribbons = ribbons;
            this.defaultSort = defaultSort;

            // need to display "re-order" option only if shop_default_sort is 'website_sequence asc'
            this.displayReOrder = this.defaultSort[0].shop_default_sort === "website_sequence asc";

            // If /shop page layout is list, do not display Size option
            this.displaySizeOption = !this.env.getEditingElement().closest("#o_wsale_container").classList.contains("o_wsale_layout_list");
        });

        onMounted(() => {
            if (this.displaySizeOption) {
                this.addClassToTableCells(this.state.itemSize.x, this.state.itemSize.y, "selected");
            }
        });
    }

    addClassToTableCells(x, y, className) {
        const table = this.tableRef.el;

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
