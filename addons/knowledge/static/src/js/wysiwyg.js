/** @odoo-module **/

import { qweb as QWeb } from 'web.core';
import { DocumentWidget } from 'wysiwyg.widgets.media';
import MediaDialog from 'wysiwyg.widgets.MediaDialog';
import Wysiwyg from 'web_editor.wysiwyg';
import { KnowledgeArticleLinkModal } from './wysiwyg/knowledge_article_link.js';
import { preserveCursor, setCursorStart } from '@web_editor/../lib/odoo-editor/src/OdooEditor';

/**
 * Override the @see DocumentWidget to manage files in a @see MediaDialog used
 * by the /file command. The purpose of this override is to redefine the
 * rendering of the media (/file block), and to merge images in the documents
 * tab of the MediaDialog, since the /file block displays a default mimetype for
 * every files.
 */
const KnowledgeDocumentWidget = DocumentWidget.extend({
    /**
     * Filter files for the documents tab of the MediaDialog. Any file with a
     * mimetype is valid. (images and documents are displayed together)
     *
     * @override
     */
    init: function (parent, media, options) {
        options = _.extend({
            accept: '*/*',
            mimetypeDomain: [['mimetype', '!=', false]],
        }, options || {});
        this._super(parent, media, options);
    },
    /**
     * Custom rendering for the /file command
     *
     * @override
     * @param {Object} img
     * @returns {Element}
     */
    _renderMedia: function (img) {
        if (img.image_src) {
            delete img.image_src;
        }
        const file = this._super(...arguments);
        const extension = (img.name && img.name.split('.').pop()) || img.mimetype;
        this.$media = $(QWeb.render('knowledge.file_block', {
            img: {
                name: img.name,
                extension: extension,
            },
        }));
        this.media = this.$media[0];
        this.media.querySelector('.o_knowledge_file_image').replaceChildren(file);
        return this.media;
    }
});

/**
 * Override the @see MediaDialog to manage documents with the
 * @see KnowledgeDocumentWidget for the /file command
 */
const KnowledgeMediaDialog = MediaDialog.extend({
    /**
     * @override
     * @param {Object} media
     * @param {Object} options
     * @returns {Widget}
     */
    getDocumentWidget: function (media, options) {
        return new KnowledgeDocumentWidget(this, media, options);
    }
});
Wysiwyg.include({
    /**
     * @override
     */
    init: function (parent, options) {
        if (options.knowledge_commands) {
            /**
             * knowledge_commands is a view option from a field_html that
             * indicates that knowledge-specific commands should be loaded.
             * powerboxFilters is an array of functions used to filter commands
             * displayed in the powerbox.
             */
            options.powerboxFilters = options.powerboxFilters ? options.powerboxFilters : [];
            options.powerboxFilters.push(this._filterKnowledgeCommandGroupInTemplate);
        }
        this._super.apply(this, arguments);
    },
    /**
     * Prevent usage of commands from the group "Knowledge" inside the block
     * inserted by the /template Knowledge command. The content of a /template
     * block is destined to be used in @see OdooEditor in modules other than
     * Knowledge, where knowledge-specific commands may not be available.
     * i.e.: prevent usage /template in a /template block
     *
     * @param {Array} commands commands available in this wysiwyg
     * @returns {Array} commands which can be used after the filter was applied
     */
    _filterKnowledgeCommandGroupInTemplate: function (commands) {
        let anchor = document.getSelection().anchorNode;
        if (anchor.nodeType !== Node.ELEMENT_NODE) {
            anchor = anchor.parentElement;
        }
        if (anchor && anchor.closest('.o_knowledge_template')) {
            commands = commands.filter(command => command.groupName != 'Knowledge');
        }
        return commands;
    },
    /**
     * @override
     * @returns {Array[Object]}
     */
    _getCommands: function () {
        const commands = this._super();
        commands.push({
            groupName: 'Medias',
            title: 'Article',
            description: 'Link an article.',
            fontawesome: 'fa-file',
            callback: () => {
                this._insertArticleLink();
            },
        });
        if (this.options.knowledge_commands) {
            commands.push({
                groupName: 'Knowledge',
                title: 'File',
                description: 'Embed a file.',
                fontawesome: 'fa-file',
                callback: () => {
                    this.openMediaDialog({
                        noVideos: true,
                        noImages: true,
                        noIcons: true,
                        noDocuments: false
                    }, KnowledgeMediaDialog);
                }
            }, {
                groupName: 'Knowledge',
                title: "Template",
                description: "Add a template section.",
                fontawesome: 'fa-pencil-square',
                callback: () => {
                    this._insertTemplate();
                },
            }, {
                groupName: 'Knowledge',
                title: 'Table Of Content',
                description: 'Add a table of content.',
                fontawesome: 'fa-bookmark',
                callback: () => {
                    this._insertTableOfContent();
                }
            });
        }
        return commands;
    },
    /**
     * Notify @see FieldHtmlInjector that toolbars need to be injected
     * @see KnowledgeToolbar
     *
     * @param {Element} container
     */
    _notifyNewToolbars(container) {
        const toolbarsData = [];
        container.querySelectorAll('.o_knowledge_toolbar_anchor').forEach(function (container, anchor) {
            const type = Array.from(anchor.classList).find(className => className.startsWith('o_knowledge_toolbar_type_'));
            if (type) {
                toolbarsData.push({
                    container: container,
                    anchor: anchor,
                    type: type,
                });
            }
        }.bind(this, container));
        this.$editable.trigger('refresh_toolbars', { toolbarsData: toolbarsData });
    },
    /**
     * Notify @see FieldHtmlInjector that behaviors need to be injected
     * @see KnowledgeBehavior
     *
     * @param {Element} anchor
     */
    _notifyNewBehaviors(anchor) {
        const behaviorsData = [];
        const type = Array.from(anchor.classList).find(className => className.startsWith('o_knowledge_behavior_type_'));
        if (type) {
            behaviorsData.push({
                anchor: anchor,
                type: type,
            });
        }
        this.$editable.trigger('refresh_behaviors', { behaviorsData: behaviorsData});
    },
    /**
     * Insert a /toc block (table of content)
     */
    _insertTableOfContent: function () {
        const tocFragment = new DocumentFragment();
        const tocBlock = $(QWeb.render('knowledge.toc_block', {}))[0];
        tocFragment.append(tocBlock);
        const [container] = this.odooEditor.execCommand('insertFragment', tocFragment);
        this._notifyNewToolbars(container);
        this._notifyNewBehaviors(container);
    },
    /**
     * Insert a /template block
     */
    _insertTemplate() {
        const templateFragment = new DocumentFragment();
        const templateBlock = $(QWeb.render('knowledge.template_block', {}))[0];
        templateFragment.append(templateBlock);
        const [container] = this.odooEditor.execCommand('insertFragment', templateFragment);
        setCursorStart(container.querySelector('.o_knowledge_content > p'));
        this._notifyNewToolbars(container);
        this._notifyNewBehaviors(container);
    },
    /**
     * Insert a /article block (through a dialog)
     */
    _insertArticleLink: function () {
        const restoreSelection = preserveCursor(this.odooEditor.document);
        const dialog = new KnowledgeArticleLinkModal(this, {});
        dialog.on('save', this, article => {
            restoreSelection();
            if (article) {
                const articleLinkFragment = new DocumentFragment();
                const articleLinkBlock = $(QWeb.render('knowledge.wysiwyg_article_link', {
                    display_name: article.display_name,
                    href: '/knowledge/article/' + article.id,
                    article_id: article.id,
                }))[0];
                articleLinkFragment.append(articleLinkBlock);
                const [anchor] = this.odooEditor.execCommand('insertFragment', articleLinkFragment);
                this._notifyNewBehaviors(anchor);
            }
            dialog.close();
        });
        dialog.on('closed', this, () => {
            restoreSelection();
        });
        dialog.open();
    },
    /**
     * Notify the @see FieldHtmlInjector when a /file block is inserted from a
     * @see MediaDialog
     *
     * @private
     * @override
     */
    _onMediaDialogSave(params, element) {
        const result = this._super(...arguments);
        if (!result) {
            return;
        }
        const [container] = result;
        if (container.classList.contains('o_knowledge_file')) {
            setCursorStart(container.nextElementSibling);
            this._notifyNewToolbars(container);
            this._notifyNewBehaviors(container);
        }
        return result;
    },
});
