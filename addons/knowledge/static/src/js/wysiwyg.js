odoo.define('knowledge.wysiwyg', function (require) {
'use strict';

const core = require('web.core');
const QWeb = core.qweb;

const { DocumentWidget } = require('wysiwyg.widgets.media');
const MediaDialog = require('wysiwyg.widgets.MediaDialog');
const Link = require('wysiwyg.widgets.Link');
const weWidgets = require('web_editor.widget');
const Wysiwyg = require('web_editor.wysiwyg');

const CustomDocumentWidget = DocumentWidget.extend({
    /**
     * @param {Object} img
     * @returns {HTMLElement}
     */
    _renderMedia: function (img) {
        let src = '';
        if (img.image_src) {
            src = img.image_src;
            if (!img.public && img.access_token) {
                src += _.str.sprintf('?access_token=%s', img.access_token);
            }
        }

        const dom = $(QWeb.render('knowledge.file_block', {
            img: img,
            src: src
        }));
        this.$media = dom;
        this.media = dom[0];

        // Add mimetype for documents
        if (!img.image_src) {
            this.media.dataset.mimetype = img.mimetype;
        }
        this.$media.trigger('image_changed');
        return this.media;
    }
});

MediaDialog.include({
    /**
     * @param {Object} media
     * @param {Object} options
     * @returns
     */
    getDocumentWidget: function (media, options) {
        return new CustomDocumentWidget(this, media, options);
    }
});

Wysiwyg.include({
    /**
     * @returns {Array[Object]}
     */
    _getCommands: function () {
        const commands = this._super();
        commands.push({
            groupName: 'Medias',
            title: 'File',
            description: 'Embed a file.',
            fontawesome: 'fa-file',
            callback: () => {
                this.openMediaDialog({
                    noVideos: true,
                    noImages: true,
                    noIcons: true,
                    noDocuments: false
                });
            }
        });
        return commands;
    }
});

const CustomLinkWidget = Link.extend({
    template: 'wysiwyg.widgets.link',
    _getLinkOptions: function () {
        return []
    },
});

weWidgets.LinkDialog.include({
    /**
     * @param {...any} args
     * @returns
     */
    getLinkWidget: function (...args) {
        return new CustomLinkWidget(this, ...args);
    }
});
});
