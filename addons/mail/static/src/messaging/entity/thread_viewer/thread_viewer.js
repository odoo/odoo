odoo.define('mail.messaging.entity.ThreadViewer', function (require) {
'use strict';

const { registerNewEntity } = require('mail.messaging.entity.core');

function ThreadViewerFactory({ Entity }) {

    class ThreadViewer extends Entity {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * This function register a hint for the component related to this
         * entity. Hints are information on changes around this viewer that
         * make require adjustment on the component. For instance, if this
         * thread viewer initiated a thread cache load and it now has become
         * loaded, then it may need to auto-scroll to last message.
         *
         * @param {string} hintType name of the hint. Used to determine what's
         *   the broad type of adjustement the component has to do.
         * @param {any} [hintData] data of the hint. Used to fine-tune
         *   adjustments on the component.
         */
        addComponentHint(hintType, hintData) {
            const hint = this._makeComponentHint(hintType, hintData);
            this.update({
                componentHintList: this.componentHintList.concat([hint]),
            });
        }

        /**
         * @returns {mail.messaging.entity.Message[]}
         */
        get checkedMessages() {
            const threadCache = this.threadCache;
            if (!threadCache) {
                return [];
            }
            return threadCache.checkedMessages;
        }

        /**
         * @param {Object} hint
         */
        markComponentHintProcessed(hint) {
            let filterFun;
            switch (hint.type) {
                case 'current-partner-just-posted-message':
                    filterFun = h => h.type !== hint.type && h.messageId !== hint.messageId;
                    break;
                default:
                    filterFun = h => h.type !== hint.type;
                    break;
            }
            this.update({
                componentHintList: this.componentHintList.filter(filterFun)
            });
        }

        /**
         * @returns {mail.messaging.entity.Message[]}
         */
        get messages() {
            const threadCache = this.threadCache;
            if (!threadCache) {
                return [];
            }
            return threadCache.messages;
        }

        /**
         * @param {string} scrollTop
         */
        saveThreadCacheScrollPositionsAsInitial(scrollTop) {
            if (!this.threadCache) {
                return;
            }
            this.update({
                threadCacheInitialScrollPositions: Object.assign({}, this.threadCacheInitialScrollPositions, {
                    [this.threadCache.localId]: scrollTop,
                }),
            });
        }

        /**
         * @returns {mail.messaging.entity.ThreadCache|undefined}
         */
        get threadCache() {
            if (!this.thread) {
                return undefined;
            }
            return this.thread.cache(this.stringifiedDomain);
        }

        /**
         * @returns {integer|undefined}
         */
        get threadCacheInitialPosition() {
            if (!this.threadCache) {
                return undefined;
            }
            return this.threadCacheInitialScrollPositions[this.threadCache.localId];
        }

        /**
         * @returns {mail.messaging.entity.Message[]}
         */
        get uncheckedMessages() {
            const threadCache = this.threadCache;
            if (!threadCache) {
                return [];
            }
            return threadCache.uncheckedMessages;
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @param {string} hintType
         * @param {any} hintData
         * @returns {Object}
         */
        _makeComponentHint(hintType, hintData) {
            let hint;
            switch (hintType) {
                case 'change-of-thread-cache':
                    hint = { type: hintType };
                    break;
                case 'current-partner-just-posted-message':
                    hint = {
                        messageId: hintData,
                        type: hintType,
                    };
                    break;
                case 'more-messages-loaded':
                    hint = { type: hintType };
                    break;
                default:
                    throw new Error(`Undefined component hint "${hintType}" for ThreadViewer`);
            }
            return hint;
        }

        /**
         * @override
         */
        _update(data) {
            const {
                /**
                 * List of component hints. Hints contain information that help
                 * components make UI/UX decisions based on their UI state.
                 * For instance, on receiving new messages and the last message
                 * is visible, it should auto-scroll to this new last message.
                 *
                 * Format of a component hint:
                 *
                 *   {
                 *       type: {string} the name of the component hint. Useful
                 *                      for components to dispatch behaviour
                 *                      based on its type.
                 *       data: {Object} data related to the component hint.
                 *                      For instance, if hint suggests to scroll
                 *                      to a certain message, data may contain
                 *                      message id.
                 *   }
                 */
                componentHintList = this.componentHintList || [],
                stringifiedDomain = this.stringifiedDomain,
                thread,
                /**
                 * List of saved initial scroll positions of thread caches.
                 * Useful to restore scroll position on changing back to this
                 * thread cache. Note that this is only applied when opening
                 * the thread cache, because scroll position may change fast so
                 * save is already throttled
                 */
                threadCacheInitialScrollPositions = this.threadCacheInitialScrollPositions || {},
            } = data;

            const prevThreadCache = this.threadCache;

            this._write({
                componentHintList,
                stringifiedDomain,
                threadCacheInitialScrollPositions,
            });

            if (thread && this.thread !== thread) {
                this.link({ thread });
                if (!this.threadCache.isLoaded && !this.threadCache.isLoading) {
                    this.threadCache.loadMessages();
                }
            }
            if (this.threadCache !== prevThreadCache) {
                this._writeComponentHint('change-of-thread-cache');
            }
        }

        /**
         * @private
         * @param {string} hintType
         * @param {any} hintData
         */
        _writeComponentHint(hintType, hintData) {
            const hint = this._makeComponentHint(hintType, hintData);
            this._write({
                componentHintList: this.componentHintList.concat([hint]),
            });
        }

    }

    Object.assign(ThreadViewer, {
        relations: Object.assign({}, Entity.relations, {
            chatter: {
                inverse: 'threadViewer',
                to: 'Chatter',
                type: 'one2one',
            },
            chatWindow: {
                inverse: 'threadViewer',
                isCausal: true,
                to: 'ChatWindow',
                type: 'one2one',
            },
            discuss: {
                inverse: 'threadViewer',
                to: 'Discuss',
                type: 'one2one',
            },
            thread: {
                inverse: 'viewers',
                to: 'Thread',
                type: 'many2one',
            },
        }),
    });

    return ThreadViewer;
}

registerNewEntity('ThreadViewer', ThreadViewerFactory);

});
