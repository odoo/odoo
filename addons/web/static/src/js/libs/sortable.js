odoo.define('web.sortable.extensions', function () {
'use strict';
 /**
 * The RubaXa sortable library extensions and fixes should be done here to
 * avoid patching in place.
 */
 var Sortable = window.Sortable;
var proto = Sortable.prototype;
var onTouchMove = proto._onTouchMove;
 $.extend(proto, {
	// extend _onTouchMove to add additional css property on clone element(add rotation)
	_onTouchMove: function (/**TouchEvent*/evt) {
		onTouchMove.call(this,evt);
		if (this.options.rotateElement) {
			var $clonedDiv = $(this.el).find('.' + this.options.rotateElement);
			$clonedDiv.css('transform', $clonedDiv.css('transform') + ' rotate(-3deg)');
		}
	},
});
});

