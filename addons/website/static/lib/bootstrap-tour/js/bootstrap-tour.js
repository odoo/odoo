/* ===========================================================
# bootstrap-tour - v0.6.0
# http://bootstraptour.com
# ==============================================================
# Copyright 2012-2013 Ulrich Sossou
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
*/
(function() {
  (function($, window) {
    var Tour, document;
    document = window.document;
    Tour = (function() {
      function Tour(options) {
        this._options = $.extend({
          name: "tour",
          container: "body",
          keyboard: true,
          storage: window.localStorage,
          debug: false,
          backdrop: false,
          redirect: true,
          orphan: false,
          basePath: "",
          template: "<div class='popover'>          <div class='arrow'></div>          <h3 class='popover-title'></h3>          <div class='popover-content'></div>          <nav class='popover-navigation'>            <div class='btn-group'>              <button class='btn btn-sm btn-default' data-role='prev'>&laquo; Prev</button>              <button class='btn btn-sm btn-default' data-role='next'>Next &raquo;</button>            </div>            <button class='btn btn-sm btn-default' data-role='end'>End tour</button>          </nav>        </div>",
          afterSetState: function(key, value) {},
          afterGetState: function(key, value) {},
          afterRemoveState: function(key) {},
          onStart: function(tour) {},
          onEnd: function(tour) {},
          onShow: function(tour) {},
          onShown: function(tour) {},
          onHide: function(tour) {},
          onHidden: function(tour) {},
          onNext: function(tour) {},
          onPrev: function(tour) {}
        }, options);
        this._steps = [];
        this.setCurrentStep();
        this.backdrop = {
          overlay: null,
          $element: null,
          $background: null
        };
      }

      Tour.prototype.setState = function(key, value) {
        var keyName;
        keyName = "" + this._options.name + "_" + key;
        this._options.storage.setItem(keyName, value);
        return this._options.afterSetState(keyName, value);
      };

      Tour.prototype.removeState = function(key) {
        var keyName;
        keyName = "" + this._options.name + "_" + key;
        this._options.storage.removeItem(keyName);
        return this._options.afterRemoveState(keyName);
      };

      Tour.prototype.getState = function(key) {
        var keyName, value;
        keyName = "" + this._options.name + "_" + key;
        value = this._options.storage.getItem(keyName);
        if (value === void 0 || value === "null") {
          value = null;
        }
        this._options.afterGetState(key, value);
        return value;
      };

      Tour.prototype.addSteps = function(steps) {
        var step, _i, _len, _results;
        _results = [];
        for (_i = 0, _len = steps.length; _i < _len; _i++) {
          step = steps[_i];
          _results.push(this.addStep(step));
        }
        return _results;
      };

      Tour.prototype.addStep = function(step) {
        return this._steps.push(step);
      };

      Tour.prototype.getStep = function(i) {
        if (this._steps[i] != null) {
          return $.extend({
            id: "step-" + i,
            path: "",
            placement: "right",
            title: "",
            content: "<p></p>",
            next: i === this._steps.length - 1 ? -1 : i + 1,
            prev: i - 1,
            animation: true,
            container: this._options.container,
            backdrop: this._options.backdrop,
            redirect: this._options.redirect,
            orphan: this._options.orphan,
            template: this._options.template,
            onShow: this._options.onShow,
            onShown: this._options.onShown,
            onHide: this._options.onHide,
            onHidden: this._options.onHidden,
            onNext: this._options.onNext,
            onPrev: this._options.onPrev
          }, this._steps[i]);
        }
      };

      Tour.prototype.start = function(force) {
        var promise,
          _this = this;
        if (force == null) {
          force = false;
        }
        if (this.ended() && !force) {
          return this._debug("Tour ended, start prevented.");
        }
        $(document).off("click.tour." + this._options.name, ".popover *[data-role=next]").on("click.tour." + this._options.name, ".popover *[data-role=next]:not(.disabled)", function(e) {
          e.preventDefault();
          return _this.next();
        });
        $(document).off("click.tour." + this._options.name, ".popover *[data-role=prev]").on("click.tour." + this._options.name, ".popover *[data-role=prev]:not(.disabled)", function(e) {
          e.preventDefault();
          return _this.prev();
        });
        $(document).off("click.tour." + this._options.name, ".popover *[data-role=end]").on("click.tour." + this._options.name, ".popover *[data-role=end]", function(e) {
          e.preventDefault();
          return _this.end();
        });
        this._onResize(function() {
          return _this.showStep(_this._current);
        });
        this._setupKeyboardNavigation();
        promise = this._makePromise(this._options.onStart != null ? this._options.onStart(this) : void 0);
        return this._callOnPromiseDone(promise, this.showStep, this._current);
      };

      Tour.prototype.next = function() {
        var promise;
        if (this.ended()) {
          return this._debug("Tour ended, next prevented.");
        }
        promise = this.hideStep(this._current);
        return this._callOnPromiseDone(promise, this._showNextStep);
      };

      Tour.prototype.prev = function() {
        var promise;
        if (this.ended()) {
          return this._debug("Tour ended, prev prevented.");
        }
        promise = this.hideStep(this._current);
        return this._callOnPromiseDone(promise, this._showPrevStep);
      };

      Tour.prototype.goto = function(i) {
        var promise;
        if (this.ended()) {
          return this._debug("Tour ended, goto prevented.");
        }
        promise = this.hideStep(this._current);
        return this._callOnPromiseDone(promise, this.showStep, i);
      };

      Tour.prototype.end = function() {
        var endHelper, hidePromise,
          _this = this;
        endHelper = function(e) {
          $(document).off("click.tour." + _this._options.name);
          $(document).off("keyup.tour." + _this._options.name);
          $(window).off("resize.tour." + _this._options.name);
          _this.setState("end", "yes");
          if (_this._options.onEnd != null) {
            return _this._options.onEnd(_this);
          }
        };
        hidePromise = this.hideStep(this._current);
        return this._callOnPromiseDone(hidePromise, endHelper);
      };

      Tour.prototype.ended = function() {
        return !!this.getState("end");
      };

      Tour.prototype.restart = function() {
        this.removeState("current_step");
        this.removeState("end");
        this.setCurrentStep(0);
        return this.start();
      };

      Tour.prototype.hideStep = function(i) {
        var hideStepHelper, promise, step,
          _this = this;
        step = this.getStep(i);
        promise = this._makePromise(step.onHide != null ? step.onHide(this, i) : void 0);
        hideStepHelper = function(e) {
          var $element;
          $element = _this._isOrphan(step) ? $("body") : $(step.element);
          $element.popover("destroy");
          if (step.reflex) {
            $element.css("cursor", "").off("click.tour." + _this._options.name);
          }
          if (step.backdrop) {
            _this._hideBackdrop();
          }
          if (step.onHidden != null) {
            return step.onHidden(_this);
          }
        };
        this._callOnPromiseDone(promise, hideStepHelper);
        return promise;
      };

      Tour.prototype.showStep = function(i) {
        var promise, showStepHelper, skipToPrevious, step,
          _this = this;
        step = this.getStep(i);
        if (!step) {
          return;
        }
        skipToPrevious = i < this._current;
        promise = this._makePromise(step.onShow != null ? step.onShow(this, i) : void 0);
        showStepHelper = function(e) {
          var current_path, path;
          _this.setCurrentStep(i);
          path = $.isFunction(step.path) ? step.path.call() : _this._options.basePath + step.path;
          current_path = [document.location.pathname, document.location.hash].join("");
          if (_this._isRedirect(path, current_path)) {
            _this._redirect(step, path);
            return;
          }
          if (_this._isOrphan(step)) {
            if (!step.orphan) {
              _this._debug("Skip the orphan step " + (_this._current + 1) + ". Orphan option is false and the element doesn't exist or is hidden.");
              if (skipToPrevious) {
                _this._showPrevStep();
              } else {
                _this._showNextStep();
              }
              return;
            }
            _this._debug("Show the orphan step " + (_this._current + 1) + ". Orphans option is true.");
          }
          if (step.backdrop) {
            _this._showBackdrop(!_this._isOrphan(step) ? step.element : void 0);
          }
          _this._showPopover(step, i);
          if (step.onShown != null) {
            step.onShown(_this);
          }
          return _this._debug("Step " + (_this._current + 1) + " of " + _this._steps.length);
        };
        return this._callOnPromiseDone(promise, showStepHelper);
      };

      Tour.prototype.setCurrentStep = function(value) {
        if (value != null) {
          this._current = value;
          return this.setState("current_step", value);
        } else {
          this._current = this.getState("current_step");
          return this._current = this._current === null ? 0 : parseInt(this._current, 10);
        }
      };

      Tour.prototype._showNextStep = function() {
        var promise, showNextStepHelper, step,
          _this = this;
        step = this.getStep(this._current);
        showNextStepHelper = function(e) {
          return _this.showStep(step.next);
        };
        promise = this._makePromise((step.onNext != null ? step.onNext(this) : void 0));
        return this._callOnPromiseDone(promise, showNextStepHelper);
      };

      Tour.prototype._showPrevStep = function() {
        var promise, showPrevStepHelper, step,
          _this = this;
        step = this.getStep(this._current);
        showPrevStepHelper = function(e) {
          return _this.showStep(step.prev);
        };
        promise = this._makePromise((step.onPrev != null ? step.onPrev(this) : void 0));
        return this._callOnPromiseDone(promise, showPrevStepHelper);
      };

      Tour.prototype._debug = function(text) {
        if (this._options.debug) {
          return window.console.log("Bootstrap Tour '" + this._options.name + "' | " + text);
        }
      };

      Tour.prototype._isRedirect = function(path, currentPath) {
        return (path != null) && path !== "" && path.replace(/\?.*$/, "").replace(/\/?$/, "") !== currentPath.replace(/\/?$/, "");
      };

      Tour.prototype._redirect = function(step, path) {
        if ($.isFunction(step.redirect)) {
          return step.redirect.call(this, path);
        } else if (step.redirect === true) {
          this._debug("Redirect to " + path);
          return document.location.href = path;
        }
      };

      Tour.prototype._isOrphan = function(step) {
        return (step.element == null) || !$(step.element).length || $(step.element).is(":hidden");
      };

      Tour.prototype._showPopover = function(step, i) {
        var $element, $navigation, $template, $tip, isOrphan, options,
          _this = this;
        options = $.extend({}, this._options);
        $template = $.isFunction(step.template) ? $(step.template(i, step)) : $(step.template);
        $navigation = $template.find(".popover-navigation");
        isOrphan = this._isOrphan(step);
        if (isOrphan) {
          step.element = "body";
          step.placement = "top";
          $template = $template.addClass("orphan");
        }
        $element = $(step.element);
        $template.addClass("tour-" + this._options.name);
        if (step.options) {
          $.extend(options, step.options);
        }
        if (step.reflex) {
          $element.css("cursor", "pointer").on("click.tour." + this._options.name, function(e) {
            if (_this._current < _this._steps.length - 1) {
              return _this.next();
            } else {
              return _this.end();
            }
          });
        }
        if (step.prev < 0) {
          $navigation.find("*[data-role=prev]").addClass("disabled");
        }
        if (step.next < 0) {
          $navigation.find("*[data-role=next]").addClass("disabled");
        }
        step.template = $template.clone().wrap("<div>").parent().html();
        $element.popover({
          placement: step.placement,
          trigger: "manual",
          title: step.title,
          content: step.content,
          html: true,
          animation: step.animation,
          container: step.container,
          template: step.template,
          selector: step.element
        }).popover("show");
        $tip = $element.data("bs.popover") ? $element.data("bs.popover").tip() : $element.data("popover").tip();
        $tip.attr("id", step.id);
        this._scrollIntoView($tip);
        this._reposition($tip, step);
        if (isOrphan) {
          return this._center($tip);
        }
      };

      Tour.prototype._reposition = function($tip, step) {
        var offsetBottom, offsetHeight, offsetRight, offsetWidth, originalLeft, originalTop, tipOffset;
        offsetWidth = $tip[0].offsetWidth;
        offsetHeight = $tip[0].offsetHeight;
        tipOffset = $tip.offset();
        originalLeft = tipOffset.left;
        originalTop = tipOffset.top;
        offsetBottom = $(document).outerHeight() - tipOffset.top - $tip.outerHeight();
        if (offsetBottom < 0) {
          tipOffset.top = tipOffset.top + offsetBottom;
        }
        offsetRight = $("html").outerWidth() - tipOffset.left - $tip.outerWidth();
        if (offsetRight < 0) {
          tipOffset.left = tipOffset.left + offsetRight;
        }
        if (tipOffset.top < 0) {
          tipOffset.top = 0;
        }
        if (tipOffset.left < 0) {
          tipOffset.left = 0;
        }
        $tip.offset(tipOffset);
        if (step.placement === "bottom" || step.placement === "top") {
          if (originalLeft !== tipOffset.left) {
            return this._replaceArrow($tip, (tipOffset.left - originalLeft) * 2, offsetWidth, "left");
          }
        } else {
          if (originalTop !== tipOffset.top) {
            return this._replaceArrow($tip, (tipOffset.top - originalTop) * 2, offsetHeight, "top");
          }
        }
      };

      Tour.prototype._center = function($tip) {
        return $tip.css("top", $(window).outerHeight() / 2 - $tip.outerHeight() / 2);
      };

      Tour.prototype._replaceArrow = function($tip, delta, dimension, position) {
        return $tip.find(".arrow").css(position, delta ? 50 * (1 - delta / dimension) + "%" : "");
      };

      Tour.prototype._scrollIntoView = function(tip) {
        return $("html, body").stop().animate({
          scrollTop: Math.ceil(tip.offset().top - ($(window).height() / 2))
        });
      };

      Tour.prototype._onResize = function(callback, timeout) {
        return $(window).on("resize.tour." + this._options.name, function() {
          clearTimeout(timeout);
          return timeout = setTimeout(callback, 100);
        });
      };

      Tour.prototype._setupKeyboardNavigation = function() {
        var _this = this;
        if (this._options.keyboard) {
          return $(document).on("keyup.tour." + this._options.name, function(e) {
            if (!e.which) {
              return;
            }
            switch (e.which) {
              case 39:
                e.preventDefault();
                if (_this._current < _this._steps.length - 1) {
                  return _this.next();
                } else {
                  return _this.end();
                }
                break;
              case 37:
                e.preventDefault();
                if (_this._current > 0) {
                  return _this.prev();
                }
                break;
              case 27:
                e.preventDefault();
                return _this.end();
            }
          });
        }
      };

      Tour.prototype._makePromise = function(result) {
        if (result && $.isFunction(result.then)) {
          return result;
        } else {
          return null;
        }
      };

      Tour.prototype._callOnPromiseDone = function(promise, cb, arg) {
        var _this = this;
        if (promise) {
          return promise.then(function(e) {
            return cb.call(_this, arg);
          });
        } else {
          return cb.call(this, arg);
        }
      };

      Tour.prototype._showBackdrop = function(element) {
        if (this.backdrop.overlay !== null) {
          return;
        }
        this._showOverlay();
        if (element != null) {
          return this._showOverlayElement(element);
        }
      };

      Tour.prototype._hideBackdrop = function() {
        if (this.backdrop.overlay === null) {
          return;
        }
        if (this.backdrop.$element) {
          this._hideOverlayElement();
        }
        return this._hideOverlay();
      };

      Tour.prototype._showOverlay = function() {
        this.backdrop = $("<div/>");
        this.backdrop.addClass("tour-backdrop");
        this.backdrop.height($(document).innerHeight());
        return $("body").append(this.backdrop);
      };

      Tour.prototype._hideOverlay = function() {
        this.backdrop.remove();
        return this.backdrop.overlay = null;
      };

      Tour.prototype._showOverlayElement = function(element) {
        var $background, $element, offset;
        $element = $(element);
        $background = $("<div/>");
        offset = $element.offset();
        offset.top = offset.top;
        offset.left = offset.left;
        $background.width($element.innerWidth()).height($element.innerHeight()).addClass("tour-step-background").offset(offset);
        $element.addClass("tour-step-backdrop");
        $("body").append($background);
        this.backdrop.$element = $element;
        return this.backdrop.$background = $background;
      };

      Tour.prototype._hideOverlayElement = function() {
        this.backdrop.$element.removeClass("tour-step-backdrop");
        this.backdrop.$background.remove();
        this.backdrop.$element = null;
        return this.backdrop.$background = null;
      };

      return Tour;

    })();
    return window.Tour = Tour;
  })(jQuery, window);

}).call(this);
