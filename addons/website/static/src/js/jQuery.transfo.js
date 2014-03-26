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

                settings :  function() {
                    if(this.length > 1) {
                        this.map(function () {
                            var $this = $(this);
                            return $this.data('transfo') && $this.data('transfo').settings;
                        });
                    }
                    return $this.data('transfo') && $this.data('transfo').settings;
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


            // generate all the controls markup
            var css = "box-sizing: border-box; position: absolute; background-color: #fff; border: 1px solid #ccc; width: 8px; height: 8px; margin-left: -4px; margin-top: -4px;";
            transfo.$markup = $(''
                + '<div class="transfo-controls">'
                +         '<div style="cursor: crosshair; position: absolute; background-color: #ccc; width: 16px; height: 16px; margin-left: -8px; margin-top: -8px; top: -15px; left: 50%; padding: 1px 0 0 1px;" class="transfo-rotator fa fa-repeat"></div>'
                +         '<div style="' + css + 'top: 0%; left: 0%; cursor: nw-resize;" class="transfo-scaler-tl"></div>'
                +         '<div style="' + css + 'top: 0%; left: 100%; cursor: ne-resize;" class="transfo-scaler-tr"></div>'
                +         '<div style="' + css + 'top: 100%; left: 100%; cursor: se-resize;" class="transfo-scaler-br"></div>'
                +         '<div style="' + css + 'top: 100%; left: 0%; cursor: sw-resize;" class="transfo-scaler-bl"></div>'
                +         '<div style="' + css + 'top: 0%; left: 50%; cursor: n-resize;" class="transfo-scaler-tc"></div>'
                +         '<div style="' + css + 'top: 100%; left: 50%; cursor: s-resize;" class="transfo-scaler-bc"></div>'
                +         '<div style="' + css + 'top: 50%; left: 0%; cursor: w-resize;" class="transfo-scaler-ml"></div>'
                +         '<div style="' + css + 'top: 50%; left: 100%; cursor: e-resize;" class="transfo-scaler-mr"></div>'
                +         '<div style="' + css + 'border: 0; width: 0px; height: 0px; top: 50%; left: 50%;" class="transfo-scaler-mc"></div>'
                + '</div>');
            transfo.$center = transfo.$markup.find(".transfo-scaler-mc");

            // init setting and get css to set wrap
            _setOptions($this, transfo);
            _overwriteOptions ($this, transfo, settings);

            // set transfo container and markup
            _targetCss($this, transfo);

            // append controls to container
            $("body").append(transfo.$markup);

            _bind($this, transfo);
        }

        function _overwriteOptions ($this, transfo, settings) {
            transfo.settings = $.extend(transfo.settings, settings || {});
        }

        function _setOptions ($this, transfo) {
            var style = $this.attr("style");
            var transform = (style||"").match(/transform\s*:([^;]+)/) ? style.match(/transform\s*:([^;]+)/)[1] : "";

            transfo.settings = {};

            transfo.settings.angle=      transform.indexOf('rotate') != -1 ? parseFloat(transform.match(/rotate\(([^)]+)deg\)/)[1]) : 0;
            transfo.settings.translatex= transform.indexOf('translateX') != -1 ? parseFloat(transform.match(/translateX\(([^)]+)\)/)[1]) : 0;
            transfo.settings.translatey= transform.indexOf('translateY') != -1 ? parseFloat(transform.match(/translateY\(([^)]+)\)/)[1]) : 0;
            transfo.settings.scalex=     transform.indexOf('scaleX') != -1 ? parseFloat(transform.match(/scaleX\(([^)]+)\)/)[1]) : 1;
            transfo.settings.scaley=     transform.indexOf('scaleY') != -1 ? parseFloat(transform.match(/scaleY\(([^)]+)\)/)[1]) : 1;

            transfo.settings.style = ($this.attr("style")||"").replace(/[^;]+transform[^;]+/g, '');
            $this.attr("style", transfo.settings.style);

            transfo.settings.height = $this.innerHeight();
            transfo.settings.width = $this.innerWidth();
            transfo.settings.css = window.getComputedStyle($this[0], null);
            transfo.settings.pos = $this.offset();
        }

        function _bind ($this, transfo) {
            function mousedown (event) {
                _mouseDown($this, transfo, event);
                $(document).on("mousemove", mousemove).on("mouseup", mouseup);
            }
            function mousemove (event) {
                _mouseMove($this, transfo, event);
            }
            function mouseup (event) {
                _mouseUp($this, transfo, event);
                $(document).off("mousemove", mousemove).off("mouseup", mouseup);
            }

            transfo.$markup.off().on("mousedown", mousedown);
            transfo.$markup.find(".transfo-rotator, .transfo-scaler").off().on("mousedown", mousedown);
        }

        function _mouseDown($this, transfo, event) {
            event.preventDefault();
            if (transfo.active || event.which !== 1) return;

            var type = "position",
                $e = $(event.srcElement);
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
                "pageX": event.pageX,
                "pageY": event.pageY,
            };
        }
        function _mouseUp($this, transfo, event) {
            transfo.active = null;
        }

        function _mouseMove($this, transfo, event) {
            event.preventDefault();
            if (!transfo.active) return;
            var settings = transfo.settings;
            var center = transfo.$center.offset();
            var cdx = center.left - event.pageX;
            var cdy = center.top - event.pageY;

            if (transfo.active.type == "rotator") {
                var ang;
                if (center.top != event.pageY) ang = Math.atan(- cdx / cdy) / rad;
                else ang = 0;
                if (event.pageY >= center.top && event.pageX >= center.left) ang += 180;
                else if (event.pageY >= center.top && event.pageX < center.left) ang += 180;
                else if (event.pageY < center.top && event.pageX < center.left) ang += 360;

                settings.angle = ang;

                // reset position : don't move center
                _targetCss($this, transfo);
                var new_center = transfo.$center.offset();
                var x = center.left - new_center.left;
                var y = center.top - new_center.top;
                var angle = ang * rad;
                settings.translatex +=   x*Math.cos(angle) - y*Math.sin(-angle);
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
                if (settings.scaley < 0.05) settings.scaley = 0.05;
                if (settings.scalex < 0.05) settings.scalex = 0.05;
                if (event.shiftKey &&
                    (transfo.active.type === "tl" || transfo.active.type === "bl" ||
                     transfo.active.type === "tr" || transfo.active.type === "br")) {
                    settings.scaley = settings.scalex;
                }
            }

            _targetCss($this, transfo);
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
                transform += " translateX("+settings.translatex+"px) ";
            }
            if (settings.translatey) {
                trans = true;
                transform += " translateY("+settings.translatey+"px) ";
            }
            if (settings.scalex != 1 && settings.scalex > 0) {
                trans = true;
                transform += " scaleX("+settings.scalex+") ";
            }
            if (settings.scaley != 1 && settings.scaley > 0){
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

            css = css.replace(/;+/g, ';').replace(/^;+|;+$/g, '');

            $this.attr("style", css);
        }

        function _targetCss ($this, transfo) {
            _setCss($this, transfo.settings.style, transfo.settings);

            var pos = $this.position();
            var settings = Object.create(transfo.settings);
            var w = parseFloat(transfo.settings.css.width);
            var h = parseFloat(transfo.settings.css.height);
            var width = settings.scalex * w;
            var height = settings.scaley * h;
            var top = settings.pos.top + (1-settings.scaley) * h / 2;
            var left = settings.pos.left + (1-settings.scalex) * w / 2;

            settings.scalex = settings.scaley = 1;

            _setCss(transfo.$markup,
                "position: absolute;" +
                "top:" + top + "px;" +
                "left:" + left + "px;" +
                "width:" + width + "px;" +
                "height:" + height + "px;" +
                "z-index: 1000;" +
                "cursor: move;",
                settings);
        }

        function _destroy ($this) {
            var transfo = $this.data('transfo');
            _setCss($this, transfo.settings.style, transfo.settings);
            $this.insertAfter(transfo.$wrap);
            transfo.$markup.remove();
            $this.removeData('transfo');
        }

})(jQuery);