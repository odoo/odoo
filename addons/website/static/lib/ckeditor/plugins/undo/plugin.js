/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

/**
 * @fileOverview Undo/Redo system for saving a shapshot for document modification
 *		and other recordable changes.
 */

(function() {
	CKEDITOR.plugins.add( 'undo', {
		lang: 'af,ar,bg,bn,bs,ca,cs,cy,da,de,el,en,en-au,en-ca,en-gb,eo,es,et,eu,fa,fi,fo,fr,fr-ca,gl,gu,he,hi,hr,hu,id,is,it,ja,ka,km,ko,ku,lt,lv,mk,mn,ms,nb,nl,no,pl,pt,pt-br,ro,ru,si,sk,sl,sq,sr,sr-latn,sv,th,tr,ug,uk,vi,zh,zh-cn', // %REMOVE_LINE_CORE%
		icons: 'redo,redo-rtl,undo,undo-rtl', // %REMOVE_LINE_CORE%
		hidpi: true, // %REMOVE_LINE_CORE%
		init: function( editor ) {
			var undoManager = editor.undoManager = new UndoManager( editor );

			var undoCommand = editor.addCommand( 'undo', {
				exec: function() {
					if ( undoManager.undo() ) {
						editor.selectionChange();
						this.fire( 'afterUndo' );
					}
				},
				startDisabled: true,
				canUndo: false
			} );

			var redoCommand = editor.addCommand( 'redo', {
				exec: function() {
					if ( undoManager.redo() ) {
						editor.selectionChange();
						this.fire( 'afterRedo' );
					}
				},
				startDisabled: true,
				canUndo: false
			} );

			editor.setKeystroke( [
				[ CKEDITOR.CTRL + 90 /*Z*/, 'undo' ],
				[ CKEDITOR.CTRL + 89 /*Y*/, 'redo' ],
				[ CKEDITOR.CTRL + CKEDITOR.SHIFT + 90 /*Z*/, 'redo' ]
			] );

			undoManager.onChange = function() {
				undoCommand.setState( undoManager.undoable() ? CKEDITOR.TRISTATE_OFF : CKEDITOR.TRISTATE_DISABLED );
				redoCommand.setState( undoManager.redoable() ? CKEDITOR.TRISTATE_OFF : CKEDITOR.TRISTATE_DISABLED );
			};

			function recordCommand( event ) {
				// If the command hasn't been marked to not support undo.
				if ( undoManager.enabled && event.data.command.canUndo !== false )
					undoManager.save();
			}

			// We'll save snapshots before and after executing a command.
			editor.on( 'beforeCommandExec', recordCommand );
			editor.on( 'afterCommandExec', recordCommand );

			// Save snapshots before doing custom changes.
			editor.on( 'saveSnapshot', function( evt ) {
				undoManager.save( evt.data && evt.data.contentOnly );
			} );

			// Registering keydown on every document recreation.(#3844)
			editor.on( 'contentDom', function() {
				editor.editable().on( 'keydown', function( event ) {
					var keystroke = event.data.getKey();

					if ( keystroke == 8 /*Backspace*/ || keystroke == 46 /*Delete*/ )
						undoManager.type( keystroke, 0 );
				} );

				editor.editable().on( 'keypress', function( event ) {
					undoManager.type( event.data.getKey(), 1 );
				} );
			} );

			// Always save an undo snapshot - the previous mode might have
			// changed editor contents.
			editor.on( 'beforeModeUnload', function() {
				editor.mode == 'wysiwyg' && undoManager.save( true );
			} );

			function toggleUndoManager() {
				undoManager.enabled = editor.readOnly ? false : editor.mode == 'wysiwyg';
				undoManager.onChange();
			}

			// Make the undo manager available only in wysiwyg mode.
			editor.on( 'mode', toggleUndoManager );

			// Disable undo manager when in read-only mode.
			editor.on( 'readOnly', toggleUndoManager );

			if ( editor.ui.addButton ) {
				editor.ui.addButton( 'Undo', {
					label: editor.lang.undo.undo,
					command: 'undo',
					toolbar: 'undo,10'
				} );

				editor.ui.addButton( 'Redo', {
					label: editor.lang.undo.redo,
					command: 'redo',
					toolbar: 'undo,20'
				} );
			}

			/**
			 * Resets the undo stack.
			 *
			 * @member CKEDITOR.editor
			 */
			editor.resetUndo = function() {
				// Reset the undo stack.
				undoManager.reset();

				// Create the first image.
				editor.fire( 'saveSnapshot' );
			};

			/**
			 * Amends the top of the undo stack (last undo image) with the current DOM changes.
			 *
			 *		function() {
			 *			editor.fire( 'saveSnapshot' );
			 *			editor.document.body.append(...);
			 *			// Makes new changes following the last undo snapshot a part of it.
			 *			editor.fire( 'updateSnapshot' );
			 *			..
			 *		}
			 *
			 * @event updateSnapshot
			 * @member CKEDITOR.editor
 			 * @param {CKEDITOR.editor} editor This editor instance.
			 */
			editor.on( 'updateSnapshot', function() {
				if ( undoManager.currentImage )
					undoManager.update();
			} );

			/**
			 * Locks the undo manager to prevent any save/update operations.
			 *
			 * It is convenient to lock the undo manager before performing DOM operations
			 * that should not be recored (e.g. auto paragraphing).
			 *
			 * See {@link CKEDITOR.plugins.undo.UndoManager#lock} for more details.
			 *
			 * **Note:** In order to unlock the undo manager, {@link #unlockSnapshot} has to be fired
			 * the same number of times that `lockSnapshot` has been fired.
			 *
			 * @since 4.0
			 * @event lockSnapshot
			 * @member CKEDITOR.editor
 			 * @param {CKEDITOR.editor} editor This editor instance.
			 */
			editor.on( 'lockSnapshot', undoManager.lock, undoManager );

			/**
			 * Unlocks the undo manager and updates the latest snapshot.
			 *
			 * @since 4.0
			 * @event unlockSnapshot
			 * @member CKEDITOR.editor
 			 * @param {CKEDITOR.editor} editor This editor instance.
			 */
			editor.on( 'unlockSnapshot', undoManager.unlock, undoManager );
		}
	} );

	CKEDITOR.plugins.undo = {};

	/**
	 * Undoes the snapshot which represents the current document status.
	 *
	 * @private
	 * @class CKEDITOR.plugins.undo.Image
	 * @constructor Creates an Image class instance.
	 * @param {CKEDITOR.editor} editor The editor instance on which the image is created.
	 */
	var Image = CKEDITOR.plugins.undo.Image = function( editor ) {
			this.editor = editor;

			editor.fire( 'beforeUndoImage' );

			var contents = editor.getSnapshot(),
				selection = contents && editor.getSelection();

			// In IE, we need to remove the expando attributes.
			CKEDITOR.env.ie && contents && ( contents = contents.replace( /\s+data-cke-expando=".*?"/g, '' ) );

			this.contents = contents;
			this.bookmarks = selection && selection.createBookmarks2( true );

			editor.fire( 'afterUndoImage' );
		};

	// Attributes that browser may changing them when setting via innerHTML.
	var protectedAttrs = /\b(?:href|src|name)="[^"]*?"/gi;

	Image.prototype = {
		equalsContent: function( otherImage ) {
			var thisContents = this.contents,
				otherContents = otherImage.contents;

			// For IE6/7 : Comparing only the protected attribute values but not the original ones.(#4522)
			if ( CKEDITOR.env.ie && ( CKEDITOR.env.ie7Compat || CKEDITOR.env.ie6Compat ) ) {
				thisContents = thisContents.replace( protectedAttrs, '' );
				otherContents = otherContents.replace( protectedAttrs, '' );
			}

			if ( thisContents != otherContents )
				return false;

			return true;
		},

		equalsSelection: function( otherImage ) {
			var bookmarksA = this.bookmarks,
				bookmarksB = otherImage.bookmarks;

			if ( bookmarksA || bookmarksB ) {
				if ( !bookmarksA || !bookmarksB || bookmarksA.length != bookmarksB.length )
					return false;

				for ( var i = 0; i < bookmarksA.length; i++ ) {
					var bookmarkA = bookmarksA[ i ],
						bookmarkB = bookmarksB[ i ];

					if ( bookmarkA.startOffset != bookmarkB.startOffset || bookmarkA.endOffset != bookmarkB.endOffset || !CKEDITOR.tools.arrayCompare( bookmarkA.start, bookmarkB.start ) || !CKEDITOR.tools.arrayCompare( bookmarkA.end, bookmarkB.end ) )
						return false;
				}
			}

			return true;
		}
	};

	/**
	 * Main logic for the Redo/Undo feature.
	 *
	 * **Note:** This class is not accessible from the global scope.
	 *
	 * @private
	 * @class CKEDITOR.plugins.undo.UndoManager
	 * @constructor Creates an UndoManager class instance.
	 * @param {CKEDITOR.editor} editor
	 */
	function UndoManager( editor ) {
		this.editor = editor;

		// Reset the undo stack.
		this.reset();
	}

	UndoManager.prototype = {
		/**
		 * When `locked` property is not `null`, the undo manager is locked, so
		 * operations like `save` or `update` are forbidden.
		 *
		 * The manager can be locked/unlocked by the {@link #lock} and {@link #unlock} methods.
		 *
		 * @private
		 * @property {Object} [locked=null]
		 */

		/**
		 * Handles keystroke support for the undo manager. It is called whenever a keystroke that
		 * can change the editor contents is pressed.
		 *
		 * @param {Number} keystroke The key code.
		 * @param {Boolean} isCharacter If `true`, it is a character ('a', '1', '&', ...). Otherwise it is the remove key (*Delete* or *Backspace*).
		 */
		type: function( keystroke, isCharacter ) {
			// Create undo snap for every different modifier key.
			var modifierSnapshot = ( !isCharacter && keystroke != this.lastKeystroke );

			// Create undo snap on the following cases:
			// 1. Just start to type .
			// 2. Typing some content after a modifier.
			// 3. Typing some content after make a visible selection.
			var startedTyping = !this.typing || ( isCharacter && !this.wasCharacter );

			var editor = this.editor;

			if ( startedTyping || modifierSnapshot ) {
				var beforeTypeImage = new Image( editor ),
					beforeTypeCount = this.snapshots.length;

				// Use setTimeout, so we give the necessary time to the
				// browser to insert the character into the DOM.
				CKEDITOR.tools.setTimeout( function() {
					var currentSnapshot = editor.getSnapshot();

					// In IE, we need to remove the expando attributes.
					if ( CKEDITOR.env.ie )
						currentSnapshot = currentSnapshot.replace( /\s+data-cke-expando=".*?"/g, '' );

					// If changes have taken place, while not been captured yet (#8459),
					// compensate the snapshot.
					if ( beforeTypeImage.contents != currentSnapshot && beforeTypeCount == this.snapshots.length ) {
						// It's safe to now indicate typing state.
						this.typing = true;

						// This's a special save, with specified snapshot
						// and without auto 'fireChange'.
						if ( !this.save( false, beforeTypeImage, false ) )
							// Drop future snapshots.
							this.snapshots.splice( this.index + 1, this.snapshots.length - this.index - 1 );

						this.hasUndo = true;
						this.hasRedo = false;

						this.typesCount = 1;
						this.modifiersCount = 1;

						this.onChange();
					}
				}, 0, this );
			}

			this.lastKeystroke = keystroke;
			this.wasCharacter = isCharacter;

			// Create undo snap after typed too much (over 25 times).
			if ( !isCharacter ) {
				this.typesCount = 0;
				this.modifiersCount++;

				if ( this.modifiersCount > 25 ) {
					this.save( false, null, false );
					this.modifiersCount = 1;
				} else {
					setTimeout(function() {
						editor.fire( 'change' );
					}, 0 );
				}
			} else {
				this.modifiersCount = 0;
				this.typesCount++;

				if ( this.typesCount > 25 ) {
					this.save( false, null, false );
					this.typesCount = 1;
				} else {
					setTimeout(function() {
						editor.fire( 'change' );
					}, 0 );
				}
			}

		},

		/**
		 * Resets the undo stack.
		 */
		reset: function() {
			// Remember last pressed key.
			this.lastKeystroke = 0;

			// Stack for all the undo and redo snapshots, they're always created/removed
			// in consistency.
			this.snapshots = [];

			// Current snapshot history index.
			this.index = -1;

			this.limit = this.editor.config.undoStackSize || 20;

			this.currentImage = null;

			this.hasUndo = false;
			this.hasRedo = false;
			this.locked = null;

			this.resetType();
		},

		/**
		 * Resets all typing variables.
		 *
		 * @see #type
		 */
		resetType: function() {
			this.typing = false;
			delete this.lastKeystroke;
			this.typesCount = 0;
			this.modifiersCount = 0;
		},

		fireChange: function() {
			this.hasUndo = !!this.getNextImage( true );
			this.hasRedo = !!this.getNextImage( false );
			// Reset typing
			this.resetType();
			this.onChange();
		},

		/**
		 * Saves a snapshot of the document image for later retrieval.
		 */
		save: function( onContentOnly, image, autoFireChange ) {
			// Do not change snapshots stack when locked.
			if ( this.locked )
				return false;

			var snapshots = this.snapshots;

			// Get a content image.
			if ( !image )
				image = new Image( this.editor );

			// Do nothing if it was not possible to retrieve an image.
			if ( image.contents === false )
				return false;

			// Check if this is a duplicate. In such case, do nothing.
			if ( this.currentImage ) {
				if ( image.equalsContent( this.currentImage ) ) {
					if ( onContentOnly )
						return false;

					if ( image.equalsSelection( this.currentImage ) )
						return false;
				} else {
					this.editor.fire( 'change' );
				}
			}

			// Drop future snapshots.
			snapshots.splice( this.index + 1, snapshots.length - this.index - 1 );

			// If we have reached the limit, remove the oldest one.
			if ( snapshots.length == this.limit )
				snapshots.shift();

			// Add the new image, updating the current index.
			this.index = snapshots.push( image ) - 1;

			this.currentImage = image;

			if ( autoFireChange !== false )
				this.fireChange();
			return true;
		},

		restoreImage: function( image ) {
			// Bring editor focused to restore selection.
			var editor = this.editor,
				sel;

			if ( image.bookmarks ) {
				editor.focus();
				// Retrieve the selection beforehand. (#8324)
				sel = editor.getSelection();
			}

			// Start transaction - do not allow any mutations to the
			// snapshots stack done when selecting bookmarks (much probably
			// by selectionChange listener).
			this.locked = 1;

			this.editor.loadSnapshot( image.contents );

			if ( image.bookmarks )
				sel.selectBookmarks( image.bookmarks );
			else if ( CKEDITOR.env.ie ) {
				// IE BUG: If I don't set the selection to *somewhere* after setting
				// document contents, then IE would create an empty paragraph at the bottom
				// the next time the document is modified.
				var $range = this.editor.document.getBody().$.createTextRange();
				$range.collapse( true );
				$range.select();
			}

			this.locked = 0;

			this.index = image.index;
			this.currentImage = this.snapshots[ this.index ];

			// Update current image with the actual editor
			// content, since actualy content may differ from
			// the original snapshot due to dom change. (#4622)
			this.update();
			this.fireChange();

			editor.fire( 'change' );
		},

		// Get the closest available image.
		getNextImage: function( isUndo ) {
			var snapshots = this.snapshots,
				currentImage = this.currentImage,
				image, i;

			if ( currentImage ) {
				if ( isUndo ) {
					for ( i = this.index - 1; i >= 0; i-- ) {
						image = snapshots[ i ];
						if ( !currentImage.equalsContent( image ) ) {
							image.index = i;
							return image;
						}
					}
				} else {
					for ( i = this.index + 1; i < snapshots.length; i++ ) {
						image = snapshots[ i ];
						if ( !currentImage.equalsContent( image ) ) {
							image.index = i;
							return image;
						}
					}
				}
			}

			return null;
		},

		/**
		 * Checks the current redo state.
		 *
		 * @returns {Boolean} Whether the document has a previous state to retrieve.
		 */
		redoable: function() {
			return this.enabled && this.hasRedo;
		},

		/**
		 * Checks the current undo state.
		 *
		 * @returns {Boolean} Whether the document has a future state to restore.
		 */
		undoable: function() {
			return this.enabled && this.hasUndo;
		},

		/**
		 * Performs undo on current index.
		 */
		undo: function() {
			if ( this.undoable() ) {
				this.save( true );

				var image = this.getNextImage( true );
				if ( image )
					return this.restoreImage( image ), true;
			}

			return false;
		},

		/**
		 * Performs redo on current index.
		 */
		redo: function() {
			if ( this.redoable() ) {
				// Try to save. If no changes have been made, the redo stack
				// will not change, so it will still be redoable.
				this.save( true );

				// If instead we had changes, we can't redo anymore.
				if ( this.redoable() ) {
					var image = this.getNextImage( false );
					if ( image )
						return this.restoreImage( image ), true;
				}
			}

			return false;
		},

		/**
		 * Updates the last snapshot of the undo stack with the current editor content.
		 *
		 * @param {CKEDITOR.plugins.undo.Image} [newImage] The image which will replace the current one.
		 * If not set defaults to image taken from editor.
		 */
		update: function( newImage ) {
			// Do not change snapshots stack is locked.
			if ( this.locked )
				return;

			if ( !newImage )
				newImage = new Image( this.editor );

			var i = this.index,
				snapshots = this.snapshots;

			// Find all previous snapshots made for the same content (which differ
			// only by selection) and replace all of them with the current image.
			while ( i > 0 && this.currentImage.equalsContent( snapshots[ i - 1 ] ) )
				i -= 1;

			snapshots.splice( i, this.index - i + 1, newImage );
			this.index = i;
			this.currentImage = newImage;
		},

		/**
		 * Locks the snapshot stack to prevent any save/update operations and when necessary,
		 * updates the tip of the snapshot stack with the DOM changes introduced during the
		 * locked period, after the {@link #unlock} method is called.
		 *
		 * It is mainly used to ensure any DOM operations that should not be recorded
		 * (e.g. auto paragraphing) are not added to the stack.
		 *
		 * **Note:** For every `lock` call you must call {@link #unlock} once to unlock the undo manager.
		 *
		 * @since 4.0
		 */
		lock: function() {
			if ( !this.locked ) {
				var imageBefore = new Image( this.editor );

				// If current editor content matches the tip of snapshot stack,
				// the stack tip must be updated by unlock, to include any changes made
				// during this period.
				var matchedTip = this.currentImage && this.currentImage.equalsContent( imageBefore );

				this.locked = { update: matchedTip ? imageBefore : null, level: 1 };
			}
			// Increase the level of lock.
			else
				this.locked.level++;
		},

		/**
		 * Unlocks the snapshot stack and checks to amend the last snapshot.
		 *
		 * See {@link #lock} for more details.
		 *
		 * @since 4.0
		 */
		unlock: function() {
			if ( this.locked ) {
				// Decrease level of lock and check if equals 0, what means that undoM is completely unlocked.
				if ( !--this.locked.level ) {
					var updateImage = this.locked.update,
						newImage = new Image( this.editor );

					this.locked = null;

					if ( updateImage && !updateImage.equalsContent( newImage ) )
						this.update( newImage );
				}
			}
		}
	};
})();

/**
 * The number of undo steps to be saved. The higher value is set, the more
 * memory is used for it.
 *
 *		config.undoStackSize = 50;
 *
 * @cfg {Number} [undoStackSize=20]
 * @member CKEDITOR.config
 */

/**
 * Fired when the editor is about to save an undo snapshot. This event can be
 * fired by plugins and customizations to make the editor save undo snapshots.
 *
 * @event saveSnapshot
 * @member CKEDITOR.editor
 * @param {CKEDITOR.editor} editor This editor instance.
 */

/**
 * Fired before an undo image is to be taken. An undo image represents the
 * editor state at some point. It is saved into the undo store, so the editor is
 * able to recover the editor state on undo and redo operations.
 *
 * @since 3.5.3
 * @event beforeUndoImage
 * @member CKEDITOR.editor
 * @param {CKEDITOR.editor} editor This editor instance.
 * @see CKEDITOR.editor#afterUndoImage
 */

/**
 * Fired after an undo image is taken. An undo image represents the
 * editor state at some point. It is saved into the undo store, so the editor is
 * able to recover the editor state on undo and redo operations.
 *
 * @since 3.5.3
 * @event afterUndoImage
 * @member CKEDITOR.editor
 * @param {CKEDITOR.editor} editor This editor instance.
 * @see CKEDITOR.editor#beforeUndoImage
 */

/**
 * Fired when the content of the editor is changed.
 *
 * Due to performance reasons, it is not verified if the content really changed.
 * The editor instead watches several editing actions that usually result in
 * changes. This event may thus in some cases be fired when no changes happen
 * or may even get fired twice.
 *
 * If it is important not to get the change event too often, you should compare the
 * previous and the current editor content inside the event listener.
 *
 * @since 4.2
 * @event change
 * @member CKEDITOR.editor
 * @param {CKEDITOR.editor} editor This editor instance.
 */
