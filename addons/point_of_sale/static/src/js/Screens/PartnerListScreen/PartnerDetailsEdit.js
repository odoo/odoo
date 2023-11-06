odoo.define("point_of_sale.PartnerDetailsEdit", function (require) {
    "use strict";

    const { _t } = require("web.core");
    const { getDataURLFromFile } = require("web.utils");
    const PosComponent = require("point_of_sale.PosComponent");
    const Registries = require("point_of_sale.Registries");

    const { onMounted, useState, onWillUnmount } = owl;

    class PartnerDetailsEdit extends PosComponent {
        setup() {
            super.setup();
            this.intFields = ["country_id", "state_id", "property_product_pricelist"];
            const partner = this.props.partner;
            this.changes = useState({
                name: partner.name || "",
                street: partner.street || "",
                city: partner.city || "",
                zip: partner.zip || "",
                state_id: partner.state_id && partner.state_id[0],
                country_id: partner.country_id && partner.country_id[0],
                lang: partner.lang || "",
                email: partner.email || "",
                phone: partner.phone || "",
                mobile: partner.mobile || "",
                barcode: partner.barcode || "",
                vat: partner.vat || "",
                property_product_pricelist: this.getDefaultPricelist(partner),
            });

            onMounted(() => {
                this.env.bus.on("save-partner", this, this.saveChanges);
            });

            onWillUnmount(() => {
                this.env.bus.off("save-partner", this);
            });
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
        getDefaultPricelist(partner) {
            if (partner.property_product_pricelist) {
                return partner.property_product_pricelist[0];
            }
            return this.env.pos.default_pricelist ? this.env.pos.default_pricelist.id : false;
        }
        // NOTE: this functions was kept for compatibility with stable
        captureChange(event) {}
        saveChanges() {
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
                this.env.pos.states.find((state) => state.id === processedChanges.state_id)
                    .country_id[0] !== processedChanges.country_id
            ) {
                processedChanges.state_id = false;
            }

            if (
                (!this.props.partner.name && !processedChanges.name) ||
                processedChanges.name === ""
            ) {
                return this.showPopup("ErrorPopup", {
                    title: _t("A Customer Name Is Required"),
                });
            }
            processedChanges.id = this.props.partner.id || false;
            this.trigger("save-changes", { processedChanges });
        }
        async uploadImage(event) {
            const file = event.target.files[0];
            if (!file.type.match(/image.*/)) {
                await this.showPopup("ErrorPopup", {
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
                    this.showPopup("ErrorPopup", {
                        title: this.env._t("Loading Image Error"),
                        body: this.env._t(
                            "Encountered error when loading image. Please try again."
                        ),
                    });
                    resolve(false);
                });
                img.src = url;
            });
        }
    }
    PartnerDetailsEdit.template = "PartnerDetailsEdit";

    Registries.Component.add(PartnerDetailsEdit);

    return PartnerDetailsEdit;
});
