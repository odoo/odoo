/*
 Copyright (c) 2012-2017 Open Lab
 Permission is hereby granted, free of charge, to any person obtaining
 a copy of this software and associated documentation files (the
 "Software"), to deal in the Software without restriction, including
 without limitation the rights to use, copy, modify, merge, publish,
 distribute, sublicense, and/or sell copies of the Software, and to
 permit persons to whom the Software is furnished to do so, subject to
 the following conditions:

 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
 LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
 WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

//----------------------------------positioning-----------------------------------------------
jQuery.fn.centerOnScreen = function () {
  return this.each(function () {
    var container = $(this);
    //console.debug($(window).height(), container.outerHeight(),(($(window).height() - container.outerHeight()) / 2))
    container.css("position", "fixed");
    container.css("top", (($(window).height() - container.outerHeight()) / 2) + 'px');
    container.css("left", (($(window).width() - container.outerWidth()) / 2) + 'px');
  });
};


function nearBestPosition(whereId, theObjId, centerOnEl) {

	var el = whereId;
	var target = theObjId;

	if (typeof whereId != "object") {
		el = $("#" + whereId);
	}
	if (typeof theObjId != "object") {
		target = $("#" + theObjId);
	}

	if (el) {
		target.css("visibility", "hidden");
		var hasContainment = false;

		target.parents().each(function () {
			if ($(this).css("position") == "static")
				return;

			hasContainment = true;
		});

		var trueX = hasContainment ? el.position().left : el.offset().left;
		var trueY = hasContainment ? el.position().top : el.offset().top;
		var h = el.outerHeight();
		var elHeight = parseFloat(h);

		if (centerOnEl) {
			var elWidth = parseFloat(el.outerWidth());
			var targetWidth = parseFloat(target.outerWidth());
			trueX += (elWidth - targetWidth) / 2;
		}

		trueY += parseFloat(elHeight);

		var left = trueX;
		var top = trueY;
		var barHeight = 45 ;
		var barWidth =  20 ;

		if (trueX && trueY) {
			target.css("left", left);
			target.css("top", top);
		}

		if (target.offset().left >= ( ($(window).width() + $(window).scrollLeft()) - target.outerWidth())) {

			left = ( ($(window).width() + $(window).scrollLeft()) - target.outerWidth() - 10 );
			target.css({left:left, marginTop: 0});
		}

		if (target.offset().left < 0) {
			left = 10;
			target.css("left", left);
		}

		if ((target.offset().top + target.outerHeight() >= ( ($(window).height() + $(window).scrollTop()) - barHeight)) && (target.outerHeight() < $(window).height())) {
			var marginTop = -(target.outerHeight() + el.outerHeight());
			target.css("margin-top", marginTop);
		}

		if (target.offset().top < 0) {
			top = 0;
			target.css("top", top);
		}


		target.css("visibility", "visible");
	}
}

$.fn.keepItVisible = function (ref) {
	var thisTop = $(this).offset().top;
	var thisLeft = $(this).offset().left;
	var fromTop =0;
	var fromLeft =0;

	var windowH =  $(window).height() + $(window).scrollTop();
	var windowW =  $(window).width() + $(window).scrollLeft();

	if (ref){
		fromTop = windowH - (ref.offset().top);
		fromLeft = windowW -  (ref.offset().left + ref.outerWidth());
	}

	if (thisTop + $(this).outerHeight() > windowH){
		var mt = (thisTop + $(this).outerHeight()) - windowH;
//		$(this).css("margin-top", -$(this).outerHeight() - fromTop);
		$(this).css("margin-top", -mt - fromTop);
	}
	if (thisLeft + $(this).outerWidth() > windowW){
		var mL = (thisLeft + $(this).outerWidth()) - windowW;
//		$(this).css("margin-left", -$(this).outerWidth() - fromLeft);
		$(this).css("margin-left", -mL - fromLeft);
	}
	$(this).css("visibility", "visible");
};

//END positioning


/*   Caret Functions
 Use setSelection with start = end to set caret
 */
function setSelection(input, start, end) {
  input.setSelectionRange(start, end);
}

$.fn.setCursorPosition = function(pos) {
	this.each(function(index, elem) {
		if (elem.setSelectionRange) {
			elem.setSelectionRange(pos, pos);
		} else if (elem.createTextRange) {
			var range = elem.createTextRange();
			range.collapse(true);
			range.moveEnd('character', pos);
			range.moveStart('character', pos);
			range.select();
		}
	});
	return this;
};

//-- Caret Functions END ---------------------------------------------------------------------------- --



/*----------------------------------------------------------------- manage bbButtons*/
$.buttonBar = {
  defaults: {},

  init: function(){
    setTimeout(function(){
      $.buttonBar.manageButtonBar();
    },100);

    $(window).on("scroll.ButtonBar",function(){
      $.buttonBar.manageButtonBar();
    });
    $(window).on("resize.ButtonBar",function(){
      $.buttonBar.manageButtonBar();
    });
  },

  manageButtonBar: function(anim) {

    $(".buttonArea").not(".bbCloned").not(".notFix").each(function(){
      var bb = this;

      //se usiamo questi si rompe la button bar flottante del save sulla issue list
      //bb.originalHeigh=bb.originalHeigh ||  $(bb).height();
      //bb.originalOffsetTop=bb.originalOffsetTop||$(bb).offset().top;

      bb.originalHeigh= $(bb).height();
      bb.originalOffsetTop=$(bb).offset().top;

      bb.isOut = $(window).scrollTop() + $(window).height() - bb.originalHeigh < bb.originalOffsetTop;

      if (bb.bbHolder)
        bb.bbHolder.css({width: $(bb).outerWidth(),left:$(bb).offset().left});

      if (bb.isOut && !bb.isCloned){
        if (bb.bbHolder)
          bb.bbHolder.remove();
        bb.isCloned = true;
        bb.bbHolder = $(bb).clone().addClass("bbCloned clone bottom").css({width: $(bb).outerWidth(), marginTop:0,left:$(bb).offset().left});
        bb.bbHolder.hide();
        bb.bbHolder.css({position:"fixed", bottom:0, left:$(bb).offset().left});
        $(bb).after(bb.bbHolder);
        bb.bbHolder.show();
        $(bb).css("visibility","hidden");

      } else if (!bb.isOut && bb.isCloned) {
      //} else {
        bb.isCloned = false;
        bb.bbHolder.remove();
        $(bb).css("visibility","visible");
      }
    });
  },

  refreshButtonBar: function() {
    $(".bbCloned").remove();
    $(".buttonArea").not(".bbCloned").each(function(){
      var bb = this;
      bb.isCloned = false;
    });

    $.buttonBar.manageButtonBar(false);
  }
};
