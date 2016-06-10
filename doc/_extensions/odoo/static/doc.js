(function ($) {
var log = function(data){
  return console.log(data);
}

var update_page = function  () {

  var
  $header               = $("header"),
  $main_navbar          = $("#main_navbar"),
  $navbar_aside         = $(".navbar-aside"),
  $navClone             = null,
  $floating_action      = $("#floating_action"),
  $floating_action_menu = $("#floating_action_menu"),
  $body                 = $("body"),
  $main                 = $("main"), // remove
  $aside                = $("aside"),
  $mask                 = $("#mask"),
  $title                = $("#main_title"),
  $cardTop              = $(".card.top")
  $cover_img            = $(".card.top .card-img"),
  ripples               = $(".ripple"),
  $main_back            = $("#main-back");

  var titleZoom = 1.5,
           Hgap = 60;

  var nav_h   = $main_navbar.height(),
  wW          = $(window).width(),
  titleOffset = ($main.offset().left - $main_back.outerWidth())-15;
  if($main.hasClass("index")){Hgap = 0}
  var img_h = $cover_img.height() - Hgap;
  $navbar_aside.find("li").has("ul").addClass("parent");

  if ($main.hasClass("index")){
    $main.find("#index .index-tree > .row").each(function(){
      var childs = $(this).find(".col-md-3");
      if(childs.length == 2){
        childs.removeClass("col-md-3").addClass("col-md-6");
      }
      if(childs.length == 3){
        childs.removeClass("col-md-3").addClass("col-md-4");
      }
    })
    $(".floating_action_container").remove();
  }

  var resize_aside = function(){
    var navbar_aside_data = $navbar_aside[0].getBoundingClientRect();
    var $navClone_ul = $navClone.find("> ul");
    var $navbar_aside_ul = $navbar_aside.find("> ul");
    var maxH = $(window).height() - 45;
    maxH_ul = maxH - ($navClone_ul.position().top + 45);
    $navClone.css({
      "width": navbar_aside_data.width,
      "left": navbar_aside_data .left,
      "height": maxH
    })
    $navClone_ul.add($navbar_aside_ul).css("max-height",maxH_ul)
  }

  var resize = function() {
    nav_h       = $main_navbar.height();
    wW          = $(window).width();
    titleOffset = $main.offset().left - $main_back.outerWidth();
    if($main.hasClass("index")){Hgap = 0}
    img_h = $cover_img.height() - Hgap;
    if($navClone != null){
      resize_aside();
    }
    header_layout();
  }


  var header_layout = function  () {
    var wTop  = $(window).scrollTop();
    var r = (wTop)/(img_h - 50);

    function rat() {
      if(r<0) return 0;
      if(r>1) return 1;
      return Number(r.toString().match(/^\d+(?:\.\d{0,2})?/));
    }

    var ratio = rat();

    if (wW >= 768) {

      $title.css({"font-size": "", "position": "", 'transform':'scale('+(1-(titleZoom-1)*ratio)+')'});

      if( (img_h - wTop) > 0 ){
        $main_navbar[0].style.cssText += "; height: " + (img_h - wTop)+ "px;";
        $cover_img[0].style.cssText += "; opacity: " + (0.8-ratio) + ";";
      }

      if (titleOffset > 0) {
        $main_back.css("margin-right", titleOffset);
      } else {
        $main_back.css("margin-right", "");
      }

      if (ratio == 1) {
        $main_navbar.css("height","").add($header).addClass("stacked");
      } else {
        $main_navbar.add($header).removeClass("stacked");
      }

      if ($navClone != null && ($aside.css("display") != "none" )) {
        var gap = $aside.offset().top - 45;
        if((wTop > gap)) {
          $navClone.removeClass("hidden");
          $navbar_aside.addClass("invisible");
          resize_aside();

          // ScrollSpy
          // if(!($navClone.hasClass("binded"))){
          //   $body.scrollspy({target: "#navClone", offset: 100 });
          //   $navClone.addClass("binded");
          //   $body.scrollspy('refresh');
          // }
        } else {
          $navClone.addClass("hidden");
          $navbar_aside.removeClass("invisible");
        }
      }

    } else {

      $cover_img.css("opacity","");
      $title.css({
        "position": "relative",
        "height" : "",
        "transform":"",
        "font-size": 18
      });
      $main_navbar.addClass("stacked").css({
        "height":"",
        "margin": 0
      })
    }
  };
  header_layout();

  var floating_menu_layout = function () {
    var lis = $navbar_aside.find("> ul > li").clone(true)
      .addClass("ripple")
      .css({
        position: 'relative',
        overflow: 'hidden'
      });
    lis.find("ul").remove().end()
      .find("a").removeClass("ripple").on("click", function  () {
        floating_menu_toggle();
      });
    $floating_action_menu.find(".content").empty().append(lis);
  }
  floating_menu_layout();

  var floating_menu_toggle = function  () {
    $floating_action.toggleClass("active");
    setTimeout(function  () {
      $floating_action_menu.toggleClass("active");
      $mask.toggleClass("active");
    }, 300);
  };

  var scroll_to = function(el_list) {
    var offset = 80;
    el_list.each(function () {
      var $link = $(this),
          href = $link.attr("href");

      $link.on("click", function () {
        var val = $(href).offset().top - 60;
        $('html, body').animate({
          scrollTop: val
        }, 600);
        log(el_list)
        $navClone.find("li").removeClass("active");
        $link.parents("li").addClass("active");
        return false;
      })
    })
  }


  var ripple_animation = function(el_list) {
    el_list.each(function () {
      var btn = $(this);
      btn
        .css({
          position: 'relative',
          overflow: 'hidden'
        })
        .bind('mousedown', function (e) {
          var ripple;
          if (btn.find('.inner-ripple').length === 0) {
            ripple = $('<span class="inner-ripple"/>');
            btn.prepend(ripple);
          } else {
            ripple = btn.find('.inner-ripple');
          }
          ripple.removeClass('inner-ripple-animated');

          if (!ripple.height() && !ripple.width()) {
            var diameter = Math.max(btn.outerWidth(), btn.outerHeight());
            ripple.css({
              height: diameter,
              width: diameter
            });
          }
          var x = e.pageX - btn.offset().left - ripple.width() / 2;
          var y = e.pageY - btn.offset().top - ripple.height() / 2;
          ripple .css({top: y + 'px', left: x + 'px'}) .addClass('inner-ripple-animated');
          setTimeout(function () {
            ripple.removeClass('inner-ripple-animated');
          }, 351);
        });
    });
  }
  var aside_layout = function  () {

    if ($navbar_aside.length > 0) {

      var navbar_aside_data = $navbar_aside[0].getBoundingClientRect();

      if ($navClone == null) { // build affix menu

        $navClone = $navbar_aside.clone().attr("id","navClone").appendTo($body);

        //force repainting
        $navClone[0].style.display='none';
        setTimeout(function () {
          $navClone[0].offsetHeight;
          $navClone[0].style.display='';
        }, 10);
        $navClone.addClass("affix hidden");

        ripple_animation($navClone.find("li > a"));
        scroll_to($navClone.find("li > a"));

        $navClone.css({
          "width": navbar_aside_data.width,
          "left": navbar_aside_data .left
        })
        $(window).trigger("resize");
        //$body.scrollspy('refresh');
      } // End - build affix menu

    }
  };
  aside_layout();

  var cards_animate = function  (type, speed) {
    type = type || 'in';
    speed = speed || 2000;
    var $container = $(".container.index"),
      $cards = $container.find(".card"),
      $titles = $container.find("h2");

    $cards.each(function  () {
      var $card = $(this),
        cardOffset = this.getBoundingClientRect(),
        offset = cardOffset.left * 0.8 + cardOffset.top,
        delay = parseFloat(offset / speed).toFixed(2);
      $card.css("transition-delay", delay + "s");
    });

    if (type === "in") {
      $titles.fadeTo(0, 0);
      $titles.fadeTo(1000, 1);
      $container.addClass("animating");
    } else {
      $titles.fadeTo(300, 0);
      $container.removeClass("animating");
    }
  };
  cards_animate();


  // BIND EVENTS

  $floating_action.on("click", function  () {
    floating_menu_toggle();
    return false;
  });

  $mask.on("click", function  () {
    floating_menu_toggle();
    return false;
  });

  $(".content-switcher").each(function  (index, switcher) {
    var $switcher = $(switcher),
        $links = $switcher.find('> ul > li'),
        $tabs = $switcher.find('> .tabs > *'),
        $all = $links.add($tabs);

    function select(index) {
      $all.removeClass('active');
      $links.eq(index).add($tabs.eq(index)).addClass('active');
    }
    select(0);
    $switcher.on('click', '> ul > li', function () {
      select($(this).index());
      return false;
    });
  });


  $(window)
    .on("scroll", function () {
      header_layout();
      //aside_layout();
    })
    .on("resize", function () {
      resize();
      header_layout();
      //aside_layout();
    })
    .trigger("scroll");

  //Ripples

  ripple_animation(ripples);

};

$(document).ready(function () {
  update_page();
});

})(jQuery);
