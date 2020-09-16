odoo.define('mail/static/src/models/thread_viewer/thread_viewer.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2one, one2one } = require('mail/static/src/model/model_field_utils.js');

function factory(dependencies) {

    class ThreadViewer extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @param {string} scrollTop
         */
        saveThreadCacheScrollPositionsAsInitial(scrollTop) {
            if (!this.__mfield_threadCache(this)) {
                return;
            }
            this.update({
                __mfield_threadCacheInitialScrollPositions: Object.assign(
                    {},
                    this.__mfield_threadCacheInitialScrollPositions(this),
                    {
                        [this.__mfield_threadCache(this).localId]: scrollTop,
                    }
                ),
            });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasThreadView() {
            if (this.__mfield_chatter(this)) {
                return this.__mfield_chatter(this).__mfield_hasThreadView(this);
            }
            if (this.__mfield_chatWindow(this)) {
                return this.__mfield_chatWindow(this).__mfield_hasThreadView(this);
            }
            if (this.__mfield_discuss(this)) {
                return this.__mfield_discuss(this).__mfield_hasThreadView(this);
            }
            return this.__mfield_hasThreadView(this);
        }

        /**
         * @private
         * @returns {string}
         */
        _computeStringifiedDomain() {
            if (this.__mfield_chatter(this)) {
                return '[]';
            }
            if (this.__mfield_chatWindow(this)) {
                return '[]';
            }
            if (this.__mfield_discuss(this)) {
                return this.__mfield_discuss(this).__mfield_stringifiedDomain(this);
            }
            return this.__mfield_stringifiedDomain(this);
        }

        /**
         * @private
         * @returns {mail.thread|undefined}
         */
         _computeThread() {
            if (this.__mfield_chatter(this)) {
                if (!this.__mfield_chatter(this).__mfield_thread(this)) {
                    return [['unlink']];
                }
                return [['link', this.__mfield_chatter(this).__mfield_thread(this)]];
            }
            if (this.__mfield_chatWindow(this)) {
                if (!this.__mfield_chatWindow(this).__mfield_thread(this)) {
                    return [['unlink']];
                }
                return [['link', this.__mfield_chatWindow(this).__mfield_thread(this)]];
            }
            if (this.__mfield_discuss(this)) {
                if (!this.__mfield_discuss(this).__mfield_thread(this)) {
                    return [['unlink']];
                }
                return [['link', this.__mfield_discuss(this).__mfield_thread(this)]];
            }
            return [];
        }

        /**
         * @private
         * @returns {mail.thread_cache|undefined}
         */
        _computeThreadCache() {
            if (!this.__mfield_thread(this)) {
                return [['unlink']];
            }
            return [['link', this.__mfield_thread(this).cache(this.__mfield_stringifiedDomain(this))]];
        }

        /**
         * @private
         * @returns {mail.thread_viewer|undefined}
         */
        _computeThreadView() {
            if (!this.__mfield_hasThreadView(this)) {
                return [['unlink']];
            }
            if (this.__mfield_threadView(this)) {
                return [];
            }
            return [['create']];
        }

    }

    ThreadViewer.fields = {
        /**
         * States the `mail.chatter` managing `this`. This field is computed
         * through the inverse relation and should be considered read-only.
         */
        __mfield_chatter: one2one('mail.chatter', {
            inverse: '__mfield_threadViewer',
        }),
        /**
         * Serves as compute dependency.
         */
        __mfield_chatterHasThreadView: attr({
            related: '__mfield_chatter.__mfield_hasThreadView',
        }),
        /**
         * Serves as compute dependency.
         */
        __mfield_chatterThread: many2one('mail.thread', {
            related: '__mfield_chatter.__mfield_thread',
        }),
        /**
         * States the `mail.chat_window` managing `this`. This field is computed
         * through the inverse relation and should be considered read-only.
         */
        __mfield_chatWindow: one2one('mail.chat_window', {
            inverse: '__mfield_threadViewer',
        }),
        /**
         * Serves as compute dependency.
         */
        __mfield_chatWindowHasThreadView: attr({
            related: '__mfield_chatWindow.__mfield_hasThreadView',
        }),
        /**
         * Serves as compute dependency.
         */
        __mfield_chatWindowThread: many2one('mail.thread', {
            related: '__mfield_chatWindow.__mfield_thread',
        }),
        /**
         * States the `mail.discuss` managing `this`. This field is computed
         * through the inverse relation and should be considered read-only.
         */
        __mfield_discuss: one2one('mail.discuss', {
            inverse: '__mfield_threadViewer',
        }),
        /**
         * Serves as compute dependency.
         */
        __mfield_discussHasThreadView: attr({
            related: '__mfield_discuss.__mfield_hasThreadView',
        }),
        /**
         * Serves as compute dependency.
         */
        __mfield_discussStringifiedDomain: attr({
            related: '__mfield_discuss.__mfield_stringifiedDomain',
        }),
        /**
         * Serves as compute dependency.
         */
        __mfield_discussThread: many2one('mail.thread', {
            related: '__mfield_discuss.__mfield_thread',
        }),
        /**
         * Determines whether `this.thread` should be displayed.
         */
        __mfield_hasThreadView: attr({
            compute: '_computeHasThreadView',
            default: false,
            dependencies: [
                '__mfield_chatterHasThreadView',
                '__mfield_chatWindowHasThreadView',
                '__mfield_discussHasThreadView',
            ],
        }),
        /**
         * Determines the domain to apply when fetching messages for `this.thread`.
         */
        __mfield_stringifiedDomain: attr({
            compute: '_computeStringifiedDomain',
            default: '[]',
            dependencies: [
                '__mfield_discussStringifiedDomain',
            ],
        }),
        /**
         * Determines the `mail.thread` that should be displayed by `this`.
         */
        __mfield_thread: many2one('mail.thread', {
            compute: '_computeThread',
            dependencies: [
                '__mfield_chatterThread',
                '__mfield_chatWindowThread',
                '__mfield_discussThread',
            ],
        }),
        /**
         * States the `mail.thread_cache` that should be displayed by `this`.
         */
        __mfield_threadCache: many2one('mail.thread_cache', {
            compute: '_computeThreadCache',
            dependencies: [
                '__mfield_stringifiedDomain',
                '__mfield_thread',
            ],
        }),
        /**
         * Determines the initial scroll positions of thread caches.
         * Useful to restore scroll position on changing back to this
         * thread cache. Note that this is only applied when opening
         * the thread cache, because scroll position may change fast so
         * save is already throttled.
         */
        __mfield_threadCacheInitialScrollPositions: attr({
            default: {},
        }),
        /**
         * States the `mail.thread_view` currently displayed and managed by `this`.
         */
        __mfield_threadView: one2one('mail.thread_view', {
            compute: '_computeThreadView',
            dependencies: [
                '__mfield_hasThreadView',
            ],
            inverse: '__mfield_threadViewer',
            isCausal: true,
        }),
    };

    ThreadViewer.modelName = 'mail.thread_viewer';

    return ThreadViewer;
}

registerNewModel('mail.thread_viewer', factory);

});
