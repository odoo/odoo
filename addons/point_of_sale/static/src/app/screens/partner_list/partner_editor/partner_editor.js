/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { getDataURLFromFile } from "@web/core/utils/urls";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { useAsyncLockedMethod } from "@point_of_sale/app/utils/hooks";

export class PartnerEditor extends Component {
    static template = "point_of_sale.PartnerEditor";
    static props = {
        partner: { type: Object, optional: true },
        missingFields: { type: Array, optional: true, element: String },
        closePartnerList: Function,
        getPayload: { type: Function, optional: true },
        close: Function,
    };
    static defaultProps = {
        missingFields: [],
    };
    static components = { Dialog };

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.intFields = ["country_id", "state_id", "property_product_pricelist"];
        const partner = this.props.partner;
        this.changes = useState({
            ...Object.fromEntries(
                [
                    "name",
                    "street",
                    "city",
                    "zip",
                    "lang",
                    "email",
                    "phone",
                    "mobile",
                    "barcode",
                    "vat",
                ].map((field) => [field, partner[field] || ""])
            ),
            state_id: partner.state_id && partner.state_id.id,
            country_id: partner.country_id && partner.country_id.id,
            property_product_pricelist: this.setDefaultPricelist(partner),
        });
        this.confirm = useAsyncLockedMethod(this.confirm);
    }
    // FIXME POSREF naming
    setDefaultPricelist(partner) {
        if (partner.property_product_pricelist) {
            return partner.property_product_pricelist.id;
        }
        return this.pos.config.pricelist_id?.id ?? false;
    }
    get partnerImageUrl() {
        // We prioritize image_1920 in the `changes` field because we want
        // to show the uploaded image without fetching new data from the server.
        const partner = this.props.partner;
        if (this.changes.image_1920) {
            return this.changes.image_1920;
        } else if (partner.id) {
            return `/web/image?model=res.partner&id=${partner.id}&field=avatar_128&unique=${partner.write_date}`;
        } else {
            return false;
        }
    }
    goToOrders() {
        this.props.closePartnerList();
        this.props.close();
        const partnerHasActiveOrders = this.pos
            .get_order_list()
            .some((order) => order.partner?.id === this.props.partner.id);
        const ui = {
            searchDetails: {
                fieldName: "PARTNER",
                searchTerm: this.props.partner.name,
            },
            filter: partnerHasActiveOrders ? "" : "SYNCED",
        };
        this.pos.showScreen("TicketScreen", { ui });
    }
    async confirm() {
        const processedChanges = {};
        for (const [key, value] of Object.entries(this.changes)) {
            if (this.intFields.includes(key)) {
                processedChanges[key] = parseInt(value) || false;
            } else {
                processedChanges[key] = value;
            }
        }
        if (
            processedChanges.state_id &&
            this.pos.models["res.country.state"].find(
                (state) => state.id === processedChanges.state_id
            ).country_id.id !== processedChanges.country_id
        ) {
            processedChanges.state_id = false;
        }

        if ((!this.props.partner.name && !processedChanges.name) || processedChanges.name === "") {
            return this.dialog.add(AlertDialog, {
                title: _t("A Customer Name Is Required"),
            });
        }
        processedChanges.id = this.props.partner.id || false;

        if (processedChanges.image_1920) {
            processedChanges.image_1920 = processedChanges.image_1920.split(",")[1];
        }

        if (processedChanges.id) {
            this.pos.data.write("res.partner", [processedChanges.id], processedChanges);
        } else {
            await this.pos.data.create("res.partner", [processedChanges]);
        }

        this.props.close();
    }
    async uploadImage(event) {
        const file = event.target.files[0];
        if (!file.type.match(/image.*/)) {
            this.dialog.add(AlertDialog, {
                title: _t("Unsupported File Format"),
                body: _t("Only web-compatible Image formats such as .png or .jpeg are supported."),
            });
        } else {
            const imageUrl = await getDataURLFromFile(file);
            const loadedImage = await this._loadImage(imageUrl);
            if (loadedImage) {
                const resizedImage = await this._resizeImage(loadedImage, 800, 600);
                this.changes.image_1920 = resizedImage.toDataURL();
            }
        }
    }
    _resizeImage(img, maxwidth, maxheight) {
        var canvas = document.createElement("canvas");
        var ctx = canvas.getContext("2d");
        var ratio = 1;

        if (img.width > maxwidth) {
            ratio = maxwidth / img.width;
        }
        if (img.height * ratio > maxheight) {
            ratio = maxheight / img.height;
        }
        var width = Math.floor(img.width * ratio);
        var height = Math.floor(img.height * ratio);

        canvas.width = width;
        canvas.height = height;
        ctx.drawImage(img, 0, 0, width, height);
        return canvas;
    }
    /**
     * Loading image is converted to a Promise to allow await when
     * loading an image. It resolves to the loaded image if successful,
     * else, resolves to false.
     *
     * [Source](https://stackoverflow.com/questions/45788934/how-to-turn-this-callback-into-a-promise-using-async-await)
     */
    _loadImage(url) {
        return new Promise((resolve) => {
            const img = new Image();
            img.addEventListener("load", () => resolve(img));
            img.addEventListener("error", () => {
                this.dialog.add(AlertDialog, {
                    title: _t("Loading Image Error"),
                    body: _t("Encountered error when loading image. Please try again."),
                });
                resolve(false);
            });
            img.src = url;
        });
    }

    isFieldCommercialAndPartnerIsChild(field) {
        return (
            this.pos.isChildPartner(this.props.partner) &&
            this.pos.partner_commercial_fields.includes(field)
        );
    }
}
