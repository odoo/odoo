odoo.define('mail_media_repository/static/src/models/attachment/attachment.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    class Attachment extends dependencies['mail.model'] {
        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * fetch attachment files
         *
         * @static
         * @param {integer} [number]
         * @param {integer} [offset]
         * @returns {[ir.attachment]}
         */
        async performRpcMediaFetch(number, offset) {
            const attachments = await this.env.services.rpc({
                model: 'ir.attachment',
                method: 'search_read',
                args: [],
                kwargs: {
                    domain: this._getAttachmentsDomain(this.needle),
                    fields: ['name', 'mimetype', 'description', 'checksum', 'url', 'type', 'res_id', 'res_model', 'public', 'access_token', 'image_src', 'image_width', 'image_height', 'original_id'],
                    order: [{name: 'id', asc: false}],
                    // Try to fetch first record of next page just to know whether there is a next page.
                    limit: number + 1,
                    offset: offset,
                },
            }, { shadow: true });

            attachments.forEach(attachment => {
                if (attachment.image_src.startsWith('/')) {
                    const newURL = new URL(attachment.image_src, window.location.origin);
                    // Set height so that db images load faster
                    newURL.searchParams.set('height', '256');
                    attachment.thumbnail_src = newURL.pathname + newURL.search;
                }
            });

            this.update({
                mediaList: offset == 0 ? attachments : this.mediaList.concat(attachments),
            });
            return attachments;
        }

        _getAttachmentsDomain(needle) {
            let domain = [];

            // domain = ['|', ['public', '=', true]].concat(domain);
            domain = domain.concat([['mimetype', 'ilike', 'image']]);
            if (needle && needle.length) {
                domain.push(['name', 'ilike', needle]);
            }
            // domain.push('!', ['name', '=like', '%.crop']);
            // domain.push('|', ['type', '=', 'binary'], '!', ['url', '=like', '/%/static/%']);
            return domain;
        }

    }

    Attachment.fields = {
        needle: attr(),
        mediaType: attr({
            default: 'image'
        }),
        mediaList: attr({
            default: [],
        }),
    };

    Attachment.modelName = 'mail_media_repository.attachment';

    return Attachment;
}

registerNewModel('mail_media_repository.attachment', factory);

});
