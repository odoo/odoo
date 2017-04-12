odoo.define('web.libs', function () {
"use strict";

/**
 * External Libraries Customization
 *
 * This is the place where we do some slightly crappy libraries customization.
 * We are not proud of this, but at least, we try to avoid patching them in
 * place.
 *
 * In an ideal world, this file would not be needed, because external libraries
 * would not have bugs, their APIS would be done in a way that we could use them
 * as is, and their distribution process would make sure that they are properly
 * configured.  However, we do not live in such a world, so this file is
 * necessary.
 */

// nvd3 customization
//-------------------------------------------------------------------------
if ('nv' in window) {
    nv.dev = false;  // sets nvd3 library in production mode

    // monkey patch nvd3 to allow removing eventhandler on windowresize events
    // see https://github.com/novus/nvd3/pull/396 for more details

    // Adds a resize listener to the window.
    nv.utils.onWindowResize = function(fun) {
        if (fun === null) return;
        window.addEventListener('resize', fun);
    };

    // Backwards compatibility with current API.
    nv.utils.windowResize = nv.utils.onWindowResize;

    // Removes a resize listener from the window.
    nv.utils.offWindowResize = function(fun) {
        if (fun === null) return;
        window.removeEventListener('resize', fun);
    };

    // monkey patch nvd3 to prevent crashes when user changes view and nvd3
    // tries to remove tooltips after 500 ms...  seriously nvd3, what were you
    // thinking?
    nv.tooltip.cleanup = function () {
        $('.nvtooltip').remove();
    };

    // monkey patch nvd3 to prevent it to display a tooltip (position: absolute)
    // with a negative `top`; with this patch the highest tooltip's position is
    // still in the graph
    var originalCalcTooltipPosition = nv.tooltip.calcTooltipPosition;
    nv.tooltip.calcTooltipPosition = function () {
        var container = originalCalcTooltipPosition.apply(this, arguments);
        container.style.top = container.style.top.split('px')[0] < 0 ? 0 + 'px' : container.style.top;
        return container;
    };
}

// Bootstrap customization
//-------------------------------------------------------------------------
/* Bootstrap defaults overwrite */
$.fn.tooltip.Constructor.DEFAULTS.placement = 'auto top';
$.fn.tooltip.Constructor.DEFAULTS.html = true;
$.fn.tooltip.Constructor.DEFAULTS.trigger = 'hover focus click';
$.fn.tooltip.Constructor.DEFAULTS.container = 'body';
$.fn.tooltip.Constructor.DEFAULTS.delay = { show: 1000, hide: 0 };
//overwrite bootstrap tooltip method to prevent showing 2 tooltip at the same time
var bootstrap_show_function = $.fn.tooltip.Constructor.prototype.show;
$.fn.modal.Constructor.prototype.enforceFocus = function () { };
$.fn.tooltip.Constructor.prototype.show = function () {
    $('.tooltip').remove();
    //the following fix the bug when using placement
    //auto and the parent element does not exist anymore resulting in
    //an error. This should be remove once we updade bootstrap to a version that fix the bug
    //edit: bug has been fixed here : https://github.com/twbs/bootstrap/pull/13752
    var e = $.Event('show.bs.' + this.type);
    var inDom = $.contains(document.documentElement, this.$element[0]);
    if (e.isDefaultPrevented() || !inDom) return;
    return bootstrap_show_function.call(this);
};

// jquery customization
//-------------------------------------------------------------------------
jQuery.expr[":"].Contains = jQuery.expr.createPseudo(function(arg) {
    return function( elem ) {
        return jQuery(elem).text().toUpperCase().indexOf(arg.toUpperCase()) >= 0;
    };
});

/** Custom jQuery plugins */
$.fn.getAttributes = function() {
    var o = {};
    if (this.length) {
        for (var attr, i = 0, attrs = this[0].attributes, l = attrs.length; i < l; i++) {
            attr = attrs.item(i);
            o[attr.nodeName] = attr.value;
        }
    }
    return o;
};
$.fn.openerpBounce = function() {
    return this.each(function() {
        $(this).css('box-sizing', 'content-box').effect('bounce', {distance: 18, times: 5}, 250);
    });
};

// jquery autocomplete tweak to allow html and classnames
var proto = $.ui.autocomplete.prototype;
var initSource = proto._initSource;

function filter( array, term ) {
    var matcher = new RegExp( $.ui.autocomplete.escapeRegex(term), "i" );
    return $.grep( array, function(value_) {
        return matcher.test( $( "<div>" ).html( value_.label || value_.value || value_ ).text() );
    });
}

$.extend( proto, {
    _initSource: function() {
        if ( this.options.html && $.isArray(this.options.source) ) {
            this.source = function( request, response ) {
                response( filter( this.options.source, request.term ) );
            };
        } else {
            initSource.call( this );
        }
    },

    _renderItem: function( ul, item) {
        return $( "<li></li>" )
            .data( "item.autocomplete", item )
            .append( $( "<a></a>" )[ this.options.html ? "html" : "text" ]( item.label ) )
            .appendTo( ul )
            .addClass(item.classname);
    }
});

});
