import { BaseOptionComponent } from "@html_builder/core/utils";
import { Component, xml, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { BuilderButton } from "@html_builder/core/building_blocks/builder_button";

export class TableCell extends Component {
  static template = xml`
                      <td t-on-mouseover="()=>this.props._onTableCellMouseEnter(this.props.i, this.props.j)"
                          t-att-id="'cell_'+this.props.i+this.props.j" >
                          <BuilderButton actionValue="{'i': this.props.i, 'j': this.props.j}" />
                      </td>`;
  static components = { BuilderButton };
  static props = {
    i: Number,
    j: Number,
    _onTableMouseEnter: Function,
  };
}

export class ProductsItemOption extends BaseOptionComponent {
  static template = "website_sale.ProductsItemOptionPlugin";
  static components = { TableCell };

  setup() {
    super.setup();
    this.orm = useService("orm");
    this.state = useState({ ribbonEditMode: false });
    onWillStart(async () => {
      this.ribbons = await this.orm.searchRead(
        "product.ribbon",
        [],
        ["id", "name", "bg_color", "text_color", "position"]
      );
      this.defaultSort = await this.orm.searchRead(
        "website",
        [],
        ["shop_default_sort"]
      );
      // need to display "re-order" option only if shop_default_sort is 'website_sequence asc'
      this.displayReOrder =
        this.defaultSort[0].shop_default_sort === "website_sequence asc";
    });
  }

  _onTableMouseEnter(ev) {
    ev.currentTarget.classList.add("oe_hover");
  }

  _onTableMouseLeave(ev) {
    ev.currentTarget.classList.remove("oe_hover");
  }

  _onTableCellMouseEnter(i, j) {
    const y = i + 1;
    const x = j + 1;
    const allCells = document.querySelectorAll("[id^='cell_']");

    allCells.forEach((cell) => {
      cell.classList.remove("select");
    });

    for (let row = 0; row < y; row++) {
      for (let col = 0; col < x; col++) {
        const cellToSelect = document.querySelector(`#cell_${row}${col}`);
        if (cellToSelect) {
          cellToSelect.classList.add("select");
        }
      }
    }
  }
}
