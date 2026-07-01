/**@odoo-module **/
import AbstractAwaitablePopup from "point_of_sale.AbstractAwaitablePopup";
import Registries from "point_of_sale.Registries";
import { useListener } from "@web/core/utils/hooks";
let base64_img = "";
let img = "";
class EditProductPopup extends AbstractAwaitablePopup {
  setup() {
    super.setup();
    useListener("change", "#img_field", this._onChangeImgField);
  }
  async _onChangeImgField(ev) {
    try {
      // This function will work when adding image to the image field
      var self = this;
      let current = ev.target.files[0];
      const reader = new FileReader();
      reader.readAsDataURL(current);
      reader.onload = await function () {
        img = reader.result;
        base64_img = reader.result.toString().replace(/^data:(.*,)?/, "");
        const myTimeout = setTimeout(() => {
          $("#img_url_tag_edit").hide();
          let element =
            "<img src=" +
            img +
            " style='max-width: 150px;max-height: 150px;'/>";
          $(".product-img-edit-popup").append($(element));
        }, 100);
      };
      reader.onerror = (error) =>
        reject(() => {
          console.log("error", error);
        });
    } catch (error) {
      if (isConnectionError(error)) {
        this.showPopup("ErrorPopup", {
          title: this.env._t("Network Error"),
          body: this.env._t("Cannot access Product screen if offline."),
        });
      } else {
        throw error;
      }
    }
  }

  confirm() {
    let values = {};
    if (base64_img) {
      values["image_1920"] = base64_img;
    }
    if ($("#display_name").val() != this.props.product.display_name) {
      values["name"] = $("#display_name").val();
    }
    if ($("#list_price").val() != this.props.product.list_price) {
      values["lst_price"] = $("#list_price").val();
    }
    if ($("#product_category").val()) {
      values["pos_categ_id"] = parseInt($("#product_category").val());
    }
    if ($("#barcode").val()) {
      values["barcode"] = parseInt($("#barcode").val());
    }
    if ($("#default_code").val()) {
      values["default_code"] = parseInt($("#default_code").val());
    }
    this.rpc({
      model: "product.product",
      method: "write",
      args: [this.props.product.id, values],
    }).then((result) => {
      if (result) {
        this.props.product.display_name = $("#display_name").val();
        this.props.product.lst_price = $("#list_price").val();
        this.props.product.barcode = $("#barcode").val();
        this.props.product.default_code = $("#default_code").val();
        this.props.product.pos_categ_id = [
          parseInt($("#product_category").val()),
          $("#product_category")[0].selectedOptions[0].title,
        ];
        this.showNotification(_.str.sprintf(this.env._t("%s - Product Updated"),$("#display_name").val()),3000);
      } else {
        this.showNotification(_.str.sprintf(this.env._t("%s - Product Updation Failed"),$("#display_name").val()),3000);
      }
      this.env.posbus.trigger("close-popup", {
        popupId: this.props.id,
        response: {
          confirmed: false,
          payload: null,
        },
      });
    });
  }
  cancel() {
    this.env.posbus.trigger("close-popup", {
      popupId: this.props.id,
      response: {
        confirmed: false,
        payload: null,
      },
    });
  }
  get imageUrl() {
    const product = this.props.product;
    return `/web/image?model=product.product&field=image_128&id=${product.id}&unique=${product.write_date}`;
  }
}
EditProductPopup.template = "EditProductPopup";
Registries.Component.add(EditProductPopup);
