import { BaseOptionComponent } from "@html_builder/core/utils";
import {
  Component,
  xml,
  onWillStart,
  onMounted,
  useState,
  useRef,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { BuilderButton } from "@html_builder/core/building_blocks/builder_button";

export class TableCell extends Component {
  static template = xml`
                      <td t-on-mouseover="()=>this.props._onTableCellMouseEnter(this.props.i, this.props.j)"
                          t-on-click="()=>this.props._onTableCellMouseClick(this.props.i, this.props.j)"
                        >
                          <BuilderButton preview="false" actionValue="{'i': this.props.i, 'j': this.props.j}" />
                      </td>`;
  static components = { BuilderButton };
  static props = {
    i: Number,
    j: Number,
    _onTableMouseEnter: Function,
    _onTableMouseClick: Function,
  };
}

export class ProductsItemOption extends BaseOptionComponent {
  static template = "website_sale.ProductsItemOptionPlugin";
  static props = {
    loadRibbons: Function,
    getDefaultSort: Function,
    itemSize: Object,
    count : Object
  };
  static components = { TableCell };

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
      const [ribbons, defaultSort] = await Promise.all([
        this.props.loadRibbons(),
        this.props.getDefaultSort(),
      ]);
      this.state.ribbons = ribbons;
      this.defaultSort = defaultSort;

      // need to display "re-order" option only if shop_default_sort is 'website_sequence asc'
      this.displayReOrder =
        this.defaultSort[0].shop_default_sort === "website_sequence asc";
    });

    onMounted(() => {
      this.addClassToTableCells(
        this.state.itemSize.x,
        this.state.itemSize.y,
        "selected"
      );
    });
  }

  addClassToTableCells(x, y, className) {
    const table = this.tableRef.el;

    if (table) {
      const rows = table.rows;
      for (let row = 0; row < y; row++) {
        const cells = rows[row].cells;
        for (let col = 0; col < x; col++) {
          cells[col].classList.add(className);
        }
      }
    }
  }

  _onTableMouseEnter(ev) {
    ev.currentTarget.classList.add("oe_hover");
  }

  _onTableMouseLeave(ev) {
    ev.currentTarget.classList.remove("oe_hover");
  }

  _onTableCellMouseEnter(i, j) {
    const allCells = this.tableRef.el.querySelectorAll("td.select");

    allCells.forEach((cell) => {
      cell.classList.remove("select");
    });

    this.addClassToTableCells(j + 1, i + 1, "select");
  }

  _onTableCellMouseClick(i, j) {
    const allCells = this.tableRef.el.querySelectorAll("td.selected");

    allCells.forEach((cell) => {
      cell.classList.remove("selected");
    });
    this.addClassToTableCells(j + 1, i + 1, "selected");
  }
}
