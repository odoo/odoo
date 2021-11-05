odoo.define('point_of_sale.ClientDetailsEdit', function(require) {
    'use strict';

    const { getDataURLFromFile } = require('web.utils');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class ClientDetailsEdit extends PosComponent {
        get partnerImageUrl() {
            // We prioritize image_1920 in the `changes` field because we want
            // to show the uploaded image without fetching new data from the server.
            const partner = this.props.partner;
            if (this.props.changes.image_1920) {
                return this.props.changes.image_1920;
            } else if (partner.id) {
                return `/web/image?model=res.partner&id=${partner.id}&field=avatar_128&write_date=${partner.write_date}&unique=1`;
            } else {
                return false;
            }
        }
        /**
         * Save to field `changes` all input changes from the form fields.
         */
        captureChange(event) {
            this.props.changes[event.target.name] = event.target.value;
        }
        async uploadImage(event) {
            const file = event.target.files[0];
            if (!file.type.match(/image.*/)) {
                await this.showPopup('ErrorPopup', {
                    title: this.env._t('Unsupported File Format'),
                    body: this.env._t(
                        'Only web-compatible Image formats such as .png or .jpeg are supported.'
                    ),
                });
            } else {
                const imageUrl = await getDataURLFromFile(file);
                const loadedImage = await this._loadImage(imageUrl);
                if (loadedImage) {
                    const resizedImage = await this._resizeImage(loadedImage, 800, 600);
                    this.props.changes.image_1920 = resizedImage.toDataURL();
                    // Rerender to reflect the changes in the screen
                    this.render();
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
         * loading an image. It resolves to the loaded image if succesful,
         * else, resolves to false.
         *
         * [Source](https://stackoverflow.com/questions/45788934/how-to-turn-this-callback-into-a-promise-using-async-await)
         */
        _loadImage(url) {
            return new Promise((resolve) => {
                const img = new Image();
                img.addEventListener('load', () => resolve(img));
                img.addEventListener('error', () => {
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Loading Image Error'),
                        body: this.env._t(
                            'Encountered error when loading image. Please try again.'
                        ),
                    });
                    resolve(false);
                });
                img.src = url;
            });
        }
    }
    ClientDetailsEdit.template = 'ClientDetailsEdit';

    Registries.Component.add(ClientDetailsEdit);

    return ClientDetailsEdit;
});
