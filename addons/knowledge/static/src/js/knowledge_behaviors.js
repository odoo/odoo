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
    }
});

const HEADINGS = new Set([
    'H1',
    'H2',
    'H3',
    'H4',
    'H5',
    'H6',
]);
/**
 * A behavior for the /toc command @see Wysiwyg . This behavior use a
 * mutatiionObserver to listen to changes on <h1> -> <h6> nodes, and create
 * a table of contents. It is an extension of @see ContentsContainerBehavior
 */
const TableOfContentsBehavior = ContentsContainerBehavior.extend({
    /**
     * @override
     */
    init: function () {
        this.observer = new MutationObserver((mutationList) => {
            this.observer.disconnect();
            const update = mutationList.find(mutation => {
                let target = mutation.target;
                if (target) {
                    if (target.nodeType === Node.TEXT_NODE && target.parentElement) {
                        /**
                         * stop updating the TOC if the user is potentially
                         * in the process of typing a command for the
                         * @see PowerBox
                         */
                        if (target.data.includes('/')) {
                            return false;
                        }
                        target = target.parentElement;
                    }
                    return target.parentElement === this.handler.field && target.nodeType === Node.ELEMENT_NODE && HEADINGS.has(target.tagName);
                }
                return false;
            });
            setTimeout(() => {
                this._observeTableOfContents(!!update);
            }, 50);
        });
        this.tocLinkClickHandler = this._onTocLinkClick.bind(this);
        this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    applyAttributes: function () {
        this._super.apply(this, arguments);
        if (this.mode === 'edit') {
            this.anchor.querySelectorAll('a').forEach(element => {
                element.setAttribute('contenteditable', 'false');
            });
        }
    },
    /**
     * @override
     */
    applyListeners: function () {
        this._super.apply(this, arguments);
        $(this.anchor).on('click', '.o_toc_link', this.tocLinkClickHandler);
        if (this.mode === 'edit') {
            this._observeTableOfContents();
        }
    },
    /**
     * @override
     */
    disableListeners: function () {
        $(this.anchor).off('click', '.o_toc_link', this.tocLinkClickHandler);
        if (this.mode === 'edit') {
            this.observer.disconnect();
        }
    },
    /**
     * @param {boolean} update whether the toc needs to be updated
     */
    _observeTableOfContents: function (update=true) {
        if (update) {
            this._updateTableOfContents();
        }
        this.observer.observe(this.handler.field, {
            childList: true,
            attributes: false,
            subtree: true,
            characterData: true,
        });
    },
    /**
     * Construct the TOC
     */
    _updateTableOfContents: function () {
        var doc = $(this.handler.field);
        const $toc = doc.find('.o_knowledge_toc_content');
        this.handler.editor.observerUnactive('knowledge_toc_update');
        if ($toc.length) {
            $toc.empty();
            const stack = [];
            const $titles = doc.find('h1,h2,h3,h4,h5,h6').filter(function () {
                return $(this).text().trim().length > 0;
            });
            let prevLevel = 0;
            $titles.each((_index, title) => {
                const level = ~~title.tagName.substring(1);
                if (level > stack.length && level > prevLevel) {
                    const $ol = $('<ol/>');
                    if (stack.length > 0) {
                        const $li = $('<li/>');
                        $li.append($ol);
                        stack[stack.length - 1].append($li);
                    }
                    stack.push($ol);
                }
                while (level < stack.length) {
                    stack.pop();
                }
                prevLevel = level;
                const $title = $(title);
                const $a = $('<a contenteditable="false" class="oe_unremovable o_no_link_popover o_toc_link" href="#" id="' + _index + '"/>');
                $a.text($title.text());
                const $li = $('<li/>');
                $li.append($a);
                stack[stack.length - 1].append($li);
            });
            if (stack.length > 0) {
                $toc.append(stack[0].get(0));
            }
            else {
                $toc.append($('<i/>').text(_t('No heading found in this document.')));
            }
        }
        this.handler.editor.observerActive('knowledge_toc_update');
    },
    /**
     * Scroll through the view to display the matching heading
     *
     * @param {Event} event
     */
    _onTocLinkClick: function (event) {
        event.preventDefault();
        const id = event.target.id;
        const el = $(this.handler.field).find('h1, h2, h3, h4, h5, h6')[id];
        if (el){
            el.scrollIntoView({
                behavior: 'smooth',
            });
            el.setAttribute('highlight', true);
            setTimeout(() => {
                el.removeAttribute('highlight');
            }, 2000);
        }
        else{
            this._updateTableOfContents();
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
        const res_id = parseInt(event.currentTarget.dataset.res_id);
        if (res_id) {
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

export {
    KnowledgeBehavior,
    ContentsContainerBehavior,
    ArticleBehavior,
    TableOfContentsBehavior,
};
