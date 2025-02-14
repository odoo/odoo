import { Component, xml, useState, markup } from "@odoo/owl";

export class DocTable extends Component {
    static template = xml`
        <table class="o-doc-table w-100 rounded bg-1">
            <tr t-if="props.data.headers" class="bg-1">
                <th
                    t-foreach="props.data.headers"
                    t-as="header"
                    t-key="header_index"
                    t-on-click="() => this.onRowHeaderClick(header_index)"
                    class="position-relative text-start cursor-pointer user-select-none pt-1 pb-1 ps-2"
                >
                    <span t-out="header"></span>
                    <i
                        t-att-class="getSortIcon(header_index)"
                        aria-hidden="true"
                    ></i>
                </th>
            </tr>
            <tr t-foreach="items" t-as="rows" t-key="rows_index" class="bg-1">
                <td t-foreach="rows" t-as="row" t-key="row_index" t-attf-style="width: {{ 100 / rows.length }}%" class="text-start">
                    <t t-if="row and row.type == 'tooltip'">
                        <div t-if="row.value" class="tooltip w-100 h-100">
                            <i class="fa fa-question-circle" aria-hidden="true"></i>
                            <span class="tooltiptext" t-out="asMarkup(row.value)"></span>
                        </div>
                    </t>
                    <t t-else="" t-tag="getTag(row)" t-att-class="getClass(row)" t-out="getValue(row)"/>
                </td>
            </tr>
            <tr t-if="items.length === 0" class="bg-1">
                <td t-foreach="props.data.headers" t-as="row" t-key="row_index" t-attf-style="width: {{ 100 / props.data.headers.length }}%" class="text-start text-muted">
                    <t t-if="row_index === 0">
                        No Data
                    </t>
                </td>
            </tr>
        </table>
    `;

    static props = {
        data: true,
    };

    get items() {
        if (this.state.sortBy >= 0) {
            const items = [...this.props.data.items];
            items.sort((itemA, itemB) => {
                const a = this.getValue(itemA[this.state.sortBy]);
                const b = this.getValue(itemB[this.state.sortBy]);
                if (this.state.sortOrder === "asc") {
                    return b.localeCompare(a);
                } else {
                    return a.localeCompare(b);
                }
            });
            return items;
        } else {
            return this.props.data.items;
        }
    }

    setup() {
        this.state = useState({
            items: [],
            sortBy: 0,
            sortOrder: "desc",
        });
    }

    getTag(row) {
        return row && typeof row === "object" && row.type === "code" ? "pre" : "span";
    }

    getValue(row) {
        return String(row && typeof row === "object" ? row.value : row);
    }

    getClass(row) {
        const classList = [];
        if (row && typeof row === "object") {
            if (row.type === "code-like") {
                classList.push("font-monospace");
            }
            if (row.class) {
                classList.push(row.class);
            }
        }
        return classList.join(" ");
    }

    asMarkup(value) {
        return markup(value);
    }

    onRowHeaderClick(rowIndex) {
        if (this.state.sortBy === rowIndex) {
            this.state.sortOrder = this.state.sortOrder === "asc" ? "desc" : "asc";
        }
        this.state.sortBy = rowIndex;
    }

    getSortIcon(rowIndex) {
        if (this.state.sortBy !== rowIndex) {
            return "fa fa-sort";
        } else if (this.state.sortOrder === "asc") {
            return "fa fa-sort-asc";
        } else {
            return "fa fa-sort-desc";
        }
    }
}
