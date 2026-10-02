/**@odoo-module **/
import PosComponent from "point_of_sale.PosComponent";
import Registries from "point_of_sale.Registries";
import { Gui } from 'point_of_sale.Gui';

class ProductLine extends PosComponent {
  get imageUrl() {
    const product = this.props.product;
    return `/web/image?model=product.product&field=image_128&id=${product.id}&unique=${product.write_date}`;
  }
  async editCurrentProduct() {
    await Gui.showPopup("EditProductPopup", {
      product: this.props.product,
    });
  }
}
ProductLine.template = "ProductLine";
Registries.Component.add(ProductLine);
