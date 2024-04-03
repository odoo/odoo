/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";
import { onMounted, useState } from "@odoo/owl";
import { PickupLocations } from "./pickup_locations_template";

export class ChoosePickupPointFormController extends FormController {
  static template = "delivery.ChoosePickupPointForm";

  static components = {
    ...super.components,
    PickupLocations
  };

  setup() {
    super.setup();

    this.action = useService("action");

    this.pickupPoints = useState({ data: [] });
    this.zipCode = useState({ value: "" });
    this.selectedPickupPoint = useState({});
    this.loading = useState({ value: true });
    this.searchByZipCode = useState({ value: false });

    onMounted(async () => {
      this.loading.value = true;
      if (this.model.root.data.order_id) {
        this.order = await this.orm.searchRead(
          "sale.order",
          [["id", "=", this.model.root.data.order_id[0]]],
          ["partner_id", "partner_shipping_id", "carrier_id"]
        );
        this.initialAddress = await this.orm.searchRead(
          "res.partner",
          [["id", "=", this.order[0].partner_shipping_id[0]]],
          ["zip"]
        );
      } else {
        this.picking = await this.orm.searchRead(
          "stock.picking",
          [["id", "=", this.model.root.data.picking_id[0]]],
          ["partner_id", "carrier_id"]
        );
        this.initialAddress = await this.orm.searchRead(
          "res.partner",
          [["id", "=", this.picking[0].partner_id[0]]],
          ["zip", "parent_id"]
        );
      }
      if (!this.initialAddress[0]) {
        this.initialAddress = await this.orm.searchRead(
          "res.partner",
          [["id", "=", this.model.root.evalContext.current_company_id]],
          ["zip"]
        );
      }
      this.zipCode.value = this.initialAddress[0]?.zip;
      this.chooseDeliveryCarrierWizardId =
        this.model.root.data.choose_delivery_carrier_id;
      if (this.chooseDeliveryCarrierWizardId) {
        this.chooseCarrierWizard = await this.orm.searchRead(
          "choose.delivery.carrier",
          [["id", "=", this.chooseDeliveryCarrierWizardId[0]]],
          ["carrier_id"]
        );
      }
      this.carrier = await this.orm.searchRead(
        "delivery.carrier",
        [
          [
            "id",
            "=",
            this.chooseCarrierWizard
              ? this.chooseCarrierWizard[0].carrier_id[0]
              : this.order
              ? this.order[0].carrier_id[0]
              : this.picking[0].carrier_id[0],
          ],
        ],
        ["delivery_type"]
      );
      this.pickupPoints.data = await this.orm.call(
        "delivery.carrier",
        `${this.carrier[0].delivery_type}_get_close_locations`,
        [this.carrier[0].id, this.initialAddress[0]?.id]
      );
      this.loading.value = false;
    });
  }

  onChangeZipCode(ev) {
    this.zipCode.value = ev.target.value;
  }

  async searchPickupPoints() {
    this.selectedPickupPoint = {};
    this.loading.value = true;
    this.pickupPoints.data = await this.orm.call(
      "delivery.carrier",
      `${this.carrier[0].delivery_type}_get_close_locations`,
      [
        this.carrier[0].id,
        this.order ? this.order[0].partner_id[0] : this.initialAddress[0].id,
      ],
      { zip_code: this.zipCode.value }
    );
    this.loading.value = false;
    // When searching by zip code only, sendcloud doesn't return distance data. So we need this variable to show/hide the distance column
    this.searchByZipCode.value =
      this.zipCode.value?.length > 0 &&
      this.carrier[0].delivery_type === "sendcloud";
  }

  onSelectPickupPoint(pickupPoint) {
    this.selectedPickupPoint = pickupPoint;
    this.render();
  }

  async onWillSaveRecord() {
    let alreadyExistingAddress = await this.orm.searchRead("res.partner", [
      [
        "parent_id",
        "=",
        this.order
          ? this.order[0].partner_id[0]
          : this.initialAddress[0].parent_id
          ? this.initialAddress[0].parent_id[0]
          : null,
      ],
      ["name", "=", this.selectedPickupPoint.name],
      ["street", "=", this.selectedPickupPoint.street],
      ["city", "=", this.selectedPickupPoint.city],
      ["state_id", "=", this.selectedPickupPoint.state],
      ["country_id", "=", this.selectedPickupPoint.country],
      ["type", "=", "delivery"],
    ]);
    if (alreadyExistingAddress.length === 0) {
      let country = await this.orm.searchRead(
        "res.country",
        [["code", "=", this.selectedPickupPoint.country]],
        ["code"]
      );
      let state =
        country.length === 0
          ? null
          : await this.orm.searchRead(
              "res.country.state",
              [
                ["code", "=", this.selectedPickupPoint.state],
                ["country_id", "=", country[0].id],
              ],
              ["code"]
            );
      let newAddress = {
        parent_id: this.order
          ? this.order[0].partner_id[0]
          : this.initialAddress[0].parent_id
          ? this.initialAddress[0].parent_id[0]
          : null,
        name: this.selectedPickupPoint.name,
        street: this.selectedPickupPoint.street,
        city: this.selectedPickupPoint.city,
        country_id: country.length === 0 ? null : country[0].id,
        state_id: state?.length === 0 ? null : state[0].id,
        zip: this.selectedPickupPoint.zip,
        type: "delivery",
        external_id: this.selectedPickupPoint.external_id,
      };
      let newAddressId = await this.orm.create("res.partner", [newAddress]);
      await this.orm.write(
        this.model.root.evalContext.context.active_model,
        [this.model.root.evalContext.context.active_id],
        this.model.root.evalContext.context.active_model === "stock.picking"
          ? {
              partner_id: newAddressId[0],
            }
          : {
              delivery_address_id: newAddressId[0],
            }
      );
    } else {
      await this.orm.write(
        this.model.root.evalContext.context.active_model,
        [this.model.root.evalContext.context.active_id],
        this.model.root.evalContext.context.active_model === "stock.picking"
          ? {
              partner_id: alreadyExistingAddress[0].id,
            }
          : {
              delivery_address_id: alreadyExistingAddress[0].id,
            }
      );
    }
    await this.retrieveFirstWizard();
  }

  async discard() {
    if (this.props.discardRecord) {
      this.props.discardRecord(this.model.root);
      return;
    }
    await this.model.root.discard();
    if (this.props.onDiscard) {
      this.props.onDiscard(this.model.root);
    }
    if (!this.chooseDeliveryCarrierWizardId) {
      this.env.config.historyBack();
    } else {
      await this.retrieveFirstWizard();
    }
  }

  async retrieveFirstWizard() {
    if (this.chooseDeliveryCarrierWizardId) {
      let wizardAction = await this.orm.call(
        "choose.delivery.carrier",
        "action_close_pickup_point",
        [this.chooseDeliveryCarrierWizardId[0]]
      );
      this.action.doAction(wizardAction);
    }
  }
}

registry.category("views").add("choose_pickup_point_form", {
  ...formView,
  Controller: ChoosePickupPointFormController,
  buttonTemplate: "delivery.ChoosePickupPointFormButtons",
});
