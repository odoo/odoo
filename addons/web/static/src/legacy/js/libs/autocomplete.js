odoo.define('web.autocomplete.extensions', function () {
'use strict';

/**
 * The jquery autocomplete library extensions and fixes should be done here to
 * avoid patching in place.
 */

// jquery autocomplete tweak to allow html and classnames
var proto = $.ui.autocomplete.prototype;
var initSource = proto._initSource;

function filter( array, term ) {
    var matcher = new RegExp( $.ui.autocomplete.escapeRegex(term), "i" );
    return $.grep( array, function (value_) {
        return matcher.test( $( "<div>" ).html( value_.label || value_.value || value_ ).text() );
    });
}

$.extend(proto, {
    _initSource: function () {
        if ( this.options.html && $.isArray(this.options.source) ) {
            this.source = function (request, response) {
                response( filter( this.options.source, request.term ) );
            };
        } else {
            initSource.call( this );
        }
    },
    _renderItem: function (ul, item) {
        return $( "<li></li>" )
            .data( "item.autocomplete", item )
            .append( $( "<a></a>" )[ this.options.html ? "html" : "text" ]( item.label ) )
            .appendTo( ul )
            .addClass(item.classname);
    },
});
});
