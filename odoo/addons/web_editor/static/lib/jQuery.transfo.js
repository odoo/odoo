/*
Copyright (c) 2014 Christophe Matthieu,

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
*/

(function($){
    'use strict';
        var rad = Math.PI/180;

        // public methods
        var methods = {
                init : function(settings) {
                    return this.each(function() {
                        var $this = $(this), transfo = $this.data('transfo');
                        if (!transfo) {
                            _init($this, settings);
                        } else {
                            _overwriteOptions($this, transfo, settings);
                            _targetCss($this, transfo);
                        }
                    });
                },

                destroy : function() {
                    return this.each(function() {
                        var $this = $(this);
                        if ($this.data('transfo')) {
                            _destroy($this);
                        }
                    });
                },

                reset : function() {
                    return this.each(function() {
                        var $this = $(this);
                        if ($this.data('transfo')) {
                            _reset($this);
                        }
                    });
                },

                toggle : function() {
                    return this.each(function() {
                        var $this = $(this);
                        var transfo = $this.data('transfo');
                        if (transfo) {
                            transfo.settings.hide = !transfo.settings.hide;
                            _showHide($this, transfo);
                        }
                    });
                },

                hide : function() {
                    return this.each(function() {
                        var $this = $(this);
                        var transfo = $this.data('transfo');
                        if (transfo) {
                            transfo.settings.hide = true;
                            _showHide($this, transfo);
                        }
                    });
                },

                show : function() {
                    return this.each(function() {
                        var $this = $(this);
                        var transfo = $this.data('transfo');
                        if (transfo) {
                            transfo.settings.hide = false;
                            _showHide($this, transfo);
                        }
                    });
                },

                settings :  function() {
                    if(this.length > 1) {
                        this.map(function () {
                            var $this = $(this);
                            return $this.data('transfo') && $this.data('transfo').settings;
                        });
                    }
                    return this.data('transfo') && $this.data('transfo').settings;
                },
                center :  function() {
                    if(this.length > 1) {
                        this.map(function () {
                            var $this = $(this);
                            return $this.data('transfo') && $this.data('transfo').$center.offset();
                        });
                    }
                    return this.data('transfo') && this.data('transfo').$center.offset();
                }
        };

        $.fn.transfo = function( method ) {
            if ( methods[method] ) {
                    return methods[method].apply( this, Array.prototype.slice.call( arguments, 1 ));
            } else if ( typeof method === 'object' || ! method ) {
                    return methods.init.apply( this, arguments );
            } else {
                    $.error( 'Method ' +  method + ' does not exist on jQuery.transfo' );
            }
            return false;
        };

        function _init ($this, settings) {
            var transfo = {};
            $this.data('transfo', transfo);
            transfo.settings = settings;
            transfo.settings.document = transfo.settings.document || document;

            // generate all the controls markup
            var css = "box-sizing: border-box; position: absolute; background-color: #fff; border: 1px solid #ccc; width: 8px; height: 8px; margin-left: -4px; margin-top: -4px;";
            transfo.$markup = $(''
                + '<div class="transfo-container">'
                +  '<div class="transfo-controls">'
                +   '<div style="cursor: crosshair; position: absolute; margin: -30px; top: 0; right: 0; padding: 1px 0 0 1px;" class="transfo-rotator">'
                +    '<span class="fa-stack fa-lg">'
                +    '<i class="fa fa-circle fa-stack-2x"></i>'
                +    '<i class="fa fa-repeat fa-stack-1x fa-inverse"></i>'
                +    '</span>'
                +   '</div>'
                +   '<div style="' + css + 'top: 0%; left: 0%; cursor: nw-resize;" class="transfo-scaler-tl"></div>'
                +   '<div style="' + css + 'top: 0%; left: 100%; cursor: ne-resize;" class="transfo-scaler-tr"></div>'
                +   '<div style="' + css + 'top: 100%; left: 100%; cursor: se-resize;" class="transfo-scaler-br"></div>'
                +   '<div style="' + css + 'top: 100%; left: 0%; cursor: sw-resize;" class="transfo-scaler-bl"></div>'
                +   '<div style="' + css + 'top: 0%; left: 50%; cursor: n-resize;" class="transfo-scaler-tc"></div>'
                +   '<div style="' + css + 'top: 100%; left: 50%; cursor: s-resize;" class="transfo-scaler-bc"></div>'
                +   '<div style="' + css + 'top: 50%; left: 0%; cursor: w-resize;" class="transfo-scaler-ml"></div>'
                +   '<div style="' + css + 'top: 50%; left: 100%; cursor: e-resize;" class="transfo-scaler-mr"></div>'
                +   '<div style="' + css + 'border: 0; width: 0px; height: 0px; top: 50%; left: 50%;" class="transfo-scaler-mc"></div>'
                +  '</div>'
                + '</div>');
            transfo.$center = transfo.$markup.find(".transfo-scaler-mc");

            // init setting and get css to set wrap
            _setOptions($this, transfo);
            _overwriteOptions ($this, transfo, settings);

            // append controls to container
            $(transfo.settings.document.body).append(transfo.$markup);

            // set transfo container and markup
            setTimeout(function () {
                _targetCss($this, transfo);
            },0);

            _bind($this, transfo);
            
            _targetCss($this, transfo);
            _stop_animation($this[0]);
        }

        function _overwriteOptions ($this, transfo, settings) {
            transfo.settings = $.extend(transfo.settings, settings || {});
        }

        function _stop_animation (target) {
            target.style.webkitAnimationPlayState = "paused";
            target.style.animationPlayState = "paused";
            target.style.webkitTransition = "none";
            target.style.transition = "none";
        }

        function _setOptions ($this, transfo) {
            var style = $this.attr("style") || "";
            var transform = style.match(/transform\s*:([^;]+)/) ? style.match(/transform\s*:([^;]+)/)[1] : "";

            transfo.settings = {};

            transfo.settings.angle=      transform.indexOf('rotate') != -1 ? parseFloat(transform.match(/rotate\(([^)]+)deg\)/)[1]) : 0;
            transfo.settings.scalex=     transform.indexOf('scaleX') != -1 ? parseFloat(transform.match(/scaleX\(([^)]+)\)/)[1]) : 1;
            transfo.settings.scaley=     transform.indexOf('scaleY') != -1 ? parseFloat(transform.match(/scaleY\(([^)]+)\)/)[1]) : 1;

            transfo.settings.style = style.replace(/[^;]*transform[^;]+/g, '').replace(/;+/g, ';');

            $this.attr("style", transfo.settings.style);
            _stop_animation($this[0]);
            transfo.settings.pos = $this.offset();

            transfo.settings.height = $this.innerHeight();
            transfo.settings.width = $this.innerWidth();

            var translatex = transform.match(/translateX\(([0-9.-]+)(%|px)\)/);
            var translatey = transform.match(/translateY\(([0-9.-]+)(%|px)\)/);
            transfo.settings.translate = "%";

            if (translatex && translatex[2] === "%") {
                transfo.settings.translatexp = parseFloat(translatex[1]);
                transfo.settings.translatex = transfo.settings.translatexp / 100 * transfo.settings.width;
            } else {
                transfo.settings.translatex = translatex ? parseFloat(translatex[1]) : 0;
            }
            if (translatey && translatey[2] === "%") {
                transfo.settings.translateyp = parseFloat(translatey[1]);
                transfo.settings.translatey = transfo.settings.translateyp / 100 * transfo.settings.height;
            } else {
                transfo.settings.translatey = translatey ? parseFloat(translatey[1]) : 0;
            }

            transfo.settings.css = window.getComputedStyle($this[0], null);

            transfo.settings.rotationStep = 5;
            transfo.settings.hide = false;
            transfo.settings.callback = function () {};
        }

        function _bind ($this, transfo) {
            function mousedown (event) {
                _mouseDown($this, this, transfo, event);
                $(transfo.settings.document).on("mousemove", mousemove).on("mouseup", mouseup);
            }
            function mousemove (event) {
                _mouseMove($this, this, transfo, event);
            }
            function mouseup (event) {
                _mouseUp($this, this, transfo, event);
                $(transfo.settings.document).off("mousemove", mousemove).off("mouseup", mouseup);
            }

            transfo.$markup.off().on("mousedown", mousedown);
            transfo.$markup.find(".transfo-controls >:not(.transfo-scaler-mc)").off().on("mousedown", mousedown);
        }

        function _mouseDown($this, div, transfo, event) {
            event.preventDefault();
            if (transfo.active || event.which !== 1) return;

            var type = "position", $e = $(div);
            if ($e.hasClass("transfo-rotator")) type = "rotator";
            else if ($e.hasClass("transfo-scaler-tl")) type = "tl";
            else if ($e.hasClass("transfo-scaler-tr")) type = "tr";
            else if ($e.hasClass("transfo-scaler-br")) type = "br";
            else if ($e.hasClass("transfo-scaler-bl")) type = "bl";
            else if ($e.hasClass("transfo-scaler-tc")) type = "tc";
            else if ($e.hasClass("transfo-scaler-bc")) type = "bc";
            else if ($e.hasClass("transfo-scaler-ml")) type = "ml";
            else if ($e.hasClass("transfo-scaler-mr")) type = "mr";

            transfo.active = {
                "type": type,
                "scalex": transfo.settings.scalex,
                "scaley": transfo.settings.scaley,
                "pageX": event.pageX,
                "pageY": event.pageY,
                "center": transfo.$center.offset(),
            };
        }
        function _mouseUp($this, div, transfo, event) {
            transfo.active = null;
        }

        function _mouseMove($this, div, transfo, event) {
            event.preventDefault();
            if (!transfo.active) return;
            var settings = transfo.settings;
            var center = transfo.active.center;
            var cdx = center.left - event.pageX;
            var cdy = center.top - event.pageY;

            if (transfo.active.type == "rotator") {
                var ang, dang = Math.atan((settings.width * settings.scalex) / (settings.height * settings.scaley)) / rad;

                if (cdy) ang = Math.atan(- cdx / cdy) / rad;
                else ang = 0;
                if (event.pageY >= center.top && event.pageX >= center.left) ang += 180;
                else if (event.pageY >= center.top && event.pageX < center.left) ang += 180;
                else if (event.pageY < center.top && event.pageX < center.left) ang += 360;
                
                ang -= dang;
                if (settings.scaley < 0 && settings.scalex < 0) ang += 180;

                if (!event.ctrlKey) {
                    settings.angle = Math.round(ang / transfo.settings.rotationStep) * transfo.settings.rotationStep;
                } else {
                    settings.angle = ang;
                }

                // reset position : don't move center
                _targetCss($this, transfo);
                var new_center = transfo.$center.offset();
                var x = center.left - new_center.left;
                var y = center.top - new_center.top;
                var angle = ang * rad;
                settings.translatex += x*Math.cos(angle) - y*Math.sin(-angle);
                settings.translatey += - x*Math.sin(angle) + y*Math.cos(-angle);
            }
            else if (transfo.active.type == "position") {
                var angle = settings.angle * rad;
                var x = event.pageX - transfo.active.pageX;
                var y = event.pageY - transfo.active.pageY;
                transfo.active.pageX = event.pageX;
                transfo.active.pageY = event.pageY;
                var dx = x*Math.cos(angle) - y*Math.sin(-angle);
                var dy = - x*Math.sin(angle) + y*Math.cos(-angle);

                settings.translatex += dx;
                settings.translatey += dy;
            }
            else if (transfo.active.type.length === 2) {
                var angle = settings.angle * rad;
                var dx =   cdx*Math.cos(angle) - cdy*Math.sin(-angle);
                var dy = - cdx*Math.sin(angle) + cdy*Math.cos(-angle);
                if (transfo.active.type.indexOf("t") != -1) {
                    settings.scaley = dy / (settings.height/2);
                }
                if (transfo.active.type.indexOf("b") != -1) {
                    settings.scaley = - dy / (settings.height/2);
                }
                if (transfo.active.type.indexOf("l") != -1) {
                    settings.scalex = dx / (settings.width/2);
                }
                if (transfo.active.type.indexOf("r") != -1) {
                    settings.scalex = - dx / (settings.width/2);
                }
                if (settings.scaley > 0 && settings.scaley < 0.05) settings.scaley = 0.05;
                if (settings.scalex > 0 && settings.scalex < 0.05) settings.scalex = 0.05;
                if (settings.scaley < 0 && settings.scaley > -0.05) settings.scaley = -0.05;
                if (settings.scalex < 0 && settings.scalex > -0.05) settings.scalex = -0.05;

                if (event.shiftKey &&
                    (transfo.active.type === "tl" || transfo.active.type === "bl" ||
                     transfo.active.type === "tr" || transfo.active.type === "br")) {
                    settings.scaley = settings.scalex;
                }
            }

            settings.angle = Math.round(settings.angle);
            settings.translatex = Math.round(settings.translatex);
            settings.translatey = Math.round(settings.translatey);
            settings.scalex = Math.round(settings.scalex*100)/100;
            settings.scaley = Math.round(settings.scaley*100)/100;

            _targetCss($this, transfo);
            _stop_animation($this[0]);
            return false;
        }

        function _setCss($this, css, settings) {
            var transform = "";
            var trans = false;
            if (settings.angle !== 0) {
                trans = true;
                transform += " rotate("+settings.angle+"deg) ";
            }
            if (settings.translatex) {
                trans = true;
                transform += " translateX("+(settings.translate === "%" ? settings.translatexp+"%" : settings.translatex+"px")+") ";
            }
            if (settings.translatey) {
                trans = true;
                transform += " translateY("+(settings.translate === "%" ? settings.translateyp+"%" : settings.translatey+"px")+") ";
            }
            if (settings.scalex != 1) {
                trans = true;
                transform += " scaleX("+settings.scalex+") ";
            }
            if (settings.scaley != 1){
                trans = true;
                transform += " scaleY("+settings.scaley+") ";
            }

            if (trans) {
                css += ";"
                        /* Safari */
                css += "-webkit-transform:" + transform + ";"
                        /* Firefox */
                    + "-moz-transform:" + transform + ";"
                        /* IE */
                    + "-ms-transform:" + transform + ";"
                        /* Opera */
                    + "-o-transform:" + transform + ";"
                        /* Other */
                    + "transform:" + transform + ";";
            }

            css = css.replace(/(\s*;)+/g, ';').replace(/^\s*;|;\s*$/g, '');

            $this.attr("style", css);
        }

        function _targetCss ($this, transfo) {
            var settings = transfo.settings;
            var width = parseFloat(settings.css.width);
            var height = parseFloat(settings.css.height);
            settings.translatexp = Math.round(settings.translatex/width*1000)/10;
            settings.translateyp = Math.round(settings.translatey/height*1000)/10;

            _setCss($this, settings.style, settings);

            transfo.$markup.css({
                "position": "absolute",
                "width": width + "px",
                "height": height + "px",
                "top": settings.pos.top + "px",
                "left": settings.pos.left + "px"
            });

            var $controls = transfo.$markup.find('.transfo-controls');
            _setCss($controls,
                "width:" + width + "px;" +
                "height:" + height + "px;" +
                "cursor: move;",
                settings);

            $controls.children().css("transform", "scaleX("+(1/settings.scalex)+") scaleY("+(1/settings.scaley)+")");

            _showHide($this, transfo);

            transfo.settings.callback.call($this[0], $this);
        }

        function _showHide ($this, transfo) {
            transfo.$markup.css("z-index", transfo.settings.hide ? -1 : 1000);
            if (transfo.settings.hide) {
                transfo.$markup.find(".transfo-controls > *").hide();
                transfo.$markup.find(".transfo-scaler-mc").show();
            } else {
                transfo.$markup.find(".transfo-controls > *").show();
            }
        }

        function _destroy ($this) {
            $this.data('transfo').$markup.remove();
            $this.removeData('transfo');
        }

        function _reset ($this) {
            var transfo = $this.data('transfo');
            _destroy($this);
            $this.transfo(transfo.settings);
        }

})(jQuery);
