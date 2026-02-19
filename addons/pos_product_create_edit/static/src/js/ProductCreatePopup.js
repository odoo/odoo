/**@odoo-module **/
import AbstractAwaitablePopup from "point_of_sale.AbstractAwaitablePopup";
import Registries from "point_of_sale.Registries";
import { isConnectionError } from "point_of_sale.utils";
import {
  useListener
} from "@web/core/utils/hooks";
let img = "";
let base64_img = "";
class CreateProductPopup extends AbstractAwaitablePopup {
  setup() {
    super.setup();
    useListener("change", "#img_field", this._onChangeImgField);
  }
  async _onChangeImgField(ev) {
    // This function will work when adding image to the image field
    try {
      let current = ev.target.files[0];
      const reader = new FileReader();
      reader.readAsDataURL(current);
      reader.onload = await
      function () {
        img = reader.result;
        base64_img = reader.result.toString().replace(/^data:(.*,)?/, "");
        const myTimeout = setTimeout(() => {
          $("#img_url_tag_create").hide();
          let element =
            "<img src=" + img + " style='max-width: 150px;max-height: 150px;'/>";
          $(".product-img-create-popup").append($(element));
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
  async confirm() {
    let img = $("#img_field").val();
    let name = $("#display_name").val();
    let price = $("#list_price").val();
    let cost = $("#cost_price").val();
    let category = $("#product_category").val();
    let barcode = $("#barcode").val();
    let default_code = $("#default_code").val();
    let values = {};
    if (base64_img) {
      values["image_1920"] = base64_img;
    }
    if (name) {
      values["name"] = name;
    }
    if (cost) {
      values["standard_price"] = cost;
    }
    if (price) {
      values["lst_price"] = price;
    }
    if (category) {
      values["pos_categ_id"] = category;
    }
    if (barcode) {
      values["barcode"] = barcode;
    }
    if (default_code) {
      values["default_code"] = default_code;
    }
    values["available_in_pos"] = true;
    await this.rpc({
      model: "product.product",
      method: "create",
      args: [values],
    }).then((result) => {
      if (result) {
        this.showNotification(_.str.sprintf(this.env._t('%s - Product Created'), $("#display_name").val()), 3000);
      } else {
        this.showNotification(_.str.sprintf(this.env._t('%s - Product Creation Failed'), $("#display_name").val()), 3000);
      }
    });
    this.env.posbus.trigger("close-popup", {
      popupId: this.props.id,
      response: {
        confirmed: false,
        payload: null,
      },
    });
  }
}
CreateProductPopup.template = "CreateProductPopup";
Registries.Component.add(CreateProductPopup);