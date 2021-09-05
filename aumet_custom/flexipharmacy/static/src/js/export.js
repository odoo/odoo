/*
Plugin Name: amCharts Export
Description: Adds export capabilities to amCharts products
Author: Benjamin Maertz, amCharts
Version: 1.4.76
Author URI: http://www.amcharts.com/

Copyright 2016 amCharts

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

	http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Please note that the above license covers only this plugin. It by all means does
not apply to any other amCharts products that are covered by different licenses.
*/

/*
 ** Polyfill translation
 */
if ( !AmCharts.translations[ "export" ] ) {
	AmCharts.translations[ "export" ] = {}
}
if ( !AmCharts.translations[ "export" ][ "en" ] ) {
	AmCharts.translations[ "export" ][ "en" ] = {
		"fallback.save.text": "CTRL + C to copy the data into the clipboard.",
		"fallback.save.image": "Rightclick -> Save picture as... to save the image.",

		"capturing.delayed.menu.label": "{{duration}}",
		"capturing.delayed.menu.title": "Click to cancel",

		"menu.label.print": "Print",
		"menu.label.undo": "Undo",
		"menu.label.redo": "Redo",
		"menu.label.cancel": "Cancel",

		"menu.label.save.image": "Download as ...",
		"menu.label.save.data": "Save as ...",

		"menu.label.draw": "Annotate ...",
		"menu.label.draw.change": "Change ...",
		"menu.label.draw.add": "Add ...",
		"menu.label.draw.shapes": "Shape ...",
		"menu.label.draw.colors": "Color ...",
		"menu.label.draw.widths": "Size ...",
		"menu.label.draw.opacities": "Opacity ...",
		"menu.label.draw.text": "Text",

		"menu.label.draw.modes": "Mode ...",
		"menu.label.draw.modes.pencil": "Pencil",
		"menu.label.draw.modes.line": "Line",
		"menu.label.draw.modes.arrow": "Arrow",

		"label.saved.from": "Saved from: "
	}
}

/*
 ** Polyfill export class
 */
( function() {
	AmCharts[ "export" ] = function( chart, config ) {
		var _timer;
		var _this = {
			name: "export",
			version: "1.4.76",
			libs: {
				async: true,
				autoLoad: true,
				reload: false,
				resources: [ "fabric.js/fabric.min.js", "FileSaver.js/FileSaver.min.js", {
					"jszip/jszip.min.js": [ "xlsx/xlsx.min.js" ],
					"pdfmake/pdfmake.min.js": [ "pdfmake/vfs_fonts.js" ]
				} ],
				namespaces: {
					"pdfmake.min.js": "pdfMake",
					"jszip.min.js": "JSZip",
					"xlsx.min.js": "XLSX",
					"fabric.min.js": "fabric",
					"FileSaver.min.js": "saveAs"
				},
				loadTimeout: 10000,
				unsupportedIE9libs: ["pdfmake.min.js", "jszip.min.js", "xlsx.min.js"]
			},
			config: {},
			setup: {
				chart: chart,
				hasBlob: false,
				wrapper: false,
				isIE: !!window.document.documentMode,
				IEversion: window.document.documentMode,
				hasTouch: typeof window.Touch == "object",
				focusedMenuItem: undefined,
				hasClasslist: ("classList" in document.createElement("_"))
			},
			drawing: {
				enabled: false,
				undos: [],
				redos: [],
				buffer: {
					position: {
						x1: 0,
						y1: 0,
						x2: 0,
						y2: 0,
						xD: 0,
						yD: 0
					}
				},
				handler: {
					undo: function() {
						var item = _this.drawing.undos.pop();

						if ( item ) {
							item.selectable = true;
							_this.drawing.redos.push( item );

							// Simply remove
							if ( item.action == "added" ) {
								_this.setup.fabric.remove( item.target );

							// Skip if unchanged
							} else if ( !item.target.changed && item.action == "added:modified" ) {
							 	_this.drawing.handler.undo();
							 	return;

							// Apply changes
							} else {
								var state = JSON.parse( item.state );
								item.target.recentState = item.state;

								// Group exception
								if ( item.target instanceof fabric.Group ) {
									state = _this.prepareGroupState(state);
									item.target.set( state );
									_this.drawing.handler.change( {
										color: state.cfg.color,
										width: state.cfg.width,
										opacity: state.cfg.opacity
									}, true, item.target );

								// Single item
								} else {
									item.target.set( state );
								}
							}

							_this.setup.fabric.renderAll();
						}
					},
					redo: function() {
						var item = _this.drawing.redos.pop();
						if ( item ) {

							item.selectable = true;
							_this.drawing.undos.push( item );

							// Simply add
							if ( item.action == "added" ) {
								_this.setup.fabric.add( item.target );

							// This aciton is only for undo;
							} else if ( item.action == "added:modified" ) {
								_this.drawing.handler.redo();
								return;
							}

							var state = JSON.parse( item.state );
							item.target.recentState = item.state;

							// Group exception
							if ( item.target instanceof fabric.Group ) {
								state = _this.prepareGroupState(state);
								item.target.set( state );
								_this.drawing.handler.change( {
									color: state.cfg.color,
									width: state.cfg.width,
									opacity: state.cfg.opacity
								}, true, item.target );

							// Single item
							} else {
								item.target.set( state );
							}

							_this.setup.fabric.renderAll();
						}
					},
					done: function( options ) {
						_this.drawing.enabled = false;
						_this.drawing.buffer.enabled = false;
						_this.drawing.undos = [];
						_this.drawing.redos = [];
						_this.createMenu( _this.config.menu );
						_this.setup.fabric.deactivateAll();

						if ( _this.isElement(_this.setup.wrapper) && _this.isElement(_this.setup.wrapper.parentNode) && _this.setup.wrapper.parentNode.removeChild ) {
							_this.setup.wrapper.parentNode.removeChild( _this.setup.wrapper );
							_this.setup.wrapper = false;
						}
					},
					add: function( options ) {
						var cfg = _this.deepMerge( {
							top: _this.setup.fabric.height / 2,
							left: _this.setup.fabric.width / 2
						}, options || {} );
						var method = cfg.url.indexOf( ".svg" ) != -1 ? fabric.loadSVGFromURL : fabric.Image.fromURL;

						method( cfg.url, function( objects, options ) {
							var group = options !== undefined ? fabric.util.groupSVGElements( objects, options ) : objects;
							var ratio = false;

							// RESCALE ONLY IF IT EXCEEDS THE CANVAS
							if ( group.height > _this.setup.fabric.height || group.width > _this.setup.fabric.width ) {
								ratio = ( _this.setup.fabric.height / 2 ) / group.height;
							}

							if ( cfg.top > _this.setup.fabric.height ) {
								cfg.top = _this.setup.fabric.height / 2;
							}

							if ( cfg.left > _this.setup.fabric.width ) {
								cfg.left = _this.setup.fabric.width / 2;
							}

							// SET DRAWING FLAG
							_this.drawing.buffer.isDrawing = true;

							group.set( {
								originX: "center",
								originY: "center",
								top: cfg.top,
								left: cfg.left,
								width: ratio ? group.width * ratio : group.width,
								height: ratio ? group.height * ratio : group.height,
								fill: _this.drawing.color
							} );
							_this.setup.fabric.add( group );
						} );
					},
					change: function( options, skipped, target ) {
						var cfg = _this.deepMerge( {}, options || {} );
						var state, i1, rgba;
						var current = target || _this.drawing.buffer.target;
						var objects = current ? current._objects ? current._objects : [ current ] : null;

						// UPDATE DRAWING OBJECT
						if ( cfg.mode ) {
							_this.drawing.mode = cfg.mode;
						}
						if ( cfg.width ) {
							_this.drawing.width = cfg.width;
							_this.drawing.fontSize = cfg.fontSize = cfg.width * 3;

							// BACK TO DEFAULT
							if ( _this.drawing.width == 1 ) {
								_this.drawing.fontSize = cfg.fontSize = _this.defaults.fabric.drawing.fontSize;
							}

						}
						if ( cfg.fontSize ) {
							_this.drawing.fontSize = cfg.fontSize;
						}
						if ( cfg.color ) {
							_this.drawing.color = cfg.color;
						}
						if ( cfg.opacity ) {
							_this.drawing.opacity = cfg.opacity;
						}

						// APPLY OPACITY ON CURRENT COLOR
						rgba = _this.getRGBA( _this.drawing.color );
						rgba.pop();
						rgba.push( _this.drawing.opacity );
						_this.drawing.color = "rgba(" + rgba.join() + ")";
						_this.setup.fabric.freeDrawingBrush.color = _this.drawing.color;
						_this.setup.fabric.freeDrawingBrush.width = _this.drawing.width;

						// UPDATE CURRENT SELECTION
						if ( current ) {
							state = JSON.parse( current.recentState ).cfg;

							// UPDATE GIVE OPTIONS ONLY
							if ( state ) {
								cfg.color = cfg.color || state.color;
								cfg.width = cfg.width || state.width;
								cfg.opacity = cfg.opacity || state.opacity;
								cfg.fontSize = cfg.fontSize || state.fontSize;

								rgba = _this.getRGBA( cfg.color );
								rgba.pop();
								rgba.push( cfg.opacity );
								cfg.color = "rgba(" + rgba.join() + ")";
							}

							current.changed = true;

							// UPDATE OBJECTS
							for ( i1 = 0; i1 < objects.length; i1++ ) {
								if (
									objects[ i1 ] instanceof fabric.Text ||
									objects[ i1 ] instanceof fabric.PathGroup ||
									objects[ i1 ] instanceof fabric.Triangle
								) {
									if ( cfg.color || cfg.opacity ) {
										objects[ i1 ].set( {
											fill: cfg.color
										} );
									}
									if ( cfg.fontSize ) {
										objects[ i1 ].set( {
											fontSize: cfg.fontSize
										} );
									}
								} else if (
									objects[ i1 ] instanceof fabric.Path ||
									objects[ i1 ] instanceof fabric.Line
								) {
									if ( current instanceof fabric.Group ) {
										if ( cfg.color || cfg.opacity ) {
											objects[ i1 ].set( {
												stroke: cfg.color
											} );
										}
									} else {
										if ( cfg.color || cfg.opacity ) {
											objects[ i1 ].set( {
												stroke: cfg.color
											} );
										}
										if ( cfg.width ) {
											objects[ i1 ].set( {
												strokeWidth: cfg.width
											} );
										}
									}
								}
							}

							// ADD UNDO
							if ( !skipped ) {
								state = JSON.stringify( _this.deepMerge( _this.getState(current), {
									cfg: {
										color: cfg.color,
										width: cfg.width,
										opacity: cfg.opacity
									}
								} ) );
								current.recentState = state;
								_this.drawing.redos = [];
								_this.drawing.undos.push( {
									action: "modified",
									target: current,
									state: state
								} );
							}

							_this.setup.fabric.renderAll();
						}
					},
					text: function( options ) {
						var cfg = _this.deepMerge( {
							text: _this.i18l( "menu.label.draw.text" ),
							top: _this.setup.fabric.height / 2,
							left: _this.setup.fabric.width / 2,
							fontSize: _this.drawing.fontSize,
							fontFamily: _this.setup.chart.fontFamily || "Verdana",
							fill: _this.drawing.color
						}, options || {} );

						cfg.click = function() {};

						var text = new fabric.IText( cfg.text, cfg );

						// SET DRAWING FLAG
						_this.drawing.buffer.isDrawing = true;

						_this.setup.fabric.add( text );
						_this.setup.fabric.setActiveObject( text );

						text.selectAll();
						text.enterEditing();

						return text;
					},
					line: function( options ) {
						var cfg = _this.deepMerge( {
							x1: ( _this.setup.fabric.width / 2 ) - ( _this.setup.fabric.width / 10 ),
							x2: ( _this.setup.fabric.width / 2 ) + ( _this.setup.fabric.width / 10 ),
							y1: ( _this.setup.fabric.height / 2 ),
							y2: ( _this.setup.fabric.height / 2 ),
							angle: 90,
							strokeLineCap: _this.drawing.lineCap,
							arrow: _this.drawing.arrow,
							color: _this.drawing.color,
							width: _this.drawing.width,
							group: [],
						}, options || {} );
						var i1, arrow, arrowTop, arrowLeft;
						var line = new fabric.Line( [ cfg.x1, cfg.y1, cfg.x2, cfg.y2 ], {
							stroke: cfg.color,
							strokeWidth: cfg.width,
							strokeLineCap: cfg.strokeLineCap
						} );

						cfg.group.push( line );

						if ( cfg.arrow ) {
							cfg.angle = cfg.angle ? cfg.angle : _this.getAngle( cfg.x1, cfg.y1, cfg.x2, cfg.y2 );

							if ( cfg.arrow == "start" ) {
								arrowTop = cfg.y1 + ( cfg.width / 2 );
								arrowLeft = cfg.x1 + ( cfg.width / 2 );
							} else if ( cfg.arrow == "middle" ) {
								arrowTop = cfg.y2 + ( cfg.width / 2 ) - ( ( cfg.y2 - cfg.y1 ) / 2 );
								arrowLeft = cfg.x2 + ( cfg.width / 2 ) - ( ( cfg.x2 - cfg.x1 ) / 2 );
							} else { // arrow: end
								arrowTop = cfg.y2 + ( cfg.width / 2 );
								arrowLeft = cfg.x2 + ( cfg.width / 2 );
							}

							arrow = new fabric.Triangle( {
								top: arrowTop,
								left: arrowLeft,
								fill: cfg.color,
								height: cfg.width * 7,
								width: cfg.width * 7,
								angle: cfg.angle,
								originX: "center",
								originY: "bottom"
							} );
							cfg.group.push( arrow );
						}

						// SET DRAWING FLAG
						_this.drawing.buffer.isDrawing = true;

						if ( cfg.action != "config" ) {
							if ( cfg.arrow ) {
								var group = new fabric.Group( cfg.group );
								group.set( {
									cfg: cfg,
									fill: cfg.color,
									action: cfg.action,
									selectable: true,
									known: cfg.action == "change"
								} );
								if ( cfg.action == "change" ) {
									_this.setup.fabric.setActiveObject( group );
								}
								_this.setup.fabric.add( group );
								return group;
							} else {
								_this.setup.fabric.add( line );
								return line;
							}
						} else {
							for ( i1 = 0; i1 < cfg.group.length; i1++ ) {
								cfg.group[ i1 ].ignoreUndo = true;
								_this.setup.fabric.add( cfg.group[ i1 ] );
							}
						}
						return cfg;
					}
				}
			},
			defaults: {
				position: "top-right",
				fileName: "pos",
				action: "download",
				overflow: true,
				path: ( ( chart.path || "" ) ),
				formats: {
					JPG: {
						mimeType: "image/jpg",
						extension: "jpg",
						capture: true
					},
					PNG: {
						mimeType: "image/png",
						extension: "png",
						capture: true
					},
					SVG: {
						mimeType: "text/xml",
						extension: "svg",
						capture: true
					},
					PDF: {
						mimeType: "application/pdf",
						extension: "pdf",
						capture: true
					},
					CSV: {
						mimeType: "text/plain",
						extension: "csv"
					},
					JSON: {
						mimeType: "text/plain",
						extension: "json"
					},
					XLSX: {
						mimeType: "application/octet-stream",
						extension: "xlsx"
					}
				},
				fabric: {
					backgroundColor: "#FFFFFF",
					removeImages: true,
					forceRemoveImages: false,
					selection: false,
					loadTimeout: 5000,
					drawing: {
						enabled: true,
						arrow: "end",
						lineCap: "butt",
						mode: "pencil",
						modes: [ "pencil", "line", "arrow" ],
						color: "#000000",
						colors: [ "#000000", "#FFFFFF", "#FF0000", "#00FF00", "#0000FF" ],
						shapes: [ "11.svg", "14.svg", "16.svg", "17.svg", "20.svg", "27.svg" ],
						width: 1,
						fontSize: 11,
						widths: [ 1, 5, 10, 15 ],
						opacity: 1,
						opacities: [ 1, 0.8, 0.6, 0.4, 0.2 ],
						menu: undefined,
						autoClose: true
					},
					border: {
						fill: "",
						fillOpacity: 0,
						stroke: "#000000",
						strokeWidth: 1,
						strokeOpacity: 1
					}
				},
				pdfMake: {
					images: {},
					pageOrientation: "portrait",
					pageMargins: 40,
					pageOrigin: true,
					pageSize: "A4",
					pageSizes: {
						"4A0": [ 4767.87, 6740.79 ],
						"2A0": [ 3370.39, 4767.87 ],
						"A0": [ 2383.94, 3370.39 ],
						"A1": [ 1683.78, 2383.94 ],
						"A2": [ 1190.55, 1683.78 ],
						"A3": [ 841.89, 1190.55 ],
						"A4": [ 595.28, 841.89 ],
						"A5": [ 419.53, 595.28 ],
						"A6": [ 297.64, 419.53 ],
						"A7": [ 209.76, 297.64 ],
						"A8": [ 147.40, 209.76 ],
						"A9": [ 104.88, 147.40 ],
						"A10": [ 73.70, 104.88 ],
						"B0": [ 2834.65, 4008.19 ],
						"B1": [ 2004.09, 2834.65 ],
						"B2": [ 1417.32, 2004.09 ],
						"B3": [ 1000.63, 1417.32 ],
						"B4": [ 708.66, 1000.63 ],
						"B5": [ 498.90, 708.66 ],
						"B6": [ 354.33, 498.90 ],
						"B7": [ 249.45, 354.33 ],
						"B8": [ 175.75, 249.45 ],
						"B9": [ 124.72, 175.75 ],
						"B10": [ 87.87, 124.72 ],
						"C0": [ 2599.37, 3676.54 ],
						"C1": [ 1836.85, 2599.37 ],
						"C2": [ 1298.27, 1836.85 ],
						"C3": [ 918.43, 1298.27 ],
						"C4": [ 649.13, 918.43 ],
						"C5": [ 459.21, 649.13 ],
						"C6": [ 323.15, 459.21 ],
						"C7": [ 229.61, 323.15 ],
						"C8": [ 161.57, 229.61 ],
						"C9": [ 113.39, 161.57 ],
						"C10": [ 79.37, 113.39 ],
						"RA0": [ 2437.80, 3458.27 ],
						"RA1": [ 1729.13, 2437.80 ],
						"RA2": [ 1218.90, 1729.13 ],
						"RA3": [ 864.57, 1218.90 ],
						"RA4": [ 609.45, 864.57 ],
						"SRA0": [ 2551.18, 3628.35 ],
						"SRA1": [ 1814.17, 2551.18 ],
						"SRA2": [ 1275.59, 1814.17 ],
						"SRA3": [ 907.09, 1275.59 ],
						"SRA4": [ 637.80, 907.09 ],
						"EXECUTIVE": [ 521.86, 756.00 ],
						"FOLIO": [ 612.00, 936.00 ],
						"LEGAL": [ 612.00, 1008.00 ],
						"LETTER": [ 612.00, 792.00 ],
						"TABLOID": [ 792.00, 1224.00 ]
					}
				},
				menu: undefined,
				divId: null,
				menuReviver: null,
				menuWalker: null,
				fallback: true,
				keyListener: true,
				fileListener: true,
				compress: true,
				debug: false
			},

			/**
			 * Buffer for latter listener clearance
			 */
			listenersToRemove: [],

			/**
			 * Returns translated message, takes english as default
			 */
			i18l: function( key, language ) {
				var lang = language ? language : _this.setup.chart.language ? _this.setup.chart.language : "en";
				var catalog = AmCharts.translations[ _this.name ][ lang ] || AmCharts.translations[ _this.name ][ "en" ];

				return catalog[ key ] || key;
			},

			/**
			 * Modifcations on given state to apply correctly on group elements
			 */
			prepareGroupState: function(state) {
				state = state || {};

				delete state.width;
				delete state.strokeWidth;

				return state;
			},

			/**
			 * Method to retrieve the state of the given item
			 */
			getState: function(item) {
				var state = item.saveState();

				return state._stateProperties || state.originalState;

			},

			/**
			 * Generates download file; if unsupported offers fallback to save manually
			 */
			download: function( data, type, filename ) {
				// SAVE
				if ( window.saveAs && _this.setup.hasBlob ) {
					var blob = _this.toBlob( {
						data: data,
						type: type
					}, function( data ) {
						saveAs( data, filename );
					} );

					// FALLBACK TEXTAREA
				} else if ( _this.config.fallback && type == "text/plain" ) {
					var div = document.createElement( "div" );
					var msg = document.createElement( "div" );
					var textarea = document.createElement( "textarea" );

					msg.innerHTML = _this.i18l( "fallback.save.text" );

					div.appendChild( msg );
					div.appendChild( textarea );
					msg.setAttribute( "class", "amcharts-export-fallback-message" );
					div.setAttribute( "class", "amcharts-export-fallback" );
					_this.setup.chart.containerDiv.appendChild( div );

					// FULFILL TEXTAREA AND PRESELECT
					textarea.setAttribute( "readonly", "" );
					textarea.value = data;
					textarea.focus();
					textarea.select();

					// UPDATE MENU
					_this.createMenu( [ {
						"class": "export-main export-close",
						label: "Done",
						click: function() {
							_this.createMenu( _this.config.menu );
							if ( _this.isElement(_this.setup.chart.containerDiv) ) {
								_this.setup.chart.containerDiv.removeChild( div );
							}
						}
					} ] );

					// FALLBACK IMAGE
				} else if ( _this.config.fallback && type.split( "/" )[ 0 ] == "image" ) {
					var div = document.createElement( "div" );
					var msg = document.createElement( "div" );
					var img = _this.toImage( {
						data: data
					} );

					msg.innerHTML = _this.i18l( "fallback.save.image" );

					// FULFILL TEXTAREA AND PRESELECT
					div.appendChild( msg );
					div.appendChild( img );
					msg.setAttribute( "class", "amcharts-export-fallback-message" );
					div.setAttribute( "class", "amcharts-export-fallback" );
					_this.setup.chart.containerDiv.appendChild( div );

					// UPDATE MENU
					_this.createMenu( [ {
						"class": "export-main export-close",
						label: "Done",
						click: function() {
							_this.createMenu( _this.config.menu );
							if ( _this.isElement(_this.setup.chart.containerDiv) ) {
								_this.setup.chart.containerDiv.removeChild( div );
							}
						}
					} ] );

					// ERROR
				} else {
					throw new Error( "Unable to create file. Ensure saveAs (FileSaver.js) is supported." );
				}
				return data;
			},

			/**
			 * Generates script, links tags and places them into the document's head
			 * In case of reload it replaces the node to force the download
			 */
			loadResource: function( src, addons ) {
				var i1, exist, node, item, check, type;
				var url = src.indexOf( "//" ) != -1 ? src : [ _this.libs.path, src ].join( "" );

				function errorCallback() {
						_this.handleLog( [ "amCharts[export]: Loading error on ", this.src || this.href ].join( "" ) );
				}

				function loadCallback() {
					if ( addons ) {
						for ( i1 = 0; i1 < addons.length; i1++ ) {
							_this.loadResource( addons[ i1 ] );
						}
					}
				}

				if ( src.indexOf( ".js" ) != -1 ) {
					node = document.createElement( "script" );
					node.setAttribute( "type", "text/javascript" );
					node.setAttribute( "src", url );
					if ( _this.libs.async ) {
						node.setAttribute( "async", "" );
					}

				} else if ( src.indexOf( ".css" ) != -1 ) {
					node = document.createElement( "link" );
					node.setAttribute( "type", "text/css" );
					node.setAttribute( "rel", "stylesheet" );
					node.setAttribute( "href", url );
				}

				// NODE CHECK
				for ( i1 = 0; i1 < document.head.childNodes.length; i1++ ) {
					item = document.head.childNodes[ i1 ];
					check = item ? ( item.src || item.href ) : false;
					type = item ? item.tagName : false;

					if ( item && check && check.indexOf( src ) != -1 ) {
						if ( _this.libs.reload ) {
							document.head.removeChild( item );
						}
						exist = true;
						break;
					}
				}

				// NAMESPACE CHECK
				Object.keys( _this.libs.namespaces ).some(function( i1 ) {
					var namespace = _this.libs.namespaces[ i1 ];
					var check = src.toLowerCase();
					var item = i1.toLowerCase();

					if ( check.indexOf( item ) != -1 ) {

						// SKIP UNSUPPORTED IE9 LIBS
						if ( _this.setup.isIE && _this.setup.IEversion <= 9 ) {
							if ( _this.libs.unsupportedIE9libs && _this.libs.unsupportedIE9libs.indexOf(item) != -1 ) {
								return false; // continue
							}
						}

						// NAMESPACE EXISTS; BREAK LOOP; NEXT
						if ( window[ namespace ] !== undefined ) {
							exist = true;
							return true; // break;
						}
					}
				});

				// EXISTS NOT NEEDED TO LOAD
				if ( !exist || _this.libs.reload ) {
					node.addEventListener( "load", loadCallback );
					_this.addListenerToRemove( "load", node, loadCallback );
					node.addEventListener( "error", errorCallback );
					_this.addListenerToRemove( "error", node, errorCallback );

					document.head.appendChild( node );
				}
			},

			/**
			 * Adds listeners to the buffer for latter listener clearance
			 */
			addListenerToRemove: function(event,node,method) {
				_this.listenersToRemove.push( {
					node: node,
					method: method,
					event: event
				} );
			},

			/**
			 * Walker to generate the script,link tags
			 */
			loadDependencies: function() {
				var i1, i2;
				if ( _this.libs.autoLoad ) {
					for ( i1 = 0; i1 < _this.libs.resources.length; i1++ ) {
						if ( _this.libs.resources[ i1 ] instanceof Object ) {
							Object.keys( _this.libs.resources[ i1 ] ).some(function( i2 ) {
								_this.loadResource( i2, _this.libs.resources[ i1 ][ i2 ] );
							});
						} else {
							_this.loadResource( _this.libs.resources[ i1 ] );
						}
					}
				}
			},

			/**
			 * Converts string to number
			 */
			pxToNumber: function( attr, returnUndefined ) {
				if ( !attr && returnUndefined ) {
					return undefined;
				}
				return Number( String( attr ).replace( "px", "" ) ) || 0;
			},

			/**
			 * Converts number to string
			 */
			numberToPx: function( attr ) {
				return String( attr ) + "px";
			},

			/**
			 * Referenceless copy of object type variables
			 */
			cloneObject: function( o ) {
				var clone, v, k, isObject, isDate;
				clone = Array.isArray( o ) ? [] : {};

				// Walkthrough values
				Object.keys( o ).some(function( k ) {
					v = o[ k ];
					isObject = typeof v === "object";
					isDate = v instanceof Date;

					// Set value; call recursivly if value is an object
					clone[ k ] = isObject && !isDate ? _this.cloneObject( v ) : v;
				});
				return clone;
			},

			/**
			 * Recursive method to merge the given objects together
			 * Overwrite flag replaces the value instead to crawl through
			 */
			deepMerge: function( a, b, overwrite ) {
				var i1, v, type = b instanceof Array ? "array" : "object";

				// SKIP; OBJECTS AND ARRAYS ONLY
				if ( !( a instanceof Object || a instanceof Array ) ) {
					return a;
				}

				// WALKTHOUGH SOURCE
				Object.keys( b ).some(function( i1 ) {

					// PREVENT METHODS
					if ( type == "array" && isNaN( i1 ) ) {
						return false; // continue
					}

					// ASSIGN VALUE
					v = b[ i1 ];

					// NEW INSTANCE
					if ( a && a[ i1 ] == undefined || overwrite ) {
						if ( v instanceof Array ) {
							a[ i1 ] = new Array();
						} else if ( v instanceof Function ) {
							a[ i1 ] = function() {};
						} else if ( v instanceof Date ) {
							a[ i1 ] = new Date();
						} else if ( v instanceof Object ) {
							a[ i1 ] = new Object();
						} else if ( v instanceof Number ) {
							a[ i1 ] = new Number();
						} else if ( v instanceof String ) {
							a[ i1 ] = new String();
						}
					}

					// WALKTHROUGH RECURSIVLY
					if (
						( v instanceof Object || v instanceof Array ) &&
						!( v instanceof Function || v instanceof Date || _this.isElement( v ) ) &&
						i1 != "chart" &&
						i1 != "scope"
					) {
						_this.deepMerge( a[ i1 ], v, overwrite );

						// ASSIGN
					} else {
						if ( a instanceof Array && !overwrite ) {
							a.push( v );
						} else if ( a ) {
							a[ i1 ] = v;
						}
					}
				});
				return a;
			},

			/**
			 * Checks if given argument is a valid node
			 */
			isElement: function( thingy ) {
				return thingy instanceof Object && thingy && thingy.nodeType === 1;
			},

			/**
			 * Checks if given argument contains a hashbang and returns it
			 */
			isHashbanged: function( thingy ) {
				var str = String( thingy ).replace( /\"/g, "" );

				return str.slice( 0, 3 ) == "url" ? str.slice( str.indexOf( "#" ) + 1, str.length - 1 ) : false;
			},

			/**
			 * Checks if given event has been thrown with pressed click / touch
			 */
			isPressed: function( event ) {
				// IE EXCEPTION
				if ( event.type == "mousemove" && event.which === 1 ) {
					// IGNORE

					// OTHERS
				} else if (
					event.type == "touchmove" ||
					event.buttons === 1 ||
					event.button === 1 ||
					event.which === 1
				) {
					_this.drawing.buffer.isPressed = true;
				} else {
					_this.drawing.buffer.isPressed = false;
				}
				return _this.drawing.buffer.isPressed;
			},

			/**
			 * Checks if given source needs to be removed
			 */
			removeImage: function( source ) {
				if ( source ) {

					// FORCE REMOVAL
					if ( _this.config.fabric.forceRemoveImages ) {
						return true;

						// REMOVE TAINTED
					} else if ( _this.config.fabric.removeImages && _this.isTainted( source ) ) {
						return true;

						// IE 10 internal bug handling SVG images in canvas context
					} else if ( _this.setup.isIE && ( _this.setup.IEversion == 10 || _this.setup.IEversion == 11 ) && source.toLowerCase().indexOf( ".svg" ) != -1 ) {
						return true;
					}
				}
				return false
			},

			/**
			 * Checks if given source is within the current origin
			 */
			isTainted: function( source ) {
				var origin = String( window.location.origin || window.location.protocol + "//" + window.location.hostname + ( window.location.port ? ':' + window.location.port : '' ) );

				// CHECK GIVEN SOURCE
				if ( source ) {
					// LOCAL FILES ARE ALWAYS TAINTED
					if (
						origin.indexOf( ":\\" ) != -1 || source.indexOf( ":\\" ) != -1 ||
						origin.indexOf( "file://" ) != -1 || source.indexOf( "file://" ) != -1
					) {
						return true

						// MISMATCHING ORIGIN
					} else if ( source.indexOf( "//" ) != -1 && source.indexOf( origin.replace( /.*:/, "" ) ) == -1 ) {
						return true;
					}
				}

				return false;
			},

			/*
			 ** Checks several indicators for acceptance;
			 */
			isSupported: function() {
				// CHECK CONFIG
				if ( !_this.config.enabled ) {
					return false;
				}

				// CHECK IE; ATTEMPT TO ACCESS HEAD ELEMENT
				if ( _this.setup.isIE && _this.setup.IEversion <= 9 ) {
					if ( !Array.prototype.indexOf || !document.head || _this.config.fallback === false ) {
						return false;
					}
				}
				return true;
			},


			getAngle: function( x1, y1, x2, y2 ) {
				var x = x2 - x1;
				var y = y2 - y1;
				var angle;
				if ( x == 0 ) {
					if ( y == 0 ) {
						angle = 0;
					} else if ( y > 0 ) {
						angle = Math.PI / 2;
					} else {
						angle = Math.PI * 3 / 2;
					}
				} else if ( y == 0 ) {
					if ( x > 0 ) {
						angle = 0;
					} else {
						angle = Math.PI;
					}
				} else {
					if ( x < 0 ) {
						angle = Math.atan( y / x ) + Math.PI;
					} else if ( y < 0 ) {
						angle = Math.atan( y / x ) + ( 2 * Math.PI );
					} else {
						angle = Math.atan( y / x );
					}
				}
				return angle * 180 / Math.PI;
			},

			/**
			 * Recursive method which crawls upwards to gather the requested attribute
			 */
			gatherAttribute: function( elm, attr, limit, lvl ) {
				var value, lvl = lvl ? lvl : 0,
					limit = limit ? limit : 3;
				if ( elm ) {
					value = elm.getAttribute( attr );

					if ( !value && lvl < limit ) {
						return _this.gatherAttribute( elm.parentNode, attr, limit, lvl + 1 );
					}
				}
				return value;
			},

			/**
			 * Recursive method which crawls upwards to gather the requested classname
			 */
			gatherClassName: function( elm, className, limit, lvl ) {
				var value, lvl = lvl ? lvl : 0,
					limit = limit ? limit : 3;

				if ( _this.isElement( elm ) ) {
					value = ( elm.getAttribute( "class" ) || "" ).split( " " ).indexOf( className ) != -1;

					if ( !value && lvl < limit ) {
						return _this.gatherClassName( elm.parentNode, className, limit, lvl + 1 );
					} else if ( value ) {
						value = elm;
					}
				}
				return value;
			},

			/**
			 * Collects the clip-paths and patterns
			 */
			gatherElements: function( group, cfg, images ) {
				var i1, i2;
				for ( i1 = 0; i1 < group.children.length; i1++ ) {
					var childNode = group.children[ i1 ];

					// CLIPPATH
					if ( childNode.tagName == "clipPath" ) {
						var bbox = {};
						var transform = fabric.parseTransformAttribute( _this.gatherAttribute( childNode, "transform" ) );

						// HIDE SIBLINGS; GATHER IT'S DIMENSIONS
						for ( i2 = 0; i2 < childNode.childNodes.length; i2++ ) {
							childNode.childNodes[ i2 ].setAttribute( "fill", "transparent" );
							bbox = {
								x: _this.pxToNumber( childNode.childNodes[ i2 ].getAttribute( "x" ) ),
								y: _this.pxToNumber( childNode.childNodes[ i2 ].getAttribute( "y" ) ),
								width: _this.pxToNumber( childNode.childNodes[ i2 ].getAttribute( "width" ) ),
								height: _this.pxToNumber( childNode.childNodes[ i2 ].getAttribute( "height" ) )
							}
						}

						group.clippings[ childNode.id ] = {
							svg: childNode,
							bbox: bbox,
							transform: transform
						};

						// PATTERN
					} else if ( childNode.tagName == "pattern" ) {
						var props = {
							node: childNode,
							source: childNode.getAttribute( "xlink:href" ),
							width: Number( childNode.getAttribute( "width" ) ),
							height: Number( childNode.getAttribute( "height" ) ),
							repeat: "repeat",
							offsetX: 0,
							offsetY: 0
						}

						// GATHER BACKGROUND
						for ( i2 = 0; i2 < childNode.childNodes.length; i2++ ) {
							// RECT; COLOR
							if ( childNode.childNodes[ i2 ].tagName == "rect" ) {
								props.fill = childNode.childNodes[ i2 ].getAttribute( "fill" );

								// IMAGE
							} else if ( childNode.childNodes[ i2 ].tagName == "image" ) {
								var attrs = fabric.parseAttributes( childNode.childNodes[ i2 ], fabric.SHARED_ATTRIBUTES );

								if ( attrs.transformMatrix ) {
									props.offsetX = attrs.transformMatrix[ 4 ];
									props.offsetY = attrs.transformMatrix[ 5 ];
								}
							}
						}

						// TAINTED
						if ( _this.removeImage( props.source ) ) {
							group.patterns[ childNode.id ] = props.fill ? props.fill : "transparent";
						} else {
							group.patterns[ props.node.id ] = props;
						}

						// IMAGES
					} else if ( childNode.tagName == "image" ) {
						images.included++;

						// LOAD IMAGE MANUALLY; TO RERENDER THE CANVAS
						fabric.Image.fromURL( childNode.getAttribute( "xlink:href" ), function( img ) {
							images.loaded++;
						} );

						// FILL STROKE POLYFILL ON EVERY ELEMENT
					} else {
						var attrs = [ "fill", "stroke" ];
						for ( i2 = 0; i2 < attrs.length; i2++ ) {
							var attr = attrs[ i2 ];
							var attrVal = childNode.getAttribute( attr );
							var attrRGBA = _this.getRGBA( attrVal );
							var isHashbanged = _this.isHashbanged( attrVal );

							// VALIDATE AND RESET UNKNOWN COLORS (avoids fabric to crash)
							if ( attrVal && !attrRGBA && !isHashbanged ) {
								childNode.setAttribute( attr, "none" );
								childNode.setAttribute( attr + "-opacity", "0" );
							}
						}
					}
				}
				return group;
			},

			/*
			 ** GET RGBA COLOR ARRAY FROM INPUT
			 */
			getRGBA: function( source, returnInstance ) {

				if ( source != "none" && source != "transparent" && !_this.isHashbanged( source ) ) {
					source = new fabric.Color( source );

					if ( source._source ) {
						return returnInstance ? source : source.getSource();
					}
				}

				return false;
			},

			/*
			 ** GATHER MOUSE POSITION;
			 */
			gatherPosition: function( event, type ) {
				var ref = _this.drawing.buffer.position;
				var ivt = fabric.util.invertTransform( _this.setup.fabric.viewportTransform );
				var pos;

				if ( event.type == "touchmove" ) {
					if ( "touches" in event ) {
						event = event.touches[ 0 ];
					} else if ( "changedTouches" in event ) {
						event = event.changedTouches[ 0 ];
					}
				}

				pos = fabric.util.transformPoint( _this.setup.fabric.getPointer( event, true ), ivt );

				if ( type == 1 ) {
					ref.x1 = pos.x;
					ref.y1 = pos.y;
				}

				ref.x2 = pos.x;
				ref.y2 = pos.y;
				ref.xD = ( ref.x1 - ref.x2 ) < 0 ? ( ref.x1 - ref.x2 ) * -1 : ( ref.x1 - ref.x2 );
				ref.yD = ( ref.y1 - ref.y2 ) < 0 ? ( ref.y1 - ref.y2 ) * -1 : ( ref.y1 - ref.y2 );

				return ref;
			},

			modifyFabric: function() {

				// ADAPTED THE WAY TO RECEIVE THE GRADIENTID
				fabric.ElementsParser.prototype.resolveGradient = function( obj, property ) {

					var instanceFillValue = obj.get( property );
					if ( !( /^url\(/ ).test( instanceFillValue ) ) {
						return;
					}
					var gradientId = instanceFillValue.slice( instanceFillValue.indexOf( "#" ) + 1, instanceFillValue.length - 1 );
					if ( fabric.gradientDefs[ this.svgUid ][ gradientId ] ) {
						var tmp = fabric.Gradient.fromElement( fabric.gradientDefs[ this.svgUid ][ gradientId ], obj );

						// WORKAROUND FOR VERTICAL GRADIENT ISSUE; FOR NONE PIE CHARTS
						if ( tmp.coords.y1 && _this.setup.chart.type != "pie" ) {
							tmp.coords.y2 = tmp.coords.y1 * -1;
							tmp.coords.y1 = 0;
						}
						obj.set( property, tmp );
					}
				};

				// MULTILINE SUPPORT; TODO: BETTER POSITIONING
				fabric.Text.fromElement = function( element, options ) {
					if ( !element ) {
						return null;
					}

					var parsedAttributes = fabric.parseAttributes( element, fabric.Text.ATTRIBUTE_NAMES );
					options = fabric.util.object.extend( ( options ? fabric.util.object.clone( options ) : {} ), parsedAttributes );

					options.top = options.top || 0;
					options.left = options.left || 0;
					if ( 'dx' in parsedAttributes ) {
						options.left += parsedAttributes.dx;
					}
					if ( 'dy' in parsedAttributes ) {
						options.top += parsedAttributes.dy;
					}
					if ( !( 'fontSize' in options ) ) {
						options.fontSize = fabric.Text.DEFAULT_SVG_FONT_SIZE;
					}

					if ( !options.originX ) {
						options.originX = 'left';
					}

					var textContent = '';
					var textBuffer = [];

					// The XML is not properly parsed in IE9 so a workaround to get
					// textContent is through firstChild.data. Another workaround would be
					// to convert XML loaded from a file to be converted using DOMParser (same way loadSVGFromString() does)
					if ( !( 'textContent' in element ) ) {
						if ( 'firstChild' in element && element.firstChild !== null ) {
							if ( 'data' in element.firstChild && element.firstChild.data !== null ) {
								textBuffer.push( element.firstChild.data );
							}
						}
					} else if ( element.childNodes ) {
						for ( var i1 = 0; i1 < element.childNodes.length; i1++ ) {
							textBuffer.push( element.childNodes[ i1 ].textContent );
						}
					} else {
						textBuffer.push( element.textContent );
					}

					textContent = textBuffer.join( "\n" );
					//textContent = textContent.replace(/^\s+|\s+$|\n+/g, '').replace(/\s+/g, ' ');

					var text = new fabric.Text( textContent, options ),
						/*
						  Adjust positioning:
						    x/y attributes in SVG correspond to the bottom-left corner of text bounding box
						    top/left properties in Fabric correspond to center point of text bounding box
						*/
						offX = 0;

					if ( text.originX === 'left' ) {
						offX = text.getWidth() / 2;
					}
					if ( text.originX === 'right' ) {
						offX = -text.getWidth() / 2;
					}

					if ( textBuffer.length > 1 ) {

						text.set( {
							left: text.getLeft() + offX,
							top: text.getTop() + text.fontSize * ( textBuffer.length - 1 ) * ( 0.18 + text._fontSizeFraction ),
							textAlign: options.originX,
							lineHeight: textBuffer.length > 1 ? 0.965 : 1.16,
						} );

					} else {
						text.set( {
							left: text.getLeft() + offX,
							top: text.getTop() - text.getHeight() / 2 + text.fontSize * ( 0.18 + text._fontSizeFraction ) /* 0.3 is the old lineHeight */
						} );
					}

					return text;
				};
			},

			/**
			 * Method to capture the current state of the chart
			 */
			capture: function( options, callback ) {
				var i1;
				var cfg = _this.deepMerge( _this.deepMerge( {}, _this.config.fabric ), options || {} );
				var groups = [];
				var offset = {
					x: 0,
					y: 0,
					pX: 0,
					pY: 0,
					lX: 0,
					lY: 0,
					width: _this.setup.chart.divRealWidth,
					height: _this.setup.chart.divRealHeight
				};
				var images = {
					loaded: 0,
					included: 0
				}
				var legends = {
					items: [],
					width: 0,
					height: 0,
					maxWidth: 0,
					maxHeight: 0
				}

				// NAMESPACE CHECK
				if ( !_this.handleNamespace( "fabric", {
						scope: this,
						cb: _this.capture,
						args: arguments
					} ) ) {
					return false;
				}

				// MODIFY FABRIC UNTIL IT'S OFFICIALLY SUPPORTED
				_this.modifyFabric();

				// BEFORE CAPTURING
				_this.handleCallback( cfg.beforeCapture, cfg );

				// GATHER SVGS
				var svgs = _this.setup.chart.containerDiv.getElementsByTagName( "svg" );
				for ( i1 = 0; i1 < svgs.length; i1++ ) {
					var group = {
						svg: svgs[ i1 ],
						parent: svgs[ i1 ].parentNode,
						children: svgs[ i1 ].getElementsByTagName( "*" ),
						offset: {
							x: 0,
							y: 0
						},
						patterns: {},
						clippings: {},
						has: {
							legend: false,
							panel: false,
							scrollbar: false
						}
					}

					// CHECK IT'S SURROUNDINGS
					group.has.legend = _this.gatherClassName( group.parent, _this.setup.chart.classNamePrefix + "-legend-div", 1 );
					group.has.panel = _this.gatherClassName( group.parent, _this.setup.chart.classNamePrefix + "-stock-panel-div" );
					group.has.scrollbar = _this.gatherClassName( group.parent, _this.setup.chart.classNamePrefix + "-scrollbar-chart-div" );

					// GATHER ELEMENTS
					group = _this.gatherElements( group, cfg, images );

					// APPEND GROUP
					groups.push( group );
				}

				// GATHER EXTERNAL LEGEND
				if ( _this.config.legend ) {

					// STOCK
					if ( _this.setup.chart.type == "stock" ) {
						for ( i1 = 0; i1 < _this.setup.chart.panels.length; i1++ ) {
							if ( _this.setup.chart.panels[ i1 ].stockLegend && _this.setup.chart.panels[ i1 ].stockLegend.divId ) {
								legends.items.push( _this.setup.chart.panels[ i1 ].stockLegend );
							}
						}

						// NORMAL
					} else if ( _this.setup.chart.legend && _this.setup.chart.legend.divId ) {
						legends.items.push( _this.setup.chart.legend );
					}

					// WALKTHROUGH
					for ( i1 = 0; i1 < legends.items.length; i1++ ) {
						var legend = legends.items[ i1 ];
						var group = {
							svg: legend.container.container,
							parent: legend.container.container.parentNode,
							children: legend.container.container.getElementsByTagName( "*" ),
							offset: {
								x: 0,
								y: 0
							},
							legend: {
								id: i1,
								type: [ "top", "left" ].indexOf( _this.config.legend.position ) != -1 ? "unshift" : "push",
								position: _this.config.legend.position,
								width: _this.config.legend.width ? _this.config.legend.width : legend.container.div.offsetWidth,
								height: _this.config.legend.height ? _this.config.legend.height : legend.container.div.offsetHeight
							},
							patterns: {},
							clippings: {},
							has: {
								legend: false,
								panel: false,
								scrollbar: false
							}
						}

						// GATHER DIMENSIONS
						legends.width += group.legend.width;
						legends.height += group.legend.height;
						legends.maxWidth = group.legend.width > legends.maxWidth ? group.legend.width : legends.maxWidth;
						legends.maxHeight = group.legend.height > legends.maxHeight ? group.legend.height : legends.maxHeight;

						// GATHER ELEMENTS
						group = _this.gatherElements( group, cfg, images );

						// PRE/APPEND SVG
						groups[ group.legend.type ]( group );
					}

					// ADAPT WIDTH IF NEEDED; EXPAND HEIGHT
					if ( [ "top", "bottom" ].indexOf( _this.config.legend.position ) != -1 ) {
						offset.width = legends.maxWidth > offset.width ? legends.maxWidth : offset.width;
						offset.height += legends.height;

						// EXPAND WIDTH; ADAPT HEIGHT IF NEEDED
					} else if ( [ "left", "right" ].indexOf( _this.config.legend.position ) != -1 ) {
						offset.width += legends.maxWidth;
						offset.height = legends.height > offset.height ? legends.height : offset.height;

						// SIMPLY EXPAND CANVAS
					} else {
						offset.height += legends.height;
						offset.width += legends.maxWidth;
					}

				}

				// CLEAR IF EXIST
				_this.drawing.enabled = cfg.drawing.enabled = cfg.action == "draw";
				_this.drawing.buffer.enabled = _this.drawing.enabled; // history reasons

				_this.setup.wrapper = document.createElement( "div" );
				_this.setup.wrapper.setAttribute( "class", _this.setup.chart.classNamePrefix + "-export-canvas" );
				_this.setup.chart.containerDiv.appendChild( _this.setup.wrapper );

				// STOCK CHART; SELECTOR OFFSET
				if ( _this.setup.chart.type == "stock" ) {
					var padding = {
						top: 0,
						right: 0,
						bottom: 0,
						left: 0
					}
					if ( _this.setup.chart.leftContainer ) {
						offset.width -= _this.setup.chart.leftContainer.offsetWidth;
						padding.left = _this.setup.chart.leftContainer.offsetWidth + ( _this.setup.chart.panelsSettings.panelSpacing * 2 );
					}
					if ( _this.setup.chart.rightContainer ) {
						offset.width -= _this.setup.chart.rightContainer.offsetWidth;
						padding.right = _this.setup.chart.rightContainer.offsetWidth + ( _this.setup.chart.panelsSettings.panelSpacing * 2 );
					}
					if ( _this.setup.chart.periodSelector && [ "top", "bottom" ].indexOf( _this.setup.chart.periodSelector.position ) != -1 ) {
						offset.height -= _this.setup.chart.periodSelector.offsetHeight + _this.setup.chart.panelsSettings.panelSpacing;
						padding[ _this.setup.chart.periodSelector.position ] += _this.setup.chart.periodSelector.offsetHeight + _this.setup.chart.panelsSettings.panelSpacing;
					}
					if ( _this.setup.chart.dataSetSelector && [ "top", "bottom" ].indexOf( _this.setup.chart.dataSetSelector.position ) != -1 ) {
						offset.height -= _this.setup.chart.dataSetSelector.offsetHeight;
						padding[ _this.setup.chart.dataSetSelector.position ] += _this.setup.chart.dataSetSelector.offsetHeight;
					}

					// APPLY OFFSET ON WRAPPER
					_this.setup.wrapper.style.paddingTop = _this.numberToPx( padding.top );
					_this.setup.wrapper.style.paddingRight = _this.numberToPx( padding.right );
					_this.setup.wrapper.style.paddingBottom = _this.numberToPx( padding.bottom );
					_this.setup.wrapper.style.paddingLeft = _this.numberToPx( padding.left );
				}

				// CREATE CANVAS
				_this.setup.canvas = document.createElement( "canvas" );
				_this.setup.wrapper.appendChild( _this.setup.canvas );

				// PREPARE CONFIG FOR FABRIC INSTANCE
				var fabricCFG = _this.removeFunctionsFromObject(_this.deepMerge( {
					width: offset.width,
					height: offset.height,
					isDrawingMode: true
				}, cfg ));

				// INITIATE FABRIC INSTANCE
				_this.setup.fabric = new fabric.Canvas( _this.setup.canvas, fabricCFG );

				// REAPPLY FOR SOME REASON
				_this.deepMerge( _this.setup.fabric, cfg );
				_this.deepMerge( _this.setup.fabric.freeDrawingBrush, cfg.drawing );

				// RELIABLE VARIABLES; UPDATE DRAWING
				_this.deepMerge( _this.drawing, cfg.drawing );
				_this.drawing.handler.change( cfg.drawing );

				// OBSERVE MOUSE EVENTS
				_this.setup.fabric.on( "mouse:down", function( e ) {
					var p = _this.gatherPosition( e.e, 1 );
					_this.drawing.buffer.pressedTS = Number( new Date() );
					_this.isPressed( e.e );

					// FLAG ISDRAWING
					_this.drawing.buffer.isDrawing = false;
					_this.drawing.buffer.isDrawingTimer = setTimeout( function() {
						if ( !_this.drawing.buffer.isSelected ) {
							_this.drawing.buffer.isDrawing = true;
						}
					}, 200 );
				} );
				_this.setup.fabric.on( "mouse:move", function( e ) {
					var p = _this.gatherPosition( e.e, 2 );
					_this.isPressed( e.e );

					// IS PRESSED BUT UNSELECTED
					if ( _this.drawing.buffer.isPressed && !_this.drawing.buffer.isSelected ) {

						// FLAG ISDRAWING
						_this.drawing.buffer.isDrawing = true;

						// CREATE INITIAL LINE / ARROW; JUST ON LEFT CLICK
						if ( !_this.drawing.buffer.line && _this.drawing.mode != "pencil" && ( p.xD > 5 || p.yD > 5 ) ) {

							// FORCE FABRIC TO DISABLE DRAWING MODE WHILE PRESSED / MOVEING MOUSE INPUT
							_this.setup.fabric.isDrawingMode = false;
							_this.setup.fabric._isCurrentlyDrawing = false;
							_this.drawing.buffer.ignoreUndoOnMouseUp = true;
							_this.setup.fabric.freeDrawingBrush.onMouseUp();
							_this.setup.fabric.remove( _this.setup.fabric._objects.pop() );

							// INITIAL POINT
							_this.drawing.buffer.line = _this.drawing.handler.line( {
								x1: p.x1,
								y1: p.y1,
								x2: p.x2,
								y2: p.y2,
								arrow: _this.drawing.mode == "line" ? false : _this.drawing.arrow,
								action: "config"
							} );
						}
					}

					if ( _this.drawing.buffer.isSelected ) {
						_this.setup.fabric.isDrawingMode = false;
					}

					// UPDATE LINE / ARROW
					if ( _this.drawing.buffer.line ) {
						var obj, top, left;
						var l = _this.drawing.buffer.line;

						l.x2 = p.x2;
						l.y2 = p.y2;

						// // RESET INTERNAL FLAGS
						// _this.drawing.buffer.isDrawing = true;
						// _this.drawing.buffer.isPressed = true;
						// _this.drawing.buffer.hasLine = true;

						for ( i1 = 0; i1 < l.group.length; i1++ ) {
							obj = l.group[ i1 ];

							if ( obj instanceof fabric.Line ) {
								obj.set( {
									x2: l.x2,
									y2: l.y2
								} );
							} else if ( obj instanceof fabric.Triangle ) {
								l.angle = ( _this.getAngle( l.x1, l.y1, l.x2, l.y2 ) + 90 );

								if ( l.arrow == "start" ) {
									top = l.y1 + ( l.width / 2 );
									left = l.x1 + ( l.width / 2 );
								} else if ( l.arrow == "middle" ) {
									top = l.y2 + ( l.width / 2 ) - ( ( l.y2 - l.y1 ) / 2 );
									left = l.x2 + ( l.width / 2 ) - ( ( l.x2 - l.x1 ) / 2 );
								} else { // arrow: end
									top = l.y2 + ( l.width / 2 );
									left = l.x2 + ( l.width / 2 );
								}

								obj.set( {
									top: top,
									left: left,
									angle: l.angle
								} );
							}
						}
						_this.setup.fabric.renderAll();
					}
				} );
				_this.setup.fabric.on( "mouse:up", function( e ) {
					// SELECT TARGET
					if ( !_this.drawing.buffer.isDrawing ) {
						var target = _this.setup.fabric.findTarget( e.e );
						if ( target && target.selectable ) {
							_this.setup.fabric.setActiveObject( target );
						}
					}

					// UPDATE LINE / ARROW
					if ( _this.drawing.buffer.line ) {
						for ( i1 = 0; i1 < _this.drawing.buffer.line.group.length; i1++ ) {
							_this.drawing.buffer.line.group[ i1 ].remove();
						}
						delete _this.drawing.buffer.line.action;
						delete _this.drawing.buffer.line.group;
						_this.drawing.handler.line( _this.drawing.buffer.line );
					}
					_this.drawing.buffer.line = false;
					_this.drawing.buffer.hasLine = false;
					_this.drawing.buffer.isPressed = false;

					// RESET ISDRAWING FLAG
					clearTimeout( _this.drawing.buffer.isDrawingTimer );
					_this.drawing.buffer.isDrawing = false;
				} );

				// OBSERVE OBJECT SELECTION
				_this.setup.fabric.on( "object:selected", function( e ) {
					_this.drawing.buffer.isSelected = true;
					_this.drawing.buffer.target = e.target;
					_this.setup.fabric.isDrawingMode = false;
				} );
				_this.setup.fabric.on( "selection:cleared", function( e ) {
					_this.drawing.buffer.target = false;

					// FREEHAND WORKAROUND
					if ( _this.drawing.buffer.isSelected ) {
						_this.setup.fabric._isCurrentlyDrawing = false;
					}

					_this.drawing.buffer.isSelected = false;
					_this.setup.fabric.isDrawingMode = true;
				} );
				_this.setup.fabric.on( "path:created", function( e ) {
					var item = e.path;
					if ( !_this.drawing.buffer.isDrawing || _this.drawing.buffer.hasLine ) {
						_this.setup.fabric.remove( item );
						_this.setup.fabric.renderAll();
						return;
					}
				} );

				// OBSERVE OBJECT MODIFICATIONS
				_this.setup.fabric.on( "object:added", function( e ) {
					var item = e.target;
					var state = _this.deepMerge( _this.getState(item), {
						cfg: {
							color: _this.drawing.color,
							width: _this.drawing.width,
							opacity: _this.drawing.opacity,
							fontSize: _this.drawing.fontSize
						}
					} );

					state = JSON.stringify( state );
					item.recentState = state;

					if ( _this.drawing.buffer.ignoreUndoOnMouseUp || !_this.drawing.buffer.isDrawing ) {
						_this.drawing.buffer.ignoreUndoOnMouseUp = false;
						return;
					}

					if ( item.selectable && !item.known && !item.ignoreUndo ) {
						item.isAnnotation = true;
						_this.drawing.undos.push( {
							action: "added",
							target: item,
							state: state
						} );
						_this.drawing.undos.push( {
							action: "added:modified",
							target: item,
							state: state
						} );
						_this.drawing.redos = [];
					}

					item.known = true;
					_this.setup.fabric.isDrawingMode = true;
				} );
				_this.setup.fabric.on( "object:modified", function( e ) {
					var item = e.target;
					console.log(item);
					var recentState = JSON.parse( item.recentState );
					var state = _this.deepMerge( _this.getState(item), {
						cfg: recentState.cfg
					} );

					state = JSON.stringify( state );
					item.recentState = state;

					_this.drawing.undos.push( {
						action: "modified",
						target: item,
						state: state
					} );

					_this.drawing.redos = [];
				} );
				_this.setup.fabric.on( "text:changed", function( e ) {
					var item = e.target;
					clearTimeout( item.timer );
					item.timer = setTimeout( function() {
						var state = JSON.stringify( _this.getState(item) );

						item.recentState = state;

						_this.drawing.redos = [];
						_this.drawing.undos.push( {
							action: "modified",
							target: item,
							state: state
						} );
					}, 250 );
				} );

				// DRAWING
				if ( _this.drawing.enabled ) {
					_this.setup.wrapper.setAttribute( "class", _this.setup.chart.classNamePrefix + "-export-canvas active" );
					_this.setup.wrapper.style.backgroundColor = cfg.backgroundColor;
					_this.setup.wrapper.style.display = "block";

				} else {
					_this.setup.wrapper.setAttribute( "class", _this.setup.chart.classNamePrefix + "-export-canvas" );
					_this.setup.wrapper.style.display = "none";
				}

				for ( i1 = 0; i1 < groups.length; i1++ ) {
					var group = groups[ i1 ];

					// STOCK CHART; SVG OFFSET; SVG OFFSET
					if ( _this.setup.chart.type == "stock" && _this.setup.chart.legendSettings.position ) {

						// TOP / BOTTOM
						if ( [ "top", "bottom" ].indexOf( _this.setup.chart.legendSettings.position ) != -1 ) {

							// POSITION; ABSOLUTE
							if ( group.parent.style.top && group.parent.style.left ) {
								group.offset.y = _this.pxToNumber( group.parent.style.top );
								group.offset.x = _this.pxToNumber( group.parent.style.left );

								// POSITION; RELATIVE
							} else {
								group.offset.x = offset.x;
								group.offset.y = offset.y;
								offset.y += _this.pxToNumber( group.parent.style.height );

								// LEGEND; OFFSET
								if ( group.has.panel ) {
									offset.pY = _this.pxToNumber( group.has.panel.style.marginTop );
									group.offset.y += offset.pY;

									// SCROLLBAR; OFFSET
								} else if ( group.has.scrollbar ) {
									group.offset.y += offset.pY;
								}
							}

							// LEFT / RIGHT
						} else if ( [ "left", "right" ].indexOf( _this.setup.chart.legendSettings.position ) != -1 ) {
							group.offset.y = _this.pxToNumber( group.parent.style.top ) + offset.pY;
							group.offset.x = _this.pxToNumber( group.parent.style.left ) + offset.pX;

							// LEGEND; OFFSET
							if ( group.has.legend ) {
								offset.pY += _this.pxToNumber( group.has.panel.style.height ) + _this.setup.chart.panelsSettings.panelSpacing;

								// SCROLLBAR; OFFSET
							} else if ( group.has.scrollbar ) {
								group.offset.y -= _this.setup.chart.panelsSettings.panelSpacing;
							}
						}

						// REGULAR CHARTS; SVG OFFSET
					} else {

						// POSITION; ABSOLUTE
						if ( group.parent.style.position == "absolute" ) {
							group.offset.absolute = true;
							group.offset.top = _this.pxToNumber( group.parent.style.top );
							group.offset.right = _this.pxToNumber( group.parent.style.right, true );
							group.offset.bottom = _this.pxToNumber( group.parent.style.bottom, true );
							group.offset.left = _this.pxToNumber( group.parent.style.left );
							group.offset.width = _this.pxToNumber( group.parent.style.width );
							group.offset.height = _this.pxToNumber( group.parent.style.height );

							// POSITION; RELATIVE
						} else if ( group.parent.style.top && group.parent.style.left ) {
							group.offset.y = _this.pxToNumber( group.parent.style.top );
							group.offset.x = _this.pxToNumber( group.parent.style.left );

							// POSITION; GENERIC
						} else {

							// EXTERNAL LEGEND
							if ( group.legend ) {
								if ( group.legend.position == "left" ) {
									offset.x = legends.maxWidth;
								} else if ( group.legend.position == "right" ) {
									group.offset.x = offset.width - legends.maxWidth;
								} else if ( group.legend.position == "top" ) {
									offset.y += group.legend.height;
								} else if ( group.legend.position == "bottom" ) {
									group.offset.y = offset.height - legends.height;
								}

								// STACK LEGENDS
								group.offset.y += offset.lY;
								offset.lY += group.legend.height;

								// NORMAL
							} else {
								group.offset.x = offset.x;
								group.offset.y = offset.y + offset.pY;
								offset.y += _this.pxToNumber( group.parent.style.height );
							}
						}

						// PANEL OFFSET (STOCK CHARTS)
						if ( group.has.legend && group.has.panel && group.has.panel.style.marginTop ) {
							offset.y += _this.pxToNumber( group.has.panel.style.marginTop );
							group.offset.y += _this.pxToNumber( group.has.panel.style.marginTop );

							// GENERAL LEFT / RIGHT POSITION
						} else if ( _this.setup.chart.legend && [ "left", "right" ].indexOf( _this.setup.chart.legend.position ) != -1 ) {
							group.offset.y = _this.pxToNumber( group.parent.style.top );
							group.offset.x = _this.pxToNumber( group.parent.style.left );
						}
					}

					// ADD TO CANVAS
					fabric.parseSVGDocument( group.svg, ( function( group ) {
						return function( objects, options ) {
							var i1, i2;
							var g = fabric.util.groupSVGElements( objects, options );
							var paths = [];
							var tmp = {
								selectable: false,
								isCoreElement: true
							};

							// GROUP OFFSET; ABSOLUTE
							if ( group.offset.absolute ) {
								if ( group.offset.bottom !== undefined ) {
									tmp.top = offset.height - group.offset.height - group.offset.bottom;
								} else {
									tmp.top = group.offset.top;
								}

								if ( group.offset.right !== undefined ) {
									tmp.left = offset.width - group.offset.width - group.offset.right;
								} else {
									tmp.left = group.offset.left;
								}

								// GROUP OFFSET; REGULAR
							} else {
								tmp.top = group.offset.y;
								tmp.left = group.offset.x;
							}

							// WALKTHROUGH ELEMENTS
							for ( i1 = 0; i1 < g.paths.length; i1++ ) {
								var PID = null;

								// OPACITY; TODO: DISTINGUISH OPACITY TYPES
								if ( g.paths[ i1 ] ) {

									// CHECK ORIGIN; REMOVE TAINTED
									if ( _this.removeImage( g.paths[ i1 ][ "xlink:href" ] ) ) {
										continue;
									}

									// SET OPACITY
									if ( g.paths[ i1 ].fill instanceof Object ) {

										// MISINTERPRETATION OF FABRIC
										if ( g.paths[ i1 ].fill.type == "radial" ) {

											// OTHERS
											if ( [ "pie", "gauge" ].indexOf( _this.setup.chart.type ) == -1 ) {
												g.paths[ i1 ].fill.coords.r2 = g.paths[ i1 ].fill.coords.r1 * -1;
												g.paths[ i1 ].fill.coords.r1 = 0;
												g.paths[ i1 ].set( {
													opacity: g.paths[ i1 ].fillOpacity
												} );
											}
										}

										// FILLING; TODO: DISTINGUISH OPACITY TYPES
									} else if ( PID = _this.isHashbanged( g.paths[ i1 ].fill ) ) {

										// PATTERN
										if ( group.patterns && group.patterns[ PID ] ) {

											var props = group.patterns[ PID ];

											images.included++;

											// LOAD IMAGE MANUALLY; TO RERENDER THE CANVAS
											fabric.Image.fromURL( props.source, ( function( props, i1 ) {
												return function( img ) {
													images.loaded++;

													// ADAPT IMAGE
													img.set( {
														top: props.offsetY,
														left: props.offsetX,
														width: props.width,
														height: props.height
													} );

													// RETINA DISPLAY
													if ( _this.setup.fabric._isRetinaScaling() ) {
														img.set( {
															top: props.offsetY / 2,
															left: props.offsetX / 2,
															scaleX: 0.5,
															scaleY: 0.5
														} );
													}

													// CREATE CANVAS WITH BACKGROUND COLOR
													var patternSourceCanvas = new fabric.StaticCanvas( undefined, {
														backgroundColor: props.fill,
														width: img.getWidth(),
														height: img.getHeight()
													} );
													patternSourceCanvas.add( img );

													// CREATE PATTERN OBTAIN OFFSET TO TARGET
													var pattern = new fabric.Pattern( {
														source: patternSourceCanvas.getElement(),
														offsetX: g.paths[ i1 ].width / 2,
														offsetY: g.paths[ i1 ].height / 2,
														repeat: 'repeat',
													} );

													// ASSIGN TO OBJECT
													g.paths[ i1 ].set( {
														fill: pattern,
														opacity: g.paths[ i1 ].fillOpacity
													} );
												}
											} )( props, i1 ) );
										}
									}

									// CLIPPATH;
									if ( PID = _this.isHashbanged( g.paths[ i1 ].clipPath ) ) {

										if ( group.clippings && group.clippings[ PID ] ) {

											// TODO: WAIT UNTIL FABRICJS HANDLES CLIPPATH FOR SVG OUTPUT
											( function( i1, PID ) {
												var toSVG = g.paths[ i1 ].toSVG;

												g.paths[ i1 ].toSVG = function( original_reviver ) {
													return toSVG.apply( this, [ function( string ) {
														return original_reviver( string, group.clippings[ PID ] );
													} ] );
												}
											} )( i1, PID );

											g.paths[ i1 ].set( {
												clipTo: ( function( i1, PID ) {
													return function( ctx ) {
														var cp = group.clippings[ PID ];
														var tm = this.transformMatrix || [ 1, 0, 0, 1, 0, 0 ];
														var dim = {
															top: cp.bbox.y,
															left: cp.bbox.x,
															width: cp.bbox.width,
															height: cp.bbox.height
														}

														if ( _this.setup.chart.type == "map" ) {
															dim.top += cp.transform[ 5 ];
															dim.left += cp.transform[ 4 ];
														}

														if ( cp.bbox.x && tm[ 4 ] && cp.bbox.y && tm[ 5 ] ) {
															dim.top -= tm[ 5 ];
															dim.left -= tm[ 4 ];
														}

														// SMOOTHCUSTOMBULLETS PLUGIN SUPPORT; ROUND BORDER
														if (
															_this.setup.chart.smoothCustomBullets !== undefined &&
															this.className == _this.setup.chart.classNamePrefix + "-graph-bullet" &&
															g.paths[ i1 ].svg.tagName == "image"
														) {
															radius = cp.svg.firstChild.rx.baseVal.value / 2 + 2;
															ctx.beginPath();
															ctx.moveTo(dim.left + radius, dim.top);
															ctx.lineTo(dim.left + dim.width - radius, dim.top);
															ctx.quadraticCurveTo(dim.left + dim.width, dim.top, dim.left + dim.width, dim.top + radius);
															ctx.lineTo(dim.left + dim.width, dim.top + dim.height - radius);
															ctx.quadraticCurveTo(dim.left + dim.width, dim.top + dim.height, dim.left + dim.width - radius, dim.top + dim.height);
															ctx.lineTo(dim.left + radius, dim.top + dim.height);
															ctx.quadraticCurveTo(dim.left, dim.top + dim.height, dim.left, dim.top + dim.height - radius);
															ctx.lineTo(dim.left, dim.top + radius);
															ctx.quadraticCurveTo(dim.left, dim.top, dim.left + radius, dim.top);
															ctx.closePath();
														} else {
															ctx.rect( dim.left, dim.top, dim.width, dim.height );
														}
													}
												} )( i1, PID )
											} );
										}
									}
								}
								paths.push( g.paths[ i1 ] );
							}

							// REPLACE WITH WHITELIST
							g.paths = paths;

							// SET PROPS
							g.set( tmp );

							// ADD TO CANVAS
							_this.setup.fabric.add( g );

							// ADD BALLOONS
							if ( group.svg.parentNode && group.svg.parentNode.getElementsByTagName ) {
								var balloons = group.svg.parentNode.getElementsByClassName( _this.setup.chart.classNamePrefix + "-balloon-div" );
								for ( i1 = 0; i1 < balloons.length; i1++ ) {
									if ( cfg.balloonFunction instanceof Function ) {
										cfg.balloonFunction.apply( _this, [ balloons[ i1 ], group ] );
									} else {
										var elm_parent = balloons[ i1 ];
										var style_parent = fabric.parseStyleAttribute( elm_parent );
										var style_text = fabric.parseStyleAttribute( elm_parent.childNodes[ 0 ] );
										var fabric_label = new fabric.Text( elm_parent.innerText || elm_parent.textContent || elm_parent.innerHTML, {
											selectable: false,
											top: _this.pxToNumber(style_parent.top) + group.offset.y,
											left: _this.pxToNumber(style_parent.left) + group.offset.x,
											fill: style_text[ "color" ],
											fontSize: _this.pxToNumber(style_text[ "fontSize" ] || style_text[ "font-size" ]),
											fontFamily: style_text[ "fontFamily" ] || style_text[ "font-family" ],
											textAlign: style_text[ "text-align" ],
											isCoreElement: true
										} );

										_this.setup.fabric.add( fabric_label );
									}
								}
							}

							if ( group.svg.nextSibling && group.svg.nextSibling.tagName == "A" ) {
								var elm_parent = group.svg.nextSibling;
								var style_parent = fabric.parseStyleAttribute( elm_parent );
								var fabric_label = new fabric.Text( elm_parent.innerText || elm_parent.textContent || elm_parent.innerHTML, {
									selectable: false,
									top: _this.pxToNumber(style_parent.top) + group.offset.y,
									left: _this.pxToNumber(style_parent.left) + group.offset.x,
									fill: style_parent[ "color" ],
									fontSize: _this.pxToNumber(style_parent[ "fontSize" ] || style_parent[ "font-size" ]),
									fontFamily: style_parent[ "fontFamily" ] || style_parent[ "font-family" ],
									opacity: style_parent[ "opacity" ],
									isCoreElement: true
								} );

								if ( !group.has.scrollbar ) {
									_this.setup.fabric.add( fabric_label );
								}
							}

							groups.pop();

							// TRIGGER CALLBACK WITH SAFETY DELAY
							if ( !groups.length ) {
								var ts1 = Number( new Date() );
								var timer = setInterval( function() {
									var ts2 = Number( new Date() );

									// WAIT FOR LOADED IMAGES OR UNTIL THE TIMEOUT KICKS IN
									if ( images.loaded == images.included || ts2 - ts1 > _this.config.fabric.loadTimeout ) {
										clearTimeout( timer );
										_this.handleBorder( cfg );
										_this.handleCallback( cfg.afterCapture, cfg );
										_this.setup.fabric.renderAll();
										_this.handleCallback( callback, cfg );
									}
								}, AmCharts.updateRate );
							}
						}

						// IDENTIFY ELEMENTS THROUGH CLASSNAMES
					} )( group ), function( svg, obj ) {
						var i1;
						var className = _this.gatherAttribute( svg, "class" );
						var visibility = _this.gatherAttribute( svg, "visibility" );
						var clipPath = _this.gatherAttribute( svg, "clip-path" );

						obj.className = String( className );
						obj.classList = String( className ).split( " " );
						obj.clipPath = clipPath;
						obj.svg = svg;

						// TRANSPORT FILL/STROKE OPACITY
						var attrs = [ "fill", "stroke" ];
						for ( i1 = 0; i1 < attrs.length; i1++ ) {
							var attr = attrs[ i1 ]
							var attrVal = String( svg.getAttribute( attr ) || "none" );
							var attrOpacity = Number( svg.getAttribute( attr + "-opacity" ) || "1" );
							var attrRGBA = _this.getRGBA( attrVal );

							// HIDE HIDDEN ELEMENTS; TODO: FIND A BETTER WAY TO HANDLE THAT
							if ( visibility == "hidden" ) {
								obj.opacity = 0;
								attrOpacity = 0;
							}

							// SET COLOR
							if ( attrRGBA ) {
								attrRGBA.pop();
								attrRGBA.push( attrOpacity )
								obj[ attr ] = "rgba(" + attrRGBA.join() + ")";
								obj[ attr + _this.capitalize( "opacity" ) ] = attrOpacity;
							}
						}

						// REVIVER
						_this.handleCallback( cfg.reviver, obj, svg );
					} );
				}
			},

			/**
			 * Returns the current canvas
			 */
			toCanvas: function( options, callback ) {
				var cfg = _this.deepMerge( {
					// NUFFIN
				}, options || {} );
				var data = _this.setup.canvas;

				// TRIGGER CALLBACK
				_this.handleCallback( callback, data, cfg );

				return data;
			},

			/**
			 * Returns an image; by default PNG
			 */
			toImage: function( options, callback ) {
				var cfg = _this.deepMerge( {
					format: "png",
					quality: 1,
					multiplier: _this.config.multiplier
				}, options || {} );
				var data = cfg.data;
				var img = document.createElement( "img" );

				// NAMESPACE CHECK
				if ( !_this.handleNamespace( "fabric", {
						scope: this,
						cb: _this.toImage,
						args: arguments
					} ) ) {
					return false;
				}

				if ( !cfg.data ) {
					if ( cfg.lossless || cfg.format == "svg" ) {
						data = _this.toSVG( _this.deepMerge( cfg, {
							getBase64: true
						} ) );
					} else {
						data = _this.setup.fabric.toDataURL( cfg );
					}
				}

				img.setAttribute( "src", data );

				_this.handleCallback( callback, img, cfg );

				return img;
			},

			/**
			 * Generates a blob instance image; returns base64 datastring
			 */
			toBlob: function( options, callback ) {
				var cfg = _this.deepMerge( {
					data: "empty",
					type: "text/plain"
				}, options || {} );
				var data;
				var isBase64 = /^data:.+;base64,(.*)$/.exec( cfg.data );

				// GATHER BODY
				if ( isBase64 ) {
					cfg.data = isBase64[ 0 ];
					cfg.type = cfg.data.slice( 5, cfg.data.indexOf( "," ) - 7 );
					cfg.data = _this.toByteArray( {
						data: cfg.data.slice( cfg.data.indexOf( "," ) + 1, cfg.data.length )
					} );
				}

				if ( cfg.getByteArray ) {
					data = cfg.data;
				} else {
					data = new Blob( [ cfg.data ], {
						type: cfg.type
					} );
				}

				// TRIGGER CALLBACK
				_this.handleCallback( callback, data, cfg );

				return data;
			},

			/**
			 * Generates JPG image; returns base64 datastring
			 */
			toJPG: function( options, callback ) {
				var cfg = _this.deepMerge( {
					format: "jpeg",
					quality: 1,
					multiplier: _this.config.multiplier
				}, options || {} );
				cfg.format = cfg.format.toLowerCase();
				var data;

				// DISABLE SCALING ON IOS DEVICES
				if ( /iP(hone|od|ad)/.test(navigator.platform) ) {
					cfg.multiplier = 1;
				}

				// NAMESPACE CHECK
				if ( !_this.handleNamespace( "fabric", {
						scope: this,
						cb: _this.toJPG,
						args: arguments
					} ) ) {
					return false;
				}

				// Get data context from fabric
				data = _this.setup.fabric.toDataURL( cfg );

				// TRIGGER CALLBACK
				_this.handleCallback( callback, data, cfg );

				return data;
			},

			/**
			 * Generates PNG image; returns base64 datastring
			 */
			toPNG: function( options, callback ) {
				var cfg = _this.deepMerge( {
					format: "png",
					quality: 1,
					multiplier: _this.config.multiplier
				}, options || {} );
				var data;

				// DISABLE SCALING ON IOS DEVICES
				if ( /iP(hone|od|ad)/.test(navigator.platform) ) {
					cfg.multiplier = 1;
				}

				// NAMESPACE CHECK
				if ( !_this.handleNamespace( "fabric", {
						scope: this,
						cb: _this.toPNG,
						args: arguments
					} ) ) {
					return false;
				}

				// Get data context from fabric
				data = _this.setup.fabric.toDataURL( cfg );

				// TRIGGER CALLBACK
				_this.handleCallback( callback, data, cfg );

				return data;
			},

			/**
			 * Generates SVG image; returns base64 datastring
			 */
			toSVG: function( options, callback ) {
				var clipPaths = [];
				var clipPathIds = [];
				var cfg = _this.deepMerge( {
					compress: _this.config.compress,
					reviver: function( string, clipPath ) {
						var matcher = new RegExp( /\bstyle=(['"])(.*?)\1/ );
						var match = matcher.exec( string )[ 0 ].slice( 7, -1 );
						var styles = match.split( ";" );
						var replacement = [];

						// BEAUTIFY STYLES
						for ( i1 = 0; i1 < styles.length; i1++ ) {
							if ( styles[ i1 ] ) {
								var pair = styles[ i1 ].replace( /\s/g, "" ).split( ":" );
								var key = pair[ 0 ];
								var value = pair[ 1 ];

								if ( [ "fill", "stroke" ].indexOf( key ) != -1 ) {
									value = _this.getRGBA( value, true );
									if ( value ) {
										var color = "#" + value.toHex();
										var opacity = value._source[ 3 ];

										replacement.push( [ key, color ].join( ":" ) );
										replacement.push( [ key + "-opacity", opacity ].join( ":" ) );
									} else {
										replacement.push( styles[ i1 ] );
									}
								} else if ( key != "opactiy" ) {
									replacement.push( styles[ i1 ] );
								}
							}
						}
						string = string.replace( match, replacement.join( ";" ) );

						// TODO: WAIT UNTIL FABRICJS HANDLES CLIPPATH FOR SVG OUTPUT
						if ( clipPath && clipPath.svg ) {
							var clipPathId = clipPath.svg.id;
							var sliceOffset = 2;
							var end = string.slice( -sliceOffset );

							if ( end != "/>" ) {
								sliceOffset = 3;
								end = string.slice( -sliceOffset );
							}

							var start = string.slice( 0, string.length - sliceOffset );
							var clipPathAttr = " clip-path=\"url(#" + clipPathId + ")\" ";
							var parentClassList = _this.gatherAttribute(clipPath.svg,"class");

							parentClassList = parentClassList ? parentClassList.split(" ") : [];

							// APPLY CLIP PATH DIRECTLY ON GRAPHLINES
							if ( parentClassList.indexOf(_this.setup.chart.classNamePrefix + "-graph-line") != -1 ) {
								string = start + clipPathAttr + end;

							// WRAP ELEMENT TO BE ABLE TO APPLY THE CLIP-PATH
							} else {
								string = "<g " + clipPathAttr + ">" + string + "</g>";
							}

							// INJECT CLIP PATH ONCE INTO THE DOCUMENT
							if ( clipPathIds.indexOf( clipPathId ) == -1 ) {
								var clipPathString = new XMLSerializer().serializeToString( clipPath.svg );
								clipPaths.push( clipPathString );
								clipPathIds.push( clipPathId );
							}
						}

						return string;
					}
				}, options || {} );
				var data;

				// NAMESPACE CHECK
				if ( !_this.handleNamespace( "fabric", {
						scope: this,
						cb: _this.toSVG,
						args: arguments
					} ) ) {
					return false;
				}

				// Get SVG context from fabric
				data = _this.setup.fabric.toSVG( cfg, cfg.reviver );

				// TODO: WAIT UNTIL FABRICJS HANDLES CLIPPATH FOR SVG OUTPUT
				if ( clipPaths.length ) {
					var start = data.slice( 0, data.length - 6 );
					var end = data.slice( -6 );
					data = start + clipPaths.join( "" ) + end;
				}

				// SOLVES #21840
				if ( cfg.compress ) {
					data = data.replace( /[\t\r\n]+/g, "" );
				}

				if ( cfg.getBase64 ) {
					data = "data:image/svg+xml;base64," + btoa( data );
				}

				// TRIGGER CALLBACK
				_this.handleCallback( callback, data, cfg );

				return data;
			},

			/**
			 * Generates PDF; returns base64 datastring
			 */
			toPDF: function( options, callback ) {
				var cfg = _this.deepMerge( _this.deepMerge( {
					multiplier: _this.config.multiplier || 2,
					pageOrigin: _this.config.pageOrigin === undefined ? true : false
				}, _this.config.pdfMake ), options || {}, true );
				var data;

				// DISABLE SCALING ON IOS DEVICES
				if ( /iP(hone|od|ad)/.test(navigator.platform) ) {
					cfg.multiplier = 1;
				}

				// NAMESPACE CHECK
				if ( !_this.handleNamespace( "pdfMake", {
						scope: this,
						cb: _this.toPDF,
						args: arguments
					} ) ) {
					return false;
				}

				// Get image data
				cfg.images.reference = _this.toPNG( cfg );

				// Get page margins; exported from pdfMake
				function getMargins( margin ) {
					if ( typeof margin === 'number' || margin instanceof Number ) {
						margin = {
							left: margin,
							right: margin,
							top: margin,
							bottom: margin
						};
					} else if ( margin instanceof Array ) {
						if ( margin.length === 2 ) {
							margin = {
								left: margin[ 0 ],
								top: margin[ 1 ],
								right: margin[ 0 ],
								bottom: margin[ 1 ]
							};
						} else if ( margin.length === 4 ) {
							margin = {
								left: margin[ 0 ],
								top: margin[ 1 ],
								right: margin[ 2 ],
								bottom: margin[ 3 ]
							};
						} else throw 'Invalid pageMargins definition';
					} else {
						margin = {
							left: _this.defaults.pdfMake.pageMargins,
							top: _this.defaults.pdfMake.pageMargins,
							right: _this.defaults.pdfMake.pageMargins,
							bottom: _this.defaults.pdfMake.pageMargins
						};
					}

					return margin;
				}

				// Get page dimensions
				function getSize( pageSize, pageOrientation ) {
					var pageDimensions = _this.defaults.pdfMake.pageSizes[ String( pageSize ).toUpperCase() ].slice();

					if ( !pageDimensions ) {
						throw new Error( "The given pageSize \"" + pageSize + "\" does not exist!" );
					}

					// Revers in case of landscape
					if ( pageOrientation == "landscape" ) {
						pageDimensions.reverse();
					}

					return pageDimensions;
				}

				// Polyfill default content if none is given
				if ( !cfg.content ) {
					var pageContent = [];
					var pageDimensions = getSize( cfg.pageSize, cfg.pageOrientation );
					var pageMargins = getMargins( cfg.pageMargins );

					pageDimensions[ 0 ] -= ( pageMargins.left + pageMargins.right );
					pageDimensions[ 1 ] -= ( pageMargins.top + pageMargins.bottom );

					if ( cfg.pageOrigin ) {
						pageContent.push( _this.i18l( "label.saved.from" ) );
						pageContent.push( window.location.href );
						pageDimensions[ 1 ] -= ( 14.064 * 2 );
					}

					pageContent.push( {
						image: "reference",
						fit: pageDimensions
					} );

					cfg.content = pageContent;
				}

				// Create PDF instance
				data = new pdfMake.createPdf( cfg );

				if ( callback ) {
					data.getDataUrl( ( function( callback ) {
						return function( a ) {
							callback.apply( _this, arguments );
						}
					} )( callback ) );
				}

				return data;
			},

			/**
			 * Generates an image; hides all elements on page to trigger native print method
			 */
			toPRINT: function( options, callback ) {
				var i1;
				var cfg = _this.deepMerge( {
					delay: 1,
					lossless: false
				}, options || {} );
				var data = _this.toImage( cfg );
				var states = [];
				var items = document.body.childNodes;
				var scroll = document.documentElement.scrollTop || document.body.scrollTop;

				data.setAttribute( "style", "width: 100%; max-height: 100%;" );

				for ( i1 = 0; i1 < items.length; i1++ ) {
					if ( _this.isElement( items[ i1 ] ) ) {
						states[ i1 ] = items[ i1 ].style.display;
						items[ i1 ].style.display = "none";
					}
				}

				document.body.appendChild( data );

				// CONVERT TO SECONDS
				cfg.delay *= 1000;

				// IOS EXCEPTION DELAY MIN. 1 SECOND
				var isIOS = /iPad|iPhone|iPod/.test( navigator.userAgent ) && !window.MSStream;
				if ( isIOS && cfg.delay < 1000 ) {
					cfg.delay = 1000;
				}

				// DELAY WHOLE PROCESS
				setTimeout(function() {
					// PRINT
					window.print();

					setTimeout( function() {
						for ( i1 = 0; i1 < items.length; i1++ ) {
							if ( _this.isElement( items[ i1 ] ) ) {
								items[ i1 ].style.display = states[ i1 ];
							}
						}
						document.body.removeChild( data );
						document.documentElement.scrollTop = document.body.scrollTop = scroll;

						// TRIGGER CALLBACK
						_this.handleCallback( callback, data, cfg );
					}, cfg.delay );
				}, cfg.delay);

				return data;
			},

			/**
			 * Generates JSON string
			 */
			toJSON: function( options, callback ) {
				var cfg = _this.deepMerge( {
					dateFormat: _this.config.dateFormat || "dateObject"
				}, options || {}, true );
				var data = {};

				// NAMESPACE CHECK
				if ( !_this.handleNamespace( "JSON", {
						scope: this,
						cb: _this.toJSON,
						args: arguments
					} ) ) {
					return false;
				}

				// GATHER DATA
				cfg.data = cfg.data !== undefined ? cfg.data : _this.getChartData( cfg );

				// STRINGIFY DATA
				data = JSON.stringify( cfg.data, undefined, "\t" );

				// TRIGGER CALLBACK
				_this.handleCallback( callback, data, cfg );

				return data;
			},

			/**
			 * Generates CSV string
			 */
			toCSV: function( options, callback ) {
				var row, col;
				var cfg = _this.deepMerge( {
					delimiter: ",",
					quotes: true,
					escape: true,
					withHeader: true
				}, options || {}, true );
				var buffer = [];
				var data = "";

				// GATHER DATA
				buffer = _this.toArray( cfg );

				// MERGE
				Object.keys( buffer ).some(function( row ) {
					if ( !isNaN( row ) ) {
						data += buffer[ row ].join( cfg.delimiter ) + "\n";
					}
				});

				// TRIGGER CALLBACK
				_this.handleCallback( callback, data, cfg );

				return data;
			},

			/**
			 * Generates excel sheet; returns base64 datastring
			 */
			toXLSX: function( options, callback ) {
				var cfg = _this.deepMerge( {
					name: "amCharts",
					dateFormat: _this.config.dateFormat || "dateObject",
					withHeader: true,
					stringify: false
				}, options || {}, true );
				var buffer = [];
				var data = "";
				var wb = {
					SheetNames: [],
					Sheets: {}
				}

				// NAMESPACE CHECK
				if ( !_this.handleNamespace( "XLSX", {
						scope: this,
						cb: _this.toXLSX,
						args: arguments
					} ) ) {
					return false;
				}

				// GATHER DATA
				buffer = _this.toArray( cfg );

				function datenum( v, date1904 ) {
					if ( date1904 ) v += 1462;
					var epoch = Date.parse( v );
					var offset = v.getTimezoneOffset() * 60 * 1000;
					return ( epoch - offset - new Date( Date.UTC( 1899, 11, 30 ) ) ) / ( 24 * 60 * 60 * 1000 );
				}

				function sheet_from_array_of_arrays( data, opts ) {
					var ws = {};
					var range = {
						s: {
							c: 10000000,
							r: 10000000
						},
						e: {
							c: 0,
							r: 0
						}
					};
					for ( var R = 0; R != data.length; ++R ) {
						for ( var C = 0; C != data[ R ].length; ++C ) {
							if ( range.s.r > R ) range.s.r = R;
							if ( range.s.c > C ) range.s.c = C;
							if ( range.e.r < R ) range.e.r = R;
							if ( range.e.c < C ) range.e.c = C;
							var cell = {
								v: data[ R ][ C ]
							};
							if ( cell.v == null ) continue;
							var cell_ref = XLSX.utils.encode_cell( {
								c: C,
								r: R
							} );

							if ( typeof cell.v === "number" ) {
								cell.t = "n";
							} else if ( typeof cell.v === "boolean" ) {
								cell.t = "b";
							} else if ( cell.v instanceof Date ) {
								cell.t = "n";
								cell.z = XLSX.SSF._table[ 14 ];
								cell.v = datenum( cell.v );
							} else if ( cell.v instanceof Object ) {
								cell.t = "s";
								cell.v = JSON.stringify( cell.v );
							} else {
								cell.t = "s";
							}

							ws[ cell_ref ] = cell;
						}
					}
					if ( range.s.c < 10000000 ) ws[ "!ref" ] = XLSX.utils.encode_range( range );
					return ws;
				}

				wb.SheetNames.push( cfg.name );
				wb.Sheets[ cfg.name ] = sheet_from_array_of_arrays( buffer );

				data = XLSX.write( wb, {
					bookType: "xlsx",
					bookSST: true,
					type: "base64"
				} );

				data = "data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64," + data;

				// TRIGGER CALLBACK
				_this.handleCallback( callback, data, cfg );

				return data;
			},

			/**
			 * Generates an array of arrays
			 */
			toArray: function( options, callback ) {
				var row, col;
				var cfg = _this.deepMerge( {
					withHeader: false,
					stringify: true,
					escape: false,
					quotes: false
				}, options || {}, true );
				var data = [];
				var cols = [];
				var buffer = [];
				var _processData = _this.config.processData;

				// RETRIEVES RIGHT FIELD ORDER OF TRANSLATED FIELDS
				function processData( data, cfg ) {
					var fields = cfg.exportFields || Object.keys( cfg.dataFieldsMap );

					// WALKTHROUGH FIELDS
					for ( col = 0; col < fields.length; col++ ) {
						var key = fields[ col ];
						var field = cfg.dataFieldsTitlesMap[ key ];
						cols.push( field );
					}

					// TRIGGER GIVEN CALLBACK
					if ( _processData ) {
						return _this.handleCallback( _processData, data, cfg );
					}
					return data;
				}

				// STRING PROCESSOR
				function enchant( value ) {

					if ( typeof value === "string" ) {
						if ( cfg.escape ) {
							value = value.replace( '"', '""' );
						}
						if ( cfg.quotes ) {
							value = [ '"', value, '"' ].join( "" );
						}
					}

					return value;
				}

				// INVOKE PROCESS DATA
				cfg.processData = processData;

				// GET DATA
				cfg.data = cfg.data !== undefined ? _this.processData( cfg ) : _this.getChartData( cfg );

				// HEADER
				if ( cfg.withHeader ) {
					buffer = [];
					Object.keys( cols ).some(function( col ) {
						if ( !isNaN( col ) ) {
							buffer.push( enchant( cols[ col ] ) );
						}
					});
					data.push( buffer );
				}

				// BODY
				Object.keys( cfg.data ).some(function( row ) {
					buffer = [];
					if ( !isNaN( row ) ) {
						Object.keys( cols ).some(function( col ) {
							if ( !isNaN( col ) ) {
								var col = cols[ col ];
								var value = cfg.data[ row ][ col ];
								if ( value == null ) {
									value = "";
								} else if ( cfg.stringify ) {
									value = String( value );
								} else {
									value = value;
								}
								buffer.push( enchant( value ) );
							}
						});
						data.push( buffer );
					}
				});

				// TRIGGER CALLBACK
				_this.handleCallback( callback, data, cfg );

				return data;
			},

			/**
			 * Generates byte array with given base64 datastring; returns byte array
			 */
			toByteArray: function( options, callback ) {
				var cfg = _this.deepMerge( {
					// NUFFIN
				}, options || {} );
				var Arr = ( typeof Uint8Array !== 'undefined' ) ? Uint8Array : Array
				var PLUS = '+'.charCodeAt( 0 )
				var SLASH = '/'.charCodeAt( 0 )
				var NUMBER = '0'.charCodeAt( 0 )
				var LOWER = 'a'.charCodeAt( 0 )
				var UPPER = 'A'.charCodeAt( 0 )
				var data = b64ToByteArray( cfg.data );

				function decode( elt ) {
					var code = elt.charCodeAt( 0 )
					if ( code === PLUS )
						return 62 // '+'
					if ( code === SLASH )
						return 63 // '/'
					if ( code < NUMBER )
						return -1 //no match
					if ( code < NUMBER + 10 )
						return code - NUMBER + 26 + 26
					if ( code < UPPER + 26 )
						return code - UPPER
					if ( code < LOWER + 26 )
						return code - LOWER + 26
				}

				function b64ToByteArray( b64 ) {
					var i, j, l, tmp, placeHolders, arr

					if ( b64.length % 4 > 0 ) {
						throw new Error( 'Invalid string. Length must be a multiple of 4' )
					}

					// THE NUMBER OF EQUAL SIGNS (PLACE HOLDERS)
					// IF THERE ARE TWO PLACEHOLDERS, THAN THE TWO CHARACTERS BEFORE IT
					// REPRESENT ONE BYTE
					// IF THERE IS ONLY ONE, THEN THE THREE CHARACTERS BEFORE IT REPRESENT 2 BYTES
					// THIS IS JUST A CHEAP HACK TO NOT DO INDEXOF TWICE
					var len = b64.length
					placeHolders = '=' === b64.charAt( len - 2 ) ? 2 : '=' === b64.charAt( len - 1 ) ? 1 : 0

					// BASE64 IS 4/3 + UP TO TWO CHARACTERS OF THE ORIGINAL DATA
					arr = new Arr( b64.length * 3 / 4 - placeHolders )

					// IF THERE ARE PLACEHOLDERS, ONLY GET UP TO THE LAST COMPLETE 4 CHARS
					l = placeHolders > 0 ? b64.length - 4 : b64.length

					var L = 0

					function push( v ) {
						arr[ L++ ] = v
					}

					for ( i = 0, j = 0; i < l; i += 4, j += 3 ) {
						tmp = ( decode( b64.charAt( i ) ) << 18 ) | ( decode( b64.charAt( i + 1 ) ) << 12 ) | ( decode( b64.charAt( i + 2 ) ) << 6 ) | decode( b64.charAt( i + 3 ) )
						push( ( tmp & 0xFF0000 ) >> 16 )
						push( ( tmp & 0xFF00 ) >> 8 )
						push( tmp & 0xFF )
					}

					if ( placeHolders === 2 ) {
						tmp = ( decode( b64.charAt( i ) ) << 2 ) | ( decode( b64.charAt( i + 1 ) ) >> 4 )
						push( tmp & 0xFF )
					} else if ( placeHolders === 1 ) {
						tmp = ( decode( b64.charAt( i ) ) << 10 ) | ( decode( b64.charAt( i + 1 ) ) << 4 ) | ( decode( b64.charAt( i + 2 ) ) >> 2 )
						push( ( tmp >> 8 ) & 0xFF )
						push( tmp & 0xFF )
					}

					return arr
				}

				// TRIGGER CALLBACK
				_this.handleCallback( callback, data, cfg );

				return data;
			},

			/**
			 * Method to remove functions from given object
			 */
			removeFunctionsFromObject: function( obj ) {
				Object.keys( obj ).some(function( key ) {
					if ( typeof obj[key] === "function" ) {
						delete obj[key];
					}
				});
				return obj;
			},

			/**
			 * Callback handler; injects additional arguments to callback
			 */
			handleCallback: function( callback ) {
				var i1, data = Array();
				if ( callback && callback instanceof Function ) {
					for ( i1 = 0; i1 < arguments.length; i1++ ) {
						if ( i1 > 0 ) {
							data.push( arguments[ i1 ] );
						}
					}
					return callback.apply( _this, data );
				}
			},

			/**
			 * Logger
			 */
			handleLog: function( msg ) {
				if ( _this.config.debug === true ) {
					console.log( msg );
				}
			},

			/**
			 * Namespace checker; delays given callback until the dependency is available
			 */
			handleNamespace: function( namespace, opts ) {
				var scope = _this.config.scope || window;
				var exists = false;
				var startTS = Number( new Date() );
				var timer;

				// SIMPLE CHECK
				exists = !!( namespace in scope );

				// RESURSIVE DEPENDENCY CHECK
				function waitForIt() {
					var tmpTS = Number( new Date() );

					// SIMPLE CHECK
					exists = !!( namespace in scope );

					// PDFMAKE EXCEPTION; WAIT ADDITIONALLY FOR FONTS
					if ( namespace == "pdfMake" && exists ) {
						exists = scope.pdfMake.vfs;
					}

					// FOUND TRIGGER GIVEN CALLBACK
					if ( exists ) {
						clearTimeout( timer );
						opts.cb.apply( opts.scope, opts.args );
						_this.handleLog( [ "AmCharts [export]: Namespace \"", namespace, "\" showed up in: ", String( scope ) ].join( "" ) );

						// NOT FOUND SCHEDULE RECHECK
					} else if ( tmpTS - startTS < _this.libs.loadTimeout ) {
						timer = setTimeout( waitForIt, 250 );

						// LIBS TIMEOUT REACHED
					} else {
						_this.handleLog( [ "AmCharts [export]: Gave up waiting for \"", namespace, "\" in: ", String( scope ) ].join( "" ) );
					}
				}

				// THROW MESSAGE IF IT DOESNT EXIST
				if ( !exists ) {
					_this.handleLog( [ "AmCharts [export]: Could not find \"", namespace, "\" in: ", String( scope ) ].join( "" ) );
					waitForIt();
				}

				return exists;
			},

			/**
			 * Border handler; injects additional border to canvas
			 */
			handleBorder: function( options ) {
				if ( _this.config.border instanceof Object ) {
					var cfg = _this.deepMerge( _this.defaults.fabric.border, options.border || {}, true );
					var border = new fabric.Rect();

					cfg.width = _this.setup.fabric.width - cfg.strokeWidth;
					cfg.height = _this.setup.fabric.height - cfg.strokeWidth;

					border.set( cfg );

					_this.setup.fabric.add( border );
				}
			},

			/**
			 * Handles drag/drop events; loads given imagery
			 */
			handleDropbox: function( e ) {
				if ( _this.drawing.enabled ) {
					e.preventDefault();
					e.stopPropagation();

					// DRAG OVER
					if ( e.type == "dragover" ) {
						_this.setup.wrapper.setAttribute( "class", _this.setup.chart.classNamePrefix + "-export-canvas active dropbox" );

						// DRAGLEAVE; DROP
					} else {
						_this.setup.wrapper.setAttribute( "class", _this.setup.chart.classNamePrefix + "-export-canvas active" );

						if ( e.type == "drop" && e.dataTransfer.files.length ) {
							for ( var i1 = 0; i1 < e.dataTransfer.files.length; i1++ ) {
								var reader = new FileReader();
								reader.onloadend = ( function( index ) {
									return function() {
										_this.drawing.handler.add( {
											url: reader.result,
											top: e.layerY - ( index * 10 ),
											left: e.layerX - ( index * 10 )
										} );
									}
								} )( i1 );
								reader.readAsDataURL( e.dataTransfer.files[ i1 ] );
							}
						}
					}
				}
			},

			/**
			 * Calls ready callback when dependencies are available within window scope
			 */
			handleReady: function( callback ) {
				var t1, t2;
				var _this = this;
				var tsStart = Number( new Date() );

				// READY FOR DATA EXPORT
				_this.handleCallback( callback, "data", false );

				// READY CALLBACK FOR EACH DEPENDENCY
				Object.keys( _this.libs.namespaces ).some(function( key ) {
					var namespace = _this.libs.namespaces[key];
					( function( namespace ) {
						var t1 = setInterval( function() {
							var tsEnd = Number( new Date() );

							if ( tsEnd - tsStart > _this.libs.loadTimeout || namespace in window ) {
								clearTimeout( t1 );
								_this.handleCallback( callback, namespace, tsEnd - tsStart > _this.libs.loadTimeout );
							}
						}, AmCharts.updateRate )
					} )( namespace );
				});
			},

			/**
			 * Gathers chart data according to its type
			 */
			getChartData: function( options ) {
				var cfg = _this.deepMerge( {
					data: [],
					titles: {},
					dateFields: [],
					dataFields: [],
					dataFieldsMap: {},
					exportTitles: _this.config.exportTitles,
					exportFields: _this.config.exportFields,
					exportSelection: _this.config.exportSelection,
					columnNames: _this.config.columnNames
				}, options || {}, true );
				var uid, i1, i2, i3;
				var lookupFields = [ "valueField", "openField", "closeField", "highField", "lowField", "xField", "yField" ];
				var buffer;

				// HANDLE FIELDS
				function addField( field, title, type ) {

					function checkExistance( field, type ) {
						if ( cfg.dataFields.indexOf( field ) != -1 ) {
							return checkExistance( [ field, ".", type ].join( "" ) );
						}
						return field;
					}

					if ( field && cfg.exportTitles && _this.setup.chart.type != "gantt" ) {
						uid = checkExistance( field, type );
						cfg.dataFieldsMap[ uid ] = field;
						cfg.dataFields.push( uid );
						cfg.titles[ uid ] = title || uid;
					}
				}

				if ( cfg.data.length == 0 ) {

					// STOCK DATA; GATHER COMPARED GRAPHS
					if ( _this.setup.chart.type == "stock" ) {
						cfg.data = _this.cloneObject( _this.setup.chart.mainDataSet.dataProvider );

						// CATEGORY AXIS
						addField( _this.setup.chart.mainDataSet.categoryField );
						cfg.dateFields.push( _this.setup.chart.mainDataSet.categoryField );

						// WALKTHROUGH GRAPHS
						for ( i1 = 0; i1 < _this.setup.chart.mainDataSet.fieldMappings.length; i1++ ) {
							var fieldMap = _this.setup.chart.mainDataSet.fieldMappings[ i1 ];
							for ( i2 = 0; i2 < _this.setup.chart.panels.length; i2++ ) {
								var panel = _this.setup.chart.panels[ i2 ]
								for ( i3 = 0; i3 < panel.stockGraphs.length; i3++ ) {
									var graph = panel.stockGraphs[ i3 ];

									for ( i4 = 0; i4 < lookupFields.length; i4++ ) {
										if ( graph[ lookupFields[ i4 ] ] == fieldMap.toField ) {
											addField( fieldMap.fromField, graph.title, lookupFields[ i4 ] );
										}
									}
								}
							}
						}

						// MERGE DATA OF COMPARED GRAPHS IN RIGHT PLACE
						if ( _this.setup.chart.comparedGraphs.length ) {

							// BUFFER DATES FROM MAIN DATA SET
							buffer = [];
							for ( i1 = 0; i1 < cfg.data.length; i1++ ) {
								buffer.push( cfg.data[ i1 ][ _this.setup.chart.mainDataSet.categoryField ] );
							}

							// WALKTHROUGH COMPARISON AND MERGE IT'S DATA
							for ( i1 = 0; i1 < _this.setup.chart.comparedGraphs.length; i1++ ) {
								var graph = _this.setup.chart.comparedGraphs[ i1 ];
								for ( i2 = 0; i2 < graph.dataSet.dataProvider.length; i2++ ) {
									var categoryField = graph.dataSet.categoryField;
									var categoryValue = graph.dataSet.dataProvider[ i2 ][ categoryField ];
									var comparedIndex = buffer.indexOf( categoryValue );

									// PLACE IN RIGHT PLACE
									if ( comparedIndex != -1 ) {
										for ( i3 = 0; i3 < graph.dataSet.fieldMappings.length; i3++ ) {
											var fieldMap = graph.dataSet.fieldMappings[ i3 ];
											var uid = graph.dataSet.id + "_" + fieldMap.toField;

											cfg.data[ comparedIndex ][ uid ] = graph.dataSet.dataProvider[ i2 ][ fieldMap.fromField ];

											// UNIQUE TITLE
											if ( !cfg.titles[ uid ] ) {
												addField( uid, graph.dataSet.title )
											}
										}
									}
								}
							}
						}

						// GANTT DATA; FLATTEN SEGMENTS
					} else if ( _this.setup.chart.type == "gantt" ) {
						// CATEGORY AXIS
						addField( _this.setup.chart.categoryField );

						var field = _this.setup.chart.segmentsField;
						for ( i1 = 0; i1 < _this.setup.chart.dataProvider.length; i1++ ) {
							var dataItem = _this.setup.chart.dataProvider[ i1 ];
							if ( dataItem[ field ] ) {
								for ( i2 = 0; i2 < dataItem[ field ].length; i2++ ) {
									dataItem[ field ][ i2 ][ _this.setup.chart.categoryField ] = dataItem[ _this.setup.chart.categoryField ];
									cfg.data.push( dataItem[ field ][ i2 ] );
								}
							}
						}

						// GRAPHS
						for ( i1 = 0; i1 < _this.setup.chart.graphs.length; i1++ ) {
							var graph = _this.setup.chart.graphs[ i1 ];

							for ( i2 = 0; i2 < lookupFields.length; i2++ ) {
								var dataField = lookupFields[ i2 ];
								var graphField = graph[ dataField ];
								var title = graph.title;

								addField( graphField, graph.title, dataField );
							}
						}

						// PIE/FUNNEL DATA;
					} else if ( [ "pie", "funnel" ].indexOf( _this.setup.chart.type ) != -1 ) {
						cfg.data = _this.setup.chart.dataProvider;

						// CATEGORY AXIS
						addField( _this.setup.chart.titleField );
						cfg.dateFields.push( _this.setup.chart.titleField );

						// VALUE
						addField( _this.setup.chart.valueField );

						// DEFAULT DATA;
					} else if ( _this.setup.chart.type != "map" ) {
						cfg.data = _this.setup.chart.dataProvider;

						// CATEGORY AXIS
						if ( _this.setup.chart.categoryAxis ) {
							addField( _this.setup.chart.categoryField, _this.setup.chart.categoryAxis.title );
							if ( _this.setup.chart.categoryAxis.parseDates !== false ) {
								cfg.dateFields.push( _this.setup.chart.categoryField );
							}
						}

						// GRAPHS
						for ( i1 = 0; i1 < _this.setup.chart.graphs.length; i1++ ) {
							var graph = _this.setup.chart.graphs[ i1 ];

							for ( i2 = 0; i2 < lookupFields.length; i2++ ) {
								var dataField = lookupFields[ i2 ];
								var graphField = graph[ dataField ];

								addField( graphField, graph.title, dataField );
							}
						}
					}
				}
				return _this.processData( cfg );
			},

			/**
			 * Returns embedded annotations in an array
			 */
			getAnnotations: function( options, callback ) {
				var cfg = _this.deepMerge( {
					// For the future
				}, options || {}, true );
				var i1;
				var data = [];

				// Collect annotations
				for ( i1 = 0; i1 < _this.setup.fabric._objects.length; i1++ ) {

					// Internal flag to distinguish between annotations and "core" elements
					if ( !_this.setup.fabric._objects[ i1 ].isCoreElement ) {
						var obj = _this.setup.fabric._objects[ i1 ].toJSON();

						// Revive before adding to allow modifying the object
						_this.handleCallback( cfg.reviver, obj, i1 );

						// Push into output
						data.push( obj );
					}
				}

				_this.handleCallback( callback, data );

				return data;
			},

			/**
			 * Inserts the given annotations
			 */
			setAnnotations: function( options, callback ) {
				var cfg = _this.deepMerge( {
					data: []
				}, options || {}, true );

				// Convert annotations objects into fabric instances
				fabric.util.enlivenObjects( cfg.data, function( enlivenedObjects ) {
					enlivenedObjects.forEach( function( obj, i1 ) {

						// Revive before adding to allow modifying the object
						_this.handleCallback( cfg.reviver, obj, i1 );

						// Add into active instance canvas
						_this.setup.fabric.add( obj );
					} );

					_this.handleCallback( callback, cfg );
				} );

				return cfg.data;
			},

			/**
			 * Walkthrough data to format dates and titles
			 */
			processData: function( options ) {
				var cfg = _this.deepMerge( {
					data: [],
					titles: {},
					dateFields: [],
					dataFields: [],
					dataFieldsMap: {},
					dataFieldsTitlesMap: {},
					dataDateFormat: _this.setup.chart.dataDateFormat,
					dateFormat: _this.config.dateFormat || _this.setup.chart.dataDateFormat || "YYYY-MM-DD",
					exportTitles: _this.config.exportTitles,
					exportFields: _this.config.exportFields,
					exportSelection: _this.config.exportSelection,
					columnNames: _this.config.columnNames,
					processData: _this.config.processData
				}, options || {}, true );
				var i1, i2;

				if ( cfg.data.length ) {
					// GATHER MISSING FIELDS
					for ( i1 = 0; i1 < cfg.data.length; i1++ ) {
						Object.keys( cfg.data[ i1 ] ).some(function( i2 ) {
							if ( cfg.dataFields.indexOf( i2 ) == -1 ) {
								cfg.dataFields.push( i2 );
								cfg.dataFieldsMap[ i2 ] = i2;
							}
						});
					}

					// REMOVE FIELDS SELECTIVELY
					if ( cfg.exportFields !== undefined ) {
						cfg.dataFields = cfg.exportFields.filter( function( n ) {
							return cfg.dataFields.indexOf( n ) != -1;
						} );
					}

					// REBUILD DATA
					var buffer = [];
					for ( i1 = 0; i1 < cfg.data.length; i1++ ) {
						var tmp = {};
						var skip = false;
						for ( i2 = 0; i2 < cfg.dataFields.length; i2++ ) {
							var uniqueField = cfg.dataFields[ i2 ];
							var dataField = cfg.dataFieldsMap[ uniqueField ];
							var title = ( cfg.columnNames && cfg.columnNames[ uniqueField ] ) || cfg.titles[ uniqueField ] || uniqueField;
							var value = cfg.data[ i1 ][ dataField ];

							// SKIP NULL ONES
							if ( value == null ) {
								value = undefined;
							}

							// TITLEFY
							if ( cfg.exportTitles && _this.setup.chart.type != "gantt" ) {
								if ( title in tmp ) {
									title += [ "( ", uniqueField, " )" ].join( "" );
								}
							}

							// PROCESS CATEGORY
							if ( cfg.dateFields.indexOf( dataField ) != -1 ) {

								// CONVERT DATESTRING TO DATE OBJECT
								if ( cfg.dataDateFormat && ( value instanceof String || typeof value == "string" ) ) {
									value = AmCharts.stringToDate( value, cfg.dataDateFormat );

									// CONVERT TIMESTAMP TO DATE OBJECT
								} else if ( cfg.dateFormat && ( value instanceof Number || typeof value == "number" ) ) {
									value = new Date( value );
								}

								// CATEGORY RANGE
								if ( cfg.exportSelection ) {
									if ( value instanceof Date ) {
										if ( value < chart.startDate || value > chart.endDate ) {
											skip = true;
										}

									} else if ( i1 < chart.startIndex || i1 > chart.endIndex ) {
										skip = true;
									}
								}

								// CATEGORY FORMAT
								if ( cfg.dateFormat && cfg.dateFormat != "dateObject" && value instanceof Date ) {
									value = AmCharts.formatDate( value, cfg.dateFormat );
								}
							}

							cfg.dataFieldsTitlesMap[ dataField ] = title;

							tmp[ title ] = value;
						}
						if ( !skip ) {
							buffer.push( tmp );
						}
					}
					cfg.data = buffer;
				}

				if ( cfg.processData !== undefined ) {
					cfg.data = _this.handleCallback( cfg.processData, cfg.data, cfg );
				}

				return cfg.data;
			},

			/**
			 * Prettifies string
			 */
			capitalize: function( string ) {
				return string.charAt( 0 ).toUpperCase() + string.slice( 1 ).toLowerCase();
			},

			/**
			 * Generates export menu; returns UL node
			 */
			createMenu: function( list, container ) {
				var div;
				var buffer = [];

				function buildList( list, container ) {
					var i1, i2, ul = document.createElement( "ul" );
					for ( i1 = 0; i1 < list.length; i1++ ) {
						var item = typeof list[ i1 ] === "string" ? {
							format: list[ i1 ]
						} : list[ i1 ];
						var li = document.createElement( "li" );
						var a = document.createElement( "a" );
						var img = document.createElement( "img" );
						var span = document.createElement( "span" );
						var action = String( item.action ? item.action : item.format ).toLowerCase();

						item.format = String( item.format ).toUpperCase();

						// REMOVE ACTIVE CLASS ON MOUSELEAVE
						li.addEventListener("mouseleave",function(e) {
							this.classList.remove("active");
						});

						// LISTEN ON FOCUS; NON-TOUCH DEVICES ONLY
						a.addEventListener( "focus", function( e ) {
							if ( !_this.setup.hasTouch ) {
								_this.setup.focusedMenuItem = this;
								var list = this.parentNode;

								if ( list.tagName != "UL" ) {
									list = list.parentNode;
								}

								// REMOVE ACTIVE CLASSES
								var items = list.getElementsByTagName("li");
								for ( i1 = 0; i1 < items.length; i1++ ) {
									items[i1].classList.remove("active");
								}

								this.parentNode.classList.add( "active" );
								this.parentNode.parentNode.parentNode.classList.add( "active" );
							}
						} );

						// MERGE WITH GIVEN FORMAT
						if ( _this.config.formats[ item.format ] ) {
							item = _this.deepMerge( {
								label: item.icon ? "" : item.format,
								format: item.format,
								mimeType: _this.config.formats[ item.format ].mimeType,
								extension: _this.config.formats[ item.format ].extension,
								capture: _this.config.formats[ item.format ].capture,
								action: _this.config.action,
								fileName: _this.config.fileName
							}, item );
						} else if ( !item.label ) {
							item.label = item.label ? item.label : _this.i18l( "menu.label." + action );
						}

						// FILTER; TOGGLE FLAG
						if ( [ "CSV", "JSON", "XLSX" ].indexOf( item.format ) != -1 && [ "map", "gauge" ].indexOf( _this.setup.chart.type ) != -1 ) {
							continue;

							// BLOB EXCEPTION
						} else if ( !_this.setup.hasBlob && item.format != "UNDEFINED" ) {
							if ( item.mimeType && item.mimeType.split( "/" )[ 0 ] != "image" && item.mimeType != "text/plain" ) {
								continue;
							}
						}

						// DRAWING
						if ( item.action == "draw" ) {
							if ( _this.config.fabric.drawing.enabled ) {
								item.menu = item.menu ? item.menu : _this.config.fabric.drawing.menu;
								item.click = ( function( item ) {
									return function() {
										this.capture( item, function() {
											this.createMenu( item.menu );
										} );
									}
								} )( item );
							} else {
								item.menu = [];
							}

							// DRAWING CHOICES
						} else if ( !item.populated && item.action && item.action.indexOf( "draw." ) != -1 ) {
							var type = item.action.split( "." )[ 1 ];
							var items = item[ type ] || _this.config.fabric.drawing[ type ] || [];

							item.menu = [];
							item.populated = true;

							for ( i2 = 0; i2 < items.length; i2++ ) {
								var tmp = {
									"label": items[ i2 ]
								}

								if ( type == "shapes" ) {
									var io = items[ i2 ].indexOf( "//" ) == -1;
									var url = ( io ? _this.config.path + "shapes/" : "" ) + items[ i2 ];

									tmp.action = "add";
									tmp.url = url;
									tmp.icon = url;
									tmp.ignore = io;
									tmp[ "class" ] = "export-drawing-shape";

								} else if ( type == "colors" ) {
									tmp.style = "background-color: " + items[ i2 ];
									tmp.action = "change";
									tmp.color = items[ i2 ];
									tmp[ "class" ] = "export-drawing-color";

								} else if ( type == "widths" ) {
									tmp.action = "change";
									tmp.width = items[ i2 ];
									tmp.label = document.createElement( "span" );

									tmp.label.style.width = _this.numberToPx( items[ i2 ] );
									tmp.label.style.height = _this.numberToPx( items[ i2 ] );
									tmp[ "class" ] = "export-drawing-width";
								} else if ( type == "opacities" ) {
									tmp.style = "opacity: " + items[ i2 ];
									tmp.action = "change";
									tmp.opacity = items[ i2 ];
									tmp.label = ( items[ i2 ] * 100 ) + "%";
									tmp[ "class" ] = "export-drawing-opacity";
								} else if ( type == "modes" ) {
									tmp.label = _this.i18l( "menu.label.draw.modes." + items[ i2 ] );
									tmp.click = ( function( mode ) {
										return function() {
											_this.drawing.mode = mode;
										}
									} )( items[ i2 ] );
									tmp[ "class" ] = "export-drawing-mode";
								}

								item.menu.push( tmp );
							}

							// ADD CLICK HANDLER
						} else if ( !item.click && !item.menu && !item.items ) {
							// DRAWING METHODS
							if ( _this.drawing.handler[ action ] instanceof Function ) {
								item.action = action;
								item.click = ( function( item ) {
									return function() {
										this.drawing.handler[ item.action ]( item );

										if ( item.action != "cancel" ) {
											this.createMenu( this.config.fabric.drawing.menu );
										}
									}
								} )( item );

								// DRAWING
							} else if ( _this.drawing.enabled ) {
								item.click = ( function( item ) {
									return function() {
										if ( this.config.drawing.autoClose ) {
											this.drawing.handler.done();
										}
										this[ "to" + item.format ]( item, function( data ) {
											if ( item.action == "download" ) {
												this.download( data, item.mimeType, [ item.fileName, item.extension ].join( "." ) );
											}
										} );
									}
								} )( item );

								// REGULAR
							} else if ( item.format != "UNDEFINED" ) {
								item.click = ( function( item ) {
									return function() {
										if ( item.capture || item.action == "print" || item.format == "PRINT" ) {
											this.capture( item, function() {
												this.drawing.handler.done();
												this[ "to" + item.format ]( item, function( data ) {
													if ( item.action == "download" ) {
														this.download( data, item.mimeType, [ item.fileName, item.extension ].join( "." ) );
													}
												} );
											} )

										} else if ( this[ "to" + item.format ] ) {
											this[ "to" + item.format ]( item, function( data ) {
												this.download( data, item.mimeType, [ item.fileName, item.extension ].join( "." ) );
											} );
										} else {
											throw new Error( 'Invalid format. Could not determine output type.' );
										}
									}
								} )( item );
							}
						}

						// HIDE EMPTY ONES
						if ( item.menu !== undefined && !item.menu.length ) {
							continue;
						}

						// ADD LINK ATTR
						a.setAttribute( "href", "#" );

						// ENABLE MANUAL ACTIVE STATE ON TOUCH DEVICES
						if ( _this.setup.hasTouch && li.classList ) {
							a.addEventListener( "touchend", ( function( callback, item ) {
								return function( e ) {
									e.preventDefault();
									var args = [ e, item ];

									// DELAYED
									if ( ( item.action == "draw" || item.format == "PRINT" || ( item.format != "UNDEFINED" && item.capture ) ) && !_this.drawing.enabled ) {

										// VALIDATE DELAY
										if ( !isNaN( item.delay ) || !isNaN( _this.config.delay ) ) {
											item.delay = !isNaN( item.delay ) ? item.delay : _this.config.delay;
											_this.delay( item, callback );
											return;
										}
									}

									callback.apply( _this, args );
								}
							} )( item.click || function( e ) {
								e.preventDefault();
							}, item ) );

							a.addEventListener( "touchend", ( function( item ) {
								return function( e ) {
									e.preventDefault();
									var li = item.elements.li;
									var parentIsActive = hasActiveParent( li );
									var siblingIsActive = hasActiveSibling( li );
									var childHasSubmenu = hasSubmenu( li );

									// CHECK IF PARENT IS ACTIVE
									function hasActiveParent( elm ) {
										var parentNode = elm.parentNode.parentNode;
										var classList = parentNode.classList;

										if ( parentNode.tagName == "LI" && classList.contains( "active" ) ) {
											return true;
										}
										return false;
									}

									// CHECK IF ANY SIBLING IS ACTIVE
									function hasActiveSibling( elm ) {
										var siblings = elm.parentNode.children;

										for ( i1 = 0; i1 < siblings.length; i1++ ) {
											var sibling = siblings[ i1 ];
											var classList = sibling.classList;
											if ( sibling !== elm && classList.contains( "active" ) ) {
												classList.remove( "active" );
												return true;
											}
										}

										return false;
									}

									// CHECK IF SUBEMNU EXIST
									function hasSubmenu( elm ) {
										return elm.getElementsByTagName( "ul" ).length > 0;
									}

									// CHECK FOR ROOT ITEMS
									function isRoot( elm ) {
										return elm.classList.contains( "export-main" ) || elm.classList.contains( "export-drawing" );
									}

									// TOGGLE MAIN MENU
									if ( isRoot( li ) || !childHasSubmenu ) {
										_this.setup.menu.classList.toggle( "active" );
									}

									// UNTOGGLE BUFFERED ITEMS
									if ( !parentIsActive || !childHasSubmenu ) {
										while ( buffer.length ) {
											var tmp = buffer.pop();
											var tmpRoot = isRoot( tmp );
											var tmpOdd = tmp !== li;

											if ( tmpRoot ) {
												if ( !childHasSubmenu ) {
													tmp.classList.remove( "active" );
												}
											} else if ( tmpOdd ) {
												tmp.classList.remove( "active" );
											}
										}
									}

									// BUFFER ITEMS
									buffer.push( li );

									// TOGGLE CLASS
									if ( childHasSubmenu ) {
										li.classList.toggle( "active" );
									}
								}
							} )( item ) );

						// NON TOUCH DEVICES
						} else {
							a.addEventListener( "click", ( function( callback, item ) {
								return function( e ) {
									e.preventDefault();
									var args = [ e, item ];

									// DELAYED
									if ( ( item.action == "draw" || item.format == "PRINT" || ( item.format != "UNDEFINED" && item.capture ) ) && !_this.drawing.enabled ) {

										// VALIDATE DELAY
										if ( !isNaN( item.delay ) || !isNaN( _this.config.delay ) ) {
											item.delay = !isNaN( item.delay ) ? item.delay : _this.config.delay;
											_this.delay( item, callback );
											return;
										}
									}

									callback.apply( _this, args );
								}
							} )( item.click || function( e ) {
								e.preventDefault();
							}, item ) );
						}

						li.appendChild( a );

						// ADD LABEL
						if ( _this.isElement( item.label ) ) {
							span.appendChild( item.label );
						} else {
							span.innerHTML = item.label;
						}

						// APPEND ITEMS
						if ( item[ "class" ] ) {
							li.className = item[ "class" ];
						}

						if ( item.style ) {
							li.setAttribute( "style", item.style );
						}

						if ( item.icon ) {
							img.setAttribute( "src", ( !item.ignore && item.icon.slice( 0, 10 ).indexOf( "//" ) == -1 ? chart.pathToImages : "" ) + item.icon );
							a.appendChild( img );
						}
						if ( item.label ) {
							a.appendChild( span );
						}
						if ( item.title ) {
							a.setAttribute( "title", item.title );
						}

						// CALLBACK; REVIVER FOR MENU ITEMS
						if ( _this.config.menuReviver ) {
							li = _this.config.menuReviver.apply( _this, [ item, li ] );
						}

						// ADD ELEMENTS FOR EASY ACCESS
						item.elements = {
							li: li,
							a: a,
							img: img,
							span: span
						}

						// ADD SUBLIST; JUST WITH ENTRIES
						if ( ( item.menu || item.items ) && item.action != "draw" ) {
							if ( buildList( item.menu || item.items, li ).childNodes.length ) {
								ul.appendChild( li );
							}
						} else {
							ul.appendChild( li );
						}
					}

					// JUST ADD THOSE WITH ENTRIES
					if ( ul.childNodes.length ) {
						container.appendChild( ul );
					}

					return ul;
				}

				// DETERMINE CONTAINER
				if ( !container ) {
					if ( typeof _this.config.divId == "string" ) {
						_this.config.divId = container = document.getElementById( _this.config.divId );
					} else if ( _this.isElement( _this.config.divId ) ) {
						container = _this.config.divId;
					} else {
						container = _this.setup.chart.containerDiv;
					}
				}

				// CREATE / RESET MENU CONTAINER
				if ( _this.isElement( _this.setup.menu ) ) {
					_this.setup.menu.innerHTML = "";
				} else {
					_this.setup.menu = document.createElement( "div" );
				}
				_this.setup.menu.setAttribute( "class", _this.setup.chart.classNamePrefix + "-export-menu " + _this.setup.chart.classNamePrefix + "-export-menu-" + _this.config.position + " amExportButton" );

				// CALLBACK; REPLACES THE MENU WALKER
				if ( _this.config.menuWalker ) {
					buildList = _this.config.menuWalker;
				}
				buildList.apply( this, [ list, _this.setup.menu ] );

				// JUST ADD THOSE WITH ENTRIES
				if ( _this.setup.menu.childNodes.length ) {
					container.appendChild( _this.setup.menu );
				}

				return _this.setup.menu;
			},

			/**
			 * Method to trigger the callback delayed
			 */
			delay: function( options, callback ) {
				var cfg = _this.deepMerge( {
					delay: 3,
					precision: 2
				}, options || {} );
				var t1, t2, start = Number( new Date() );
				var menu = _this.createMenu( [ {
					label: _this.i18l( "capturing.delayed.menu.label" ).replace( "{{duration}}", AmCharts.toFixed( cfg.delay, cfg.precision ) ),
					title: _this.i18l( "capturing.delayed.menu.title" ),
					"class": "export-delayed-capturing",
					click: function() {
						clearTimeout( t1 );
						clearTimeout( t2 );
						_this.createMenu( _this.config.menu );
					}
				} ] );
				var label = menu.getElementsByTagName( "a" )[ 0 ];

				// MENU UPDATE
				t1 = setInterval( function() {
					var diff = cfg.delay - ( Number( new Date() ) - start ) / 1000;
					if ( diff <= 0 ) {
						clearTimeout( t1 );
						if ( cfg.action != "draw" ) {
							_this.createMenu( _this.config.menu );
						}
					} else if ( label ) {
						label.innerHTML = _this.i18l( "capturing.delayed.menu.label" ).replace( "{{duration}}", AmCharts.toFixed( diff, 2 ) );
					}
				}, AmCharts.updateRate );

				// CALLBACK
				t2 = setTimeout( function() {
					callback.apply( _this, arguments );
				}, cfg.delay * 1000 );
			},

			/**
			 * Migration method to support old export setup
			 */
			migrateSetup: function( setup ) {
				var cfg = {
					enabled: true,
					migrated: true,
					libs: {
						autoLoad: true
					},
					menu: []
				};

				function crawler( object ) {
					var key;
					Object.keys( object ).some(function( key ) {
						var value = object[ key ];

						if ( key.slice( 0, 6 ) == "export" && value ) {
							cfg.menu.push( key.slice( 6 ) );
						} else if ( key == "userCFG" ) {
							crawler( value );
						} else if ( key == "menuItems" ) {
							cfg.menu = value;
						} else if ( key == "libs" ) {
							cfg.libs = value;
						} else if ( typeof key == "string" ) {
							cfg[ key ] = value;
						}
					});
				}

				crawler( setup );

				return cfg;
			},

			/*
			 ** Method to clear all listeners
			 */
			clear: function() {
				var i1, listener;

				// Remove fabric listeners
				if ( _this.setup.fabric !== undefined ) {
					_this.setup.fabric.removeListeners();
				}

				// Loop through the buffered listeners
				for ( i1 = 0; i1 < _this.listenersToRemove.length; i1++ ) {
					listener = _this.listenersToRemove[ i1 ];
					listener.node.removeEventListener( listener.event, listener.method );
				}

				// Remove wrapper
				if ( _this.isElement(_this.setup.wrapper) && _this.isElement(_this.setup.wrapper.parentNode) && _this.setup.wrapper.parentNode.removeChild ) {
					_this.setup.wrapper.parentNode.removeChild(_this.setup.wrapper);
				}

				// Remove menu
				if ( _this.isElement(_this.setup.menu) && _this.isElement(_this.setup.wrapper.parentNode) && _this.setup.wrapper.parentNode.removeChild ) {
					_this.setup.menu.parentNode.removeChild(_this.setup.menu);
				}

				// Remove references
				_this.listenersToRemove = [];
				_this.setup.chart.AmExport = undefined;
				_this.setup.chart.export = undefined;
				_this.setup = undefined;
			},

			/*
			 ** Add event listener
			 */
			loadListeners: function() {
				function handleClone( clone ) {
					if ( clone ) {
						clone.set( {
							top: clone.top + 10,
							left: clone.left + 10
						} );
						_this.setup.fabric.add( clone );
					}
				}

				// OBSERVE; KEY LISTENER; DRAWING FEATURES
				if ( _this.config.keyListener && _this.config.keyListener != "attached" ) {

					_this.docListener = function( e ) {
						var current = _this.drawing.buffer.target;
						var KEY_WHITELIST = [ 37, 38, 39, 40, 13, 9, 27 ];
						var MENU_LEFT = [ "top-left", "bottom-left" ].indexOf( _this.config.position ) != -1;
						var MENU_RIGHT = [ "top-right", "bottom-right" ].indexOf( _this.config.position ) != -1;

						// FOCUS FIRST ITEM IN MENU
						function focusFirst( list, throughTab ) {
							for ( i1 = 0; i1 < list.length; i1++ ) {
								var item = list[ i1 ];
								item.parentNode.classList.remove( "active" );

								// DO NOT THAT THROUGH TAB COMMANDS
								if ( i1 == 0 && !throughTab ) {
									item.focus();
								}
							}
						}

						// FOCUS NEXT MENU
						function focusNext( throughTab ) {
							if ( _this.setup.focusedMenuItem && _this.setup.focusedMenuItem.nextSibling ) {
								_this.setup.focusedMenuItem.parentNode.classList.add( "active" );
								focusFirst( _this.setup.focusedMenuItem.nextSibling.getElementsByTagName( "a" ), throughTab );
							}
						}

						// FOCUS PREVIOUS MENU
						function focusPrev( throughTab ) {
							if ( _this.setup.focusedMenuItem && _this.setup.focusedMenuItem.parentNode.parentNode.parentNode ) {
								_this.setup.focusedMenuItem.parentNode.classList.add( "active" );
								focusFirst( _this.setup.focusedMenuItem.parentNode.parentNode.parentNode.getElementsByTagName( "a" ), throughTab );
							}
						}

						// FOCUS NEXT ITEM
						function focusDown( throughTab ) {
							if ( _this.setup.focusedMenuItem && _this.setup.focusedMenuItem.parentNode.nextSibling ) {
								_this.setup.focusedMenuItem.parentNode.classList.remove( "active" );
								focusFirst( _this.setup.focusedMenuItem.parentNode.nextSibling.getElementsByTagName( "a" ), throughTab );
							}
						}
						// FOCUS PREVIOUS ITEM
						function focusUp( throughTab ) {
							if ( _this.setup.focusedMenuItem && _this.setup.focusedMenuItem.parentNode.previousSibling ) {
								_this.setup.focusedMenuItem.parentNode.classList.remove( "active" );
								focusFirst( _this.setup.focusedMenuItem.parentNode.previousSibling.getElementsByTagName( "a" ), throughTab );
							}
						}

						// BLUR EVERYTHING
						function blurAll() {
							function unselectParents( elm ) {
								if ( _this.isElement(elm) ) {
									try {
										elm.blur();
									} catch(e) {
										// Lovely IE
									}

									// BLUR PARENT
									if ( elm.parentNode ) {
										elm.parentNode.classList.remove( "active" );
									}

									// ENOUGH; EXIT ON MENU WRAPPER
									if ( !elm.classList.contains( "amExportButton" ) ) {
										unselectParents( elm.parentNode );
									}
								}
							}

							// TRIGGER PRIV. FUNC. ONLY ON FOCUSED ELEMENT
							if ( _this.setup.focusedMenuItem ) {
								unselectParents( _this.setup.focusedMenuItem );
								_this.setup.focusedMenuItem = undefined;
							}
						}

						// IF WE'VE A FOCUSED ELEMENT
						if ( _this.setup.focusedMenuItem && KEY_WHITELIST.indexOf( e.keyCode ) != -1 ) {

							// TAB (focusedMenuItem holds the previous selected element)
							if ( e.keyCode == 9 ) {

								// NEXT ITEM AVAILABLE?
								if ( !_this.setup.focusedMenuItem.nextSibling ) {
									_this.setup.focusedMenuItem.parentNode.classList.remove( "active" );

									// NEXT PARENT ITEM AVAILABLE?
									if ( !_this.setup.focusedMenuItem.parentNode.nextSibling ) {
										_this.setup.focusedMenuItem.parentNode.classList.remove( "active" );
										_this.setup.focusedMenuItem.parentNode.parentNode.parentNode.classList.remove( "active" );
									}

									// SHIFT
								} else if ( e.shiftKey ) {
									_this.setup.focusedMenuItem.parentNode.classList.remove( "active" );
								}
								return;
							}

							// ENTER
							if ( e.keyCode == 13 && _this.setup.focusedMenuItem.nextSibling ) {
								focusNext();
							}

							// LEFT
							if ( e.keyCode == 37 ) {
								if ( MENU_RIGHT ) {
									focusNext();
								} else {
									focusPrev();
								}
							}

							// RIGHT
							if ( e.keyCode == 39 ) {
								if ( MENU_RIGHT ) {
									focusPrev();
								} else {
									focusNext();
								}
							}

							// DOWN
							if ( e.keyCode == 40 ) {
								focusDown();
							}
							// UP
							if ( e.keyCode == 38 ) {
								focusUp();
							}
							// ESC
							if ( e.keyCode == 27 ) {
								blurAll();
							}
						}

						// REMOVE; key: BACKSPACE / DELETE
						if ( ( e.keyCode == 8 || e.keyCode == 46 ) && current ) {
							e.preventDefault();
							_this.setup.fabric.remove( current );

							// ESCAPE DRAWIN MODE; key: escape
						} else if ( e.keyCode == 27 && _this.drawing.enabled ) {
							e.preventDefault();

							// DESELECT ACTIVE OBJECTS
							if ( _this.drawing.buffer.isSelected ) {
								_this.setup.fabric.discardActiveObject();

								// QUIT DRAWING MODE
							} else {
								_this.drawing.handler.done();
							}

							// COPY; key: C
						} else if ( e.keyCode == 67 && ( e.metaKey || e.ctrlKey ) && current ) {
							_this.drawing.buffer.copy = current;

							// CUT; key: X
						} else if ( e.keyCode == 88 && ( e.metaKey || e.ctrlKey ) && current ) {
							_this.drawing.buffer.copy = current;
							_this.setup.fabric.remove( current );

							// PASTE; key: V
						} else if ( e.keyCode == 86 && ( e.metaKey || e.ctrlKey ) ) {
							if ( _this.drawing.buffer.copy ) {
								handleClone( _this.drawing.buffer.copy.clone( handleClone ) )
							}

							// UNDO / REDO; key: Z
						} else if ( e.keyCode == 90 && ( e.metaKey || e.ctrlKey ) ) {
							e.preventDefault();
							if ( e.shiftKey ) {
								_this.drawing.handler.redo();
							} else {
								_this.drawing.handler.undo();
							}
						}
					}

					_this.config.keyListener = "attached";

					document.addEventListener( "keydown", _this.docListener );
					_this.addListenerToRemove( "keydown", document, _this.docListener );
				}

				// OBSERVE; DRAG AND DROP LISTENER; DRAWING FEATURE
				if ( _this.config.fileListener ) {
					_this.setup.chart.containerDiv.addEventListener( "dragover", _this.handleDropbox );
					_this.addListenerToRemove( "dragover", _this.setup.chart.containerDiv, _this.handleDropbox );
					_this.setup.chart.containerDiv.addEventListener( "dragleave", _this.handleDropbox );
					_this.addListenerToRemove( "dragleave", _this.setup.chart.containerDiv, _this.handleDropbox );
					_this.setup.chart.containerDiv.addEventListener( "drop", _this.handleDropbox );
					_this.addListenerToRemove( "drop", _this.setup.chart.containerDiv, _this.handleDropbox );
				}
			},

			/**
			 * Initiate export menu; waits for chart container to place menu
			 */
			init: function() {
				clearTimeout( _timer );

				_timer = setInterval( function() {
					if ( _this.setup && _this.setup.chart.containerDiv ) {
						clearTimeout( _timer );

						if ( _this.config.enabled ) {
							// CREATE REFERENCE
							_this.setup.chart.AmExport = _this;

							// OVERWRITE PARENT OVERFLOW
							if ( _this.config.overflow ) {
								_this.setup.chart.div.style.overflow = "visible";
							}

							// ATTACH EVENTS
							_this.loadListeners();

							// CREATE MENU
							_this.createMenu( _this.config.menu );

							_this.handleReady( _this.config.onReady );
						}
					}
				}, AmCharts.updateRate );

			},

			/**
			 * Initiates export instance; merges given config; attaches event listener
			 */
			construct: function() {
				// ANNOTATION; MAP "DONE"
				_this.drawing.handler.cancel = _this.drawing.handler.done;

				// CHECK BLOB CONSTRUCTOR
				try {
					_this.setup.hasBlob = !!new Blob;
				} catch ( e ) {}

				// WORK AROUND TO BYPASS FILESAVER CHECK TRYING TO OPEN THE BLOB URL IN SAFARI BROWSER
				window.safari = window.safari ? window.safari : {};

				// OVERTAKE CHART FONTSIZE IF GIVEN
				_this.defaults.fabric.drawing.fontSize = _this.setup.chart.fontSize || 11;

				// MERGE SETTINGS
				_this.config.drawing = _this.deepMerge( _this.defaults.fabric.drawing, _this.config.drawing || {}, true );
				if ( _this.config.border ) {
					_this.config.border = _this.deepMerge( _this.defaults.fabric.border, _this.config.border || {}, true );
				}
				_this.deepMerge( _this.defaults.fabric, _this.config, true );
				_this.deepMerge( _this.defaults.fabric, _this.config.fabric || {}, true );
				_this.deepMerge( _this.defaults.pdfMake, _this.config, true );
				_this.deepMerge( _this.defaults.pdfMake, _this.config.pdfMake || {}, true );
				_this.deepMerge( _this.libs, _this.config.libs || {}, true );

				// UPDATE CONFIG
				_this.config.drawing = _this.defaults.fabric.drawing;
				_this.config.fabric = _this.defaults.fabric;
				_this.config.pdfMake = _this.defaults.pdfMake;
				_this.config = _this.deepMerge( _this.defaults, _this.config, true );

				// MERGE; SETUP DRAWING MENU
				if ( _this.config.fabric.drawing.enabled ) {
					if ( _this.config.fabric.drawing.menu === undefined ) {
						_this.config.fabric.drawing.menu = [];
						_this.deepMerge( _this.config.fabric.drawing.menu, [ {
							"class": "export-drawing",
							menu: [ {
								label: _this.i18l( "menu.label.draw.add" ),
								menu: [ {
									label: _this.i18l( "menu.label.draw.shapes" ),
									action: "draw.shapes"
								}, {
									label: _this.i18l( "menu.label.draw.text" ),
									action: "text"
								} ]
							}, {
								label: _this.i18l( "menu.label.draw.change" ),
								menu: [ {
									label: _this.i18l( "menu.label.draw.modes" ),
									action: "draw.modes"
								}, {
									label: _this.i18l( "menu.label.draw.colors" ),
									action: "draw.colors"
								}, {
									label: _this.i18l( "menu.label.draw.widths" ),
									action: "draw.widths"
								}, {
									label: _this.i18l( "menu.label.draw.opacities" ),
									action: "draw.opacities"
								}, "UNDO", "REDO" ]
							}, {
								label: _this.i18l( "menu.label.save.image" ),
								menu: [ "PNG", "JPG", "SVG", "PDF" ]
							}, "PRINT", "CANCEL" ]
						} ] );
					}
				}

				// MERGE; SETUP MAIN MENU
				if ( _this.config.menu === undefined ) {
					_this.config.menu = [];
					// PARENT MENU
					_this.deepMerge( _this.config, {
						menu: [ {
							"class": "export-main",
							menu: [ {
								label: _this.i18l( "menu.label.save.image" ),
								menu: [ "PNG", "JPG", "SVG", "PDF" ]
							}, {
								label: _this.i18l( "menu.label.save.data" ),
								menu: [ "CSV", "XLSX", "JSON" ]
							}, {
								label: _this.i18l( "menu.label.draw" ),
								action: "draw",
								menu: _this.config.fabric.drawing.menu
							}, {
								format: "PRINT",
								label: _this.i18l( "menu.label.print" )
							} ]
						} ]
					} );
				}

				// ADD MISSING PATH
				if ( !_this.libs.path ) {
					_this.libs.path = _this.config.path + "libs/";
				}

				// ADD CLASSLIST POLYFILL IF NEEDED
				if (!_this.setup.hasClasslist) {
					_this.libs.resources.push("classList.js/classList.min.js");
				}

				// CHECK ACCEPTANCE
				if ( _this.isSupported() ) {
					// LOAD DEPENDENCIES
					_this.loadDependencies( _this.libs.resources, _this.libs.reload );
					// ADD CLASSNAMES
					_this.setup.chart.addClassNames = true;
					// REFERENCE
					_this.setup.chart[ _this.name ] = _this;
					// INIT MENU; WAIT FOR CHART INSTANCE
					_this.init();
				}
			}
		}

		// USE GIVEN CONFIG
		if ( config ) {
			_this.config = config;

			// USE CHART EXPORT CONFIG
		} else if ( _this.setup.chart[ _this.name ] ) {
			_this.config = _this.setup.chart[ _this.name ];

			// MIGRATE OLD EXPORT CHART CONFIG
		} else if ( _this.setup.chart.amExport || _this.setup.chart.exportConfig ) {
			_this.config = _this.migrateSetup( _this.setup.chart.amExport || _this.setup.chart.exportConfig );

			// EXIT; NO CONFIG
		} else {
			return;
		}

		// CONSTRUCT INSTANCE
		_this.construct();

		// EXPORT SCOPE
		return _this.deepMerge( this, _this );
	}
} )();

/**
 * Set init handler
 */
AmCharts.addInitHandler( function( chart ) {
	new AmCharts[ "export" ]( chart );
}, [ "pie", "serial", "xy", "funnel", "radar", "gauge", "stock", "map", "gantt" ] );
