/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @ignore
 * File overview: DOM iterator, which iterates over list items, lines and paragraphs.
 */

(function() {
	/**
	 * Represents iterator class.
	 *
	 * @class CKEDITOR.dom.iterator
	 * @constructor Creates an iterator class instance.
	 * @param {CKEDITOR.dom.range} range
	 * @todo
	 */
	function iterator( range ) {
		if ( arguments.length < 1 )
			return;

		this.range = range;
		this.forceBrBreak = 0;

		// Whether include <br>s into the enlarged range.(#3730).
		this.enlargeBr = 1;
		this.enforceRealBlocks = 0;

		this._ || ( this._ = {} );
	}

	var beginWhitespaceRegex = /^[\r\n\t ]+$/,
		// Ignore bookmark nodes.(#3783)
		bookmarkGuard = CKEDITOR.dom.walker.bookmark( false, true ),
		whitespacesGuard = CKEDITOR.dom.walker.whitespaces( true ),
		skipGuard = function( node ) {
			return bookmarkGuard( node ) && whitespacesGuard( node );
		};

	// Get a reference for the next element, bookmark nodes are skipped.
	function getNextSourceNode( node, startFromSibling, lastNode ) {
		var next = node.getNextSourceNode( startFromSibling, null, lastNode );
		while ( !bookmarkGuard( next ) )
			next = next.getNextSourceNode( startFromSibling, null, lastNode );
		return next;
	}

	iterator.prototype = {
		/**
		 * @todo
		 */
		getNextParagraph: function( blockTag ) {
			blockTag = blockTag || 'p';

			// Block-less range should be checked first.
			if ( !CKEDITOR.dtd[ this.range.root.getName() ][ blockTag ] )
				return null;

			// The block element to be returned.
			var block;

			// The range object used to identify the paragraph contents.
			var range;

			// Indicats that the current element in the loop is the last one.
			var isLast;

			// Indicate at least one of the range boundaries is inside a preformat block.
			var touchPre;

			// Instructs to cleanup remaining BRs.
			var removePreviousBr, removeLastBr;

			// This is the first iteration. Let's initialize it.
			if ( !this._.started ) {
				range = this.range.clone();

				// Shrink the range to exclude harmful "noises" (#4087, #4450, #5435).
				range.shrink( CKEDITOR.NODE_ELEMENT, true );

				touchPre = range.endContainer.hasAscendant( 'pre', true ) || range.startContainer.hasAscendant( 'pre', true );

				range.enlarge( this.forceBrBreak && !touchPre || !this.enlargeBr ? CKEDITOR.ENLARGE_LIST_ITEM_CONTENTS : CKEDITOR.ENLARGE_BLOCK_CONTENTS );

				if ( !range.collapsed ) {
					var walker = new CKEDITOR.dom.walker( range.clone() ),
						ignoreBookmarkTextEvaluator = CKEDITOR.dom.walker.bookmark( true, true );
					// Avoid anchor inside bookmark inner text.
					walker.evaluator = ignoreBookmarkTextEvaluator;
					this._.nextNode = walker.next();
					// TODO: It's better to have walker.reset() used here.
					walker = new CKEDITOR.dom.walker( range.clone() );
					walker.evaluator = ignoreBookmarkTextEvaluator;
					var lastNode = walker.previous();
					this._.lastNode = lastNode.getNextSourceNode( true );

					// We may have an empty text node at the end of block due to [3770].
					// If that node is the lastNode, it would cause our logic to leak to the
					// next block.(#3887)
					if ( this._.lastNode && this._.lastNode.type == CKEDITOR.NODE_TEXT && !CKEDITOR.tools.trim( this._.lastNode.getText() ) && this._.lastNode.getParent().isBlockBoundary() ) {
						var testRange = this.range.clone();
						testRange.moveToPosition( this._.lastNode, CKEDITOR.POSITION_AFTER_END );
						if ( testRange.checkEndOfBlock() ) {
							var path = new CKEDITOR.dom.elementPath( testRange.endContainer, testRange.root );
							var lastBlock = path.block || path.blockLimit;
							this._.lastNode = lastBlock.getNextSourceNode( true );
						}
					}

					// Probably the document end is reached, we need a marker node.
					if ( !this._.lastNode ) {
						this._.lastNode = this._.docEndMarker = range.document.createText( '' );
						this._.lastNode.insertAfter( lastNode );
					}

					// Let's reuse this variable.
					range = null;
				}

				this._.started = 1;
			}

			var currentNode = this._.nextNode;
			lastNode = this._.lastNode;

			this._.nextNode = null;
			while ( currentNode ) {
				// closeRange indicates that a paragraph boundary has been found,
				// so the range can be closed.
				var closeRange = 0,
					parentPre = currentNode.hasAscendant( 'pre' );

				// includeNode indicates that the current node is good to be part
				// of the range. By default, any non-element node is ok for it.
				var includeNode = ( currentNode.type != CKEDITOR.NODE_ELEMENT ),
					continueFromSibling = 0;

				// If it is an element node, let's check if it can be part of the
				// range.
				if ( !includeNode ) {
					var nodeName = currentNode.getName();

					if ( currentNode.isBlockBoundary( this.forceBrBreak && !parentPre && { br:1 } ) ) {
						// <br> boundaries must be part of the range. It will
						// happen only if ForceBrBreak.
						if ( nodeName == 'br' )
							includeNode = 1;
						else if ( !range && !currentNode.getChildCount() && nodeName != 'hr' ) {
							// If we have found an empty block, and haven't started
							// the range yet, it means we must return this block.
							block = currentNode;
							isLast = currentNode.equals( lastNode );
							break;
						}

						// The range must finish right before the boundary,
						// including possibly skipped empty spaces. (#1603)
						if ( range ) {
							range.setEndAt( currentNode, CKEDITOR.POSITION_BEFORE_START );

							// The found boundary must be set as the next one at this
							// point. (#1717)
							if ( nodeName != 'br' )
								this._.nextNode = currentNode;
						}

						closeRange = 1;
					} else {
						// If we have child nodes, let's check them.
						if ( currentNode.getFirst() ) {
							// If we don't have a range yet, let's start it.
							if ( !range ) {
								range = this.range.clone();
								range.setStartAt( currentNode, CKEDITOR.POSITION_BEFORE_START );
							}

							currentNode = currentNode.getFirst();
							continue;
						}
						includeNode = 1;
					}
				} else if ( currentNode.type == CKEDITOR.NODE_TEXT ) {
					// Ignore normal whitespaces (i.e. not including &nbsp; or
					// other unicode whitespaces) before/after a block node.
					if ( beginWhitespaceRegex.test( currentNode.getText() ) )
						includeNode = 0;
				}

				// The current node is good to be part of the range and we are
				// starting a new range, initialize it first.
				if ( includeNode && !range ) {
					range = this.range.clone();
					range.setStartAt( currentNode, CKEDITOR.POSITION_BEFORE_START );
				}

				// The last node has been found.
				isLast = ( ( !closeRange || includeNode ) && currentNode.equals( lastNode ) );

				// If we are in an element boundary, let's check if it is time
				// to close the range, otherwise we include the parent within it.
				if ( range && !closeRange ) {
					while ( !currentNode.getNext( skipGuard ) && !isLast ) {
						var parentNode = currentNode.getParent();

						if ( parentNode.isBlockBoundary( this.forceBrBreak && !parentPre && { br:1 } ) ) {
							closeRange = 1;
							includeNode = 0;
							isLast = isLast || ( parentNode.equals( lastNode ) );
							// Make sure range includes bookmarks at the end of the block. (#7359)
							range.setEndAt( parentNode, CKEDITOR.POSITION_BEFORE_END );
							break;
						}

						currentNode = parentNode;
						includeNode = 1;
						isLast = ( currentNode.equals( lastNode ) );
						continueFromSibling = 1;
					}
				}

				// Now finally include the node.
				if ( includeNode )
					range.setEndAt( currentNode, CKEDITOR.POSITION_AFTER_END );

				currentNode = getNextSourceNode( currentNode, continueFromSibling, lastNode );
				isLast = !currentNode;

				// We have found a block boundary. Let's close the range and move out of the
				// loop.
				if ( isLast || ( closeRange && range ) )
					break;
			}

			// Now, based on the processed range, look for (or create) the block to be returned.
			if ( !block ) {
				// If no range has been found, this is the end.
				if ( !range ) {
					this._.docEndMarker && this._.docEndMarker.remove();
					this._.nextNode = null;
					return null;
				}

				var startPath = new CKEDITOR.dom.elementPath( range.startContainer, range.root );
				var startBlockLimit = startPath.blockLimit,
					checkLimits = { div:1,th:1,td:1 };
				block = startPath.block;

				if ( !block && startBlockLimit && !this.enforceRealBlocks && checkLimits[ startBlockLimit.getName() ] && range.checkStartOfBlock() && range.checkEndOfBlock() && !startBlockLimit.equals( range.root ) )
					block = startBlockLimit;
				else if ( !block || ( this.enforceRealBlocks && block.getName() == 'li' ) ) {
					// Create the fixed block.
					block = this.range.document.createElement( blockTag );

					// Move the contents of the temporary range to the fixed block.
					range.extractContents().appendTo( block );
					block.trim();

					// Insert the fixed block into the DOM.
					range.insertNode( block );

					removePreviousBr = removeLastBr = true;
				} else if ( block.getName() != 'li' ) {
					// If the range doesn't includes the entire contents of the
					// block, we must split it, isolating the range in a dedicated
					// block.
					if ( !range.checkStartOfBlock() || !range.checkEndOfBlock() ) {
						// The resulting block will be a clone of the current one.
						block = block.clone( false );

						// Extract the range contents, moving it to the new block.
						range.extractContents().appendTo( block );
						block.trim();

						// Split the block. At this point, the range will be in the
						// right position for our intents.
						var splitInfo = range.splitBlock();

						removePreviousBr = !splitInfo.wasStartOfBlock;
						removeLastBr = !splitInfo.wasEndOfBlock;

						// Insert the new block into the DOM.
						range.insertNode( block );
					}
				} else if ( !isLast ) {
					// LIs are returned as is, with all their children (due to the
					// nested lists). But, the next node is the node right after
					// the current range, which could be an <li> child (nested
					// lists) or the next sibling <li>.

					this._.nextNode = ( block.equals( lastNode ) ? null : getNextSourceNode( range.getBoundaryNodes().endNode, 1, lastNode ) );
				}
			}

			if ( removePreviousBr ) {
				var previousSibling = block.getPrevious();
				if ( previousSibling && previousSibling.type == CKEDITOR.NODE_ELEMENT ) {
					if ( previousSibling.getName() == 'br' )
						previousSibling.remove();
					else if ( previousSibling.getLast() && previousSibling.getLast().$.nodeName.toLowerCase() == 'br' )
						previousSibling.getLast().remove();
				}
			}

			if ( removeLastBr ) {
				var lastChild = block.getLast();
				if ( lastChild && lastChild.type == CKEDITOR.NODE_ELEMENT && lastChild.getName() == 'br' ) {
					// Take care not to remove the block expanding <br> in non-IE browsers.
					if ( CKEDITOR.env.ie || lastChild.getPrevious( bookmarkGuard ) || lastChild.getNext( bookmarkGuard ) )
						lastChild.remove();
				}
			}

			// Get a reference for the next element. This is important because the
			// above block can be removed or changed, so we can rely on it for the
			// next interation.
			if ( !this._.nextNode ) {
				this._.nextNode = ( isLast || block.equals( lastNode ) || !lastNode ) ? null : getNextSourceNode( block, 1, lastNode );
			}

			return block;
		}
	};

	/**
	 * Creates {CKEDITOR.dom.iterator} instance for this range.
	 *
	 * @member CKEDITOR.dom.range
	 * @returns {CKEDITOR.dom.iterator}
	 */
	CKEDITOR.dom.range.prototype.createIterator = function() {
		return new iterator( this );
	};
})();
