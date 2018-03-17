(function(root, factory) {
    if (typeof define === 'function' && define.amd) {
        define(factory);
    } else if (typeof exports === 'object') {
        module.exports = factory(require, exports, module);
    } else {
        root.CountUp = factory();
    }
}(this, function(require, exports, module) {

    /*
        countUp.js
        by @inorganik
    */

    // target = id of html element or var of previously selected html element where counting occurs
    // startVal = the value you want to begin at
    // endVal = the value you want to arrive at
    // decimals = number of decimal places, default 0
    // duration = duration of animation in seconds, default 2
    // options = optional object of options (see below)

    var CountUp = function(target, startVal, endVal, decimals, duration, options) {

        // make sure requestAnimationFrame and cancelAnimationFrame are defined
        // polyfill for browsers without native support
        // by Opera engineer Erik Möller
        var lastTime = 0;
        var vendors = ['webkit', 'moz', 'ms', 'o'];
        for (var x = 0; x < vendors.length && !window.requestAnimationFrame; ++x) {
            window.requestAnimationFrame = window[vendors[x] + 'RequestAnimationFrame'];
            window.cancelAnimationFrame =
                window[vendors[x] + 'CancelAnimationFrame'] || window[vendors[x] + 'CancelRequestAnimationFrame'];
        }
        if (!window.requestAnimationFrame) {
            window.requestAnimationFrame = function(callback, element) {
                var currTime = new Date().getTime();
                var timeToCall = Math.max(0, 16 - (currTime - lastTime));
                var id = window.setTimeout(function() {
                        callback(currTime + timeToCall);
                    },
                    timeToCall);
                lastTime = currTime + timeToCall;
                return id;
            };
        }
        if (!window.cancelAnimationFrame) {
            window.cancelAnimationFrame = function(id) {
                clearTimeout(id);
            };
        }

        var self = this;

        // default options
        self.options = {
            useEasing: true, // toggle easing
            useGrouping: true, // 1,000,000 vs 1000000
            separator: ',', // character to use as a separator
            decimal: '.', // character to use as a decimal
            easingFn: null, // optional custom easing closure function, default is Robert Penner's easeOutExpo
            formattingFn: null // optional custom formatting function, default is self.formatNumber below
        };
        // extend default options with passed options object
        for (var key in options) {
            if (options.hasOwnProperty(key)) {
                self.options[key] = options[key];
            }
        }
        if (self.options.separator === '') {
            self.options.useGrouping = false;
        }
        if (!self.options.prefix) self.options.prefix = '';
        if (!self.options.suffix) self.options.suffix = '';

        self.d = (typeof target === 'string') ? document.getElementById(target) : target;
        self.startVal = Number(startVal);
        self.endVal = Number(endVal);
        self.countDown = (self.startVal > self.endVal);
        self.frameVal = self.startVal;
        self.decimals = Math.max(0, decimals || 0);
        self.dec = Math.pow(10, self.decimals);
        self.duration = Number(duration) * 1000 || 2000;

        self.formatNumber = function(nStr) {
            nStr = nStr.toFixed(self.decimals);
            nStr += '';
            var x, x1, x2, rgx;
            x = nStr.split('.');
            x1 = x[0];
            x2 = x.length > 1 ? self.options.decimal + x[1] : '';
            rgx = /(\d+)(\d{3})/;
            if (self.options.useGrouping) {
                while (rgx.test(x1)) {
                    x1 = x1.replace(rgx, '$1' + self.options.separator + '$2');
                }
            }
            return self.options.prefix + x1 + x2 + self.options.suffix;
        };
        // Robert Penner's easeOutExpo
        self.easeOutExpo = function(t, b, c, d) {
            return c * (-Math.pow(2, -10 * t / d) + 1) * 1024 / 1023 + b;
        };

        self.easingFn = self.options.easingFn ? self.options.easingFn : self.easeOutExpo;
        self.formattingFn = self.options.formattingFn ? self.options.formattingFn : self.formatNumber;

        self.version = function() {
            return '1.7.1';
        };

        // Print value to target
        self.printValue = function(value) {
            var result = self.formattingFn(value);

            if (self.d.tagName === 'INPUT') {
                this.d.value = result;
            } else if (self.d.tagName === 'text' ||  self.d.tagName === 'tspan') {
                this.d.textContent = result;
            } else {
                this.d.innerHTML = result;
            }
        };

        self.count = function(timestamp) {

            if (!self.startTime) {
                self.startTime = timestamp;
            }

            self.timestamp = timestamp;
            var progress = timestamp - self.startTime;
            self.remaining = self.duration - progress;

            // to ease or not to ease
            if (self.options.useEasing) {
                if (self.countDown) {
                    self.frameVal = self.startVal - self.easingFn(progress, 0, self.startVal - self.endVal, self.duration);
                } else {
                    self.frameVal = self.easingFn(progress, self.startVal, self.endVal - self.startVal, self.duration);
                }
            } else {
                if (self.countDown) {
                    self.frameVal = self.startVal - ((self.startVal - self.endVal) * (progress / self.duration));
                } else {
                    self.frameVal = self.startVal + (self.endVal - self.startVal) * (progress / self.duration);
                }
            }

            // don't go past endVal since progress can exceed duration in the last frame
            if (self.countDown) {
                self.frameVal = (self.frameVal < self.endVal) ? self.endVal : self.frameVal;
            } else {
                self.frameVal = (self.frameVal > self.endVal) ? self.endVal : self.frameVal;
            }

            // decimal
            self.frameVal = Math.round(self.frameVal * self.dec) / self.dec;

            // format and print value
            self.printValue(self.frameVal);

            // whether to continue
            if (progress < self.duration) {
                self.rAF = requestAnimationFrame(self.count);
            } else {
                if (self.callback) {
                    self.callback();
                }
            }
        };
        // start your animation
        self.start = function(callback) {
            self.callback = callback;
            self.rAF = requestAnimationFrame(self.count);
            return false;
        };
        // toggles pause/resume animation
        self.pauseResume = function() {
            if (!self.paused) {
                self.paused = true;
                cancelAnimationFrame(self.rAF);
            } else {
                self.paused = false;
                delete self.startTime;
                self.duration = self.remaining;
                self.startVal = self.frameVal;
                requestAnimationFrame(self.count);
            }
        };
        // reset to startVal so animation can be run again
        self.reset = function() {
            self.paused = false;
            delete self.startTime;
            self.startVal = startVal;
            cancelAnimationFrame(self.rAF);
            self.printValue(self.startVal);
        };
        // pass a new endVal and start animation
        self.update = function(newEndVal) {
            cancelAnimationFrame(self.rAF);
            self.paused = false;
            delete self.startTime;
            self.startVal = self.frameVal;
            self.endVal = Number(newEndVal);
            self.countDown = (self.startVal > self.endVal);
            self.rAF = requestAnimationFrame(self.count);
        };

        // format startVal on initialization
        self.printValue(self.startVal);
    };

    return CountUp;

}));
