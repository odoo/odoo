odoo.define('point_of_sale.ClientDetailsEdit', function(require) {
    'use strict';

    const { getDataURLFromFile } = require('web.utils');
    const { PosComponent } = require('point_of_sale.PosComponent');
    const Registry = require('point_of_sale.ComponentsRegistry');

    class ClientDetailsEdit extends PosComponent {
        static template = 'ClientDetailsEdit';
        constructor() {
            super(...arguments);
            this.intFields = ['country_id', 'state_id', 'property_product_pricelist'];
            this.changes = {};
        }
        get partnerImageUrl() {
            // We prioritize image_1920 in the `changes` field because we want
            // to show the uploaded image without fetching new data from the server.
            if (this.changes.image_1920) {
                return this.changes.image_1920;
            } else if (this.props.partner.id) {
                return `/web/image?model=res.partner&id=${this.props.partner.id}&field=image_128`;
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
            let processedChanges = {};
            for (let [key, value] of Object.entries(this.changes)) {
                if (this.intFields.includes(key)) {
                    processedChanges[key] = parseInt(value) || false;
                } else {
                    processedChanges[key] = value;
                }
            }
            processedChanges.id = this.props.partner.id || false;
            this.trigger('save-changes', { processedChanges });
        }
        async uploadImage(event) {
            const file = event.target.files[0];
            try {
                if (!file.type.match(/image.*/)) {
                    throw {
                        name: 'UnsupportedFileFormat',
                        message: {
                            title: _t('Unsupported File Format'),
                            body: _t(
                                'Only web-compatible Image formats such as .png or .jpeg are supported.'
                            ),
                        },
                    };
                }
                const imageUrl = await getDataURLFromFile(file);
                const loadedImage = await this._loadImage(imageUrl);
                const resizedImage = await this._resizeImage(loadedImage, 800, 600);
                this.changes.image_1920 = resizedImage.toDataURL();
                // Rerender to reflect the changes in the screen
                this.render();
            } catch (err) {
                // TODO jcb: show popup instead of console error
                switch (err.name) {
                    // can be error from FileReader abort or error
                    case 'UnsupportedFileFormat':
                    case 'LoadingImageError':
                        // ErrorPopup.show(err.message);
                        break;
                    default:
                        console.error(['Unhandled Error', err]);
                        break;
                }
            }
        }
        _resizeImage(img, maxwidth, maxheight) {
            var canvas = document.createElement('canvas');
            var ctx = canvas.getContext('2d');
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
         * loading an image. It resolves to the loaded image.
         *
         * [Source](https://stackoverflow.com/questions/45788934/how-to-turn-this-callback-into-a-promise-using-async-await)
         */
        _loadImage(url) {
            return new Promise((resolve, reject) => {
                const img = new Image();
                img.addEventListener('load', () => resolve(img));
                img.addEventListener('error', () =>
                    reject({
                        name: 'LoadingImageError',
                        message: {
                            title: 'Loading Image Error',
                            body: 'We encountered error when loading image. Please try again.',
                        },
                    })
                );
                img.src = url;
            });
        }
    }

    Registry.add('ClientDetailsEdit', ClientDetailsEdit);

    return { ClientDetailsEdit };
});
