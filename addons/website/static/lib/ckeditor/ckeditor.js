/**
 * @license Copyright (c) 2003-2013, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

// Compressed version of core/ckeditor_base.js. See original for instructions.
/*jsl:ignore*/
window.CKEDITOR||(window.CKEDITOR=function(){var l=Math.floor(900*Math.random())+100,b=window.CKEDITOR_BASEPATH||"";if(!b)for(var g=document.getElementsByTagName("script"),e=0;e<g.length;e++){var h=g[e].src.match(/(^|.*[\\\/])ckeditor(?:_basic)?(?:_source)?.js(?:\?.*)?$/i);if(h){b=h[1];break}}-1==b.indexOf(":/")&&(b=0===b.indexOf("/")?location.href.match(/^.*?:\/\/[^\/]*/)[0]+b:location.href.match(/^[^\?]*\/(?:)/)[0]+b);if(!b)throw'The CKEditor installation path could not be automatically detected. Please set the global variable "CKEDITOR_BASEPATH" before creating editor instances.';var c=function(){try{document.addEventListener?(document.removeEventListener("DOMContentLoaded",c,!1),j()):document.attachEvent&&"complete"===document.readyState&&(document.detachEvent("onreadystatechange",c),j())}catch(a){}},j=function(){for(var a;a=f.shift();)a()},f=[],d={timestamp:"",version:"%VERSION%",revision:"%REV%",rnd:l,_:{pending:[]},status:"unloaded",basePath:b,getUrl:function(a){-1==a.indexOf(":/")&&0!==a.indexOf("/")&&(a=this.basePath+a);this.timestamp&&("/"!=a.charAt(a.length-1)&&!/[&?]t=/.test(a))&&(a+=(0<=a.indexOf("?")?"&":"?")+"t="+this.timestamp);return a},domReady:function(a){f.push(a);"complete"===document.readyState&&setTimeout(c,1);if(1==f.length)if(document.addEventListener)document.addEventListener("DOMContentLoaded",c,!1),window.addEventListener("load",c,!1);else if(document.attachEvent){document.attachEvent("onreadystatechange",c);window.attachEvent("onload",c);a=!1;try{a=!window.frameElement}catch(b){}if(document.documentElement.doScroll&&a){var d=function(){try{document.documentElement.doScroll("left")}catch(a){setTimeout(d,1);return}c()};d()}}}},k=window.CKEDITOR_GETURL;if(k){var m=d.getUrl;d.getUrl=function(a){return k.call(d,a)||m.call(d,a)}}return d}());
/*jsl:end*/

if ( CKEDITOR.loader )
	CKEDITOR.loader.load( 'ckeditor' );
else {
	// Set the script name to be loaded by the loader.
	CKEDITOR._autoLoad = 'ckeditor';

	// Include the loader script.
	if ( document.body && ( !document.readyState || document.readyState == 'complete' ) ) {
		var script = document.createElement( 'script' );
		script.type = 'text/javascript';
		script.src = CKEDITOR.getUrl( 'core/loader.js' );
		document.body.appendChild( script );
	} else {
		document.write( '<script type="text/javascript" src="' + CKEDITOR.getUrl( 'core/loader.js' ) + '"></script>' );
	}
}

/**
 * The skin to load for all created instances, it may be the name of the skin
 * folder inside the editor installation path, or the name and the path separated
 * by a comma.
 *
 * **Note:** This is a global configuration that applies to all instances.
 *
 *		CKEDITOR.skinName = 'moono';
 *
 *		CKEDITOR.skinName = 'myskin,/customstuff/myskin/';
 *
 * @cfg {String} [skinName='moono']
 * @member CKEDITOR
 */
CKEDITOR.skinName = 'moono';
