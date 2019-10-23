odoo.define('mail.component.ComposerTextInput', function (require) {
'use strict';

const ajax = require('web.ajax');
const utils = require('web.utils');

const { Component } = owl;
const { useDispatch, useGetters, useRef, useStore } = owl.hooks;

/**
 * Enforced empty content of the contenteditable. This is necessary because
 * a contenteditable may have many different value when empty, like "", "<br/>",
 * or even "<p><br/></p>". This is dependent of user interaction and browser
 * specific, hence this value is enforced when contenteditable should be empty.
 */
const EMPTY_HTML = "<p></p>";

/**
 * ComposerInput relies on a minimal HTML editor in order to support mentions.
 */
class ComposerTextInput extends Component {

    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);

        /**
         * Max frequency for searching for mention suggestions. Useful to
         * limit amount of RPC while user types something that starts a mention.
         */
        this.MENTION_THROTTLE = 200;
        this.storeDispatch = useDispatch();
        this.storeGetters = useGetters();
        this.storeProps = useStore(state => {
            return {
                isMobile: state.isMobile,
            };
        });
        /**
         * jQuery node reference to textarea that is used to configure
         * summernote editor on. Useful to invoke summernote commands.
         */
        this._$textarea = undefined;
        /**
         * Node reference of the contenteditable that is part of summernote
         * editor. Useful to interact with content of the composer.
         */
        this._editable = undefined;
        /**
         * Last tracked range in the contenteditable. Useful to correctly insert
         * some content at the correct position.
         */
        this._lastRange = undefined;
        /**
         * Reference of the textarea. Only useful to compute the jQuery node
         * reference of it...
         */
        this._textareaRef = useRef('textarea');
        /**
         * Tribute instance that has been configured on contenteditable of
         * summernote editor. Tribute is a small framework to enable mentions
         * in the contenteditable.
         */
        this._tribute = undefined; // list of tribute mentions (partner, canned responses, etc.)

        this._searchChannelMentionSuggestions = _.throttle(
            this._searchChannelMentionSuggestions.bind(this),
            this.MENTION_THROTTLE
        );
        this._searchPartnerMentionSuggestions = _.throttle(
            this._searchPartnerMentionSuggestions.bind(this),
            this.MENTION_THROTTLE
        );
    }

    /**
     * Load summernote, since this is not in the assets bundle.
     */
    willStart() {
        if (this.env.isTest) {
            return;
        }
        return ajax.loadLibs({
            assetLibs: ['web_editor.compiled_assets_wysiwyg'],
        });
    }

    /**
     * Configure summernote and tribute on mount
     */
    mounted() {
        const {
            $textarea,
            editable,
        } = this._configSummernote();
        const tribute = this._configTribute({ editable });

        this._$textarea = $textarea;
        this._editable = editable;
        this._tribute = tribute;

        if (this.props.initialHtmlContent) {
            this.setHtmlContent(this.props.initialHtmlContent);
        }
        this._update(); // remove initial <p></br></p>
    }

    willUnmount() {
        this._tribute.detach(this._editable);
        this._$textarea.summernote('destroy');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    focus() {
        this._editable.focus();
    }

    focusout() {
        this._editable.blur();
    }

    /**
     * @return {string}
     */
    getHtmlContent() {
        return this._editable.innerHTML;
    }

    /**
     * Insert some text content in the contenteditable.
     *
     * @param {string} textContent
     */
    insertTextContent(textContent) {
        if (!this._lastRange) {
            this._placeCursorAtEnd();
        } else if (this._lastRange.sc.nodeType === 3) {
            /**
             * Restore range only if it makes sense, i.e. it targets a text node.
             * This is not the case right after mentioning, in which the cursor
             * position is buggy. Summernote fallbacks by inserting content as
             * child of editor's container, which is very bad... This instead
             * insert text at the default position, which is the beginning of
             * the editor.
             */
            if (this._lastRange.so <= this._lastRange.sc.length) {
                this._$textarea.summernote('editor.restoreRange');
            } else {
                this._placeCursorAtEnd();
            }
        }
        this._$textarea.summernote('editor.insertText', textContent);
        this._update();
    }

    /**
     * Determine whether the editable is empty or not.
     *
     * @return {boolean}
     */
    isEmpty() {
        return this._editable.innerHTML === EMPTY_HTML;
    }

    reset() {
        this._editable.innerHTML = EMPTY_HTML;
        this._update();
    }

    /**
     * Insert some HTML content in the textarea. This is useful when we need
     * to restore the content in the contenteditable, while preserving the
     * mentions.
     *
     * @param {string} htmlContent
     */
    setHtmlContent(htmlContent) {
        this.focus();
        if (htmlContent.startsWith('<')) {
            this._$textarea.code(htmlContent);
        } else {
            this._$textarea.summernote('editor.pasteHTML', htmlContent);
        }
        this._placeCursorAtEnd();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Configure summernote editor using the textarea.
     *
     * @private
     * @return {Object}
     */
    _configSummernote() {
        const $textarea = $(this._textareaRef.el);

        $textarea.summernote({
            callbacks: {
                onPaste(ev) {
                    const bufferText = ((ev.originalEvent || ev).clipboardData ||
                        window.clipboardData).getData('Text');
                    ev.preventDefault();
                    document.execCommand('insertText', false, bufferText);
                },
            },
            disableDragAndDrop: true,
            disableResizeEditor: true,
            placeholder: this.env._t("Write something..."),
            popover: {
                image: [],
                link: [],
                air: [],
            },
            shortcuts: false,
            toolbar: false,
        });

        const editingArea = this.el.querySelector(':scope > .note-editor > .note-editing-area');
        const editable = editingArea.querySelector(':scope .note-editable');
        $textarea.summernote('removeModule', 'autoLink'); // conflict with this summernote module and tribute

        editable.classList.add('o_ComposerTextInput_editable');
        editable.addEventListener('click', ev => this._onClickEditable(ev));
        editable.addEventListener('input', ev => this._onInputEditable(ev));
        editable.addEventListener('keydown', ev => this._onKeydownEditable(ev));
        editable.addEventListener('keyup', ev => this._onKeyupEditable(ev));
        editable.addEventListener('selectionchange', ev => this._onSelectionChangeEditable(ev));

        return { $textarea, editable };
    }

    /**
     * Configure tribute with the contenteditable made with summernote editor.
     * This enables mentions.
     *
     * @private
     * @param {Object} param0
     * @param {HTMLElement} param0.editable
     * @return {Object} tribute object
     */
    _configTribute({ editable }) {
        const tribute = new window.Tribute({
            collection: [
                this._configTributeCollectionItemCannedResponse(),
                this._configTributeCollectionItemChannel(),
                this._configTributeCollectionItemCommand(),
                this._configTributeCollectionItemPartner(),
            ],
        });

        tribute.attach(editable);
        return tribute;
    }

    /**
     * Configure canned responses with tribute.
     *
     * @private
     * @return {Object}
     */
    _configTributeCollectionItemCannedResponse() {
        const self = this;
        const collectionItem = {
            lookup: 'source',
            menuItemTemplate(item) {
                return self.env.qweb.renderToString('mail.component.ComposerTextInput.CannedReponseMentionMenuItem', {
                    isMobile: self.storeProps.isMobile,
                    item,
                });
            },
            selectTemplate(item) {
                return item ? item.original.substitution : null;
            },
            trigger: ':',
            values(keyword, callback) {
                const cannedResponses = self._searchCannedResponseSuggestions(keyword);
                callback(cannedResponses);
            },
        };
        return collectionItem;
    }

    /**
     * Configure channel mentions with tribute.
     *
     * @private
     * @return {Object}
     */
    _configTributeCollectionItemChannel() {
        const self = this;
        const collectionItem = {
            lookup: 'name',
            menuItemTemplate(item) {
                return self.env.qweb.renderToString('mail.component.ComposerTextInput.ChannelMentionMenuItem', {
                    isMobile: self.storeProps.isMobile,
                    item,
                });
            },
            selectTemplate(item) {
                if (!item) {
                    // no match keeps mentioning state, hence handle no item selection
                    return null;
                }
                return self.env.qweb.renderToString('mail.component.ComposerTextInput.ChannelMentionSelectItem', { item });
            },
            trigger: '#',
            values(keyword, callback) {
                self._searchChannelMentionSuggestions(keyword, channels => callback(channels));
            },
        };
        return collectionItem;
    }

    /**
     * Configure commands with tribute.
     *
     * @private
     * @return {Object}
     */
    _configTributeCollectionItemCommand() {
        const self = this;
        const collectionItem = {
            lookup: 'name',
            menuItemTemplate(item) {
                return self.env.qweb.renderToString('mail.component.ComposerTextInput.CommandMentionMenuItem', {
                    isMobile: self.storeProps.isMobile,
                    item,
                });
            },
            selectTemplate(item) {
                return item ? '/' + item.original.name : null;
            },
            trigger: '/',
            values(keyword, callback) {
                const commands = self._searchCommandSuggestions(keyword);
                callback(commands);
            },
        };
        return collectionItem;
    }

    /**
     * Configure partner mentions with tribute.
     *
     * @private
     * @return {Object}
     */
    _configTributeCollectionItemPartner() {
        const self = this;
        const collectionItem = {
            lookup: 'name',
            menuItemTemplate(item) {
                return self.env.qweb.renderToString('mail.component.ComposerTextInput.PartnerMentionMenuItem', {
                    isMobile: self.storeProps.isMobile,
                    item,
                    partnerName: self.storeGetters.partnerName(item.original.localId),
                });
            },
            selectTemplate(item) {
                if (!item) {
                    // no match may keep mentioning state, hence handle no item selection
                    return null;
                }
                return self.env.qweb.renderToString('mail.component.ComposerTextInput.PartnerMentionSelectItem', {
                    item,
                    partnerName: self.storeGetters.partnerName(item.original.localId),
                });
            },
            trigger: '@',
            values(keyword, callback) {
                self._searchPartnerMentionSuggestions(keyword, partners => callback(partners));
            },
        };
        return collectionItem;
    }

    /**
     * Places the cursor at the end of a contenteditable container
     * (should also work for textarea / input)
     *
     * @private
     */
    _placeCursorAtEnd() {
        const el = this._editable;
        const childLength = el.childNodes.length;
        if (childLength === 0) {
            return;
        }
        const range = document.createRange();
        const sel = window.getSelection();
        const lastNode = el.childNodes[childLength - 1];
        const lastNodeChildren = lastNode.childNodes.length;
        range.setStart(lastNode, lastNodeChildren);
        range.collapse(true);
        sel.removeAllRanges();
        sel.addRange(range);
    }

    /**
     * Save the range of the contenteditable. This is useful in order to set
     * content in it at the correct position, after losing the focus, such as
     * when adding an emoji from the emoji button.
     *
     * @private
     */
    _saveRange() {
        this._$textarea.summernote('editor.saveRange');
        if (this.isEmpty()) {
            this._lastRange = undefined;
        } else {
            this._lastRange = this._$textarea.summernote('editor.createRange');
        }
    }

    /**
     * Search available canned responses based on typed characters after the
     * canned response mention trigger character.
     *
     * @private
     * @param {string} keyword
     * @returns {Object[]}
     */
    _searchCannedResponseSuggestions(keyword) {
        const cannedResponseList = Object.values(this.env.store.state.cannedResponses);
        const matches = fuzzy.filter(
            utils.unaccent(keyword),
            cannedResponseList.map(cannedResponse => cannedResponse.source));
        return matches.slice(0, 10).map(match => cannedResponseList[match.index]);
    }

    /**
     * Search available channel mentions suggestions based on typed characters
     * after the channel mention trigger character.
     *
     * @private
     * @param {string} keyword
     * @param {function} callback
     */
    async _searchChannelMentionSuggestions(keyword, callback) {
        const suggestions = await this.env.rpc({
            model: 'mail.channel',
            method: 'get_mention_suggestions',
            kwargs: {
                limit: 10,
                search: keyword,
            },
        });
        callback(suggestions);
    }

    /**
     * Search available commands based on typed characters after the command
     * trigger character. This should only work when the trigger character is
     * the 1st character in the contenteditable, because commands should only
     * work on the whole composer text input content.
     *
     * @private
     * @param {string} keyword
     * @return {Object[]}
     */
    _searchCommandSuggestions(keyword) {
        const selection = window.getSelection();
        if (!selection) {
            return [];
        }
        if (!selection.anchorNode) {
            return [];
        }
        if (!selection.anchorNode.parentNode) {
            return [];
        }

        /**
         * @return {DOMNode}
         */
        function getAnchorParentFirstChildNotEmptyText() {
            return Array.prototype.find.call(selection.anchorNode.parentNode.childNodes, childNode =>
                childNode.nodeType !== 3 || childNode.textContent.trim().length !== 0);
        }

        if (getAnchorParentFirstChildNotEmptyText() !== selection.anchorNode) {
            return [];
        }

        if (this._tribute.current.selectedOffset - 1 !== keyword.length) {
            return [];
        }

        const commandList = Object.values(this.env.store.state.commands);
        const matches = fuzzy.filter(
            utils.unaccent(keyword),
            commandList.map(command => command.name));
        return matches.slice(0, 10).map(match => commandList[match.index]);
    }

    /**
     * Search available partner mention suggestions based on typed characters
     * after the partner mention trigger character.
     *
     * @private
     * @param {string} keyword
     * @param {function} callback
     */
    async _searchPartnerMentionSuggestions(keyword, callback) {
        this.storeDispatch('searchPartners', { callback, keyword, limit: 10 });
    }

    /**
     * Called when contenteditable content should be checked for emptiness.
     * Useful to enforce html value for "empty".
     *
     * @private
     */
    _update() {
        if (this._editable.textContent.length === 0) {
            this._editable.innerHTML = EMPTY_HTML;
        }
        this._editable.classList.toggle('o-empty', this.isEmpty());
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when clicking on the contenteditable.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickEditable(ev) {
        this._saveRange();
    }

    /**
     * Called whenever there are changes on the contenteditable.
     *
     * @private
     * @param {KeyboardEvent} ev
     */
    _onInputEditable(ev) {
        this._update();
        this._saveRange();
        this.trigger('o-input-composer-text-input');
    }

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydownEditable(ev) {
        this._saveRange();
        switch (ev.key) {
            case 'Backspace':
                this._onKeydownEditableBackspace(ev);
                break;
            case 'Enter':
                this._onKeydownEditableEnter(ev);
                break;
            case 'Escape':
                this._onKeydownEditableEscape(ev);
                break;
            default:
                break;
        }
    }

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeyupEditable(ev) {
        this._saveRange();
    }

    /**
     * Force deleting contenteditable = 'false' inside editable.
     * It works by default on Chrome and Safari works fine, but not on Firefox
     * due to following bug:
     * https://bugzilla.mozilla.org/show_bug.cgi?id=685452
     *
     * Adapted code from:
     * https://stackoverflow.com/questions/2177958/how-to-delete-an-html-element-inside-a-div-with-attribute-contenteditable/30574622#30574622
     *
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydownEditableBackspace(ev) {
        if (this.isEmpty()) {
            return;
        }
        const selection = window.getSelection();
        if (!selection.isCollapsed || !selection.rangeCount) {
            return;
        }
        const curRange = selection.getRangeAt(selection.rangeCount - 1);
        if (curRange.commonAncestorContainer.nodeType === 3 && curRange.startOffset > 0) {
            // we are in child selection. The characters of the text node is being deleted
            return;
        }

        const range = document.createRange();
        if (selection.anchorNode !== ev.target) {
            // selection is in character mode. expand it to the whole editable field
            range.selectNodeContents(ev.target);
            range.setEndBefore(selection.anchorNode);
        } else if (selection.anchorOffset > 0) {
            range.setEnd(ev.target, selection.anchorOffset);
        } else {
            // reached the beginning of editable field
            return;
        }
        try {
            range.setStart(ev.target, range.endOffset - 2);
        } catch (err) {
            return;
        }
        const previousNode = range.cloneContents().lastChild;
        if (previousNode) {
            if (previousNode.contentEditable === 'false') {
                range.deleteContents();
                ev.preventDefault();
            }
            /**
             * Prevent cursor bug in Firefox with contenteditable='false'
             * inside contenteditable='true', by having more aggressive delete
             * behaviour:
             * https://bugzilla.mozilla.org/show_bug.cgi?id=685452
             */
            const formerPreviousNode = previousNode.previousSibling;
            if (formerPreviousNode && formerPreviousNode.contentEditable === 'false') {
                range.deleteContents();
                ev.preventDefault();
            }
        }
        this._update();
    }

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydownEditableEnter(ev) {
        if (this._tribute.isActive) {
            return;
        }
        if (ev.shiftKey) {
            return;
        }
        if (this.storeProps.isMobile) {
            return;
        }
        this.trigger('o-keydown-enter');
        ev.preventDefault();
    }

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydownEditableEscape(ev) {
        if (this._editable.innerHTML.length !== 0) {
            return;
        }
        this.trigger('o-discard');
        ev.preventDefault();
    }

    /**
     * @private
     * @param {Event} ev
     */
    _onSelectionChangeEditable(ev) {
        this._saveRange();
    }
}

ComposerTextInput.props = {
    initialHtmlContent: {
        type: String,
        optional: true,
    },
};

ComposerTextInput.template = 'mail.component.ComposerTextInput';

return ComposerTextInput;

});
