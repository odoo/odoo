/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { getDataURLFromFile } from "@web/core/utils/urls";
import { ErrorPopup } from "@point_of_sale/js/Popups/ErrorPopup";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

export class PartnerDetailsEdit extends Component {
    static template = "PartnerDetailsEdit";

    setup() {
        super.setup();
        this.popup = useService("popup");
        this.intFields = ["country_id", "state_id", "property_product_pricelist"];
        const partner = this.props.partner;
        this.changes = {
            country_id: partner.country_id && partner.country_id[0],
            state_id: partner.state_id && partner.state_id[0],
            property_product_pricelist: this.setDefaultPricelist(partner),
        };
        Object.assign(this.props.imperativeHandle, {
            save: () => this.saveChanges(),
        });
    }
    setDefaultPricelist(partner) {
        if (partner.property_product_pricelist) {
            return partner.property_product_pricelist[0];
        } else if (this.env.pos.default_pricelist) {
            return this.env.pos.default_pricelist.id;
        }
        return false;
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
    /**
     * Save to field `changes` all input changes from the form fields.
     */
    captureChange(event) {
        this.changes[event.target.name] = event.target.value;
    }
    saveChanges() {
        const processedChanges = {};
        for (const [key, value] of Object.entries(this.changes)) {
            if (this.intFields.includes(key)) {
                processedChanges[key] = parseInt(value) || false;
            } else {
                processedChanges[key] = value;
            }
        }
        if ((!this.props.partner.name && !processedChanges.name) || processedChanges.name === "") {
            return this.popup.add(ErrorPopup, {
                title: _t("A Customer Name Is Required"),
            });
        }
        processedChanges.id = this.props.partner.id || false;
        this.props.saveChanges(processedChanges);
    }
    async uploadImage(event) {
        const file = event.target.files[0];
        if (!file.type.match(/image.*/)) {
            await this.popup.add(ErrorPopup, {
                title: this.env._t("Unsupported File Format"),
                body: this.env._t(
                    "Only web-compatible Image formats such as .png or .jpeg are supported."
                ),
            });
        } else {
            const imageUrl = await getDataURLFromFile(file);
            const loadedImage = await this._loadImage(imageUrl);
            if (loadedImage) {
                const resizedImage = await this._resizeImage(loadedImage, 800, 600);
                this.changes.image_1920 = resizedImage.toDataURL();
                // Rerender to reflect the changes in the screen
                this.render(true);
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
     * loading an image. It resolves to the loaded image if succesful,
     * else, resolves to false.
     *
     * [Source](https://stackoverflow.com/questions/45788934/how-to-turn-this-callback-into-a-promise-using-async-await)
     */
    _loadImage(url) {
        return new Promise((resolve) => {
            const img = new Image();
            img.addEventListener("load", () => resolve(img));
            img.addEventListener("error", () => {
                this.popup.add(ErrorPopup, {
                    title: this.env._t("Loading Image Error"),
                    body: this.env._t("Encountered error when loading image. Please try again."),
                });
                resolve(false);
            });
            img.src = url;
        });
    }
}
