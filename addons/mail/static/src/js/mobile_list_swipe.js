/**
 * Allows to add swipe actions (left and right) on DOM elements
 */
var mobileUtils = (function () {
    'use strict';
    return {
        _listSwipeData: {},
        listSwipe: function (target, options) {
            this._options = _.extend({
                itemSelector: '>', // The item in the list that has the side actions
                itemActionWidth: 80, // In pixels
                leftAction: true, // Whether there is an action on the left
                rightAction: true, // Whether there is an action on the right
                snapThreshold: 0.8, // Percent threshold for snapping to position on touch end
                closeOnOpen: true, // Close other item actions if a new one is moved
                maxYDelta: 40, // Number of pixels in the Y-axis before preventing swiping
                initialXDelta: 25, // Number of pixels in the X-axis before allowing swiping
            }, options);
            // When swipped Left to Right
            this._onRightSwipe = options.onRightSwipe;
            // When swipped Right to Left
            this._onLeftSwipe = options.onLeftSwipe;
            // Called when item moving with touch and returns true if action allowed
            this._allowAction = options.allowAction;
            // Called when item moving with touch
            this._onElementMoving = options.onElementMoving;
            this._target = target.get(0);
            this._items = this._target.querySelectorAll(options.itemSelector);
            this._items.forEach((el) => {
                let touchStart = (ev) => this._onTouchStart(ev);
                let touchMove = (ev) => this._onTouchMove(ev);
                let touchEnd = (ev) => this._onTouchEnd(ev);
                el.removeEventListener('touchstart', touchStart, false);
                el.removeEventListener('touchmove', touchMove, false);
                el.removeEventListener('touchend', touchEnd, false);
                el.addEventListener('touchstart', touchStart, false);
                el.addEventListener('touchmove', touchMove, false);
                el.addEventListener('touchend', touchEnd, false);
            });
        },
        _getTouchPositions: function (event) {
            return {
                x: event.changedTouches[0].clientX,
                y: event.changedTouches[0].clientY
            };
        },
        _getTouchDelta: function (touch, data, settings) {
            let xDelta = touch.x - data.touchStart.x + data.startLeft;
            let yDelta = touch.y - data.touchStart.y;
            if ((!settings.rightAction && xDelta < 0) || (!settings.leftAction && xDelta > 0)) {
                xDelta = 0;
            }
            return {
                xDelta: xDelta,
                yDelta: yDelta
            };
        },
        _calculateTouchDelta: function (touch, data, settings) {
            let touchDelta = this._getTouchDelta(touch, data, settings);
            let xThreshold = Math.abs(touchDelta.xDelta) / settings.itemActionWidth;
            if (xThreshold >= settings.snapThreshold) {
                touchDelta.xDelta = (touchDelta.xDelta < 0) ? -settings.itemActionWidth : settings.itemActionWidth;
            } else {
                touchDelta.xDelta = 0;
            }
            return touchDelta;
        },
        _onTouchStart: function (ev) {
            let listItem = ev.currentTarget;
            let options = this._options;
            if (options.closeOnOpen) {
                this._items.forEach(function(el) {
                    if (listItem != el) {
                        el.style.left = '0px';
                    }
                });
            }
            let touch = this._getTouchPositions(ev);
            let rawStartLeft = listItem.style.left || 0;
            let dataId = _.uniqueId('_listSwipe_data_');
            let data = {
                touchStart: touch,
                startLeft: rawStartLeft === 'auto' ? 0 : parseInt(rawStartLeft),
                initialXDeltaReached: false,
                maxYDeltaReached: false,
                allowAction: {
                    left: options.leftAction,
                    right: options.rightAction
                }
            };
            this._listSwipeData[dataId] = data;
            listItem.setAttribute('data-listSwipe', dataId);
        },
        _onTouchMove: function (ev) {
            let listItem = ev.currentTarget;
            let dataId = listItem.getAttribute("data-listSwipe");
            let data = this._listSwipeData[dataId];
            let touch = this._getTouchPositions(ev);
            let settings = this._options;
            if (data.maxYDeltaReached) {
                return;
            }
            // Check for action to allow based on action and delta
            let touchDelta = this._calculateTouchDelta(touch, data, settings);
            if (this._allowAction) {
                let action = touchDelta.xDelta > 0 ? 'left' : touchDelta.xDelta < 0 ? 'right' : false;
                if (!this._allowAction(ev, action, touchDelta.xDelta)) {
                    data.allowAction[action] = false;
                    this._listSwipeData[dataId] = data;
                    return;
                } else {
                    data.allowAction[action] = (action == "left" ? settings.leftAction : settings.rightAction);
                }
            }

            touchDelta = this._getTouchDelta(touch, data, settings);
            let actionButton = touchDelta.xDelta > 0 ? 'left' : touchDelta.xDelta < 0 ? 'right' : false;
            if (actionButton) {
                listItem.querySelector(".swipe-action." + actionButton).style.left = -touchDelta.xDelta + 'px';
            }
            if (!data.maxYDeltaReached && Math.abs(touchDelta.yDelta) > settings.maxYDelta) {
                data.maxYDeltaReached = true;
                listItem.style.left = '0px';
            } else if (!data.initialXDeltaReached && Math.abs(touchDelta.xDelta) > settings.initialXDelta) {
                data.initialXDeltaReached = true;
                listItem.style.left = touchDelta.xDelta + 'px';
            } else if (data.initialXDeltaReached) {
                listItem.style.left = touchDelta.xDelta + 'px';
            }
            this._listSwipeData[dataId] = data;
            touchDelta = this._calculateTouchDelta(touch, data, settings);
            if (this._onElementMoving) {
                let action = touchDelta.xDelta > 0 ? 'right' : touchDelta.xDelta < 0 ? 'left' : false;
                this._onElementMoving(ev, action, touchDelta.xDelta);
            }
        },
        _onTouchEnd: function (ev) {
            let listItem = ev.currentTarget;
            let dataId = listItem.getAttribute("data-listSwipe");
            let data = this._listSwipeData[dataId];
            let touch = this._getTouchPositions(ev);
            let settings = this._options;
            if (data.maxYDeltaReached) {
                return;
            }
            let touchDelta = this._calculateTouchDelta(touch, data, settings);
            let actionButton = touchDelta.xDelta > 0 ? 'left' : touchDelta.xDelta < 0 ? 'right' : false;

            if (actionButton && data.allowAction && !data.allowAction[actionButton]) {
                return;
            }
            listItem.style.left = touchDelta.xDelta + 'px';
            if (actionButton) {
                let actionWidth = actionButton == "left" ? -touchDelta.xDelta : settings.itemActionWidth;
                listItem.querySelector(".swipe-action." + actionButton).style.left = actionWidth + 'px';
            }
            if (touchDelta.xDelta > 0 && settings.onRightSwipe) {
                settings.onRightSwipe(ev);
            }
            if (touchDelta.xDelta < 0 && settings.onLeftSwipe) {
                settings.onLeftSwipe(ev);
            }
        },
    };
})();
