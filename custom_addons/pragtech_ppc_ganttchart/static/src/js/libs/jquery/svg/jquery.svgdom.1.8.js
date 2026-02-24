/* http://keith-wood.name/svg.html
 jQuery DOM compatibility for jQuery SVG v1.4.5.
 Written by Keith Wood (kbwood{at}iinet.com.au) April 2009.
 Dual licensed under the GPL (http://dev.jquery.com/browser/trunk/jquery/GPL-LICENSE.txt) and
 MIT (http://dev.jquery.com/browser/trunk/jquery/MIT-LICENSE.txt) licenses.
 Please attribute the author if you use it. */

(function ($) { // Hide scope, no $ conflict

  var rclass = /[\t\r\n]/g,
    rspace = /\s+/,
    rwhitespace = "[\\x20\\t\\r\\n\\f]";

  /* Support adding class names to SVG nodes. */
  $.fn.addClass = function (origAddClass) {
    return function (value) {
      var classNames, i, l, elem,
        setClass, c, cl;

      if (jQuery.isFunction(value)) {
        return this.each(function (j) {
          jQuery(this).addClass(value.call(this, j, this.className));
        });
      }

      if (value && typeof value === "string") {
        classNames = value.split(rspace);

        for (i = 0, l = this.length; i < l; i++) {
          elem = this[ i ];

          if (elem.nodeType === 1) {
            if (!(elem.className && elem.getAttribute('class')) && classNames.length === 1) {
              if ($.svg.isSVGElem(elem)) {
                (elem.className ? elem.className.baseVal = value
                  : elem.setAttribute('class', value));
              } else {
                elem.className = value;
              }
            } else {
              setClass = !$.svg.isSVGElem(elem) ? elem.className :
                elem.className ? elem.className.baseVal :
                  elem.getAttribute('class');

              setClass = (" " + setClass + " ");
              for (c = 0, cl = classNames.length; c < cl; c++) {
                if (setClass.indexOf(" " + classNames[ c ] + " ") < 0) {
                  setClass += classNames[ c ] + " ";
                }
              }

              setClass = jQuery.trim(setClass);
              if ($.svg.isSVGElem(elem)) {

                (elem.className ? elem.className.baseVal = setClass
                  : elem.setAttribute('class', setClass));
              } else {
                elem.className = setClass;
              }
            }
          }
        }
      }

      return this;
    };
  }($.fn.addClass);

  /* Support removing class names from SVG nodes. */
  $.fn.removeClass = function (origRemoveClass) {
    return function (value) {
      var classNames, i, l, elem, className, c, cl;

      if (jQuery.isFunction(value)) {
        return this.each(function (j) {
          jQuery(this).removeClass(value.call(this, j, this.className));
        });
      }

      if ((value && typeof value === "string") || value === undefined) {
        classNames = ( value || "" ).split(rspace);

        for (i = 0, l = this.length; i < l; i++) {
          elem = this[ i ];

          if (elem.nodeType === 1 && (elem.className || elem.getAttribute('class'))) {
            if (value) {
              className = !$.svg.isSVGElem(elem) ? elem.className :
                elem.className ? elem.className.baseVal :
                  elem.getAttribute('class');

              className = (" " + className + " ").replace(rclass, " ");

              for (c = 0, cl = classNames.length; c < cl; c++) {
                // Remove until there is nothing to remove,
                while (className.indexOf(" " + classNames[ c ] + " ") >= 0) {
                  className = className.replace(" " + classNames[ c ] + " ", " ");
                }
              }

              className = jQuery.trim(className);
            } else {
              className = "";
            }

            if ($.svg.isSVGElem(elem)) {
              (elem.className ? elem.className.baseVal = className
                : elem.setAttribute('class', className));
            } else {
              elem.className = className;
            }
          }
        }
      }

      return this;
    };
  }($.fn.removeClass);

  /* Support toggling class names on SVG nodes. */
  $.fn.toggleClass = function (origToggleClass) {
    return function (className, state) {
      return this.each(function () {
        if ($.svg.isSVGElem(this)) {
          if (typeof state !== 'boolean') {
            state = !$(this).hasClass(className);
          }
          $(this)[(state ? 'add' : 'remove') + 'Class'](className);
        }
        else {
          origToggleClass.apply($(this), [className, state]);
        }
      });
    };
  }($.fn.toggleClass);

  /* Support checking class names on SVG nodes. */
  $.fn.hasClass = function (origHasClass) {
    return function (selector) {

      var className = " " + selector + " ",
        i = 0,
        l = this.length,
        elem, classes;

      for (; i < l; i++) {
        elem = this[i];
        if (elem.nodeType === 1) {
          classes = !$.svg.isSVGElem(elem) ? elem.className :
            elem.className ? elem.className.baseVal :
              elem.getAttribute('class');
          if ((" " + classes + " ").replace(rclass, " ").indexOf(className) > -1) {
            return true;
          }
        }
      }

      return false;
    };
  }($.fn.hasClass);

  /* Support attributes on SVG nodes. */
  $.fn.attr = function (origAttr) {
    return function (name, value, type) {
      var origArgs = arguments;
      if (typeof name === 'string' && value === undefined) {
        var val = origAttr.apply(this, origArgs);
        if (val && val.baseVal && val.baseVal.numberOfItems != null) { // Multiple values
          value = '';
          val = val.baseVal;
          if (name == 'transform') {
            for (var i = 0; i < val.numberOfItems; i++) {
              var item = val.getItem(i);
              switch (item.type) {
                case 1:
                  value += ' matrix(' + item.matrix.a + ',' + item.matrix.b + ',' +
                    item.matrix.c + ',' + item.matrix.d + ',' +
                    item.matrix.e + ',' + item.matrix.f + ')';
                  break;
                case 2:
                  value += ' translate(' + item.matrix.e + ',' + item.matrix.f + ')';
                  break;
                case 3:
                  value += ' scale(' + item.matrix.a + ',' + item.matrix.d + ')';
                  break;
                case 4:
                  value += ' rotate(' + item.angle + ')';
                  break; // Doesn't handle new origin
                case 5:
                  value += ' skewX(' + item.angle + ')';
                  break;
                case 6:
                  value += ' skewY(' + item.angle + ')';
                  break;
              }
            }
            val = value.substring(1);
          }
          else {
            val = val.getItem(0).valueAsString;
          }
        }
        return (val && val.baseVal ? val.baseVal.valueAsString : val);
      }

      var options = name;
      if (typeof name === 'string') {
        options = {};
        options[name] = value;
      }
      return $(this).each(function () {
        if ($.svg.isSVGElem(this)) {
          for (var n in options) {
            var val = ($.isFunction(options[n]) ? options[n]() : options[n]);
            (type ? this.style[n] = val : this.setAttribute(n, val));
          }
        }
        else {
          origAttr.apply($(this), origArgs);
        }
      });
    };
  }($.fn.attr);

  /* Support removing attributes on SVG nodes. */
  $.fn.removeAttr = function (origRemoveAttr) {
    return function (name) {
      return this.each(function () {
        if ($.svg.isSVGElem(this)) {
          (this[name] && this[name].baseVal ? this[name].baseVal.value = '' :
            this.setAttribute(name, ''));
        }
        else {
          origRemoveAttr.apply($(this), [name]);
        }
      });
    };
  }($.fn.removeAttr);

  /* Add numeric only properties. */
  $.extend($.cssNumber, {
    'stopOpacity':     true,
    'strokeMitrelimit':true,
    'strokeOpacity':   true
  });

  /* Support retrieving CSS/attribute values on SVG nodes. */
  if ($.cssProps) {
    $.css = function (origCSS) {
      return function (elem, name, numeric, extra) {
        var value = (name.match(/^svg.*/) ? $(elem).attr($.cssProps[name] || name) : '');
        return value || origCSS(elem, name, numeric, extra);
      };
    }($.css);
  }

  $.find.isXML = function (origIsXml) {
    return function (elem) {
      return $.svg.isSVGElem(elem) || origIsXml(elem);
    }
  }($.find.isXML)

  var div = document.createElement('div');
  div.appendChild(document.createComment(''));
  if (div.getElementsByTagName('*').length > 0) { // Make sure no comments are found
    $.expr.find.TAG = function (match, context) {
      var results = context.getElementsByTagName(match[1]);
      if (match[1] === '*') { // Filter out possible comments
        var tmp = [];
        for (var i = 0; results[i] || results.item(i); i++) {
          if ((results[i] || results.item(i)).nodeType === 1) {
            tmp.push(results[i] || results.item(i));
          }
        }
        results = tmp;
      }
      return results;
    };
  }

  $.expr.filter.CLASS = function (className) {
    var pattern = new RegExp("(^|" + rwhitespace + ")" + className + "(" + rwhitespace + "|$)");
    return function (elem) {
      var elemClass = (!$.svg.isSVGElem(elem) ? elem.className || (typeof elem.getAttribute !== "undefined" && elem.getAttribute("class")) || "" :
        (elem.className ? elem.className.baseVal : elem.getAttribute('class')));

      return pattern.test(elemClass);
    };
  };

  /*
   In the removeData function (line 1881, v1.7.2):

   if ( jQuery.support.deleteExpando ) {
   delete elem[ internalKey ];
   } else {
   try { // SVG
   elem.removeAttribute( internalKey );
   } catch (e) {
   elem[ internalKey ] = null;
   }
   }

   In the event.add function (line 2985, v1.7.2):

   if ( !special.setup || special.setup.call( elem, data, namespaces, eventHandle ) === false ) {
   // Bind the global event handler to the element
   try { // SVG
   elem.addEventListener( type, eventHandle, false );
   } catch(e) {
   if ( elem.attachEvent ) {
   elem.attachEvent( "on" + type, eventHandle );
   }
   }
   }

   In the event.remove function (line 3074, v1.7.2):

   if ( !special.teardown || special.teardown.call( elem, namespaces ) === false ) {
   try { // SVG
   elem.removeEventListener(type, elemData.handle, false);
   }
   catch (e) {
   if (elem.detachEvent) {
   elem.detachEvent("on" + type, elemData.handle);
   }
   }
   }

   In the event.fix function (line 3394, v1.7.2):

   if (event.target.namespaceURI == 'http://www.w3.org/2000/svg') { // SVG
   event.button = [1, 4, 2][event.button];
   }

   // Add which for click: 1 === left; 2 === middle; 3 === right
   // Note: button is not normalized, so don't use it
   if ( !event.which && button !== undefined ) {
   event.which = ( button & 1 ? 1 : ( button & 2 ? 3 : ( button & 4 ? 2 : 0 ) ) );
   }

   In the Sizzle function (line 4083, v1.7.2):

   if ( toString.call(checkSet) === "[object Array]" ) {
   if ( !prune ) {
   results.push.apply( results, checkSet );

   } else if ( context && context.nodeType === 1 ) {
   for ( i = 0; checkSet[i] != null; i++ ) {
   if ( checkSet[i] && (checkSet[i] === true || checkSet[i].nodeType === 1 && Sizzle.contains(context, checkSet[i])) ) {
   results.push( set[i] || set.item(i) ); // SVG
   }
   }

   } else {
   for ( i = 0; checkSet[i] != null; i++ ) {
   if ( checkSet[i] && checkSet[i].nodeType === 1 ) {
   results.push( set[i] || set.item(i) ); // SVG
   }
   }
   }
   } else {...

   In the fallback for the Sizzle makeArray function (line 4877, v1.7.2):

   if ( toString.call(array) === "[object Array]" ) {
   Array.prototype.push.apply( ret, array );

   } else {
   if ( typeof array.length === "number" ) {
   for ( var l = array.length; i &lt; l; i++ ) {
   ret.push( array[i] || array.item(i) ); // SVG
   }

   } else {
   for ( ; array[i]; i++ ) {
   ret.push( array[i] );
   }
   }
   }

   In the jQuery.cleandata function (line 6538, v1.7.2):

   if ( deleteExpando ) {
   delete elem[ jQuery.expando ];

   } else {
   try { // SVG
   elem.removeAttribute( jQuery.expando );
   } catch (e) {
   // Ignore
   }
   }

   In the fallback getComputedStyle function (line 6727, v1.7.2):

   defaultView = (elem.ownerDocument ? elem.ownerDocument.defaultView : elem.defaultView); // SVG
   if ( defaultView &&
   (computedStyle = defaultView.getComputedStyle( elem, null )) ) {

   ret = computedStyle.getPropertyValue( name );
   ...

   */

})(jQuery);