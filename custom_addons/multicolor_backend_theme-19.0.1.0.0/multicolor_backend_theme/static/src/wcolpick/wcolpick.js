/*
Wcolpick - A Web Color Picker

Copyright (C) 2017-2023  devpelux (Salvatore Peluso)
Find me on github: https://github.com/devpelux
Dual licensed under GPL v3    .0 and MIT licenses.
(Based on Jose Vargas' Color Picker)

Description, how to use, and examples: https://github.com/devpelux/wcolpick

Last Edit: 2023/05/05 18:53
*/


(function ($) {
	var wcolpick = function () {
		var
			tpl = '<div class="wcolpick"><div class="wcolpick_color"><div class="wcolpick_color_overlay1"><div class="wcolpick_color_overlay2"><div class="wcolpick_selector_outer"><div class="wcolpick_selector_inner"></div></div></div></div></div><div class="wcolpick_hue"><div class="wcolpick_hue_underlay"></div><div class="wcolpick_hue_overlay"></div><div class="wcolpick_hue_arrs"><div class="wcolpick_hue_larr"></div><div class="wcolpick_hue_rarr"></div></div></div><div class="wcolpick_alpha"><div class="wcolpick_alpha_underlay wcolpick_checkerboards"></div><div class="wcolpick_alpha_overlay"></div><div class="wcolpick_alpha_arrs"><div class="wcolpick_alpha_darr"></div><div class="wcolpick_alpha_uarr"></div></div></div><div class="wcolpick_hex_field"><div class="wcolpick_field_letter">#</div><input type="text" maxlength="8" size="6" /></div><div class="wcolpick_rgb_r wcolpick_field"><div class="wcolpick_field_letter">R</div><input type="text" maxlength="3" size="3" /><div class="wcolpick_field_arrs"><div class="wcolpick_field_uarr"></div><div class="wcolpick_field_darr"></div></div></div><div class="wcolpick_rgb_g wcolpick_field"><div class="wcolpick_field_letter">G</div><input type="text" maxlength="3" size="3" /><div class="wcolpick_field_arrs"><div class="wcolpick_field_uarr"></div><div class="wcolpick_field_darr"></div></div></div><div class="wcolpick_rgb_b wcolpick_field"><div class="wcolpick_field_letter">B</div><input type="text" maxlength="3" size="3" /><div class="wcolpick_field_arrs"><div class="wcolpick_field_uarr"></div><div class="wcolpick_field_darr"></div></div></div><div class="wcolpick_hsb_h wcolpick_field"><div class="wcolpick_field_letter">H</div><input type="text" maxlength="3" size="3" /><div class="wcolpick_field_arrs"><div class="wcolpick_field_uarr"></div><div class="wcolpick_field_darr"></div></div></div><div class="wcolpick_hsb_s wcolpick_field"><div class="wcolpick_field_letter">S</div><input type="text" maxlength="3" size="3" /><div class="wcolpick_field_arrs"><div class="wcolpick_field_uarr"></div><div class="wcolpick_field_darr"></div></div></div><div class="wcolpick_hsb_b wcolpick_field"><div class="wcolpick_field_letter">B</div><input type="text" maxlength="3" size="3" /><div class="wcolpick_field_arrs"><div class="wcolpick_field_uarr"></div><div class="wcolpick_field_darr"></div></div></div><div class="wcolpick_alpha_field wcolpick_field"><div class="wcolpick_field_letter">A</div><input type="text" maxlength="3" size="3" /><div class="wcolpick_field_arrs"><div class="wcolpick_field_uarr"></div><div class="wcolpick_field_darr"></div></div></div><div class="wcolpick_colors"><div class="wcolpick_colors_underlay wcolpick_checkerboards"></div><div class="wcolpick_new_color"></div><div class="wcolpick_current_color"></div></div><div class="wcolpick_submit"><div class="wcolpick_tear"></div></div></div>',
			defaults = {
				alphaOutline: true,
				appendToBody: false,
				arrowsColor: 'default',
				backgroundColor: 'default',
				border: 1,
				borderColor: 'default',
				checkersColor: 'default',
				color: {h:0, s:0, b:20, a:1},
				colorOutline: true,
				colorScheme: 'light-full',
				colorSelOutline: true,
				compactLayout: false,
				enableAlpha: true,
				enableSubmit: true,
				enableUpDown: true,
				fieldsBackground: 'default',
				flat: true,
				hueOutline: true,
				layout: 'full',
				livePreview: true,
				polyfill: false,
				position: 'auto',
				readonlyFields: false,
				readonlyHexField: false,
				showEvent: 'click',
				submitBackground: 'default',
				submitColor: 'default',
				variant: 'standard',
				onBeforeShow: function () {},
				onChange: function () {},
				onDestroy: function () {},
				onHide: function () {},
				onLoaded: function () {},
				onShow: function () {},
				onSubmit: function () {}
			},
			//Fill the inputs of the plugin
			fillRGBFields = function  (rgba, cal) {
				$(cal).data('wcolpick').fields
					.eq(1).val(rgba.r).end()
					.eq(2).val(rgba.g).end()
					.eq(3).val(rgba.b).end()
			},

			fillHSBFields = function  (hsba, cal) {
				$(cal).data('wcolpick').fields
					.eq(4).val(Math.round(hsba.h)).end()
					.eq(5).val(Math.round(hsba.s)).end()
					.eq(6).val(Math.round(hsba.b)).end();
			},
			fillAlphaField = function (hsba, cal) {
				$(cal).data('wcolpick').fields.eq(7).val(Math.round(hsba.a*100)).end();
			},
			fillHexField = function (hex, cal) {
				if ($(cal).data('wcolpick').enableAlpha) $(cal).data('wcolpick').fields.eq(0).val(hex);
				else $(cal).data('wcolpick').fields.eq(0).val(hex.substring(0,6));
			},
			//Set selector's color and selector's indicator position
			setSelectorPos = function (hsba, cal) {
				$(cal).data('wcolpick').selectorIndic.css({
					left: Math.round($(cal).data('wcolpick').size * hsba.s/100),
					top: Math.round($(cal).data('wcolpick').size * (100-hsba.b)/100)
				});
			},
			setSelectorColor = function (hsba, cal) {
				if (isInternetExplorer()) { //Compatibility with IE 6-9
					var rgba = hsbaToRgba({h: Math.round(hsba.h), s: 100, b: 100, a: 255});
					$(cal).data('wcolpick').selector.css('backgroundColor', 'rgb('+rgba.r+','+rgba.g+','+rgba.b+')');
				} else $(cal).data('wcolpick').selector.css('backgroundColor', 'hsl('+Math.round(hsba.h)+','+100+'%,'+50+'%)');
			},
			//Set hue's arrows position
			setHuePos = function (hsba, cal) {
				$(cal).data('wcolpick').hue.css('top', Math.round($(cal).data('wcolpick').size - $(cal).data('wcolpick').size * hsba.h/360));
			},
			//Set alpha bar color and alpha's arrows position
			setAlphaPos = function (hsba, cal) {
				if ($(cal).data('wcolpick').enableAlpha) $(cal).data('wcolpick').alpha.css('left', Math.round($(cal).data('wcolpick').size * hsba.a));
			},
			setAlphaColor = function (rgba, cal) {
				if ($(cal).data('wcolpick').enableAlpha) {
					if (isInternetExplorer()) { //Compatibility with IE 6-9
						var end = rgbaToHex(rgba).substring(0,6);
						$(cal).data('wcolpick').alphaBar.attr('style','filter:progid:DXImageTransform.Microsoft.gradient(GradientType=1,startColorstr=0,endColorstr=#'+end+'); -ms-filter:"progid:DXImageTransform.Microsoft.gradient(GradientType=1,startColorstr=0,endColorstr=#'+end+')";');
					} else {
						var begin = 'rgba('+rgba.r+','+rgba.g+','+rgba.b+',0)', end = 'rgba('+rgba.r+','+rgba.g+','+rgba.b+',1)';
					} $(cal).data('wcolpick').alphaBar.attr('style','background:-webkit-linear-gradient(left,'+begin+' 0%,'+end+' 100%); background:-moz-linear-gradient(left,'+begin+' 0%,'+end+' 100%); background:-ms-linear-gradient(left,'+begin+' 0%,'+end+' 100%); background:-o-linear-gradient(left,'+begin+' 0%,'+end+' 100%); background:linear-gradient(to right,'+begin+' 0%,'+end+' 100%);');
				}
			},
			//Set current and new colors
			setCurrentColor = function (rgba, cal) {
				$(cal).data('wcolpick').currentColor.css('backgroundColor', 'rgba('+rgba.r+','+rgba.g+','+rgba.b+','+rgba.a+')');
			},
			setNewColor = function (rgba, cal) {
				$(cal).data('wcolpick').newColor.css('backgroundColor', 'rgba('+rgba.r+','+rgba.g+','+rgba.b+','+rgba.a+')');
			},
			//Called when the new color is changed
			change = function () {
				var cal = $(this).parent().parent(), hsba, rgba, hex;
				if (this.parentNode.className.indexOf('_alpha') > 0) {
					hsba = {
						h: cal.data('wcolpick').color.h,
						s: cal.data('wcolpick').color.s,
						b: cal.data('wcolpick').color.b,
						a: fixAlpha(cal.data('wcolpick').fields.eq(7).val()/100)
					};
					rgba = hsbaToRgba(hsba);
					hex = rgbaToHex(rgba);
				} else if (this.parentNode.className.indexOf('_hex') > 0) {
					rgba = hexToRgba(adaptHex(cal.data('wcolpick').fields.eq(0).val(), cal));
					hsba = rgbaToHsba(rgba);
					hex = rgbaToHex(rgba);
				} else if (this.parentNode.className.indexOf('_hsb') > 0) {
					hsba = fixHSBA({
						h: Math.round(cal.data('wcolpick').fields.eq(4).val()),
						s: Math.round(cal.data('wcolpick').fields.eq(5).val()),
						b: Math.round(cal.data('wcolpick').fields.eq(6).val()),
						a: cal.data('wcolpick').color.a
					});
					rgba = hsbaToRgba(hsba);
					hex = rgbaToHex(rgba);
				} else {
					rgba = fixRGBA({
						r: Math.round(cal.data('wcolpick').fields.eq(1).val()),
						g: Math.round(cal.data('wcolpick').fields.eq(2).val()),
						b: Math.round(cal.data('wcolpick').fields.eq(3).val()),
						a: cal.data('wcolpick').color.a
					});
					hsba = rgbaToHsba(rgba);
					hex = rgbaToHex(rgba);
				}
				//Store new color
				cal.data('wcolpick').color = cloneHSBA(hsba, true);
				//Show new color
				setNewColor(rgba, cal.get(0));
				//Fill fields with new color
				fillHSBFields(hsba, cal.get(0));
				fillAlphaField(hsba, cal.get(0));
				fillRGBFields(rgba, cal.get(0));
				fillHexField(hex, cal.get(0));
				//Setup other elements with new color
				setSelectorPos(hsba, cal.get(0));
				setSelectorColor(hsba, cal.get(0));
				setHuePos(hsba, cal.get(0));
				setAlphaPos(hsba, cal.get(0));
				setAlphaColor(rgba, cal.get(0));
				//Fires onChange (bySetColor = false)
				var hsla = hsbaToHsla(hsba);
				cal.data('wcolpick').onChange.apply(cal.parent(), [{bySetColor:false, colorDiv:cal.get(0), el:cal.data('wcolpick').el, hex:hex.substring(0,6), hexa:hex, hsb:cloneHSBA(hsba, false), hsba:hsba, hsl:cloneHSLA(hsla, false), hsla:hsla, rgb:cloneRGBA(rgba, false), rgba:rgba}]);
			},
			//Change style on blur and on focus of inputs
			blur = function () {
				$(this).parent().removeClass('wcolpick_focus');
			},
			focus = function () {
				$(this).parent().parent().data('wcolpick').fields.parent().removeClass('wcolpick_focus');
				$(this).parent().addClass('wcolpick_focus');
			},
			//Increment/decrement arrows functions
			downIncrement = function (ev) {
				ev.preventDefault ? ev.preventDefault() : ev.returnValue = false;
				var field = $(this).parent().find('input').focus();
				var current = {
					el: $(this).parent().addClass('wcolpick_changing'),
					max: this.parentNode.className.indexOf('_hsb_h') > 0 ? 360 : (this.parentNode.className.indexOf('_hsb') > 0 ? 100 : (this.parentNode.className.indexOf('_alpha') > 0 ? 100 : 255)),
					y: ev.pageY,
					field: field,
					val: Math.round(field.val()),
					preview: $(this).parent().parent().data('wcolpick').livePreview
				};
				$(document).mouseup(current, upIncrement);
				$(document).mousemove(current, moveIncrement);
			},
			moveIncrement = function (ev) {
				//livePreview = true: update colors | livePreview = false: update only field's value
				ev.data.field.val(fixVal(Math.round(ev.data.val - ev.pageY + ev.data.y), 0, ev.data.max));
				if (ev.data.preview) change.apply(ev.data.field.get(0));
				return false;
			},
			upIncrement = function (ev) {
				//livePreview = true: do nothing | livePreview = false: update colors
				if (!ev.data.preview) change.apply(ev.data.field.get(0));
				ev.data.el.removeClass('wcolpick_changing').find('input').focus();
				$(document).off('mouseup', upIncrement);
				$(document).off('mousemove', moveIncrement);
				return false;
			},
			//Alpha slider functions
			downAlpha = function (ev) {
				ev.preventDefault ? ev.preventDefault() : ev.returnValue = false;
				var current = {
					cal: $(this).parent(),
					x: $(this).offset().left,
					preview: $(this).parent().data('wcolpick').livePreview
				};
				$(document).on('mouseup touchend',current,upAlpha);
				$(document).on('mousemove touchmove',current,moveAlpha);
				//Update alpha value with selected value
				var pageX = ((ev.type == 'touchstart') ? ev.originalEvent.changedTouches[0].pageX : ev.pageX);
				change.apply(
					current.cal.data('wcolpick').fields
					.eq(7).val(Math.round(100 * fixVal(pageX - current.x, 0, current.cal.data('wcolpick').size) / current.cal.data('wcolpick').size))
					.get(0)
				);
				return false;
			},
			moveAlpha = function (ev) {
				var pageX = ((ev.type == 'touchmove') ? ev.originalEvent.changedTouches[0].pageX : ev.pageX);
				var alpha = Math.round(100 * fixVal(pageX - ev.data.x, 0, ev.data.cal.data('wcolpick').size) / ev.data.cal.data('wcolpick').size);
				//livePreview = true: update colors | livePreview = false: update only position
				if (ev.data.preview) change.apply(ev.data.cal.data('wcolpick').fields.eq(7).val(alpha).get(0));
				else setAlphaPos({a:alpha/100}, ev.data.cal.get(0));
				return false;
			},
			upAlpha = function (ev) {
				//livePreview = true: do nothing | livePreview = false: update colors
				if (!ev.data.preview) {
					var pageX = ((ev.type == 'touchend') ? ev.originalEvent.changedTouches[0].pageX : ev.pageX);
					change.apply(
						ev.data.cal.data('wcolpick').fields
						.eq(7).val(Math.round(100 * fixVal(pageX - ev.data.x, 0, ev.data.cal.data('wcolpick').size) / ev.data.cal.data('wcolpick').size))
						.get(0)
					);
				}
				$(document).off('mouseup touchend',upAlpha);
				$(document).off('mousemove touchmove',moveAlpha);
				return false;
			},
			//Hue slider functions
			downHue = function (ev) {
				ev.preventDefault ? ev.preventDefault() : ev.returnValue = false;
				var current = {
					cal: $(this).parent(),
					y: $(this).offset().top,
					preview: $(this).parent().data('wcolpick').livePreview
				};
				$(document).on('mouseup touchend',current,upHue);
				$(document).on('mousemove touchmove',current,moveHue);
				//Update hue value with selected value
				var pageY = ((ev.type == 'touchstart') ? ev.originalEvent.changedTouches[0].pageY : ev.pageY);
				change.apply(
					current.cal.data('wcolpick').fields
					.eq(4).val(Math.round(360 * (current.cal.data('wcolpick').size - fixVal(pageY - current.y, 0, current.cal.data('wcolpick').size)) / current.cal.data('wcolpick').size))
					.get(0)
				);
				return false;
			},
			moveHue = function (ev) {
				var pageY = ((ev.type == 'touchmove') ? ev.originalEvent.changedTouches[0].pageY : ev.pageY);
				var hue = Math.round(360 * (ev.data.cal.data('wcolpick').size - fixVal(pageY - ev.data.y, 0, ev.data.cal.data('wcolpick').size)) / ev.data.cal.data('wcolpick').size);
				//livePreview = true: update colors | livePreview = false: update only position
				if (ev.data.preview) change.apply(ev.data.cal.data('wcolpick').fields.eq(4).val(hue).get(0));
				else setHuePos({h:hue}, ev.data.cal.get(0));
				return false;
			},
			upHue = function (ev) {
				//livePreview = true: do nothing | livePreview = false: update colors
				if (!ev.data.preview) {
					var pageY = ((ev.type == 'touchend') ? ev.originalEvent.changedTouches[0].pageY : ev.pageY);
					change.apply(
						ev.data.cal.data('wcolpick').fields
						.eq(4).val(Math.round(360 * (ev.data.cal.data('wcolpick').size - fixVal(pageY - ev.data.y, 0, ev.data.cal.data('wcolpick').size)) / ev.data.cal.data('wcolpick').size))
						.get(0)
					);
				}
				$(document).off('mouseup touchend',upHue);
				$(document).off('mousemove touchmove',moveHue);
				return false;
			},
			//Color selector functions
			downSelector = function (ev) {
				ev.preventDefault ? ev.preventDefault() : ev.returnValue = false;
				var current = {
					cal: $(this).parent(),
					pos: $(this).offset(),
					preview: $(this).parent().data('wcolpick').livePreview
				};
				$(document).on('mouseup touchend',current,upSelector);
				$(document).on('mousemove touchmove',current,moveSelector);
				//Update saturation and brightness with selected values
				var pageX, pageY;
				if(ev.type == 'touchstart') {pageX = ev.originalEvent.changedTouches[0].pageX; pageY = ev.originalEvent.changedTouches[0].pageY;} else {pageX = ev.pageX; pageY = ev.pageY;}
				change.apply(
					current.cal.data('wcolpick').fields
					.eq(6).val(Math.round(100 * (current.cal.data('wcolpick').size - fixVal(pageY - current.pos.top, 0, current.cal.data('wcolpick').size)) / current.cal.data('wcolpick').size)).end()
					.eq(5).val(Math.round(100 * fixVal(pageX - current.pos.left, 0, current.cal.data('wcolpick').size) / current.cal.data('wcolpick').size))
					.get(0)
				);
				return false;
			},
			moveSelector = function (ev) {
				var pageX, pageY;
				if(ev.type == 'touchmove') {pageX = ev.originalEvent.changedTouches[0].pageX; pageY = ev.originalEvent.changedTouches[0].pageY;} else {pageX = ev.pageX; pageY = ev.pageY;}
				var saturation = Math.round(100 * fixVal(pageX - ev.data.pos.left, 0, ev.data.cal.data('wcolpick').size) / ev.data.cal.data('wcolpick').size);
				var brightness = Math.round(100 * (ev.data.cal.data('wcolpick').size - fixVal(pageY - ev.data.pos.top, 0, ev.data.cal.data('wcolpick').size)) / ev.data.cal.data('wcolpick').size);
				//livePreview = true: update colors | livePreview = false: update only position
				if (ev.data.preview) change.apply(ev.data.cal.data('wcolpick').fields.eq(6).val(brightness).end().eq(5).val(saturation).get(0));
				else setSelectorPos({s:saturation, b:brightness}, ev.data.cal.get(0));
				return false;
			},
			upSelector = function (ev) {
				//livePreview = true: do nothing | livePreview = false: update colors
				if (!ev.data.preview) {
					var pageX, pageY;
					if(ev.type == 'touchend') {pageX = ev.originalEvent.changedTouches[0].pageX; pageY = ev.originalEvent.changedTouches[0].pageY; } else { pageX = ev.pageX; pageY = ev.pageY;}
					change.apply(
						ev.data.cal.data('wcolpick').fields
						.eq(6).val(Math.round(100 * (ev.data.cal.data('wcolpick').size - fixVal(pageY - ev.data.pos.top, 0, ev.data.cal.data('wcolpick').size)) / ev.data.cal.data('wcolpick').size)).end()
						.eq(5).val(Math.round(100 * fixVal(pageX - ev.data.pos.left, 0, ev.data.cal.data('wcolpick').size) / ev.data.cal.data('wcolpick').size))
						.get(0)
					);
				}
				$(document).off('mouseup touchend',upSelector);
				$(document).off('mousemove touchmove',moveSelector);
				return false;
			},
			//Change values of the fields with up/down keys
			keyDownFields = function(ev) {
				if ($(this).parent().parent().data('wcolpick').enableUpDown) {
					//Not triggered for hexadecimal field (there is no standard to define an order among the colors)
					if (this.parentNode.className.indexOf('_hex_field') == -1) {
						if (ev.which == 38 || ev.which == 40) {
							ev.preventDefault();
							//Get the value from the selected element
							var value = $(this).val();
							if (ev.which == 38) value++; //Up
							else value--; //Down
							//Set the new value and apply changes
							change.apply($(this).val(value).get(0));
						}
					}
				}
			},
			//Submit button
			clickSubmit = function () {
				var cal = $(this).parent();
				var hsba = cloneHSBA(cal.data('wcolpick').color, true);
				var rgba = hsbaToRgba(hsba);
				var hex = rgbaToHex(rgba);
				cal.data('wcolpick').origColor = cloneHSBA(hsba, true);
				setCurrentColor(rgba, cal.get(0));
				//Fires onSubmit
				var hsla = hsbaToHsla(hsba);
				cal.data('wcolpick').onSubmit({colorDiv:cal.get(0), el:cal.data('wcolpick').el, hex:hex.substring(0,6), hexa:hex, hsb:cloneHSBA(hsba, false), hsba:hsba, hsl:cloneHSLA(hsla, false), hsla:hsla, rgb:cloneRGBA(rgba, false), rgba:rgba});
			},
			//Restore original color by clicking on current color
			restoreOriginal = function () {
				var cal = $(this).parent().parent();
				var hsba = cloneHSBA(cal.data('wcolpick').origColor, true);
				var rgba = hsbaToRgba(hsba);
				var hex = rgbaToHex(rgba);
				cal.data('wcolpick').color = cloneHSBA(hsba, true);
				//Reapplies current color to all elements
				fillHexField(hex, cal.get(0));
				fillRGBFields(rgba, cal.get(0));
				fillHSBFields(hsba, cal.get(0));
				fillAlphaField(hsba, cal.get(0));
				setSelectorPos(hsba, cal.get(0));
				setSelectorColor(hsba, cal.get(0));
				setHuePos(hsba, cal.get(0));
				setAlphaPos(hsba, cal.get(0));
				setAlphaColor(rgba, cal.get(0));
				setNewColor(rgba, cal.get(0));
				//Fires onChange (bySetColor = false)
				var hsla = hsbaToHsla(hsba);
				cal.data('wcolpick').onChange.apply(cal.parent(), [{bySetColor:false, colorDiv:cal.get(0), el:cal.data('wcolpick').el, hex:hex.substring(0,6), hexa:hex, hsb:cloneHSBA(hsba, false), hsba:hsba, hsl:cloneHSLA(hsla, false), hsla:hsla, rgb:cloneRGBA(rgba, false), rgba:rgba}]);
			},
			//Fix alpha value, if the user enters a wrong value
			fixAlpha = function (alpha) {
				return fixVal(isNaN(alpha) ? 1 : alpha, 0, 1);
			},
			//Remove alpha from hexadecimal, if alpha channel is disabled
			adaptHex = function (hex, cal) {
				if (hex === undefined) hex = '000000ff';
				if (!cal.data('wcolpick').enableAlpha) {
					hex = removeAlpha(hex);
				}
				return hex;
			},
			//Remove alpha value from hexadecimals/objects
			removeAlpha = function (col) {
				if (col !== undefined) {
					if (typeof col === 'string') {
						if (col.indexOf('#') != 0) {
							if (col.length == 4) col = col.substring(0,3);
							if (col.length == 8) col = col.substring(0,6);
						} else {
							if (col.length == 5) col = col.substring(0,4);
							if (col.length == 9) col = col.substring(0,7);
						}
					} else if (col.a !== undefined) col.a = 1;
				}
				return col;
			},
			//Clone color objects
			cloneRGBA = function (rgba, withAlpha) {
				if (rgba === undefined) return {r:0, g:0, b:0, a:1};
				if (withAlpha) {
					if (rgba.a === undefined) return {r:rgba.r, g:rgba.g, b:rgba.b, a:1};
					else return {r:rgba.r, g:rgba.g, b:rgba.b, a:rgba.a};
				} else return {r:rgba.r, g:rgba.g, b:rgba.b};
			},
			cloneHSBA = function (hsba, withAlpha) {
				if (hsba === undefined) return {h:0, s:0, b:0, a:1};
				if (withAlpha) {
					if (hsba.a === undefined) return {h:hsba.h, s:hsba.s, b:hsba.b, a:1};
					else return {h:hsba.h, s:hsba.s, b:hsba.b, a:hsba.a};
				} else return {h:hsba.h, s:hsba.s, b:hsba.b};
			},
			cloneHSLA = function (hsla, withAlpha) {
				if (hsla === undefined) return {h:0, s:0, l:0, a:1};
				if (withAlpha) {
					if (hsla.a === undefined) return {h:hsla.h, s:hsla.s, l:hsla.l, a:1};
					else return {h:hsla.h, s:hsla.s, l:hsla.l, a:hsla.a};
				} else return {h:hsla.h, s:hsla.s, l:hsla.l};
			},
			//Compare color objects
			compareHSBA = function (hsba1, hsba2) {
				if (hsba1 === undefined || hsba2 === undefined) return false;
				return (hsba1.h == hsba2.h && hsba1.s == hsba2.s && hsba1.b == hsba2.b && hsba1.a == hsba2.a);
			},
			//Shows/hides the color picker
			show = function (ev) {
				//Prevent the trigger of any direct parent
				if (ev) ev.stopPropagation();
				//cal is the color picker (dom object)
				var cal = $('#' + $(this).data('wcolpickId')), overridePos = {};
				//Trying to access to a property (e.g. color) and, if is generated an error, abort!
				try {var temp = cal.data('wcolpick').color;}
				catch (e) {return this;}
				//Polyfill fixes
				if (ev && !cal.data('wcolpick').polyfill) ev.preventDefault();
				//Fires onBeforeShow
				cal.data('wcolpick').onBeforeShow.apply(this, [{colorDiv:cal.get(0), el:cal.data('wcolpick').el, overridePos:overridePos}]);
				//If flat is true, simply shows the color picker!
				if (cal.data('wcolpick').flat) {
					//Fires onShow
					if (!(cal.data('wcolpick').onShow.apply(this, [{colorDiv:cal.get(0), el:cal.data('wcolpick').el}]) != false)) return this;
					//Shows the picker and terminates
					cal.show();
					return;
				}
				//Positions the color picker...
				if (overridePos.left === undefined || isNaN(overridePos.left) || overridePos.top === undefined || isNaN(overridePos.top)) {
					//Calculates the correctly position
					var finalPos = {top:0, left:0}, pos = cal.data('wcolpick').appendedToBody ? $(this).offset() : $(this).position();
					if (cal.data('wcolpick').position == 'center') { //... on center of viewport
						//Positions the color picker on top-left corner of viewport
						finalPos.top = pos.top - ($(this).offset().top - $(window).scrollTop());
						finalPos.left = pos.left - ($(this).offset().left - $(window).scrollLeft());
						//Positions the color picker on center of viewport by adding coordinates
						var centerViewport = {top:$(window).height()/2, left:$(window).width()/2};
						finalPos.top += centerViewport.top - cal.outerHeight()/2;
						finalPos.left += centerViewport.left - cal.outerWidth()/2;
					} else { //... automatically (default)
						//Positions the color picker under his related html object
						finalPos.top = pos.top + this.offsetHeight;
						finalPos.left = pos.left;
						//Fixes, if the color picker is showing outside of viewport
						if (outOfViewportHeight(cal, $(this), this) && $(this).offset().top - $(window).scrollTop() >= cal.outerHeight()) {
							finalPos.top -= (cal.outerHeight() + this.offsetHeight);
						}
						if (outOfViewportWidth(cal, $(this))) {
							if ($(this).offset().left - $(window).scrollLeft() + this.offsetWidth >= cal.outerWidth()) {
								finalPos.left -= (cal.outerWidth() - this.offsetWidth);
							} else {
								var leftMargin = $(this).offset().left - $(window).scrollLeft();
								var outWidth = leftMargin + cal.outerWidth() - $(window).width();
								if (leftMargin > outWidth) { finalPos.left -= outWidth; } else { finalPos.left -= leftMargin; }
							}
						}
					}
					//Applies the result
					cal.css({top: finalPos.top + 'px', left: finalPos.left + 'px'});
				} else {
					//Applies the user-defined position
					cal.css({top: overridePos.top + 'px', left: overridePos.left + 'px'});
				}
				//Fires onShow
				if (!(cal.data('wcolpick').onShow.apply(this, [{colorDiv:cal.get(0), el:cal.data('wcolpick').el}]) != false)) return this;
				//Shows the picker
				cal.show();
				//Hides when user clicks outside
				$('html').mousedown({cal:cal}, hide);
				cal.mousedown(function(ev){ev.stopPropagation();})
			},
			hide = function (ev) {
				var cal = $('#' + $(this).data('wcolpickId'));
				if (ev) cal = ev.data.cal;
				//Trying to access to a property (e.g. color) and, if is generated an error, abort!
				try {var temp = cal.data('wcolpick').color;}
				catch (e) {return this;}
				//Fires onHide
				if (!(cal.data('wcolpick').onHide.apply(this, [{colorDiv:cal.get(0), el:cal.data('wcolpick').el}]) != false)) return this;
				//Hides the picker
				cal.hide();
				$('html').off('mousedown', hide);
			},
			//Detect if the color picker is out of viewport
			outOfViewportHeight = function (cal, wrapEl, domEl) {
				var calViewTop = wrapEl.offset().top - $(window).scrollTop() + domEl.offsetHeight; //Top of the color picker in viewport
				var calHeight = cal.outerHeight(); //Height of the color picker
				var viewHeight = $(window).height(); //Viewport height
				return (calViewTop + calHeight > viewHeight);
			},
			outOfViewportWidth = function (cal, wrapEl) {
				var calViewLeft = wrapEl.offset().left - $(window).scrollLeft(); //Left of the color picker in viewport
				var calWidth = cal.outerWidth(); //Width of the color picker
				var viewWidth = $(window).width(); //Viewport width
				return (calViewLeft + calWidth > viewWidth);
			},
			//Destroys the color picker
			destroy = function (ev) {
				var cal = $('#' + $(this).data('wcolpickId'));
				if (ev) cal = ev.data.cal;
				//Fires onDestroy
				if (!(cal.data('wcolpick').onDestroy.apply(this, [{colorDiv:cal.get(0), el:cal.data('wcolpick').el}]) != false)) return this;
				//Destroys the picker
				cal.remove();
				//Prevent firing of hide event on a destroyed object! //bySetColor
				$('html').off('mousedown', hide);
			},
			//Generate a random unique id
			getUniqueID = (function () {
				var cnt = Math.round(Math.random() * 10000);
				return function () {
					cnt += 1;
					return cnt;
				};
			})(),
			//Used to detect if the browser in use is Microsoft Internet Explorer
			isInternetExplorer = function () {
				var isIE = (navigator.appName === 'Microsoft Internet Explorer');
				if (!isIE) return false;
				var UA = navigator.userAgent.toLowerCase();
				var IEver = parseFloat(UA.match( /msie ([0-9]{1,}[\.0-9]{0,})/ )[1]);
				var ngIE = (isIE && IEver < 10);
				return ngIE;
			};
		return {
			init: function (opt) {
				opt = $.extend({}, defaults, opt||{});
				//Set color
				if (typeof opt.color === 'string') opt.color = hexToHsba(opt.color);
				else if (opt.color.r !== undefined && opt.color.g !== undefined && opt.color.b !== undefined) opt.color = rgbaToHsba(fixRGBA(opt.color));
				else if (opt.color.h !== undefined && opt.color.s !== undefined && opt.color.b !== undefined) opt.color = fixHSBA(opt.color);
				else if (opt.color.h !== undefined && opt.color.s !== undefined && opt.color.l !== undefined) opt.color = hslaToHsba(fixHSLA(opt.color));
				else opt.color = {h:0, s:0, b:0, a:1}; //Black = Error color
				//Normalizes string options
				opt.arrowsColor = opt.arrowsColor.toLowerCase();
				opt.checkersColor = opt.checkersColor.toLowerCase();
				opt.colorScheme = opt.colorScheme.toLowerCase();
				opt.layout = opt.layout.toLowerCase();
				opt.position = opt.position.toLowerCase();
				opt.showEvent = opt.showEvent.toLowerCase();
				opt.submitColor = opt.submitColor.toLowerCase();
				opt.variant = opt.variant.toLowerCase();
				if (typeof opt.fieldsBackground === 'string') opt.fieldsBackground = opt.fieldsBackground.toLowerCase();
				if (typeof opt.submitBackground === 'string') opt.submitBackground = opt.submitBackground.toLowerCase();
				//For each selected DOM element
				return this.each(function () {
					//If the element does not have an ID
					if (!$(this).data('wcolpickId')) {
						var options = $.extend({}, opt);
						//Fixes color if alpha is disabled
						if (!opt.enableAlpha) opt.color = removeAlpha(opt.color);
						//Setup current color
						options.origColor = cloneHSBA(opt.color, true);
						// Set polyfill
						if (typeof opt.polyfill == 'function') options.polyfill = opt.polyfill(this);
						//Input field operations
						options.input = $(this).is('input');
						//Polyfill fixes
						if (options.polyfill && options.input && this.type === 'color') return;
						//Generate and assign a random ID
						var id = 'colorpicker_' + getUniqueID();
						$(this).data('wcolpickId', id);
						//Set the tpl's ID and get the HTML
						var cal = $(tpl).attr('id', id);
						//Setup size of the selected variant (Add other "else-if" for other future variants)
						if (options.variant == 'small') options.size = 160; //Small Version!
						else if (options.variant == 'extra-large') options.size = 300; //Extra Large Version!
						else options.size = 225; //Standard Version (default)!
						//Loading the choosen layout
						if (options.variant == 'small') { //Add class according to layout (small)
							cal.addClass('wcolpickS wcolpickS_'+options.layout+(options.enableSubmit?'':' wcolpickS_'+options.layout+'_ns'));
							if(!options.enableAlpha) cal.addClass('wcolpickS_noalpha wcolpickS_'+options.layout+'_noalpha'+(options.enableSubmit?'':' wcolpickS_'+options.layout+'_noalpha_ns')); //Disable alpha channel, if requested
						} else if (options.variant == 'extra-large') { //Add class according to layout (extra-large)
							cal.addClass('wcolpickXL wcolpickXL_'+options.layout+(options.enableSubmit?'':' wcolpickXL_'+options.layout+'_ns'));
							if(!options.enableAlpha) cal.addClass('wcolpickXL_noalpha wcolpickXL_'+options.layout+'_noalpha'+(options.enableSubmit?'':' wcolpickXL_'+options.layout+'_noalpha_ns')); //Disable alpha channel, if requested
						} else { //Add class according to layout (default -> standard)
							cal.addClass('wcolpick_'+options.layout+(options.enableSubmit?'':' wcolpick_'+options.layout+'_ns'));
							if(!options.enableAlpha) cal.addClass('wcolpick_noalpha wcolpick_'+options.layout+'_noalpha'+(options.enableSubmit?'':' wcolpick_'+options.layout+'_noalpha_ns')); //Disable alpha channel, if requested
						}
						//Loading Compact layout, if requested
						if (options.compactLayout) {
							if (options.variant == 'small') { //Add class according to layout (small)
								cal.addClass('wcolpickS_compact wcolpickS_compact_'+options.layout+(options.enableSubmit?'':' wcolpickS_compact_'+options.layout+'_ns'));
								if(!options.enableAlpha) cal.addClass('wcolpickS_compact_noalpha wcolpickS_compact_'+options.layout+'_noalpha'+(options.enableSubmit?'':' wcolpickS_compact_'+options.layout+'_noalpha_ns')); //Disable alpha channel, if requested
							} else if (options.variant == 'extra-large') { //Add class according to layout (extra-large)
								cal.addClass('wcolpickXL_compact wcolpickXL_compact_'+options.layout+(options.enableSubmit?'':' wcolpickXL_compact_'+options.layout+'_ns'));
								if(!options.enableAlpha) cal.addClass('wcolpickXL_compact_noalpha wcolpickXL_compact_'+options.layout+'_noalpha'+(options.enableSubmit?'':' wcolpickXL_compact_'+options.layout+'_noalpha_ns')); //Disable alpha channel, if requested
							} else { //Add class according to layout (default -> standard)
								cal.addClass('wcolpick_compact wcolpick_compact_'+options.layout+(options.enableSubmit?'':' wcolpick_compact_'+options.layout+'_ns'));
								if(!options.enableAlpha) cal.addClass('wcolpick_compact_noalpha wcolpick_compact_'+options.layout+'_noalpha'+(options.enableSubmit?'':' wcolpick_compact_'+options.layout+'_noalpha_ns')); //Disable alpha channel, if requested
							}
						}
						//Loading the choosen color scheme
						if (options.colorScheme.indexOf('light') == 0) { //All light color schemes start with "light"
							cal.addClass('wcolpick_light'); //Loading default light color scheme
							if(options.colorScheme != 'light') cal.addClass('wcolpick_'+options.colorScheme); //Loading light-based color scheme
							//INFO: You can implement light-based color schemes, in css, naming them: light-[name] (IMPORTANT: Use only lowercase names!)
						} else if (options.colorScheme.indexOf('dark') == 0) { //All dark color schemes start with "dark"
							cal.addClass('wcolpick_dark'); //Loading default dark color scheme
							if(options.colorScheme != 'dark') cal.addClass('wcolpick_'+options.colorScheme); //Loading dark-based color scheme
							//INFO: You can implement dark-based color schemes, in css, naming them: dark-[name] (IMPORTANT: Use only lowercase names!)
						} else { //If the scheme does not starts with "light" or "dark"
							cal.addClass('wcolpick_light'); //Loading default color scheme for all (light)
							cal.addClass('wcolpick_'+options.colorScheme); //Loading the "strange" color scheme
						}
						//Change color scheme for arrows, if requested
						if (options.arrowsColor == 'light') cal.addClass('wcolpick_lightArrs');
						else if (options.arrowsColor == 'dark') cal.addClass('wcolpick_darkArrs');
						//Change color scheme for checkerboards, if requested
						if (options.checkersColor == 'light') cal.addClass('wcolpick_lightCheckerboards');
						else if (options.checkersColor == 'dark') cal.addClass('wcolpick_darkCheckerboards');
						//Change color scheme for submit button, if requested
						if (options.submitColor == 'light') cal.addClass('wcolpick_lightSubmit');
						else if (options.submitColor == 'dark') cal.addClass('wcolpick_darkSubmit');
						//Hide outlines, if requested
						if (!options.colorSelOutline) cal.addClass('wcolpick_noCSOutline');
						if (!options.hueOutline) cal.addClass('wcolpick_noHOutline');
						if (!options.alphaOutline) cal.addClass('wcolpick_noAOutline');
						if (!options.colorOutline) cal.addClass('wcolpick_noNCOutline');
						//Set border width
						cal.css('border-width', options.border + 'px');
						//Setup submit button
						options.submit = cal.find('div.wcolpick_submit').click(clickSubmit);
						//Setup input fields
						options.fields = cal.find('input').change(change).keydown(keyDownFields).blur(blur).focus(focus);
						//If alpha channel is disabled, set hex field maxlength to 6
						if (!options.enableAlpha) options.fields.eq(0).prop('maxlength', 6);
						//Setup readonly attribute to fields
						for (var i = 0; i < 8; i++) options.fields.eq(i).prop('readonly', options.readonlyFields);
						if (options.readonlyHexField) options.fields.eq(0).prop('readonly', options.readonlyHexField);
						//Setup color of fields, submit button, external border, and background (if a color is different than default, it will override the default color)
						if (options.fieldsBackground != 'default') {
							var colstr = encodeToCSS(options.fieldsBackground);
							for (var i = 0; i < 8; i++) options.fields.eq(i).parent().css('background',colstr);
						}
						if (options.submitBackground != 'default') options.submit.css('background',encodeToCSS(options.submitBackground));
						if (options.backgroundColor != 'default') cal.css('background',encodeToCSS(options.backgroundColor));
						if (options.borderColor != 'default') cal.css('borderColor',encodeToCSS(options.borderColor));
						//Setup restoreOriginal to current color's click event
						cal.find('div.wcolpick_field_arrs').mousedown(downIncrement).end().find('div.wcolpick_current_color').click(restoreOriginal);
						//Setup color selector
						options.selector = cal.find('div.wcolpick_color').on('mousedown touchstart',downSelector);
						options.selectorIndic = options.selector.find('div.wcolpick_selector_outer');
						//Setup hue bar and alpha bar
						options.el = this;
						options.hue = cal.find('div.wcolpick_hue_arrs');
						options.hueBar = cal.find('div.wcolpick_hue_overlay');
						options.alpha = cal.find('div.wcolpick_alpha_arrs');
						options.alphaBar = cal.find('div.wcolpick_alpha_overlay');
						//Painting hue bar
						var stops = ['#ff0000','#ff0080','#ff00ff','#8000ff','#0000ff','#0080ff','#00ffff','#00ff80','#00ff00','#80ff00','#ffff00','#ff8000','#ff0000'];
						if (isInternetExplorer()) { //Compatibility with IE 6-9
							var i, div;
							for (i=0; i<=11; i++) {
								div = $('<div></div>').attr('style','height:8.333333%; filter:progid:DXImageTransform.Microsoft.gradient(GradientType=0,startColorstr='+stops[i]+',endColorstr='+stops[i+1]+'); -ms-filter:"progid:DXImageTransform.Microsoft.gradient(GradientType=0,startColorstr='+stops[i]+',endColorstr='+stops[i+1]+')";');
								options.hueBar.append(div);
							}
						} else {
							var stopList = stops.join(',');
							options.hueBar.attr('style','background:-webkit-linear-gradient(top,'+stopList+'); background:-moz-linear-gradient(top,'+stopList+'); background:-ms-linear-gradient(top,'+stopList+'); background:-o-linear-gradient(top,'+stopList+'); background:linear-gradient(to bottom,'+stopList+');');
						}
						//Setup remaining events, new, and current color
						cal.find('div.wcolpick_hue').on('mousedown touchstart',downHue);
						cal.find('div.wcolpick_alpha').on('mousedown touchstart',downAlpha);
						options.newColor = cal.find('div.wcolpick_new_color');
						options.currentColor = cal.find('div.wcolpick_current_color');
						//Store options
						cal.data('wcolpick', options);
						//Fill with default color
						var rgba = hsbaToRgba(options.color);
						fillHSBFields(options.color, cal.get(0));
						fillAlphaField(options.color, cal.get(0));
						fillRGBFields(rgba, cal.get(0));
						fillHexField(rgbaToHex(rgba), cal.get(0));
						setSelectorPos(options.color, cal.get(0));
						setSelectorColor(options.color, cal.get(0));
						setHuePos(options.color, cal.get(0));
						setAlphaPos(options.color, cal.get(0));
						setAlphaColor(rgba, cal.get(0));
						setCurrentColor(rgba, cal.get(0));
						setNewColor(rgba, cal.get(0));
						//Append to parent if flat=false, else show in place
						if (options.flat) {
							cal.appendTo(this).show();
							cal.css({position: 'relative', display: 'block'});
						} else {
							cal.data('wcolpick').appendedToBody = options.appendToBody;
							if (!options.appendToBody) cal.appendTo($(this).parent());
							else cal.appendTo(document.body);
							$(this).on(options.showEvent, show);
							cal.css({position: 'absolute'});
						}
						//Loading completed
						cal.data('wcolpick').onLoaded.apply(cal.parent(), [{colorDiv:cal.get(0), el:cal.data('wcolpick').el}]);
					}
				});
			},
			//Shows the picker
			showColpick: function() {
				return this.each( function () {
					if ($(this).data('wcolpickId')) {
						show.apply(this);
					}
				});
			},
			//Hides the picker
			hideColpick: function() {
				return this.each( function () {
					if ($(this).data('wcolpickId')) {
						hide.apply(this);
					}
				});
			},
			//Destroys the picker
			destroyColpick: function() {
				return this.each( function () {
					if ($(this).data('wcolpickId')) {
						destroy.apply(this);
					}
				});
			},
			//Sets a color as new and current (Default: Set only as new color)
			setColpickColor: function(col, setCurrent) {
				if (col !== undefined) { //If color is undefined, do nothing!
					if (typeof col === 'string') col = hexToHsba(col);
					else if (col.r !== undefined && col.g !== undefined && col.b !== undefined) col = rgbaToHsba(fixRGBA(col));
					else if (col.h !== undefined && col.s !== undefined && col.b !== undefined) col = fixHSBA(col);
					else if (col.h !== undefined && col.s !== undefined && col.l !== undefined) col = hslaToHsba(fixHSLA(col));
					else return this; //If color is not recognized, do nothing!
					if (setCurrent === undefined) setCurrent = false; //Default: Set only as new color
					return this.each(function(){
						if ($(this).data('wcolpickId')) {
							var cal = $('#' + $(this).data('wcolpickId'));
							//Fixes color if alpha is disabled
							if (!cal.data('wcolpick').enableAlpha) col = removeAlpha(col);
							//Check if the color is actually changed and, if is true, do nothing!
							if (setCurrent) { if (compareHSBA(col, cal.data('wcolpick').color) && compareHSBA(col, cal.data('wcolpick').origColor)) return this; }
							else { if (compareHSBA(col, cal.data('wcolpick').color)) return this; }
							//Setup new color
							cal.data('wcolpick').color = cloneHSBA(col, true);
							var rgba = hsbaToRgba(col);
							var hex = rgbaToHex(rgba);
							//Applies color to all elements
							fillHSBFields(col, cal.get(0));
							fillAlphaField(col, cal.get(0));
							fillRGBFields(rgba, cal.get(0));
							fillHexField(hex, cal.get(0));
							setSelectorPos(col, cal.get(0));
							setSelectorColor(col, cal.get(0));
							setHuePos(col, cal.get(0));
							setAlphaPos(col, cal.get(0));
							setAlphaColor(rgba, cal.get(0));
							setNewColor(rgba, cal.get(0));
							//If setCurrent is "true", sets the color as current
							if (setCurrent) {
								cal.data('wcolpick').origColor = cloneHSBA(col, true);
								setCurrentColor(rgba, cal.get(0));
							}
							//Fires onChange (bySetColor = true)
							var hsla = hsbaToHsla(col);
							cal.data('wcolpick').onChange.apply(cal.parent(), [{bySetColor:true, colorDiv:cal.get(0), el:cal.data('wcolpick').el, hex:hex.substring(0,6), hexa:hex, hsb:cloneHSBA(col, false), hsba:col, hsl:cloneHSLA(hsla, false), hsla:hsla, rgb:cloneRGBA(rgba, false), rgba:rgba}]);
						}
					});
				}
			},
			//Returns the selected color (Default: Hsb color with alpha value, and get new color (not current))
			getColpickColor: function(type, getCurrent) {
				var cal = $('#' + $(this).data('wcolpickId'));
				if (getCurrent === undefined) getCurrent = false; //Default: Get new color (not current)
				if (type === undefined) type = 'hsba'; //Default: Hsb color with alpha value
				var withAlpha = (type.indexOf('a') != -1);
				//Getting the color
				var col = getCurrent ? cloneHSBA(cal.data('wcolpick').origColor, true) : cloneHSBA(cal.data('wcolpick').color, true);
				if (type.indexOf('rgb') != -1) {
					var rgba = hsbaToRgba(col);
					return withAlpha ? {r:rgba.r, g:rgba.g, b:rgba.b, a:rgba.a} : {r:rgba.r, g:rgba.g, b:rgba.b};
				} else if (type.indexOf('hsl') != -1) {
					var hsla = hsbaToHsla(col);
					return withAlpha ? {h:hsla.h, s:hsla.s, l:hsla.l, a:hsla.a} : {h:hsla.h, s:hsla.s, l:hsla.l};
				} else if (type.indexOf('hex') != -1) return withAlpha ? hsbaToHex(col) : hsbaToHex(col).substring(0,6);
				else return withAlpha ? {h:col.h, s:col.s, b:col.b, a:col.a} : {h:col.h, s:col.s, b:col.b};
			}
		};
	}();
	//Color space convertions
	var hexToRgba = function (hex) {
		if (hex === undefined) return {r:0, g:0, b:0, a:1};
		if (hex.indexOf('#') == 0) hex = hex.substring(1);
		if (isValidHex(hex)) {
			if (hex.length == 3) hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2] + 'ff';
			else if (hex.length == 4) hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2] + hex[3] + hex[3];
			else if (hex.length == 6) hex = hex + 'ff';
			else if (hex.length != 8) return {r:0, g:0, b:0, a:1};
		} else { return {r:0, g:0, b:0, a:1}; }
		var hexI = parseInt(hex,16);
		var rgba = {r: hexI >>> 24, g: (hexI & 0x00FF0000) >>> 16, b: (hexI & 0x0000FF00) >>> 8, a: (hexI & 0x000000FF) / 255};
		return rgba;
	};
	var hexToHsba = function (hex) {
		return rgbaToHsba(hexToRgba(hex));
	};
	var hexToHsla = function (hex) {
		return rgbaToHsla(hexToRgba(hex));
	};
	var rgbaToHex = function (rgba) {
		if (rgba === undefined) return '000000ff';
		if (rgba.a === undefined) rgba.a = 1;
		var a = Math.round(rgba.a * 255);
		var hex = [ rgba.r.toString(16), rgba.g.toString(16), rgba.b.toString(16), a.toString(16) ];
		$.each(hex, function (nr, val) {
			if (val.length == 1) hex[nr] = '0' + val;
		});
		return hex.join('');
	};
	var rgbaToHsba = function (rgba) {
		if (rgba === undefined) return {h:0, s:0, b:0, a:1};
		if (rgba.a === undefined) rgba.a = 1;
		var r = rgba.r / 255, g = rgba.g / 255, b = rgba.b / 255;
		var min = Math.min(r, Math.min(g, b));
		var max = Math.max(r, Math.max(g, b));
		var delta = max - min;
		var brightness = max;
		var saturation = max != 0 ? delta / max : 0;
		var hue = delta != 0 ? (r == max ? (g - b) / delta : g == max ? ((b - r) / delta) + 2 : ((r - g) / delta) + 4) * 60 : 0;
		if (hue < 0) hue += 360;
		return fixHSBA({h: hue, s: saturation * 100, b: brightness * 100, a: rgba.a});
	};
	var rgbaToHsla = function (rgba) {
		if (rgba === undefined) return {h:0, s:0, l:0, a:1};
		if (rgba.a === undefined) rgba.a = 1;
		var r = rgba.r / 255, g = rgba.g / 255, b = rgba.b / 255;
		var min = Math.min(r, Math.min(g, b));
		var max = Math.max(r, Math.max(g, b));
		var delta = max - min;
		var lightness = (max + min) / 2;
		var saturation = delta != 0 ? delta / (1 - Math.abs(max + min - 1)) : 0;
		var hue = delta != 0 ? (r == max ? (g - b) / delta : g == max ? ((b - r) / delta) + 2 : ((r - g) / delta) + 4) * 60 : 0;
		if (hue < 0) hue += 360;
		return fixHSLA({h: hue, s: saturation * 100, l: lightness * 100, a: rgba.a});
	};
	var hsbaToHex = function (hsba) {
		return rgbaToHex(hsbaToRgba(hsba));
	};
	var hsbaToRgba = function (hsba) {
		if (hsba === undefined) return {r:0, g:0, b:0, a:1};
		if (hsba.a === undefined) hsba.a = 1;
		var hsbaL = {h: hsba.h, s: hsba.s / 100, b: hsba.b / 100, a: hsba.a};
		var red, green, blue;
		if (hsbaL.s == 0) red = green = blue = hsbaL.b;
		else
		{
			var t1 = hsbaL.b;
			var t2 = (1 - hsbaL.s) * hsbaL.b;
			var t3 = (t1 - t2) * (hsbaL.h % 60) / 60;
			if (hsbaL.h < 60 || hsbaL.h == 360) { red = t1; blue = t2; green = t2 + t3; }
			else if (hsbaL.h < 120) { green = t1; blue = t2; red = t1 - t3; }
			else if (hsbaL.h < 180) { green = t1; red = t2; blue = t2 + t3; }
			else if (hsbaL.h < 240) { blue = t1; red = t2; green = t1 - t3; }
			else if (hsbaL.h < 300) { blue = t1; green = t2; red = t2 + t3; }
			else { red = t1; green = t2; blue = t1 - t3; }
		}
		return fixRGBA({r: Math.round(red * 255), g: Math.round(green * 255), b: Math.round(blue * 255), a: hsbaL.a});
	};
	var hsbaToHsla = function (hsba) {
		if (hsba === undefined) return {h:0, s:0, l:0, a:1};
		if (hsba.a === undefined) hsba.a = 1;
		var hsbaL = {h: hsba.h, s: hsba.s / 100, b: hsba.b / 100, a: hsba.a};
		var lightness = hsbaL.b * (2 - hsbaL.s) / 2;
		var saturation = lightness != 0 && lightness != 1 ? hsba.b * hsba.s / (1 - Math.abs((2 * lightness) - 1)) : 0;
		return fixHSLA({h: hsbaL.h, s: saturation * 100, l: lightness * 100, a: hsbaL.a});
	};
	var hslaToHex = function (hsla) {
		return rgbaToHex(hslaToRgba(hsla));
	};
	var hslaToRgba = function (hsla) {
		if (hsla === undefined) return {r:0, g:0, b:0, a:1};
		if (hsla.a === undefined) hsla.a = 1;
		var hslaL = {h: hsla.h, s: hsla.s / 100, l: hsla.l / 100, a: hsla.a};
		var red, green, blue;
		var c = (1 - Math.abs(2 * hslaL.l - 1)) * hslaL.s;
		var x = c * (1 - Math.abs((hslaL.h / 60 % 2) - 1));
		var m = hslaL.l - (c / 2);
		if (hslaL.h < 60 || hslaL.h == 360) { red = c + m; green = x + m; blue = m; }
		else if (hslaL.h < 120) { red = x + m; green = c + m; blue = m; }
		else if (hslaL.h < 180) { red = m; green = c + m; blue = x + m; }
		else if (hslaL.h < 240) { red = m; green = x + m; blue = c + m; }
		else if (hslaL.h < 300) { red = x + m; green = m; blue = c + m; }
		else { red = c + m; green = m; blue = x + m; }
		return fixRGBA({r: Math.round(red * 255), g: Math.round(green * 255), b: Math.round(blue * 255), a: hslaL.a});
	};
	var hslaToHsba = function (hsla) {
		if (hsla === undefined) return {h:0, s:0, b:0, a:1};
		if (hsla.a === undefined) hsla.a = 1;
		var hslaL = {h: hsla.h, s: hsla.s / 100, l: hsla.l / 100, a: hsla.a};
		var brightness = ((2 * hslaL.l) + (hslaL.s * (1 - Math.abs((2 * hslaL.l) - 1)))) / 2;
		var saturation = brightness != 0 ? 2 * (brightness - hslaL.l) / brightness : 0;
		return fixHSBA({h: hslaL.h, s: saturation * 100, b: brightness * 100, a: hslaL.a});
	};
	//Check if a string is a valid hexadecimal string
	var isValidHex = function (hex) {
		if (hex === undefined) return false;
		while (hex.indexOf('0') == 0) hex = hex.substring(1);
		if(hex == '') hex = '0';
		return (parseInt(hex,16).toString(16) === hex.toLowerCase());
	};
	//Fix the values, if the user enters a wrong value
	var fixRGBA = function (rgba) {
		if (rgba === undefined) return {r:0, g:0, b:0, a:1};
		return {
			r: fixVal(isNaN(rgba.r) ? 0 : rgba.r, 0, 255),
			g: fixVal(isNaN(rgba.g) ? 0 : rgba.g, 0, 255),
			b: fixVal(isNaN(rgba.b) ? 0 : rgba.b, 0, 255),
			a: fixVal(isNaN(rgba.a) ? 1 : rgba.a, 0, 1)
		};
	};
	var fixHSBA = function (hsba) {
		if (hsba === undefined) return {h:0, s:0, b:0, a:1};
		return {
			h: fixVal(isNaN(hsba.h) ? 0 : hsba.h, 0, 360),
			s: fixVal(isNaN(hsba.s) ? 0 : hsba.s, 0, 100),
			b: fixVal(isNaN(hsba.b) ? 0 : hsba.b, 0, 100),
			a: fixVal(isNaN(hsba.a) ? 1 : hsba.a, 0, 1)
		};
	};
	var fixHSLA = function (hsla) {
		if (hsla === undefined) return {h:0, s:0, l:0, a:1};
		return {
			h: fixVal(isNaN(hsla.h) ? 0 : hsla.h, 0, 360),
			s: fixVal(isNaN(hsla.s) ? 0 : hsla.s, 0, 100),
			l: fixVal(isNaN(hsla.l) ? 0 : hsla.l, 0, 100),
			a: fixVal(isNaN(hsla.a) ? 1 : hsla.a, 0, 1)
		};
	};
	var fixVal = function (val, min, max) {
		return val >= max ? max : val <= min ? min : val;
	};
	//Converts a color object in a css color string
	var encodeToCSS = function (colobj) {
		if (colobj === undefined) return 'rgb(0,0,0)';
		if (colobj.r !== undefined && colobj.g !== undefined && colobj.b !== undefined) {
			var rgba = fixRGBA(colobj);
			return 'rgba('+rgba.r+','+rgba.g+','+rgba.b+','+rgba.a+')';
		} else if (colobj.h !== undefined && colobj.s !== undefined && colobj.l !== undefined) {
			var hsla = fixHSLA(colobj);
			return 'hsla('+hsla.h+','+hsla.s+'%,'+hsla.l+'%,'+hsla.a+')';
		} else if (colobj.h !== undefined && colobj.s !== undefined && colobj.b !== undefined) {
			var hsla = hsbaToHsla(fixHSBA(colobj));
			return 'hsla('+hsla.h+','+hsla.s+'%,'+hsla.l+'%,'+hsla.a+')';
		} else if (typeof colobj === 'string') {
			return colobj; //If colobj is a string, returns the string untouched (maybe is a string like "green", "blue", "black", ...).
		} else return 'rgb(0,0,0)';
	};
	//Converts a css color string in a color object
	var decodeFromCSS = function (colstr) {
		if (colstr === undefined) return {r:0, g:0, b:0, a:1};
		if (typeof colstr !== 'string') colstr = colstr.toString();
		if (colstr.indexOf('rgb') != -1) {
			var elems = colstr.substring(colstr.indexOf('(')+1, colstr.indexOf(')')).split(',');
			return fixRGBA({r:parseInt(elems[0]), g:parseInt(elems[1]), b:parseInt(elems[2]), a:parseFloat(elems[3])});
		} else if (colstr.indexOf('hsl') != -1) {
			var elems = colstr.substring(colstr.indexOf('(')+1, colstr.indexOf(')')).split(',');
			return fixHSLA({h:parseFloat(elems[0]), s:parseFloat(elems[1]), l:parseFloat(elems[2]), a:parseFloat(elems[3])});
		} else {
			return hexToHsba(colstr); //Tries to treat the unidentified string as an hexadecimal string, and, in case, returns an hsba object (ready for input).
		}
	};
	//External accessible functions
	$.fn.extend({
		loads: wcolpick.init,
		shows: wcolpick.showColpick,
		hides: wcolpick.hideColpick,
		destroys: wcolpick.destroyColpick,
		setColor: wcolpick.setColpickColor,
		getColor: wcolpick.getColpickColor
	});
	$.extend({
		wcolpick:{
			hexToRgba: hexToRgba,
			hexToHsba: hexToHsba,
			hexToHsla: hexToHsla,
			rgbaToHex: rgbaToHex,
			rgbaToHsba: rgbaToHsba,
			rgbaToHsla: rgbaToHsla,
			hsbaToHex: hsbaToHex,
			hsbaToRgba: hsbaToRgba,
			hsbaToHsla: hsbaToHsla,
			hslaToHex: hslaToHex,
			hslaToRgba: hslaToRgba,
			hslaToHsba: hslaToHsba,
			isValidHex: isValidHex,
			encodeToCSS: encodeToCSS,
			decodeFromCSS: decodeFromCSS
		}
	});
})(jQuery);
