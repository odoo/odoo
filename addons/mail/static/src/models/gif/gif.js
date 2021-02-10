/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2one, one2many } from '@mail/model/model_field';
import { link, unlink } from '@mail/model/model_field_command';

function factory(dependencies) {

    class Gif extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        favorite() {
            this.env.services.rpc({
                route: '/mail/set_gif_favorite',
                params: {
                    gif_id: this.id
                }
            });
            this.gifManager.update({
                favorites: link(this)
            });
        }

        unfavorite() {
            this.env.services.rpc({
                route: '/mail/remove_gif_favorites',
                params: {
                    gif_id: this.id
                }
            });
            this.gifManager.update({
                favorites: unlink(this)
            });
        }

        insertGif() {
            this.gifManager.insertGif(this);
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        _computeIsFavorite() {
            return this.gifManager.favorites.includes(this);
        }

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.id}`;
        }
    }

    Gif.fields = {
        gifManager: many2one('mail.gif_manager', {
            inverse: 'gifs',
            required: true,
        }),
        gifManagerFavorites: one2many('mail.gif', {
            related: 'gifManager.favorites',
        }),
        id: attr({
            required: true,
        }),
        isFavorite: attr({
            compute: '_computeIsFavorite',
            default: false,
            dependencies: [
                'gifManager',
                'gifManagerFavorites',
            ],
        }),
        /**
         * Contain the image to display inside an img tag
         */
        image: attr(),
        /**
         * contain the search term of a gif category
         */
        searchTerm: attr(),
        /**
         * Gif title
         */
        title: attr(),
        /**
         * Gif type: category or actual gif to insert
         */
        type: attr(),
        /**
         * Orginal url to post to the thread
         */
        url: attr(),
    };

    Gif.modelName = 'mail.gif';

    return Gif;
}

registerNewModel('mail.gif', factory);
