/** @odoo-module */

import Class from 'web.Class';
import core from 'web.core';
import Dialog from "web.Dialog";
const _t = core._t;

/**
 * Behavior to be injected through @see FieldHtmlInjector to @see OdooEditor
 * blocks which have specific classes calling for such behaviors.
 *
 * A typical usage could be the following:
 * - An @see OdooEditor block like /template has the generic class:
 *   @see o_knowledge_behavior_anchor to signify that it needs to have a
 *   behavior injected.
 * - This block also has the specific class:
 *   @see o_knowledge_behavior_type_[behaviorType] which specifies the type of
 *   behavior that needs to be injected. @see FieldHtmlInjector has a dictionary
 *   mapping those classes to the correct behavior class.
 *
 * The @see KnowledgeBehavior is a basic behavior intended to be overriden for
 * more complex implementations
 */
const KnowledgeBehavior = Class.extend({
    /**
     * @param {Widget} handler @see FieldHtmlInjector which has access to
     *                         widget specific functions
     * @param {Element} anchor dom node to apply the behavior to
     * @param {string} mode edit/readonly
     */
    init: function (handler, anchor, mode) {
        this.handler = handler;
        this.anchor = anchor;
        this.mode = mode;
        if (this.handler.editor) {
            this.handler.editor.observerUnactive('knowledge_attributes');
        }
        this.applyAttributes();
        if (this.handler.editor) {
            this.handler.editor.observerActive('knowledge_attributes');
        }
        this.applyListeners();
    },
    /**
     * Add specific attributes related to this behavior to this.anchor
     */
    applyAttributes: function () {},
    /**
     * Add specific listeners related to this behavior to this.anchor
     */
    applyListeners: function () {},
    /**
     * Disable the listeners added in @see applyListeners
     */
    disableListeners: function () {},
    /**
     * Used by @see KnowledgePlugin to remove behaviors when the field_html is
     * saved. Also used by @see FieldHtmlInjector to manage injected behaviors
     */
    removeBehavior: function () {
        this.handler.trigger_up('behavior_removed', {
            anchor: this.anchor,
        });
        this.disableListeners();
        delete this.anchor.oKnowledgeBehavior;
    },
});

/**
 * A behavior to set a block as uneditable. Such a block can have children
 * marked as @see o_knowledge_content which are set as editable
 */
const ContentsContainerBehavior = KnowledgeBehavior.extend({
    /**
     * @override
     */
    applyAttributes: function () {
        this._super.apply(this, arguments);
        if (this.mode === 'edit') {
            this.anchor.querySelectorAll('.o_knowledge_content').forEach(element => {
                element.setAttribute('contenteditable', 'true');
            });
            this.anchor.setAttribute('contenteditable', 'false');
        }
    },
});
/**
 * A behavior for the /article command @see Wysiwyg
 */
const ArticleBehavior = KnowledgeBehavior.extend({
    /**
     * @override
     */
    init: function () {
        this.busy = false;
        this.linkClickHandler = async function (ev) {
            if (this.busy) {
                ev.preventDefault();
                ev.stopPropagation();
            } else {
                this.busy = true;
                await this._onLinkClick(ev);
                this.busy = false;
            }
        }.bind(this);
        this.linkDblClickHandler = function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
        };
        this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    applyAttributes: function () {
        this._super.apply(this, arguments);
        if (this.mode === 'edit') {
            this.anchor.setAttribute('contenteditable', 'false');
        }
        this.anchor.setAttribute('target', '_blank');
    },
    /**
     * @override
     */
    applyListeners: function () {
        this._super.apply(this, arguments);
        this.anchor.addEventListener("click", this.linkClickHandler);
        this.anchor.addEventListener("dblclick", this.linkDblClickHandler);
    },
    /**
     * @override
     */
    disableListeners: function () {
        this._super.apply(this, arguments);
        this.anchor.removeEventListener("click", this.linkClickHandler);
        this.anchor.removeEventListener("dblclick", this.linkDblClickHandler);
    },
    /**
     * When the user clicks on an article link, we can directly open the
     * article in the current view without having to reload the page.
     *
     * @param {Event} event
     */
    _onLinkClick: async function (event) {
        const res_id = parseInt(event.currentTarget.href.slice(event.currentTarget.href.lastIndexOf('/') + 1));
        if (res_id && event.currentTarget.closest('.o_knowledge_editor')) {
            event.stopPropagation();
            event.preventDefault();
            const actionPromise = this.handler.do_action('knowledge.ir_actions_server_knowledge_home_page', {
                additional_context: {
                    res_id: res_id
                }
            });
            await actionPromise.catch(() => {
                Dialog.alert(this,
                    _t("This article was deleted or you don't have the rights to access it."), {
                    title: _t('Error'),
                });
            });
        }
    },
});
/**
 * A behavior for the /file command @see Wysiwyg
 */
const FileBehavior = ContentsContainerBehavior.extend({
    init: function (handler, anchor, mode) {
        this.fileNameEl = anchor.querySelector('.o_knowledge_file_name');
        this.focusFileNameHandler = this._onFocusFileName.bind(this);
        this.focusOutFileNameHandler = this._onFocusOutFileName.bind(this);
        this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    applyListeners: function () {
        this._super.apply(this, arguments);
        this.fileNameEl.addEventListener("focus", this.focusFileNameHandler);
        this.fileNameEl.addEventListener("focusout", this.focusOutFileNameHandler);
    },
    disableListeners: function () {
        this._super.apply(this, arguments);
        this.fileNameEl.removeEventListener("focus", this.focusFileNameHandler);
        this.fileNameEl.removeEventListener("focusout", this.focusOutFileNameHandler);
    },
    _onFocusFileName: function (ev) {
        if (this.handler.editor) {
            this.handler.editor.observerUnactive('knowledge_attributes');
        }
        ev.currentTarget.classList.add('o_knowledge_file_name_edit');
        if (this.handler.editor) {
            this.handler.editor.observerActive('knowledge_attributes');
        }
    },
    /**
     * Edit the file url so that the proposed filename is the customized one
     * from the article. The attachment name stored in the database is unchanged
     */
    _onFocusOutFileName: function (ev) {
        // convert any number of URL/filename unsafe/forbidden characters:
        // !',;:@&=%#>< *()+$/?[]|\ to one underscore '_', and trim the result
        // to 80 characters
        ev.currentTarget.textContent = ev.currentTarget.textContent.replace(/[_!',;:@&=%#><\s\*\(\)\+\$\/\?\[\]\|\\]+/g, '_').substring(0, 80);
        this.handler.editor.historyStep();
        if (this.handler.editor) {
            this.handler.editor.observerUnactive('knowledge_attributes');
        }
        const fileElement = ev.currentTarget.closest('.o_knowledge_file');
        const imageElement = fileElement.querySelector('.o_knowledge_file_image > a');
        const extension = fileElement.querySelector('.o_knowledge_file_extension').textContent;
        const previousName = imageElement.getAttribute('title');
        let currentName = ev.currentTarget.textContent;
        if (previousName !== currentName) {
            let href = imageElement.getAttribute('href');
            if (previousName) {
                // remove the previous name from the URL
                href = href.split(`/${previousName}`).join('');
            }
            const hrefParts = href.split('?');
            if (extension && currentName.includes('.') && !currentName.toLowerCase().endsWith(extension.toLowerCase())) {
                // append the correct file extension if the name is ambiguous
                currentName += currentName.endsWith('.') ? extension : `.${extension}`;
            }
            imageElement.setAttribute('title', currentName);
            // insert the current name
            hrefParts.splice(1, 0, currentName ? `/${currentName}?` : '?');
            imageElement.setAttribute('href', hrefParts.join(''));
        }
        ev.currentTarget.classList.remove('o_knowledge_file_name_edit');
        if (this.handler.editor) {
            this.handler.editor.observerActive('knowledge_attributes');
        }
    }
});

export {
    KnowledgeBehavior,
    ContentsContainerBehavior,
    ArticleBehavior,
    FileBehavior,
};
