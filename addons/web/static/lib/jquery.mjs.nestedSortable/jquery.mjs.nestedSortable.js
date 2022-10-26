/*
 * jQuery UI Nested Sortable
 * v 2.1a / 2016-02-04
 * https://github.com/ilikenwf/nestedSortable
 *
 * Depends on:
 *	 jquery.ui.sortable.js 1.10+
 *
 * Copyright (c) 2010-2016 Manuele J Sarfatti and contributors
 * Licensed under the MIT License
 * http://www.opensource.org/licenses/mit-license.php
 */
(function( factory ) {
	"use strict";

	if ( typeof define === "function" && define.amd ) {

		// AMD. Register as an anonymous module.
		define([
			"jquery",
			"jquery-ui/sortable"
		], factory );
	} else {

		// Browser globals
		factory( window.jQuery );
	}
}(function($) {
	"use strict";

	function isOverAxis( x, reference, size ) {
		return ( x > reference ) && ( x < ( reference + size ) );
	}

	$.widget("mjs.nestedSortable", $.extend({}, $.ui.sortable.prototype, {

		options: {
			disableParentChange: false,
			doNotClear: false,
			expandOnHover: 700,
			isAllowed: function() { return true; },
			isTree: false,
			listType: "ol",
			maxLevels: 0,
			protectRoot: false,
			rootID: null,
			rtl: false,
			startCollapsed: false,
			tabSize: 20,

			branchClass: "mjs-nestedSortable-branch",
			collapsedClass: "mjs-nestedSortable-collapsed",
			disableNestingClass: "mjs-nestedSortable-no-nesting",
			errorClass: "mjs-nestedSortable-error",
			expandedClass: "mjs-nestedSortable-expanded",
			hoveringClass: "mjs-nestedSortable-hovering",
			leafClass: "mjs-nestedSortable-leaf",
			disabledClass: "mjs-nestedSortable-disabled"
		},

		_create: function() {
			var self = this,
				err;

			this.element.data("ui-sortable", this.element.data("mjs-nestedSortable"));

			// mjs - prevent browser from freezing if the HTML is not correct
			if (!this.element.is(this.options.listType)) {
				err = "nestedSortable: " +
					"Please check that the listType option is set to your actual list type";

				throw new Error(err);
			}

			// if we have a tree with expanding/collapsing functionality,
			// force 'intersect' tolerance method
			if (this.options.isTree && this.options.expandOnHover) {
				this.options.tolerance = "intersect";
			}

			$.ui.sortable.prototype._create.apply(this, arguments);

			// prepare the tree by applying the right classes
			// (the CSS is responsible for actual hide/show functionality)
			if (this.options.isTree) {
				$(this.items).each(function() {
					var $li = this.item,
						hasCollapsedClass = $li.hasClass(self.options.collapsedClass),
						hasExpandedClass = $li.hasClass(self.options.expandedClass);

					if ($li.children(self.options.listType).length) {
						$li.addClass(self.options.branchClass);
						// expand/collapse class only if they have children

						if ( !hasCollapsedClass && !hasExpandedClass ) {
							if (self.options.startCollapsed) {
								$li.addClass(self.options.collapsedClass);
							} else {
								$li.addClass(self.options.expandedClass);
							}
						}
					} else {
						$li.addClass(self.options.leafClass);
					}
				});
			}
		},

		_destroy: function() {
			this.element
				.removeData("mjs-nestedSortable")
				.removeData("ui-sortable");
			return $.ui.sortable.prototype._destroy.apply(this, arguments);
		},

		_mouseDrag: function(event) {
			var i,
				item,
				itemElement,
				intersection,
				self = this,
				o = this.options,
				scrolled = false,
				$document = $(document),
				previousTopOffset,
				parentItem,
				level,
				childLevels,
				itemAfter,
				itemBefore,
				newList,
				method,
				a,
				previousItem,
				nextItem,
				helperIsNotSibling;

			//Compute the helpers position
			this.position = this._generatePosition(event);
			this.positionAbs = this._convertPositionTo("absolute");

			if (!this.lastPositionAbs) {
				this.lastPositionAbs = this.positionAbs;
			}

			//Do scrolling
			if (this.options.scroll) {
				if (this.scrollParent[0] !== document && this.scrollParent[0].tagName !== "HTML") {

					if (
						(
							this.overflowOffset.top +
							this.scrollParent[0].offsetHeight
						) -
						event.pageY <
						o.scrollSensitivity
					) {
						scrolled = this.scrollParent.scrollTop() + o.scrollSpeed;
						this.scrollParent.scrollTop(scrolled);
					} else if (
						event.pageY -
						this.overflowOffset.top <
						o.scrollSensitivity
					) {
						scrolled = this.scrollParent.scrollTop() - o.scrollSpeed;
						this.scrollParent.scrollTop(scrolled);
					}

					if (
						(
							this.overflowOffset.left +
							this.scrollParent[0].offsetWidth
						) -
						event.pageX <
						o.scrollSensitivity
					) {
						scrolled = this.scrollParent.scrollLeft() + o.scrollSpeed;
						this.scrollParent.scrollLeft(scrolled);
					} else if (
						event.pageX -
						this.overflowOffset.left <
						o.scrollSensitivity
					) {
						scrolled = this.scrollParent.scrollLeft() - o.scrollSpeed;
						this.scrollParent.scrollLeft(scrolled);
					}

				} else {

					if (
						event.pageY -
						$document.scrollTop() <
						o.scrollSensitivity
					) {
						scrolled = $document.scrollTop() - o.scrollSpeed;
						$document.scrollTop(scrolled);
					} else if (
						$(window).height() -
						(
							event.pageY -
							$document.scrollTop()
						) <
						o.scrollSensitivity
					) {
						scrolled = $document.scrollTop() + o.scrollSpeed;
						$document.scrollTop(scrolled);
					}

					if (
						event.pageX -
						$document.scrollLeft() <
						o.scrollSensitivity
					) {
						scrolled = $document.scrollLeft() - o.scrollSpeed;
						$document.scrollLeft(scrolled);
					} else if (
						$(window).width() -
						(
							event.pageX -
							$document.scrollLeft()
						) <
						o.scrollSensitivity
					) {
						scrolled = $document.scrollLeft() + o.scrollSpeed;
						$document.scrollLeft(scrolled);
					}

				}

				if (scrolled !== false && $.ui.ddmanager && !o.dropBehaviour) {
					$.ui.ddmanager.prepareOffsets(this, event);
				}
			}

			//Regenerate the absolute position used for position checks
			this.positionAbs = this._convertPositionTo("absolute");

			// mjs - find the top offset before rearrangement,
			previousTopOffset = this.placeholder.offset().top;

			//Set the helper position
			if (!this.options.axis || this.options.axis !== "y") {
				this.helper[0].style.left = this.position.left + "px";
			}
			if (!this.options.axis || this.options.axis !== "x") {
				this.helper[0].style.top = (this.position.top) + "px";
			}

			// mjs - check and reset hovering state at each cycle
			this.hovering = this.hovering ? this.hovering : null;
			this.mouseentered = this.mouseentered ? this.mouseentered : false;

			// mjs - let's start caching some variables
			(function() {
				var _parentItem = this.placeholder.parent().parent();
				if (_parentItem && _parentItem.closest(".ui-sortable").length) {
					parentItem = _parentItem;
				}
			}.call(this));

			level = this._getLevel(this.placeholder);
			childLevels = this._getChildLevels(this.helper);
			newList = document.createElement(o.listType);

			// Odoo begin patch
			// At this stage, the registered positions of the following tree
			// elements are not up to date with the fact that the placeholder
			// has replaced the element that is being dragged, and may have
			// different dimensions, which means that one would have to drag
			// an item further than what seems to be required visually to
			// effectively trigger an intersection if the placeholder is smaller
			// than the dragged item. By refreshing the positions here, that
			// problem is avoided.
			self.refreshPositions();
			// Odoo end patch

			//Rearrange
			for (i = this.items.length - 1; i >= 0; i--) {

				//Cache variables and intersection, continue if no intersection
				item = this.items[i];
				itemElement = item.item[0];
				intersection = this._intersectsWithPointer(item);
				if (!intersection) {
					continue;
				}

				// Only put the placeholder inside the current Container, skip all
				// items form other containers. This works because when moving
				// an item from one container to another the
				// currentContainer is switched before the placeholder is moved.
				//
				// Without this moving items in "sub-sortables" can cause the placeholder to jitter
				// beetween the outer and inner container.
				if (item.instance !== this.currentContainer) {
					continue;
				}

				// No action if intersected item is disabled
				// and the element above or below in the direction we're going is also disabled
				if (itemElement.className.indexOf(o.disabledClass) !== -1) {
					// Note: intersection hardcoded direction values from
					// jquery.ui.sortable.js:_intersectsWithPointer
					if (intersection === 2) {
						// Going down
						itemAfter = this.items[i + 1];
						if (itemAfter && itemAfter.item.hasClass(o.disabledClass)) {
							continue;
						}

					} else if (intersection === 1) {
						// Going up
						itemBefore = this.items[i - 1];
						if (itemBefore && itemBefore.item.hasClass(o.disabledClass)) {
							continue;
						}
					}
				}

				method = intersection === 1 ? "next" : "prev";

				// cannot intersect with itself
				// no useless actions that have been done before
				// no action if the item moved is the parent of the item checked
				if (itemElement !== this.currentItem[0] &&
					this.placeholder[method]()[0] !== itemElement &&
					!$.contains(this.placeholder[0], itemElement) &&
					(
						this.options.type === "semi-dynamic" ?
							!$.contains(this.element[0], itemElement) :
							true
					)
				) {

					// mjs - we are intersecting an element:
					// trigger the mouseenter event and store this state
					if (!this.mouseentered) {
						$(itemElement).mouseenter();
						this.mouseentered = true;
					}

					// mjs - if the element has children and they are hidden,
					// show them after a delay (CSS responsible)
					if (o.isTree && $(itemElement).hasClass(o.collapsedClass) && o.expandOnHover) {
						if (!this.hovering) {
							$(itemElement).addClass(o.hoveringClass);
							this.hovering = window.setTimeout(function() {
								$(itemElement)
									.removeClass(o.collapsedClass)
									.addClass(o.expandedClass);

								self.refreshPositions();
								self._trigger("expand", event, self._uiHash());
							}, o.expandOnHover);
						}
					}

					this.direction = intersection === 1 ? "down" : "up";

					// mjs - rearrange the elements and reset timeouts and hovering state
					if ((this.options.tolerance === "pointer" || this._intersectsWithSides(item)) &&
						// Odoo begin patch
						// Only allow to rearrange if itemElement was
						// intersected while going up or if the placeholder is
						// placed before itemElement in the dom, to avoid
						// a situation where the placeholder would go UP while
						// the mouse is going DOWN, which will cause flickering
						// if the placeholder has to change parent (depth)
						(intersection === 1 || (itemElement.compareDocumentPosition(this.placeholder[0]) & Node.DOCUMENT_POSITION_PRECEDING))
						// Odoo end patch
					) {
						$(itemElement).mouseleave();
						this.mouseentered = false;
						$(itemElement).removeClass(o.hoveringClass);
						if (this.hovering) {
							window.clearTimeout(this.hovering);
						}
						this.hovering = null;

						// mjs - do not switch container if
						// it's a root item and 'protectRoot' is true
						// or if it's not a root item but we are trying to make it root
						if (o.protectRoot &&
							!(
								this.currentItem[0].parentNode === this.element[0] &&
								// it's a root item
								itemElement.parentNode !== this.element[0]
								// it's intersecting a non-root item
							)
						) {
							if (this.currentItem[0].parentNode !== this.element[0] &&
								itemElement.parentNode === this.element[0]
							) {

								if ( !$(itemElement).children(o.listType).length) {
									itemElement.appendChild(newList);
									if (o.isTree) {
										$(itemElement)
											.removeClass(o.leafClass)
											.addClass(o.branchClass + " " + o.expandedClass);
									}
								}

								if (this.direction === "down") {
									a = $(itemElement).prev().children(o.listType);
								} else {
									a = $(itemElement).children(o.listType);
								}

								if (a[0] !== undefined) {
									this._rearrange(event, null, a);
								}

							} else {
								this._rearrange(event, item);
							}
						} else if (!o.protectRoot) {
							this._rearrange(event, item);
						}
					} else {
						break;
					}

					// Clear emtpy ul's/ol's
					this._clearEmpty(itemElement);

					this._trigger("change", event, this._uiHash());
					break;
				}
			}

			// mjs - to find the previous sibling in the list,
			// keep backtracking until we hit a valid list item.
			(function() {
				var _previousItem = this.placeholder.prev();
				if (_previousItem.length) {
					previousItem = _previousItem;
				} else {
					previousItem = null;
				}
			}.call(this));

			if (previousItem != null) {
				while (
					previousItem[0].nodeName.toLowerCase() !== "li" ||
					previousItem[0].className.indexOf(o.disabledClass) !== -1 ||
					previousItem[0] === this.currentItem[0] ||
					previousItem[0] === this.helper[0]
				) {
					if (previousItem[0].previousSibling) {
						previousItem = $(previousItem[0].previousSibling);
					} else {
						previousItem = null;
						break;
					}
				}
			}

			// mjs - to find the next sibling in the list,
			// keep stepping forward until we hit a valid list item.
			(function() {
				var _nextItem = this.placeholder.next();
				if (_nextItem.length) {
					nextItem = _nextItem;
				} else {
					nextItem = null;
				}
			}.call(this));

			if (nextItem != null) {
				while (
					nextItem[0].nodeName.toLowerCase() !== "li" ||
					nextItem[0].className.indexOf(o.disabledClass) !== -1 ||
					nextItem[0] === this.currentItem[0] ||
					nextItem[0] === this.helper[0]
				) {
					if (nextItem[0].nextSibling) {
						nextItem = $(nextItem[0].nextSibling);
					} else {
						nextItem = null;
						break;
					}
				}
			}

			this.beyondMaxLevels = 0;

			// mjs - if the item is moved to the left, send it one level up
			// but only if it's at the bottom of the list
			if (parentItem != null &&
				nextItem == null &&
				!(o.protectRoot && parentItem[0].parentNode == this.element[0]) &&
				(
					o.rtl &&
					(
						this.positionAbs.left +
						this.helper.outerWidth() > parentItem.offset().left +
						parentItem.outerWidth()
					) ||
					!o.rtl && (this.positionAbs.left < parentItem.offset().left)
				)
			) {

				parentItem.after(this.placeholder[0]);
				helperIsNotSibling = !parentItem
											.children(o.listItem)
											.children("li:visible:not(.ui-sortable-helper)")
											.length;
				if (o.isTree && helperIsNotSibling) {
					parentItem
						.removeClass(this.options.branchClass + " " + this.options.expandedClass)
						.addClass(this.options.leafClass);
				}
                if(typeof parentItem !== 'undefined')
				    this._clearEmpty(parentItem[0]);
				this._trigger("change", event, this._uiHash());
				// mjs - if the item is below a sibling and is moved to the right,
				// make it a child of that sibling
			} else if (previousItem != null &&
				!previousItem.hasClass(o.disableNestingClass) &&
				(
					previousItem.children(o.listType).length &&
					previousItem.children(o.listType).is(":visible") ||
					!previousItem.children(o.listType).length
				) &&
				!(o.protectRoot && this.currentItem[0].parentNode === this.element[0]) &&
				(
					o.rtl &&
					(
						this.positionAbs.left +
						this.helper.outerWidth() <
						previousItem.offset().left +
						previousItem.outerWidth() -
						o.tabSize
					) ||
					!o.rtl &&
					(this.positionAbs.left > previousItem.offset().left + o.tabSize)
				)
			) {

				this._isAllowed(previousItem, level, level + childLevels + 1);

				if (!previousItem.children(o.listType).length) {
					previousItem[0].appendChild(newList);
					if (o.isTree) {
						previousItem
							.removeClass(o.leafClass)
							.addClass(o.branchClass + " " + o.expandedClass);
					}
				}

				// mjs - if this item is being moved from the top, add it to the top of the list.
				if (previousTopOffset && (previousTopOffset <= previousItem.offset().top)) {
					previousItem.children(o.listType).prepend(this.placeholder);
				} else {
					// mjs - otherwise, add it to the bottom of the list.
					previousItem.children(o.listType)[0].appendChild(this.placeholder[0]);
				}
                if(typeof parentItem !== 'undefined')
				    this._clearEmpty(parentItem[0]);
				this._trigger("change", event, this._uiHash());
			} else {
				this._isAllowed(parentItem, level, level + childLevels);
			}

			//Post events to containers
			this._contactContainers(event);

			//Interconnect with droppables
			if ($.ui.ddmanager) {
				$.ui.ddmanager.drag(this, event);
			}

			//Call callbacks
			this._trigger("sort", event, this._uiHash());

			this.lastPositionAbs = this.positionAbs;
			return false;

		},

		_mouseStop: function(event) {
			// mjs - if the item is in a position not allowed, send it back
			if (this.beyondMaxLevels) {

				this.placeholder.removeClass(this.options.errorClass);

				if (this.domPosition.prev) {
					$(this.domPosition.prev).after(this.placeholder);
				} else {
					$(this.domPosition.parent).prepend(this.placeholder);
				}

				this._trigger("revert", event, this._uiHash());

			}

			// mjs - clear the hovering timeout, just to be sure
			$("." + this.options.hoveringClass)
				.mouseleave()
				.removeClass(this.options.hoveringClass);

			this.mouseentered = false;
			if (this.hovering) {
				window.clearTimeout(this.hovering);
			}
			this.hovering = null;

			this._relocate_event = event;
			this._pid_current = $(this.domPosition.parent).parent().attr("id");
			this._sort_current = this.domPosition.prev ? $(this.domPosition.prev).next().index() : 0;
			$.ui.sortable.prototype._mouseStop.apply(this, arguments); //asybnchronous execution, @see _clear for the relocate event.
		},

		// mjs - this function is slightly modified
		// to make it easier to hover over a collapsed element and have it expand
		_intersectsWithSides: function(item) {

			var half = this.options.isTree ? .8 : .5,
				isOverBottomHalf = isOverAxis(
					this.positionAbs.top + this.offset.click.top,
					item.top + (item.height * half),
					item.height
				),
				isOverTopHalf = isOverAxis(
					this.positionAbs.top + this.offset.click.top,
					item.top - (item.height * half),
					item.height
				),
				isOverRightHalf = isOverAxis(
					this.positionAbs.left + this.offset.click.left,
					item.left + (item.width / 2),
					item.width
				),
				verticalDirection = this._getDragVerticalDirection(),
				horizontalDirection = this._getDragHorizontalDirection();

			if (this.floating && horizontalDirection) {
				return (
					(horizontalDirection === "right" && isOverRightHalf) ||
					(horizontalDirection === "left" && !isOverRightHalf)
				);
			} else {
				return verticalDirection && (
					(verticalDirection === "down" && isOverBottomHalf) ||
					(verticalDirection === "up" && isOverTopHalf)
				);
			}

		},

		_contactContainers: function() {

			if (this.options.protectRoot && this.currentItem[0].parentNode === this.element[0] ) {
				return;
			}

			$.ui.sortable.prototype._contactContainers.apply(this, arguments);

		},

		_clear: function() {
			var i,
				item;

			$.ui.sortable.prototype._clear.apply(this, arguments);

			//relocate event
			if (!(this._pid_current === this._uiHash().item.parent().parent().attr("id") &&
				this._sort_current === this._uiHash().item.index())) {
				this._trigger("relocate", this._relocate_event, this._uiHash());
			}

			// mjs - clean last empty ul/ol
			for (i = this.items.length - 1; i >= 0; i--) {
				item = this.items[i].item[0];
				this._clearEmpty(item);
			}

		},

		serialize: function(options) {

			var o = $.extend({}, this.options, options),
				items = this._getItemsAsjQuery(o && o.connected),
				str = [];

			$(items).each(function() {
				var res = ($(o.item || this).attr(o.attribute || "id") || "")
						.match(o.expression || (/(.+)[-=_](.+)/)),
					pid = ($(o.item || this).parent(o.listType)
						.parent(o.items)
						.attr(o.attribute || "id") || "")
						.match(o.expression || (/(.+)[-=_](.+)/));

				if (res) {
					str.push(
						(
							(o.key || res[1]) +
							"[" +
							(o.key && o.expression ? res[1] : res[2]) + "]"
						) +
						"=" +
						(pid ? (o.key && o.expression ? pid[1] : pid[2]) : o.rootID));
				}
			});

			if (!str.length && o.key) {
				str.push(o.key + "=");
			}

			return str.join("&");

		},

		toHierarchy: function(options) {

			var o = $.extend({}, this.options, options),
				ret = [];

			$(this.element).children(o.items).each(function() {
				var level = _recursiveItems(this);
				ret.push(level);
			});

			return ret;

			function _recursiveItems(item) {
				var id = ($(item).attr(o.attribute || "id") || "").match(o.expression || (/(.+)[-=_](.+)/)),
					currentItem;

				var data = $(item).data();
				if (data.nestedSortableItem) {
					delete data.nestedSortableItem; // Remove the nestedSortableItem object from the data
				}

				if (id) {
					currentItem = {
						"id": id[2]
					};

					currentItem = $.extend({}, currentItem, data); // Combine the two objects

					if ($(item).children(o.listType).children(o.items).length > 0) {
						currentItem.children = [];
						$(item).children(o.listType).children(o.items).each(function() {
							var level = _recursiveItems(this);
							currentItem.children.push(level);
						});
					}
					return currentItem;
				}
			}
		},

		toArray: function(options) {

			var o = $.extend({}, this.options, options),
				sDepth = o.startDepthCount || 0,
				ret = [],
				left = 1;

			if (!o.excludeRoot) {
				ret.push({
					"item_id": o.rootID,
					"parent_id": null,
					"depth": sDepth,
					"left": left,
					"right": ($(o.items, this.element).length + 1) * 2
				});
				left++;
			}

			$(this.element).children(o.items).each(function() {
				left = _recursiveArray(this, sDepth, left);
			});

			ret = ret.sort(function(a, b) { return (a.left - b.left); });

			return ret;

			function _recursiveArray(item, depth, _left) {

				var right = _left + 1,
					id,
					pid,
					parentItem;

				if ($(item).children(o.listType).children(o.items).length > 0) {
					depth++;
					$(item).children(o.listType).children(o.items).each(function() {
						right = _recursiveArray($(this), depth, right);
					});
					depth--;
				}

				id = ($(item).attr(o.attribute || "id")).match(o.expression || (/(.+)[-=_](.+)/));

				if (depth === sDepth) {
					pid = o.rootID;
				} else {
					parentItem = ($(item).parent(o.listType)
											.parent(o.items)
											.attr(o.attribute || "id"))
											.match(o.expression || (/(.+)[-=_](.+)/));
					pid = parentItem[2];
				}

				if (id) {
					var data = $(item).children('div').data();
					var itemObj = $.extend( data, {
						"id":id[2],
						"parent_id":pid,
						"depth":depth,
						"left":_left,
						"right":right
						} );
					ret.push( itemObj );
				}

				_left = right + 1;
				return _left;
			}

		},

		_clearEmpty: function (item) {
			function replaceClass(elem, search, replace, swap) {
				if (swap) {
					search = [replace, replace = search][0];
				}

				$(elem).removeClass(search).addClass(replace);
			}

			var o = this.options,
				childrenList = $(item).children(o.listType),
				hasChildren = childrenList.has('li').length;

			var doNotClear =
				o.doNotClear ||
				hasChildren ||
				o.protectRoot && $(item)[0] === this.element[0];

			if (o.isTree) {
				replaceClass(item, o.branchClass, o.leafClass, doNotClear);
			}

			if (!doNotClear) {
				childrenList.parent().removeClass(o.expandedClass);
				childrenList.remove();
			}
		},

		_getLevel: function(item) {

			var level = 1,
				list;

			if (this.options.listType) {
				list = item.closest(this.options.listType);
				while (list && list.length > 0 && !list.is(".ui-sortable")) {
					level++;
					list = list.parent().closest(this.options.listType);
				}
			}

			return level;
		},

		_getChildLevels: function(parent, depth) {
			var self = this,
				o = this.options,
				result = 0;
			depth = depth || 0;

			$(parent).children(o.listType).children(o.items).each(function(index, child) {
				result = Math.max(self._getChildLevels(child, depth + 1), result);
			});

			return depth ? result + 1 : result;
		},

		_isAllowed: function(parentItem, level, levels) {
			var o = this.options,
				// this takes into account the maxLevels set to the recipient list
				maxLevels = this
					.placeholder
					.closest(".ui-sortable")
					.nestedSortable("option", "maxLevels"),

				// Check if the parent has changed to prevent it, when o.disableParentChange is true
				oldParent = this.currentItem.parent().parent(),
				disabledByParentchange = o.disableParentChange && (
					//From somewhere to somewhere else, except the root
					typeof parentItem !== 'undefined' && !oldParent.is(parentItem) ||
					typeof parentItem === 'undefined' && oldParent.is("li")	//From somewhere to the root
				);
			// mjs - is the root protected?
			// mjs - are we nesting too deep?
			if (
				disabledByParentchange ||
				!o.isAllowed(this.placeholder, parentItem, this.currentItem)
			) {
				this.placeholder.addClass(o.errorClass);
				if (maxLevels < levels && maxLevels !== 0) {
					this.beyondMaxLevels = levels - maxLevels;
				} else {
					this.beyondMaxLevels = 1;
				}
			} else {
				if (maxLevels < levels && maxLevels !== 0) {
					this.placeholder.addClass(o.errorClass);
					this.beyondMaxLevels = levels - maxLevels;
				} else {
					this.placeholder.removeClass(o.errorClass);
					this.beyondMaxLevels = 0;
				}
			}
		}

	}));

	$.mjs.nestedSortable.prototype.options = $.extend(
		{},
		$.ui.sortable.prototype.options,
		$.mjs.nestedSortable.prototype.options
	);
}));