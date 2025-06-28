/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { getDataURLFromFile } from "@web/core/utils/urls";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { loadImage } from "@point_of_sale/utils";

export class PartnerDetailsEdit extends Component {
    static template = "point_of_sale.PartnerDetailsEdit";

    setup() {
        this.popup = useService("popup");
        this.pos = usePos();
        this.intFields = ["country_id", "state_id", "property_product_pricelist"];
        const partner = this.props.partner;
        this.changes = useState({
            name: partner.name || false,
            street: partner.street || false,
            city: partner.city || false,
            zip: partner.zip || false,
            state_id: partner.state_id && partner.state_id[0],
            country_id: partner.country_id && partner.country_id[0],
            lang: partner.lang || false,
            email: partner.email || false,
            phone: partner.phone || false,
            mobile: partner.mobile || false,
            barcode: partner.barcode || false,
            vat: partner.vat || false,
            property_product_pricelist: this.setDefaultPricelist(partner),
        });
        // Provides translated terms used in the view
        this.partnerDetailsFields = {
            'Street': _t('Street'),
            'City': _t('City'),
            'Zip': _t('Zip'),
            'Email': _t('Email'),
            'Phone': _t('Phone'),
            'Mobile': _t('Mobile'),
            'Barcode': _t('Barcode')
        };
        Object.assign(this.props.imperativeHandle, {
            save: () => this.saveChanges(),
        });
    }
    // FIXME POSREF naming
    setDefaultPricelist(partner) {
        if (partner.property_product_pricelist) {
            return partner.property_product_pricelist[0];
        }
        return this.pos.default_pricelist?.id ?? false;
    }

    get missingFields() {
        return this.props.missingFields ? this.props.missingFields : [];
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
            this.pos.states.find((state) => state.id === processedChanges.state_id)
                .country_id[0] !== processedChanges.country_id
        ) {
            processedChanges.state_id = false;
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
                title: _t("Unsupported File Format"),
                body: _t("Only web-compatible Image formats such as .png or .jpeg are supported."),
            });
        } else {
            const imageUrl = await getDataURLFromFile(file);
            const loadedImage = await loadImage(imageUrl, {
                onError: () => {
                    this.popup.add(ErrorPopup, {
                        title: _t("Loading Image Error"),
                        body: _t("Encountered error when loading image. Please try again."),
                    });
                }
            });
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
    isFieldCommercialAndPartnerIsChild(field) {
        return (
            this.pos.isChildPartner(this.props.partner) &&
            this.pos.partner_commercial_fields.includes(field)
        );
    }
}
