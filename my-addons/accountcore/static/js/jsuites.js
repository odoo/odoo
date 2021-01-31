odoo.define('accountcore.jsuites', function (require) {
    'use strict';
    var jSuites = function (options) {
        var obj = {}
        // Find root element
        obj.el = document.querySelector('.app');
        // Backdrop
        obj.backdrop = document.createElement('div');
        obj.backdrop.classList.add('jbackdrop');
        obj.getWindowWidth = function () {
            var w = window,
                d = document,
                e = d.documentElement,
                g = d.getElementsByTagName('body')[0],
                x = w.innerWidth || e.clientWidth || g.clientWidth;
            return x;
        }
        obj.getWindowHeight = function () {
            var w = window,
                d = document,
                e = d.documentElement,
                g = d.getElementsByTagName('body')[0],
                y = w.innerHeight || e.clientHeight || g.clientHeight;
            return y;
        }
        obj.getPosition = function (e) {
            if (e.changedTouches && e.changedTouches[0]) {
                var x = e.changedTouches[0].pageX;
                var y = e.changedTouches[0].pageY;
            } else {
                var x = (window.Event) ? e.pageX : e.clientX + (document.documentElement.scrollLeft ? document.documentElement.scrollLeft : document.body.scrollLeft);
                var y = (window.Event) ? e.pageY : e.clientY + (document.documentElement.scrollTop ? document.documentElement.scrollTop : document.body.scrollTop);
            }
            return [x, y];
        }
        obj.click = function (el) {
            if (el.click) {
                el.click();
            } else {
                var evt = new MouseEvent('click', {
                    bubbles: true,
                    cancelable: true,
                    view: window
                });
                el.dispatchEvent(evt);
            }
        }
        obj.getElement = function (element, className) {
            var foundElement = false;

            function path(element) {
                if (element.className) {
                    if (element.classList.contains(className)) {
                        foundElement = element;
                    }
                }
                if (element.parentNode) {
                    path(element.parentNode);
                }
            }
            path(element);
            return foundElement;
        }
        obj.getLinkElement = function (element) {
            var targetElement = false;

            function path(element) {
                if ((element.tagName == 'A' || element.tagName == 'DIV') && element.getAttribute('data-href')) {
                    targetElement = element;
                }
                if (element.parentNode) {
                    path(element.parentNode);
                }
            }
            path(element);
            return targetElement;
        }
        obj.getFormElements = function (formObject) {
            var ret = {};
            if (formObject) {
                var elements = formObject.querySelectorAll("input, select, textarea");
            } else {
                var elements = document.querySelectorAll("input, select, textarea");
            }
            for (var i = 0; i < elements.length; i++) {
                var element = elements[i];
                var name = element.name;
                var value = element.value;
                if (name) {
                    ret[name] = value;
                }
            }
            return ret;
        }
        obj.exists = function (url, __callback) {
            var http = new XMLHttpRequest();
            http.open('HEAD', url, false);
            http.send();
            if (http.status) {
                __callback(http.status);
            }
        }
        obj.getFiles = function (element) {
            if (!element) {
                console.error('No element defined in the arguments of your method');
            }
            // Get attachments
            var files = element.querySelectorAll('.jfile');
            if (files.length > 0) {
                var data = [];
                for (var i = 0; i < files.length; i++) {
                    var file = {};
                    var src = files[i].getAttribute('src');
                    if (files[i].classList.contains('jremove')) {
                        file.remove = 1;
                    } else {
                        if (src.substr(0, 4) == 'data') {
                            file.content = src.substr(src.indexOf(',') + 1);
                            file.extension = files[i].getAttribute('data-extension');
                        } else {
                            file.file = src;
                            file.extension = files[i].getAttribute('data-extension');
                            if (!file.extension) {
                                file.extension = src.substr(src.lastIndexOf('.') + 1);
                            }
                            if (jSuites.files[file.file]) {
                                file.content = jSuites.files[file.file];
                            }
                        }
                        // Optional file information
                        if (files[i].getAttribute('data-name')) {
                            file.name = files[i].getAttribute('data-name');
                        }
                        if (files[i].getAttribute('data-file')) {
                            file.file = files[i].getAttribute('data-file');
                        }
                        if (files[i].getAttribute('data-size')) {
                            file.size = files[i].getAttribute('data-size');
                        }
                        if (files[i].getAttribute('data-date')) {
                            file.date = files[i].getAttribute('data-date');
                        }
                        if (files[i].getAttribute('data-cover')) {
                            file.cover = files[i].getAttribute('data-cover');
                        }
                    }
                    // TODO SMALL thumbs?
                    data[i] = file;
                }
                return data;
            }
        }
        obj.ajax = function (options) {
            if (!options.data) {
                options.data = {};
            }
            if (options.type) {
                options.method = options.type;
            }
            if (options.data) {
                var data = [];
                var keys = Object.keys(options.data);
                if (keys.length) {
                    for (var i = 0; i < keys.length; i++) {
                        if (typeof (options.data[keys[i]]) == 'object') {
                            var o = options.data[keys[i]];
                            for (var j = 0; j < o.length; j++) {
                                if (typeof (o[j]) == 'string') {
                                    data.push(keys[i] + '[' + j + ']=' + encodeURIComponent(o[j]));
                                } else {
                                    var prop = Object.keys(o[j]);
                                    for (var z = 0; z < prop.length; z++) {
                                        data.push(keys[i] + '[' + j + '][' + prop[z] + ']=' + encodeURIComponent(o[j][prop[z]]));
                                    }
                                }
                            }
                        } else {
                            data.push(keys[i] + '=' + encodeURIComponent(options.data[keys[i]]));
                        }
                    }
                }
                if (options.method == 'GET' && data.length > 0) {
                    if (options.url.indexOf('?') < 0) {
                        options.url += '?';
                    }
                    options.url += data.join('&');
                }
            }
            var httpRequest = new XMLHttpRequest();
            httpRequest.open(options.method, options.url, true);
            if (options.method == 'POST') {
                httpRequest.setRequestHeader('Accept', 'application/json');
                httpRequest.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
            } else {
                if (options.dataType == 'json') {
                    httpRequest.setRequestHeader('Content-Type', 'text/json');
                }
            }
            // No cache
            httpRequest.setRequestHeader('pragma', 'no-cache');
            httpRequest.setRequestHeader('cache-control', 'no-cache');
            httpRequest.onload = function () {
                if (httpRequest.status === 200) {
                    if (options.dataType == 'json') {
                        var result = JSON.parse(httpRequest.responseText);
                    } else {
                        var result = httpRequest.responseText;
                    }
                    if (options.success && typeof (options.success) == 'function') {
                        options.success(result);
                    }
                } else {
                    if (options.error && typeof (options.error) == 'function') {
                        options.error(httpRequest.responseText);
                    }
                }
                // Global complete method
                if (options.multiple && options.multiple.length) {
                    // Get index of this request in the container
                    var index = options.multiple[options.multiple.indexOf(httpRequest)];
                    // Remove from the ajax requests container
                    options.multiple.splice(index, 1);
                    // Last one?
                    if (!options.multiple.length) {
                        if (options.complete && typeof (options.complete) == 'function') {
                            options.complete(result);
                        }
                    }
                }
            }
            if (data) {
                httpRequest.send(data.join('&'));
            } else {
                httpRequest.send();
            }
            return httpRequest;
        }
        obj.slideLeft = function (element, direction, done) {
            if (direction == true) {
                element.classList.add('slide-left-in');
                setTimeout(function () {
                    element.classList.remove('slide-left-in');
                    if (typeof (done) == 'function') {
                        done();
                    }
                }, 400);
            } else {
                element.classList.add('slide-left-out');
                setTimeout(function () {
                    element.classList.remove('slide-left-out');
                    if (typeof (done) == 'function') {
                        done();
                    }
                }, 400);
            }
        }
        obj.slideRight = function (element, direction, done) {
            if (direction == true) {
                element.classList.add('slide-right-in');
                setTimeout(function () {
                    element.classList.remove('slide-right-in');
                    if (typeof (done) == 'function') {
                        done();
                    }
                }, 400);
            } else {
                element.classList.add('slide-right-out');
                setTimeout(function () {
                    element.classList.remove('slide-right-out');
                    if (typeof (done) == 'function') {
                        done();
                    }
                }, 400);
            }
        }
        obj.slideTop = function (element, direction, done) {
            if (direction == true) {
                element.classList.add('slide-top-in');
                setTimeout(function () {
                    element.classList.remove('slide-top-in');
                    if (typeof (done) == 'function') {
                        done();
                    }
                }, 400);
            } else {
                element.classList.add('slide-top-out');
                setTimeout(function () {
                    element.classList.remove('slide-top-out');
                    if (typeof (done) == 'function') {
                        done();
                    }
                }, 400);
            }
        }
        obj.slideBottom = function (element, direction, done) {
            if (direction == true) {
                element.classList.add('slide-bottom-in');
                setTimeout(function () {
                    element.classList.remove('slide-bottom-in');
                    if (typeof (done) == 'function') {
                        done();
                    }
                }, 400);
            } else {
                element.classList.add('slide-bottom-out');
                setTimeout(function () {
                    element.classList.remove('slide-bottom-out');
                    if (typeof (done) == 'function') {
                        done();
                    }
                }, 100);
            }
        }
        obj.fadeIn = function (element, done) {
            element.classList.add('fade-in');
            setTimeout(function () {
                element.classList.remove('fade-in');
                if (typeof (done) == 'function') {
                    done();
                }
            }, 2000);
        }
        obj.fadeOut = function (element, done) {
            element.classList.add('fade-out');
            setTimeout(function () {
                element.classList.remove('fade-out');
                if (typeof (done) == 'function') {
                    done();
                }
            }, 1000);
        }
        obj.keyDownControls = function (e) {
            if (e.which == 27) {
                var nodes = document.querySelectorAll('.jmodal');
                if (nodes.length > 0) {
                    for (var i = 0; i < nodes.length; i++) {
                        nodes[i].modal.close();
                    }
                }
                var nodes = document.querySelectorAll('.jslider');
                if (nodes.length > 0) {
                    for (var i = 0; i < nodes.length; i++) {
                        nodes[i].slider.close();
                    }
                }
                if (document.querySelector('.jdialog')) {
                    jSuites.dialog.close();
                }
            } else if (e.which == 13) {
                if (document.querySelector('.jdialog')) {
                    if (typeof (jSuites.dialog.options.onconfirm) == 'function') {
                        jSuites.dialog.options.onconfirm();
                    }
                    jSuites.dialog.close();
                }
            }
            // Verify mask
            if (jSuites.mask) {
                jSuites.mask.apply(e);
            }
        }
        obj.actionUpControl = function (e) {
            var element = null;
            if (element = jSuites.getLinkElement(e.target)) {
                var link = element.getAttribute('data-href');
                if (link == '#back') {
                    window.history.back();
                } else if (link == '#panel') {
                    jSuites.panel();
                } else {
                    jSuites.pages(link);
                }
            }
        }
        var controlSwipeLeft = function (e) {
            var element = jSuites.getElement(e.target, 'option');
            if (element && element.querySelector('.option-actions')) {
                element.scrollTo({
                    left: 100,
                    behavior: 'smooth'
                });
            } else {
                var element = jSuites.getElement(e.target, 'jcalendar');
                if (element && jSuites.calendar.current) {
                    jSuites.calendar.current.prev();
                } else {
                    var element = jSuites.panel.get();
                    if (element) {
                        if (element.style.display != 'none') {
                            jSuites.panel.close();
                        }
                    }
                }
            }
        }
        var controlSwipeRight = function (e) {
            var element = jSuites.getElement(e.target, 'option');
            if (element && element.querySelector('.option-actions')) {
                element.scrollTo({
                    left: 0,
                    behavior: 'smooth'
                });
            } else {
                var element = jSuites.getElement(e.target, 'jcalendar');
                if (element && jSuites.calendar.current) {
                    jSuites.calendar.current.next();
                } else {
                    var element = jSuites.panel.get();
                    if (element) {
                        if (element.style.display == 'none') {
                            jSuites.panel();
                        }
                    }
                }
            }
        }
        // Create page container
        document.addEventListener('swipeleft', controlSwipeLeft);
        document.addEventListener('swiperight', controlSwipeRight);
        document.addEventListener('keydown', obj.keyDownControls);
        if ('ontouchend' in document.documentElement === true) {
            document.addEventListener('touchend', obj.actionUpControl);
        } else {
            document.addEventListener('mouseup', obj.actionUpControl);
        }
        // Pop state control
        window.onpopstate = function (e) {
            if (e.state && e.state.route) {
                if (jSuites.pages.get(e.state.route)) {
                    jSuites.pages(e.state.route, {
                        ignoreHistory: true
                    });
                }
            }
        }
        return obj;
    }();
    jSuites.files = [];
    jSuites.calendar = (function (el, options) {
        var obj = {};
        obj.options = {};
        // Global container
        if (!jSuites.calendar.current) {
            jSuites.calendar.current = null;
        }
        // Default configuration
        var defaults = {
            // Date format
            format: 'DD/MM/YYYY',
            // Allow keyboard date entry
            readonly: true,
            // Today is default
            today: false,
            // Show timepicker
            time: false,
            // Show the reset button
            resetButton: true,
            // Placeholder
            placeholder: '',
            // Translations can be done here
            months: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            weekdays: ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
            weekdays_short: ['S', 'M', 'T', 'W', 'T', 'F', 'S'],
            // Value
            value: null,
            // Events
            onclose: null,
            onchange: null,
            // Fullscreen (this is automatic set for screensize < 800)
            fullscreen: false,
            // Internal mode controller
            mode: null,
            position: null,
            // Create the calendar closed as default
            opened: false,
        };
        // Loop through our object
        for (var property in defaults) {
            if (options && options.hasOwnProperty(property)) {
                obj.options[property] = options[property];
            } else {
                obj.options[property] = defaults[property];
            }
        }
        // Value
        if (!obj.options.value && el.value) {
            obj.options.value = el.value;
        }
        // Make sure use upper case in the format
        obj.options.format = obj.options.format.toUpperCase();
        if (obj.options.value) {
            var date = obj.options.value.split(' ');
            var time = date[1];
            var date = date[0].split('-');
            var y = parseInt(date[0]);
            var m = parseInt(date[1]);
            var d = parseInt(date[2]);
            if (time) {
                var time = time.split(':');
                var h = parseInt(time[0]);
                var i = parseInt(time[1]);
            } else {
                var h = 0;
                var i = 0;
            }
        } else {
            var date = new Date();
            var y = date.getFullYear();
            var m = date.getMonth() + 1;
            var d = date.getDate();
            var h = date.getHours();
            var i = date.getMinutes();
        }
        // Current value
        obj.date = [y, m, d, h, i, 0];
        // Two digits
        var two = function (value) {
            value = '' + value;
            if (value.length == 1) {
                value = '0' + value;
            }
            return value;
        }
        // Element
        el.classList.add('jcalendar-input');
        // Calendar elements
        var calendarReset = document.createElement('div');
        calendarReset.className = 'jcalendar-reset';
        calendarReset.innerHTML = 'Reset';
        var calendarConfirm = document.createElement('div');
        calendarConfirm.className = 'jcalendar-confirm';
        calendarConfirm.innerHTML = 'Done';
        var calendarControls = document.createElement('div');
        calendarControls.className = 'jcalendar-controls'
        if (obj.options.resetButton) {
            calendarControls.appendChild(calendarReset);
        }
        calendarControls.appendChild(calendarConfirm);
        var calendarContainer = document.createElement('div');
        calendarContainer.className = 'jcalendar-container';
        var calendarContent = document.createElement('div');
        calendarContent.className = 'jcalendar-content';
        calendarContent.appendChild(calendarControls);
        calendarContainer.appendChild(calendarContent);
        // Main element
        var calendar = document.createElement('div');
        calendar.className = 'jcalendar';
        calendar.appendChild(calendarContainer);
        // Previous button
        var calendarHeaderPrev = document.createElement('td');
        calendarHeaderPrev.setAttribute('colspan', '2');
        calendarHeaderPrev.className = 'jcalendar-prev';
        // Header with year and month
        var calendarLabelYear = document.createElement('span');
        calendarLabelYear.className = 'jcalendar-year';
        var calendarLabelMonth = document.createElement('span');
        calendarLabelMonth.className = 'jcalendar-month';
        var calendarHeaderTitle = document.createElement('td');
        calendarHeaderTitle.className = 'jcalendar-header';
        calendarHeaderTitle.setAttribute('colspan', '3');
        calendarHeaderTitle.appendChild(calendarLabelMonth);
        calendarHeaderTitle.appendChild(calendarLabelYear);
        var calendarHeaderNext = document.createElement('td');
        calendarHeaderNext.setAttribute('colspan', '2');
        calendarHeaderNext.className = 'jcalendar-next';
        var calendarHeaderRow = document.createElement('tr');
        calendarHeaderRow.appendChild(calendarHeaderPrev);
        calendarHeaderRow.appendChild(calendarHeaderTitle);
        calendarHeaderRow.appendChild(calendarHeaderNext);
        var calendarHeader = document.createElement('thead');
        calendarHeader.appendChild(calendarHeaderRow);
        var calendarBody = document.createElement('tbody');
        var calendarFooter = document.createElement('tfoot');
        // Calendar table
        var calendarTable = document.createElement('table');
        calendarTable.setAttribute('cellpadding', '0');
        calendarTable.setAttribute('cellspacing', '0');
        calendarTable.appendChild(calendarHeader);
        calendarTable.appendChild(calendarBody);
        calendarTable.appendChild(calendarFooter);
        calendarContent.appendChild(calendarTable);
        var calendarSelectHour = document.createElement('select');
        calendarSelectHour.className = 'jcalendar-select';
        calendarSelectHour.onchange = function () {
            obj.date[3] = this.value;
        }
        for (var i = 0; i < 24; i++) {
            var element = document.createElement('option');
            element.value = i;
            element.innerHTML = two(i);
            calendarSelectHour.appendChild(element);
        }
        var calendarSelectMin = document.createElement('select');
        calendarSelectMin.className = 'jcalendar-select';
        calendarSelectMin.onchange = function () {
            obj.date[4] = this.value;
        }
        for (var i = 0; i < 60; i++) {
            var element = document.createElement('option');
            element.value = i;
            element.innerHTML = two(i);
            calendarSelectMin.appendChild(element);
        }
        // Footer controls
        var calendarControls = document.createElement('div');
        calendarControls.className = 'jcalendar-controls';
        var calendarControlsTime = document.createElement('div');
        calendarControlsTime.className = 'jcalendar-time';
        calendarControlsTime.style.maxWidth = '140px';
        calendarControlsTime.appendChild(calendarSelectHour);
        calendarControlsTime.appendChild(calendarSelectMin);
        var calendarControlsUpdate = document.createElement('div');
        calendarControlsUpdate.style.flexGrow = '10';
        calendarControlsUpdate.innerHTML = '<input type="button" class="jcalendar-update" value="Update">'
        calendarControls.appendChild(calendarControlsTime);
        calendarControls.appendChild(calendarControlsUpdate);
        calendarContent.appendChild(calendarControls);
        var calendarBackdrop = document.createElement('div');
        calendarBackdrop.className = 'jcalendar-backdrop';
        calendar.appendChild(calendarBackdrop);
        // Methods
        obj.open = function (value) {
            if (!calendar.classList.contains('jcalendar-focus')) {
                if (jSuites.calendar.current) {
                    jSuites.calendar.current.close();
                }
                // Current
                jSuites.calendar.current = obj;
                // Show calendar
                calendar.classList.add('jcalendar-focus');
                // Get days
                obj.getDays();
                // Hour
                if (obj.options.time) {
                    calendarSelectHour.value = obj.date[3];
                    calendarSelectMin.value = obj.date[4];
                }
                // Get the position of the corner helper
                if (jSuites.getWindowWidth() < 800 || obj.options.fullscreen) {
                    // Full
                    calendar.classList.add('jcalendar-fullsize');
                    // Animation
                    jSuites.slideBottom(calendarContent, 1);
                } else {
                    const rect = el.getBoundingClientRect();
                    const rectContent = calendarContent.getBoundingClientRect();
                    if (obj.options.position) {
                        calendarContainer.style.position = 'fixed';
                        if (window.innerHeight < rect.bottom + rectContent.height) {
                            calendarContainer.style.top = (rect.top - (rectContent.height + 2)) + 'px';
                        } else {
                            calendarContainer.style.top = (rect.top + rect.height + 2) + 'px';
                        }
                        calendarContainer.style.left = rect.left;
                    } else {
                        if (window.innerHeight < rect.bottom + rectContent.height) {
                            calendarContainer.style.bottom = (1 * rect.height + rectContent.height + 2) + 'px';
                        } else {
                            calendarContainer.style.top = 2 + 'px';
                        }
                    }
                }
            }
        }
        obj.close = function (ignoreEvents, update) {
            // Current
            jSuites.calendar.current = null;
            if (update != false && el.tagName == 'INPUT') {
                obj.setValue(obj.getValue());
            }
            // Animation
            if (!ignoreEvents && typeof (obj.options.onclose) == 'function') {
                obj.options.onclose(el);
            }
            // Hide
            calendar.classList.remove('jcalendar-focus');
            return obj.getValue();
        }
        obj.prev = function () {
            // Check if the visualization is the days picker or years picker
            if (obj.options.mode == 'years') {
                obj.date[0] = obj.date[0] - 12;
                // Update picker table of days
                obj.getYears();
            } else {
                // Go to the previous month
                if (obj.date[1] < 2) {
                    obj.date[0] = obj.date[0] - 1;
                    obj.date[1] = 1;
                } else {
                    obj.date[1] = obj.date[1] - 1;
                }
                // Update picker table of days
                obj.getDays();
            }
        }
        obj.next = function () {
            // Check if the visualization is the days picker or years picker
            if (obj.options.mode == 'years') {
                obj.date[0] = parseInt(obj.date[0]) + 12;
                // Update picker table of days
                obj.getYears();
            } else {
                // Go to the previous month
                if (obj.date[1] > 11) {
                    obj.date[0] = obj.date[0] + 1;
                    obj.date[1] = 1;
                } else {
                    obj.date[1] = obj.date[1] + 1;
                }
                // Update picker table of days
                obj.getDays();
            }
        }
        obj.setValue = function (val) {
            if (val) {
                // Keep value
                obj.options.value = val;
                // Set label
                var value = obj.setLabel(val, obj.options.format);
                var date = obj.options.value.split(' ');
                if (!date[1]) {
                    date[1] = '00:00:00';
                }
                var time = date[1].split(':')
                var date = date[0].split('-');
                var y = parseInt(date[0]);
                var m = parseInt(date[1]);
                var d = parseInt(date[2]);
                var h = parseInt(time[0]);
                var i = parseInt(time[1]);
                obj.date = [y, m, d, h, i, 0];
                var val = obj.setLabel(val, obj.options.format);
                if (el.value != val) {
                    el.value = val;
                    // On change
                    if (typeof (obj.options.onchange) == 'function') {
                        obj.options.onchange(el, val, obj.date);
                    }
                }
                obj.getDays();
            }
        }
        obj.getValue = function () {
            if (obj.date) {
                if (obj.options.time) {
                    return two(obj.date[0]) + '-' + two(obj.date[1]) + '-' + two(obj.date[2]) + ' ' + two(obj.date[3]) + ':' + two(obj.date[4]) + ':' + two(0);
                } else {
                    return two(obj.date[0]) + '-' + two(obj.date[1]) + '-' + two(obj.date[2]) + ' ' + two(0) + ':' + two(0) + ':' + two(0);
                }
            } else {
                return "";
            }
        }
        /**
         * Update calendar
         */
        obj.update = function (element) {
            obj.date[2] = element.innerText;
            if (!obj.options.time) {
                obj.close();
            } else {
                obj.date[3] = calendarSelectHour.value;
                obj.date[4] = calendarSelectMin.value;
            }
            var elements = calendar.querySelector('.jcalendar-selected');
            if (elements) {
                elements.classList.remove('jcalendar-selected');
            }
            element.classList.add('jcalendar-selected')
        }
        /**
         * Set to blank
         */
        obj.reset = function () {
            // Clear element
            obj.date = null;
            // Reset element
            el.value = '';
            // Close calendar
            obj.close();
        }
        /**
         * Get calendar days
         */
        obj.getDays = function () {
            // Mode
            obj.options.mode = 'days';
            // Variables
            var d = 0;
            var today = 0;
            var today_d = 0;
            var calendar_day;
            // Setting current values in case of NULLs
            var date = new Date();
            var year = obj.date && obj.date[0] ? obj.date[0] : parseInt(date.getFullYear());
            var month = obj.date && obj.date[1] ? obj.date[1] : parseInt(date.getMonth()) + 1;
            var day = obj.date && obj.date[2] ? obj.date[2] : parseInt(date.getDay());
            var hour = obj.date && obj.date[3] ? obj.date[3] : parseInt(date.getHours());
            var min = obj.date && obj.date[4] ? obj.date[4] : parseInt(date.getMinutes());
            obj.date = [year, month, day, hour, min, 0];
            // Update title
            calendarLabelYear.innerHTML = year;
            calendarLabelMonth.innerHTML = obj.options.months[month - 1];
            // Flag if this is the current month and year
            if ((date.getMonth() == month - 1) && (date.getFullYear() == year)) {
                today = 1;
                today_d = date.getDate();
            }
            var date = new Date(year, month, 0, 0, 0);
            var nd = date.getDate();
            var date = new Date(year, month - 1, 0, hour, min);
            var fd = date.getDay() + 1;
            // Reset table
            calendarBody.innerHTML = '';
            // Weekdays Row
            var row = document.createElement('tr');
            row.setAttribute('align', 'center');
            calendarBody.appendChild(row);
            for (var i = 0; i < 7; i++) {
                var cell = document.createElement('td');
                cell.setAttribute('width', '30');
                cell.classList.add('jcalendar-weekday')
                cell.innerHTML = obj.options.weekdays_short[i];
                row.appendChild(cell);
            }
            // Avoid a blank line
            if (fd == 7) {
                var j = 7;
            } else {
                var j = 0;
            }
            // Days inside the table
            var row = document.createElement('tr');
            row.setAttribute('align', 'center');
            calendarBody.appendChild(row);
            // Days in the month
            for (var i = j; i < (Math.ceil((nd + fd) / 7) * 7); i++) {
                // Create row
                if ((i > 0) && (!(i % 7))) {
                    var row = document.createElement('tr');
                    row.setAttribute('align', 'center');
                    calendarBody.appendChild(row);
                }
                if ((i >= fd) && (i < nd + fd)) {
                    d += 1;
                } else {
                    d = 0;
                }
                // Create cell
                var cell = document.createElement('td');
                cell.setAttribute('width', '30');
                cell.classList.add('jcalendar-set-day');
                row.appendChild(cell);
                if (d == 0) {
                    cell.innerHTML = '';
                } else {
                    if (d < 10) {
                        cell.innerHTML = 0 + d;
                    } else {
                        cell.innerHTML = d;
                    }
                }
                // Selected
                if (d && d == day) {
                    cell.classList.add('jcalendar-selected');
                }
                // Sundays
                if (!(i % 7)) {
                    cell.style.color = 'red';
                }
                // Today
                if ((today == 1) && (today_d == d)) {
                    cell.style.fontWeight = 'bold';
                }
            }
            // Show time controls
            if (obj.options.time) {
                calendarControlsTime.style.display = '';
            } else {
                calendarControlsTime.style.display = 'none';
            }
        }
        obj.getMonths = function () {
            // Mode
            obj.options.mode = 'months';
            // Loading month labels
            var months = obj.options.months;
            // Update title
            calendarLabelYear.innerHTML = obj.date[0];
            calendarLabelMonth.innerHTML = '';
            // Create months table
            var html = '<td colspan="7"><table width="100%"><tr align="center">';
            for (i = 0; i < 12; i++) {
                if ((i > 0) && (!(i % 4))) {
                    html += '</tr><tr align="center">';
                }
                var month = parseInt(i) + 1;
                html += '<td class="jcalendar-set-month" data-value="' + month + '">' + months[i] + '</td>';
            }
            html += '</tr></table></td>';
            calendarBody.innerHTML = html;
        }
        obj.getYears = function () {
            // Mode
            obj.options.mode = 'years';
            // Array of years
            var y = [];
            for (i = 0; i < 25; i++) {
                y[i] = parseInt(obj.date[0]) + (i - 12);
            }
            // Assembling the year tables
            var html = '<td colspan="7"><table width="100%"><tr align="center">';
            for (i = 0; i < 25; i++) {
                if ((i > 0) && (!(i % 5))) {
                    html += '</tr><tr align="center">';
                }
                html += '<td class="jcalendar-set-year">' + y[i] + '</td>';
            }
            html += '</tr></table></td>';
            calendarBody.innerHTML = html;
        }
        obj.setLabel = function (value, format) {
            return jSuites.calendar.getDateString(value, format);
        }
        obj.fromFormatted = function (value, format) {
            return jSuites.calendar.extractDateFromString(value, format);
        }
        // Add properties
        el.setAttribute('autocomplete', 'off');
        el.setAttribute('data-mask', obj.options.format.toLowerCase());
        if (obj.options.readonly) {
            el.setAttribute('readonly', 'readonly');
        }
        if (obj.options.placeholder) {
            el.setAttribute('placeholder', obj.options.placeholder);
        }
        var mouseUpControls = function (e) {
            var action = e.target.className;
            // Object id
            if (action == 'jcalendar-prev') {
                obj.prev();
                e.stopPropagation();
                e.preventDefault();
            } else if (action == 'jcalendar-next') {
                obj.next();
                e.stopPropagation();
                e.preventDefault();
            } else if (action == 'jcalendar-month') {
                obj.getMonths();
                e.stopPropagation();
                e.preventDefault();
            } else if (action == 'jcalendar-year') {
                obj.getYears();
                e.stopPropagation();
                e.preventDefault();
            } else if (action == 'jcalendar-set-year') {
                obj.date[0] = e.target.innerText;
                obj.getDays();
                e.stopPropagation();
                e.preventDefault();
            } else if (action == 'jcalendar-set-month') {
                obj.date[1] = parseInt(e.target.getAttribute('data-value'));
                obj.getDays();
                e.stopPropagation();
                e.preventDefault();
            } else if (action == 'jcalendar-confirm' || action == 'jcalendar-update') {
                obj.close();
                e.stopPropagation();
                e.preventDefault();
            } else if (action == 'jcalendar-close') {
                obj.close();
                e.stopPropagation();
                e.preventDefault();
            } else if (action == 'jcalendar-backdrop') {
                obj.close(false, false);
                e.stopPropagation();
                e.preventDefault();
            } else if (action == 'jcalendar-reset') {
                obj.reset();
                e.stopPropagation();
                e.preventDefault();
            } else if (e.target.classList.contains('jcalendar-set-day')) {
                if (e.target.innerText) {
                    obj.update(e.target);
                    e.stopPropagation();
                    e.preventDefault();
                }
            }
        }
        var keyUpControls = function (e) {
            if (e.target.value && e.target.value.length > 3) {
                var test = jSuites.calendar.extractDateFromString(e.target.value, obj.options.format);
                if (test) {
                    if (e.target.getAttribute('data-completed') == 'true') {
                        obj.setValue(test);
                    }
                }
            }
        }
        var verifyControls = function (e) {
            console.log(e.target.className)
        }
        // Handle events
        el.addEventListener("keyup", keyUpControls);
        // Add global events
        calendar.addEventListener("swipeleft", function (e) {
            jSuites.slideLeft(calendarTable, 0, function () {
                obj.next();
                jSuites.slideRight(calendarTable, 1);
            });
            e.preventDefault();
            e.stopPropagation();
        });
        calendar.addEventListener("swiperight", function (e) {
            jSuites.slideRight(calendarTable, 0, function () {
                obj.prev();
                jSuites.slideLeft(calendarTable, 1);
            });
            e.preventDefault();
            e.stopPropagation();
        });
        if ('ontouchend' in document.documentElement === true) {
            calendar.addEventListener("touchend", mouseUpControls);
            el.addEventListener("touchend", function (e) {
                obj.open();
            });
        } else {
            calendar.addEventListener("mouseup", mouseUpControls);
            el.addEventListener("mouseup", function (e) {
                obj.open();
            });
        }
        // Append element to the DOM
        el.parentNode.insertBefore(calendar, el.nextSibling);
        // Keep object available from the node
        el.calendar = obj;
        if (obj.options.opened == true) {
            obj.open();
        }
        return obj;
    });
    jSuites.calendar.prettify = function (d, texts) {
        if (!texts) {
            var texts = {
                justNow: 'Just now',
                xMinutesAgo: '{0}m ago',
                xHoursAgo: '{0}h ago',
                xDaysAgo: '{0}d ago',
                xWeeksAgo: '{0}w ago',
                xMonthsAgo: '{0} mon ago',
                xYearsAgo: '{0}y ago',
            }
        }
        var d1 = new Date();
        var d2 = new Date(d);
        var total = parseInt((d1 - d2) / 1000 / 60);
        String.prototype.format = function (o) {
            return this.replace('{0}', o);
        }
        if (total == 0) {
            var text = texts.justNow;
        } else if (total < 90) {
            var text = texts.xMinutesAgo.format(total);
        } else if (total < 1440) { // One day
            var text = texts.xHoursAgo.format(Math.round(total / 60));
        } else if (total < 20160) { // 14 days
            var text = texts.xDaysAgo.format(Math.round(total / 1440));
        } else if (total < 43200) { // 30 days
            var text = texts.xWeeksAgo.format(Math.round(total / 10080));
        } else if (total < 1036800) { // 24 months
            var text = texts.xMonthsAgo.format(Math.round(total / 43200));
        } else { // 24 months+
            var text = texts.xYearsAgo.format(Math.round(total / 525600));
        }
        return text;
    }
    jSuites.calendar.prettifyAll = function () {
        var elements = document.querySelectorAll('.prettydate');
        for (var i = 0; i < elements.length; i++) {
            if (elements[i].getAttribute('data-date')) {
                elements[i].innerHTML = jSuites.calendar.prettify(elements[i].getAttribute('data-date'));
            } else {
                elements[i].setAttribute('data-date', elements[i].innerHTML);
                elements[i].innerHTML = jSuites.calendar.prettify(elements[i].innerHTML);
            }
        }
    }
    jSuites.calendar.now = function () {
        var date = new Date();
        var y = date.getFullYear();
        var m = date.getMonth() + 1;
        var d = date.getDate();
        var h = date.getHours();
        var i = date.getMinutes();
        var s = date.getSeconds();
        // Two digits
        var two = function (value) {
            value = '' + value;
            if (value.length == 1) {
                value = '0' + value;
            }
            return value;
        }
        return two(y) + '-' + two(m) + '-' + two(d) + ' ' + two(h) + ':' + two(i) + ':' + two(s);
    }
    // Helper to extract date from a string
    jSuites.calendar.extractDateFromString = function (date, format) {
        var v1 = '' + date;
        var v2 = format.replace(/[0-9]/g, '');
        var test = 1;
        // Get year
        var y = v2.search("YYYY");
        y = v1.substr(y, 4);
        if (parseInt(y) != y) {
            test = 0;
        }
        // Get month
        var m = v2.search("MM");
        m = v1.substr(m, 2);
        if (parseInt(m) != m || d > 12) {
            test = 0;
        }
        // Get day
        var d = v2.search("DD");
        d = v1.substr(d, 2);
        if (parseInt(d) != d || d > 31) {
            test = 0;
        }
        // Get hour
        var h = v2.search("HH");
        if (h >= 0) {
            h = v1.substr(h, 2);
            if (!parseInt(h) || h > 23) {
                h = '00';
            }
        } else {
            h = '00';
        }
        // Get minutes
        var i = v2.search("MI");
        if (i >= 0) {
            i = v1.substr(i, 2);
            if (!parseInt(i) || i > 59) {
                i = '00';
            }
        } else {
            i = '00';
        }
        // Get seconds
        var s = v2.search("SS");
        if (s >= 0) {
            s = v1.substr(s, 2);
            if (!parseInt(s) || s > 59) {
                s = '00';
            }
        } else {
            s = '00';
        }
        if (test == 1 && date.length == v2.length) {
            // Update source
            var data = y + '-' + m + '-' + d + ' ' + h + ':' + i + ':' + s;
            return data;
        }
        return '';
    }
    // Helper to convert date into string
    jSuites.calendar.getDateString = function (value, format) {
        // Default calendar
        if (!format) {
            var format = 'DD/MM/YYYY';
        }
        if (value) {
            var d = '' + value;
            d = d.split(' ');
            var h = '';
            var m = '';
            var s = '';
            if (d[1]) {
                h = d[1].split(':');
                m = h[1] ? h[1] : '00';
                s = h[2] ? h[2] : '00';
                h = h[0] ? h[0] : '00';
            } else {
                h = '00';
                m = '00';
                s = '00';
            }
            d = d[0].split('-');
            if (d[0] && d[1] && d[2] && d[0] > 0 && d[1] > 0 && d[1] < 13 && d[2] > 0 && d[2] < 32) {
                var calendar = new Date(d[0], d[1] - 1, d[2]);
                var weekday = new Array('Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday');
                var months = new Array('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec');
                d[1] = (d[1].length < 2 ? '0' : '') + d[1];
                d[2] = (d[2].length < 2 ? '0' : '') + d[2];
                h = (h.length < 2 ? '0' : '') + h;
                m = (m.length < 2 ? '0' : '') + m;
                s = (s.length < 2 ? '0' : '') + s;
                value = format;
                value = value.replace('WD', weekday[calendar.getDay()]);
                value = value.replace('DD', d[2]);
                value = value.replace('MM', d[1]);
                value = value.replace('YYYY', d[0]);
                value = value.replace('YY', d[0].substring(2, 4));
                value = value.replace('MON', months[parseInt(d[1]) - 1].toUpperCase());
                if (h) {
                    value = value.replace('HH24', h);
                }
                if (h > 12) {
                    value = value.replace('HH12', h - 12);
                    value = value.replace('HH', h);
                } else {
                    value = value.replace('HH12', h);
                    value = value.replace('HH', h);
                }
                value = value.replace('MI', m);
                value = value.replace('MM', m);
                value = value.replace('SS', s);
            } else {
                value = '';
            }
        }
        return value;
    }
    jSuites.calendar.isOpen = function (e) {
        if (jSuites.calendar.current) {
            if (!e.target.className || e.target.className.indexOf('jcalendar') == -1) {
                jSuites.calendar.current.close();
            }
        }
    }
    if ('ontouchstart' in document.documentElement === true) {
        document.addEventListener("touchstart", jSuites.calendar.isOpen);
    } else {
        document.addEventListener("mousedown", jSuites.calendar.isOpen);
    }
    /**
     * Color Picker v1.0.1
     * Author: paul.hodel@gmail.com
     * https://github.com/paulhodel/jtools
     */
    jSuites.color = (function (el, options) {
        var obj = {};
        obj.options = {};
        obj.values = [];
        // Global container
        if (!jSuites.color.current) {
            jSuites.color.current = null;
        }
        // Default configuration
        var defaults = {
            placeholder: '',
            value: null,
            onclose: null,
            onchange: null,
            position: null,
        };
        // Loop through our object
        for (var property in defaults) {
            if (options && options.hasOwnProperty(property)) {
                obj.options[property] = options[property];
            } else {
                obj.options[property] = defaults[property];
            }
        }
        var x = 0;
        var y = 0;
        var z = 0;
        var palette = {
            "red": {
                "50": "#ffebee",
                "100": "#ffcdd2",
                "200": "#ef9a9a",
                "300": "#e57373",
                "400": "#ef5350",
                "500": "#f44336",
                "600": "#e53935",
                "700": "#d32f2f",
                "800": "#c62828",
                "900": "#b71c1c",
            },
            "pink": {
                "50": "#fce4ec",
                "100": "#f8bbd0",
                "200": "#f48fb1",
                "300": "#f06292",
                "400": "#ec407a",
                "500": "#e91e63",
                "600": "#d81b60",
                "700": "#c2185b",
                "800": "#ad1457",
                "900": "#880e4f",
            },
            "purple": {
                "50": "#f3e5f5",
                "100": "#e1bee7",
                "200": "#ce93d8",
                "300": "#ba68c8",
                "400": "#ab47bc",
                "500": "#9c27b0",
                "600": "#8e24aa",
                "700": "#7b1fa2",
                "800": "#6a1b9a",
                "900": "#4a148c",
            },
            "deeppurple": {
                "50": "#ede7f6",
                "100": "#d1c4e9",
                "200": "#b39ddb",
                "300": "#9575cd",
                "400": "#7e57c2",
                "500": "#673ab7",
                "600": "#5e35b1",
                "700": "#512da8",
                "800": "#4527a0",
                "900": "#311b92",
            },
            "indigo": {
                "50": "#e8eaf6",
                "100": "#c5cae9",
                "200": "#9fa8da",
                "300": "#7986cb",
                "400": "#5c6bc0",
                "500": "#3f51b5",
                "600": "#3949ab",
                "700": "#303f9f",
                "800": "#283593",
                "900": "#1a237e",
            },
            "blue": {
                "50": "#e3f2fd",
                "100": "#bbdefb",
                "200": "#90caf9",
                "300": "#64b5f6",
                "400": "#42a5f5",
                "500": "#2196f3",
                "600": "#1e88e5",
                "700": "#1976d2",
                "800": "#1565c0",
                "900": "#0d47a1",
            },
            "lightblue": {
                "50": "#e1f5fe",
                "100": "#b3e5fc",
                "200": "#81d4fa",
                "300": "#4fc3f7",
                "400": "#29b6f6",
                "500": "#03a9f4",
                "600": "#039be5",
                "700": "#0288d1",
                "800": "#0277bd",
                "900": "#01579b",
            },
            "cyan": {
                "50": "#e0f7fa",
                "100": "#b2ebf2",
                "200": "#80deea",
                "300": "#4dd0e1",
                "400": "#26c6da",
                "500": "#00bcd4",
                "600": "#00acc1",
                "700": "#0097a7",
                "800": "#00838f",
                "900": "#006064",
            },
            "teal": {
                "50": "#e0f2f1",
                "100": "#b2dfdb",
                "200": "#80cbc4",
                "300": "#4db6ac",
                "400": "#26a69a",
                "500": "#009688",
                "600": "#00897b",
                "700": "#00796b",
                "800": "#00695c",
                "900": "#004d40",
            },
            "green": {
                "50": "#e8f5e9",
                "100": "#c8e6c9",
                "200": "#a5d6a7",
                "300": "#81c784",
                "400": "#66bb6a",
                "500": "#4caf50",
                "600": "#43a047",
                "700": "#388e3c",
                "800": "#2e7d32",
                "900": "#1b5e20",
            },
            "lightgreen": {
                "50": "#f1f8e9",
                "100": "#dcedc8",
                "200": "#c5e1a5",
                "300": "#aed581",
                "400": "#9ccc65",
                "500": "#8bc34a",
                "600": "#7cb342",
                "700": "#689f38",
                "800": "#558b2f",
                "900": "#33691e",
            },
            "lime": {
                "50": "#f9fbe7",
                "100": "#f0f4c3",
                "200": "#e6ee9c",
                "300": "#dce775",
                "400": "#d4e157",
                "500": "#cddc39",
                "600": "#c0ca33",
                "700": "#afb42b",
                "800": "#9e9d24",
                "900": "#827717",
            },
            "yellow": {
                "50": "#fffde7",
                "100": "#fff9c4",
                "200": "#fff59d",
                "300": "#fff176",
                "400": "#ffee58",
                "500": "#ffeb3b",
                "600": "#fdd835",
                "700": "#fbc02d",
                "800": "#f9a825",
                "900": "#f57f17",
            },
            "amber": {
                "50": "#fff8e1",
                "100": "#ffecb3",
                "200": "#ffe082",
                "300": "#ffd54f",
                "400": "#ffca28",
                "500": "#ffc107",
                "600": "#ffb300",
                "700": "#ffa000",
                "800": "#ff8f00",
                "900": "#ff6f00",
            },
            "orange": {
                "50": "#fff3e0",
                "100": "#ffe0b2",
                "200": "#ffcc80",
                "300": "#ffb74d",
                "400": "#ffa726",
                "500": "#ff9800",
                "600": "#fb8c00",
                "700": "#f57c00",
                "800": "#ef6c00",
                "900": "#e65100",
            },
            "deeporange": {
                "50": "#fbe9e7",
                "100": "#ffccbc",
                "200": "#ffab91",
                "300": "#ff8a65",
                "400": "#ff7043",
                "500": "#ff5722",
                "600": "#f4511e",
                "700": "#e64a19",
                "800": "#d84315",
                "900": "#bf360c",
            },
            "brown": {
                "50": "#efebe9",
                "100": "#d7ccc8",
                "200": "#bcaaa4",
                "300": "#a1887f",
                "400": "#8d6e63",
                "500": "#795548",
                "600": "#6d4c41",
                "700": "#5d4037",
                "800": "#4e342e",
                "900": "#3e2723"
            },
            "grey": {
                "50": "#fafafa",
                "100": "#f5f5f5",
                "200": "#eeeeee",
                "300": "#e0e0e0",
                "400": "#bdbdbd",
                "500": "#9e9e9e",
                "600": "#757575",
                "700": "#616161",
                "800": "#424242",
                "900": "#212121"
            },
            "bluegrey": {
                "50": "#eceff1",
                "100": "#cfd8dc",
                "200": "#b0bec5",
                "300": "#90a4ae",
                "400": "#78909c",
                "500": "#607d8b",
                "600": "#546e7a",
                "700": "#455a64",
                "800": "#37474f",
                "900": "#263238"
            }
        };
        var x = 0;
        var y = 0;
        var colors = [];
        Object.keys(palette).forEach(function (col) {
            y = 0;
            Object.keys(palette[col]).forEach(function (shade) {
                if (!colors[y]) {
                    colors[y] = [];
                }
                colors[y][x] = palette[col][shade];
                y++;
            });
            x++;
        });
        // Table container
        var container = document.createElement('div');
        container.className = 'jcolor';
        // Content
        var content = document.createElement('div');
        content.className = 'jcolor-content';
        // Table pallete
        var table = document.createElement('table');
        table.setAttribute('cellpadding', '7');
        table.setAttribute('cellspacing', '0');
        for (var i = 0; i < colors.length; i++) {
            var tr = document.createElement('tr');
            for (var j = 0; j < colors[i].length; j++) {
                var td = document.createElement('td');
                td.style.backgroundColor = colors[i][j];
                td.setAttribute('data-value', colors[i][j]);
                td.innerHTML = '';
                tr.appendChild(td);
                // Selected color
                if (obj.options.value == colors[i][j]) {
                    td.classList.add('jcolor-selected');
                }
                // Possible values
                obj.values[colors[i][j]] = td;
            }
            table.appendChild(tr);
        }
        /**
         * Open color pallete
         */
        obj.open = function () {
            if (jSuites.color.current) {
                if (jSuites.color.current != obj) {
                    jSuites.color.current.close();
                }
            }
            if (!jSuites.color.current) {
                // Persist element
                jSuites.color.current = obj;
                // Show colorpicker
                container.classList.add('jcolor-focus');
                const rect = el.getBoundingClientRect();
                const rectContent = content.getBoundingClientRect();
                if (obj.options.position) {
                    content.style.position = 'fixed';
                    if (window.innerHeight < rect.bottom + rectContent.height) {
                        content.style.top = (rect.top - (rectContent.height + 2)) + 'px';
                    } else {
                        content.style.top = (rect.top + rect.height + 2) + 'px';;
                    }
                } else {
                    if (window.innerHeight < rect.bottom + rectContent.height) {
                        content.style.top = (-1 * (rectContent.height + 2)) + 'px';
                    } else {
                        content.style.top = (rect.height + 2) + 'px';
                    }
                }
                container.focus();
            }
        }
        /**
         * Close color pallete
         */
        obj.close = function (ignoreEvents) {
            if (jSuites.color.current) {
                jSuites.color.current = null;
                if (!ignoreEvents && typeof (obj.options.onclose) == 'function') {
                    obj.options.onclose(el);
                }
                container.classList.remove('jcolor-focus');
            }
            return obj.options.value;
        }
        /**
         * Set value
         */
        obj.setValue = function (color) {
            if (color) {
                el.value = color;
                obj.options.value = color;
            }
            // Remove current selecded mark
            var selected = container.querySelector('.jcolor-selected');
            if (selected) {
                selected.classList.remove('jcolor-selected');
            }
            // Mark cell as selected
            obj.values[color].classList.add('jcolor-selected');
            // Onchange
            if (typeof (obj.options.onchange) == 'function') {
                obj.options.onchange(el, color);
            }
        }
        /**
         * Get value
         */
        obj.getValue = function () {
            return obj.options.value;
        }
        /**
         * If element is focus open the picker
         */
        el.addEventListener("focus", function (e) {
            obj.open();
        });
        // Select color
        container.addEventListener("click", function (e) {
            if (e.target.tagName == 'TD') {
                jSuites.color.current.setValue(e.target.getAttribute('data-value'));
                jSuites.color.current.close();
            }
        });
        // Possible to focus the container
        container.setAttribute('tabindex', '900');
        if (obj.options.placeholder) {
            el.setAttribute('placeholder', obj.options.placeholder);
        }
        // Append to the table
        content.appendChild(table);
        container.appendChild(content);
        container.onblur = function (e) {
            setTimeout(function () {
                if (jSuites.color.current) {
                    jSuites.color.current.close();
                }
            }, 200);
        }
        // Insert picker after the element
        el.parentNode.insertBefore(container, el);
        // Keep object available from the node
        el.color = obj;
        return obj;
    });
    jSuites.combo = (function (el, options) {
        var obj = {};
        if (options) {
            obj.options = options;
        }
        // Reset
        if (obj.options.reset == true) {
            el.innerHTML = '';
        }
        // Blank option?
        if (obj.options.blankOption) {
            var option = document.createElement('option');
            option.value = '';
            el.appendChild(option);
        }
        // Load options from a remote URL
        if (obj.options.url) {
            fetch(obj.options.url, {
                    headers: new Headers({
                        'content-type': 'text/json'
                    })
                })
                .then(function (data) {
                    data.json().then(function (data) {
                        obj.options.data = data;
                        Object.keys(data).forEach(function (k) {
                            var option = document.createElement('option');
                            if (data[k].id) {
                                option.value = data[k].id;
                                option.innerHTML = data[k].name;
                            } else {
                                option.value = k;
                                option.innerHTML = data[k];
                            }
                            el.appendChild(option);
                        });
                        if (obj.options.value) {
                            $(select).val(obj.options.value);
                        }
                        if (typeof (obj.options.onload) == 'function') {
                            obj.options.onload(el);
                        }
                    })
                });
        } else if (options.numeric) {
            for (var i = obj.options.numeric[0]; i <= obj.options.numeric[1]; i++) {
                var option = document.createElement('option');
                option.value = i;
                option.innerHTML = i;
                el.appendChild(option);
            }
        }
        el.combo = obj;
        return obj;
    });
    jSuites.contextmenu = (function (el, options) {
        var obj = {};
        obj.options = {};
        // Default configuration
        var defaults = {
            items: null,
        };
        // Loop through our object
        for (var property in defaults) {
            if (options && options.hasOwnProperty(property)) {
                obj.options[property] = options[property];
            } else {
                obj.options[property] = defaults[property];
            }
        }
        obj.menu = document.createElement('ul');
        obj.menu.classList.add('jcontextmenu');
        obj.menu.setAttribute('tabindex', '900');
        /**
         * Open contextmenu
         */
        obj.open = function (e, items) {
            if (items) {
                obj.options.items = items;
            }
            // Reset content
            obj.menu.innerHTML = '';
            // Append items
            for (var i = 0; i < obj.options.items.length; i++) {
                if (obj.options.items[i].type && obj.options.items[i].type == 'line') {
                    var itemContainer = document.createElement('hr');
                } else {
                    var itemContainer = document.createElement('li');
                    var itemText = document.createElement('a');
                    itemText.innerHTML = obj.options.items[i].title;
                    if (obj.options.items[i].disabled) {
                        itemContainer.className = 'jcontextmenu-disabled';
                    } else if (obj.options.items[i].onclick) {
                        itemContainer.onmouseup = obj.options.items[i].onclick;
                    }
                    itemContainer.appendChild(itemText);
                    if (obj.options.items[i].shortcut) {
                        var itemShortCut = document.createElement('span');
                        itemShortCut.innerHTML = obj.options.items[i].shortcut;
                        itemContainer.appendChild(itemShortCut);
                    }
                }
                obj.menu.appendChild(itemContainer);
            }
            // Coordinates
            if (e.target) {
                var x = e.clientX;
                var y = e.clientY;
            } else {
                var x = e.x;
                var y = e.y;
            }
            obj.menu.classList.add('jcontextmenu-focus');
            obj.menu.focus();
            const rect = obj.menu.getBoundingClientRect();
            if (window.innerHeight < y + rect.height) {
                obj.menu.style.top = (y - rect.height) + 'px';
            } else {
                obj.menu.style.top = y + 'px';
            }
            if (window.innerWidth < x + rect.width) {
                obj.menu.style.left = (x - rect.width) + 'px';
            } else {
                obj.menu.style.left = x + 'px';
            }
        }
        /**
         * Close menu
         */
        obj.close = function () {
            obj.menu.classList.remove('jcontextmenu-focus');
        }
        el.addEventListener("click", function (e) {
            obj.close();
        });
        obj.menu.addEventListener('blur', function (e) {
            obj.close();
        });
        window.addEventListener("mousewheel", function () {
            obj.close();
        });
        el.appendChild(obj.menu);
        el.contextmenu = obj;
        return obj;
    });
    /**
     * Dialog v1.0.1
     * Author: paul.hodel@gmail.com
     * https://github.com/paulhodel/jtools
     */
    jSuites.dialog = (function () {
        var obj = {};
        obj.options = {};
        var dialog = document.createElement('div');
        dialog.setAttribute('tabindex', '901');
        dialog.className = 'jdialog';
        dialog.id = 'dialog';
        var dialogHeader = document.createElement('div');
        dialogHeader.className = 'jdialog-header';
        var dialogTitle = document.createElement('div');
        dialogTitle.className = 'jdialog-title';
        dialogHeader.appendChild(dialogTitle);
        var dialogMessage = document.createElement('div');
        dialogMessage.className = 'jdialog-message';
        dialogHeader.appendChild(dialogMessage);
        var dialogFooter = document.createElement('div');
        dialogFooter.className = 'jdialog-footer';
        var dialogContainer = document.createElement('div');
        dialogContainer.className = 'jdialog-container';
        dialogContainer.appendChild(dialogHeader);
        dialogContainer.appendChild(dialogFooter);
        // Confirm
        var dialogConfirm = document.createElement('div');
        var dialogConfirmButton = document.createElement('input');
        dialogConfirmButton.value = obj.options.confirmLabel;
        dialogConfirmButton.type = 'button';
        dialogConfirmButton.onclick = function () {
            if (typeof (obj.options.onconfirm) == 'function') {
                obj.options.onconfirm();
            }
            obj.close();
        };
        dialogConfirm.appendChild(dialogConfirmButton);
        dialogFooter.appendChild(dialogConfirm);
        // Cancel
        var dialogCancel = document.createElement('div');
        var dialogCancelButton = document.createElement('input');
        dialogCancelButton.value = obj.options.cancelLabel;
        dialogCancelButton.type = 'button';
        dialogCancelButton.onclick = function () {
            if (typeof (obj.options.oncancel) == 'function') {
                obj.options.oncancel();
            }
            obj.close();
        }
        dialogCancel.appendChild(dialogCancelButton);
        dialogFooter.appendChild(dialogCancel);
        // Dialog
        dialog.appendChild(dialogContainer);
        obj.open = function (options) {
            obj.options = options;
            if (obj.options.title) {
                dialogTitle.innerHTML = obj.options.title;
            }
            if (obj.options.message) {
                dialogMessage.innerHTML = obj.options.message;
            }
            if (!obj.options.confirmLabel) {
                obj.options.confirmLabel = 'OK';
            }
            dialogConfirmButton.value = obj.options.confirmLabel;
            if (!obj.options.cancelLabel) {
                obj.options.cancelLabel = 'Cancel';
            }
            dialogCancelButton.value = obj.options.cancelLabel;
            if (obj.options.type == 'confirm') {
                dialogCancelButton.parentNode.style.display = '';
            } else {
                dialogCancelButton.parentNode.style.display = 'none';
            }
            // Append element to the app
            dialog.style.opacity = 100;
            // Append to the page
            if (jSuites.el) {
                jSuites.el.appendChild(dialog);
            } else {
                document.body.appendChild(dialog);
            }
            // Focus
            dialog.focus();
            // Show
            setTimeout(function () {
                dialogContainer.style.opacity = 100;
            }, 0);
        };
        obj.close = function () {
            dialog.style.opacity = 0;
            dialogContainer.style.opacity = 0;
            setTimeout(function () {
                dialog.remove();
            }, 100);
        };
        return obj;
    })();
    jSuites.confirm = (function (message, onconfirm) {
        if (jSuites.getWindowWidth() < 800) {
            jSuites.dialog.open({
                type: 'confirm',
                message: message,
                title: 'Confirmation',
                onconfirm: onconfirm,
            });
        } else {
            if (confirm(message)) {
                onconfirm();
            }
        }
    });
    jSuites.alert = function (message) {
        if (jSuites.getWindowWidth() < 800) {
            jSuites.dialog.open({
                title: 'Alert',
                message: message,
            });
        } else {
            alert(message);
        }
    }
    /**
     * (c) 2013 jDropdown http://www.github.com/paulhodel/jdropdown
     * 
     * @author: Paul Hodel <paul.hodel@gmail.com>
     * @description: Custom dropdowns
     */
    jSuites.dropdown = (function (el, options) {
        var obj = {};
        obj.options = {};
        obj.items = [];
        obj.groups = [];
        if (options) {
            obj.options = options;
        }
        // Global container
        if (!jSuites.dropdown.current) {
            jSuites.dropdown.current = null;
        }
        // Default configuration
        var defaults = {
            data: [],
            multiple: false,
            autocomplete: false,
            type: null,
            width: null,
            opened: false,
            onchange: null,
            onload: null,
            onopen: null,
            onclose: null,
            onblur: null,
            oninsert: null,
            allowInsert: false,
            value: null,
            placeholder: '',
            position: false, // Fixed position
        };
        // Loop through our object
        for (var property in defaults) {
            if (options && options.hasOwnProperty(property)) {
                obj.options[property] = options[property];
            } else {
                obj.options[property] = defaults[property];
            }
        }
        // Create dropdown
        el.classList.add('jdropdown');
        if (obj.options.type == 'searchbar') {
            el.classList.add('jdropdown-searchbar');
        } else if (obj.options.type == 'list') {
            el.classList.add('jdropdown-list');
        } else if (obj.options.type == 'picker') {
            el.classList.add('jdropdown-picker');
        } else {
            if (jSuites.getWindowWidth() < 800) {
                el.classList.add('jdropdown-picker');
                obj.options.type = 'picker';
            } else {
                if (obj.options.width) {
                    el.style.width = obj.options.width;
                }
                el.classList.add('jdropdown-default');
                obj.options.type = 'default';
            }
        }
        // Header container
        var containerHeader = document.createElement('div');
        containerHeader.className = 'jdropdown-container-header';
        // Header
        var header = document.createElement('input');
        header.className = 'jdropdown-header';
        if (typeof (obj.options.onblur) == 'function') {
            header.onblur = function () {
                obj.options.onblur(el);
            }
        }
        // Container
        var container = document.createElement('div');
        container.className = 'jdropdown-container';
        // Dropdown content
        var content = document.createElement('div');
        content.className = 'jdropdown-content';
        // Close button
        var closeButton = document.createElement('div');
        closeButton.className = 'jdropdown-close';
        closeButton.innerHTML = 'Done';
        // Create backdrop
        var backdrop = document.createElement('div');
        backdrop.className = 'jdropdown-backdrop';
        // Autocomplete
        if (obj.options.autocomplete == true) {
            el.setAttribute('data-autocomplete', true);
            // Handler
            header.addEventListener('keyup', function (e) {
                obj.find(header.value);
                if (!el.classList.contains('jdropdown-focus')) {
                    if (e.which > 65) {
                        obj.open();
                    }
                }
            });
        } else {
            header.setAttribute('readonly', 'readonly');
        }
        // Place holder
        if (obj.options.placeholder) {
            header.setAttribute('placeholder', obj.options.placeholder);
        }
        // Insert new elements
        if (obj.options.allowInsert == true) {
            el.classList.add('jdropdown-insert');
            // Add button
            var insertButton = document.createElement('div');
            insertButton.className = 'jdropdown-insert-button';
            insertButton.innerHTML = '+';
            insertButton.onclick = function () {
                if (header.value) {
                    obj.addItem(header.value);
                }
            }
            containerHeader.appendChild(insertButton);
        }
        // Append elements
        containerHeader.appendChild(header);
        container.appendChild(closeButton);
        container.appendChild(content);
        el.appendChild(containerHeader);
        el.appendChild(container);
        el.appendChild(backdrop);
        obj.init = function () {
            if (obj.options.url) {
                jSuites.ajax({
                    url: obj.options.url,
                    method: 'GET',
                    dataType: 'json',
                    success: function (data) {
                        if (data) {
                            obj.options.data = data;
                            obj.setData();
                            if (typeof (obj.options.onload) == 'function') {
                                obj.options.onload(el, obj, data);
                            }
                        }
                    }
                });
            } else {
                obj.setData();
                if (typeof (obj.options.onload) == 'function') {
                    obj.options.onload(el, obj, data);
                }
            }
            // Values
            obj.setValue(obj.options.value);
            if (obj.options.opened == true) {
                obj.open();
            }
            // Fix width - Workaround important to get the correct width
            if (obj.options.type == 'default') {
                setTimeout(function () {
                    container.style.minWidth = header.outerWidth;
                }, 0);
            }
        }
        obj.getUrl = function () {
            return obj.options.url;
        }
        obj.setUrl = function (url) {
            obj.options.url = url;
            jSuites.ajax({
                url: obj.options.url,
                method: 'GET',
                dataType: 'json',
                success: function (data) {
                    obj.setData(data);
                }
            });
        }
        obj.setData = function (data) {
            if (data) {
                obj.options.data = data;
            } else {
                var data = obj.options.data;
            }
            // Make sure the content container is blank
            content.innerHTML = '';
            // Containers
            var items = [];
            var groups = [];
            // Foreach in the data to create all items
            if (data.length) {
                data.forEach(function (v, k) {
                    // Compatibility
                    if (typeof (v) != 'object') {
                        var value = v;
                        v = {}
                        v.id = value;
                        v.name = value;
                        // Fix array
                        obj.options.data[k] = v;
                    }
                    // Create item
                    items[k] = document.createElement('div');
                    items[k].className = 'jdropdown-item';
                    items[k].value = v.id;
                    items[k].text = v.name;
                    // Image
                    if (v.image) {
                        var image = document.createElement('img');
                        image.className = 'jdropdown-image';
                        image.src = v.image;
                        if (!v.title) {
                            image.classList.add('jdropdown-image-small');
                        }
                        items[k].appendChild(image);
                    }
                    // Set content
                    var node = document.createElement('div');
                    node.className = 'jdropdown-description';
                    node.innerHTML = v.name;
                    items[k].appendChild(node);
                    // Title
                    if (v.title) {
                        var title = document.createElement('div');
                        title.className = 'jdropdown-title';
                        title.innerHTML = v.title;
                        node.appendChild(title);
                    }
                    // Append to the container
                    if (v.group) {
                        if (!groups[v.group]) {
                            groups[v.group] = document.createElement('div');
                            groups[v.group].className = 'jdropdown-group-items';
                        }
                        groups[v.group].appendChild(items[k]);
                    } else {
                        content.appendChild(items[k]);
                    }
                });
                // Append groups in case exists
                if (Object.keys(groups).length > 0) {
                    Object.keys(groups).forEach(function (v, k) {
                        var group = document.createElement('div');
                        group.className = 'jdropdown-group';
                        group.innerHTML = '<div class="jdropdown-group-name">' + v + '<i class="jdropdown-group-arrow jdropdown-group-arrow-down"></i></div>';
                        group.appendChild(groups[v]);
                        obj.groups.push(group);
                        content.appendChild(group);
                    });
                }
                // Add index property
                var items = content.querySelectorAll('.jdropdown-item');
                for (var i = 0; i < items.length; i++) {
                    obj.items[i] = items[i];
                    items[i].setAttribute('data-index', i);
                }
            }
            // Reset value
            obj.setValue(obj.options.value ? obj.options.value : '');
        }
        obj.getText = function (asArray) {
            // Result
            var result = [];
            // Get selected items
            var items = el.querySelectorAll('.jdropdown-selected');
            // Append options
            for (var i = 0; i < items.length; i++) {
                result.push(items[i].text);
            }
            if (asArray) {
                return result
            } else {
                return result.join('; ');
            }
        }
        obj.getValue = function (asArray) {
            // Result
            var result = [];
            // Get selected items
            var items = el.querySelectorAll('.jdropdown-selected');
            // Append options
            for (var i = 0; i < items.length; i++) {
                result.push(items[i].value);
            }
            if (asArray) {
                return result;
            } else {
                return result.join(';');
            }
        }
        obj.setValue = function (value) {
            // Remove values
            var items = el.querySelectorAll('.jdropdown-selected');
            for (var j = 0; j < items.length; j++) {
                items[j].classList.remove('jdropdown-selected')
            }
            // Set values
            if (value != null) {
                if (Array.isArray(value)) {
                    for (var i = 0; i < obj.items.length; i++) {
                        value.forEach(function (val) {
                            if (obj.items[i].value == val) {
                                obj.items[i].classList.add('jdropdown-selected');
                            }
                        });
                    }
                } else {
                    for (var i = 0; i < obj.items.length; i++) {
                        if (obj.items[i].value == value) {
                            obj.items[i].classList.add('jdropdown-selected');
                        }
                    }
                }
            }
            // Update labels
            obj.updateLabel();
        }
        obj.addItem = function () {
            console.log(obj.items);
        }
        obj.selectIndex = function (index) {
            if (index >= 0) {
                // Current selection
                var oldValue = obj.getValue();
                var oldLabel = obj.getText();
                // Focus behaviour
                if (!obj.options.multiple) {
                    // Cursor
                    obj.items[index].classList.add('jdropdown-cursor');
                    // Unselect option
                    if (obj.items[index].classList.contains('jdropdown-selected')) {
                        obj.items[index].classList.remove('jdropdown-selected');
                    } else {
                        // Update selected item
                        obj.items.forEach(function (v) {
                            v.classList.remove('jdropdown-cursor');
                            v.classList.remove('jdropdown-selected');
                        });
                        obj.items[index].classList.add('jdropdown-selected');
                        // Close
                        obj.close();
                    }
                } else {
                    // Toggle option
                    if (obj.items[index].classList.contains('jdropdown-selected')) {
                        obj.items[index].classList.remove('jdropdown-selected');
                        obj.items[index].classList.remove('jdropdown-cursor');
                    } else {
                        obj.items.forEach(function (v) {
                            v.classList.remove('jdropdown-cursor');
                        });
                        obj.items[index].classList.add('jdropdown-selected');
                        obj.items[index].classList.add('jdropdown-cursor');
                    }
                    // Update cursor position
                    obj.currentIndex = index;
                    // Update labels for multiple dropdown
                    if (!obj.options.autocomplete) {
                        obj.updateLabel();
                    }
                }
                // Current selection
                var newValue = obj.getValue();
                var newLabel = obj.getText();
                // Events
                if (typeof (obj.options.onchange) == 'function') {
                    obj.options.onchange(el, index, oldValue, newValue, oldLabel, newLabel);
                }
            }
        }
        obj.selectItem = function (item) {
            var index = item.getAttribute('data-index');
            if (jSuites.dropdown.current) {
                obj.selectIndex(item.getAttribute('data-index'));
            } else {
                // List
                if (obj.options.type == 'list') {
                    if (!obj.options.multiple) {
                        obj.items.forEach(function (k, v) {
                            v.classList.remove('jdropdown-cursor');
                            v.classList.remove('jdropdown-selected');
                        });
                        obj.items[index].classList.add('jdropdown-selected');
                        obj.items[index].classList.add('jdropdown-cursor');
                    } else {
                        // Toggle option
                        if (obj.items[index].classList.contains('jdropdown-selected')) {
                            obj.items[index].classList.remove('jdropdown-selected');
                            obj.items[index].classList.remove('jdropdown-cursor');
                        } else {
                            obj.items.forEach(function (v) {
                                v.classList.remove('jdropdown-cursor');
                            });
                            obj.items[index].classList.add('jdropdown-selected');
                            obj.items[index].classList.add('jdropdown-cursor');
                        }
                        // Update cursor position
                        obj.currentIndex = index;
                    }
                }
            }
        }
        obj.find = function (str) {
            // Append options
            for (var i = 0; i < obj.items.length; i++) {
                if (str == null || obj.items[i].classList.contains('jdropdown-selected') || obj.items[i].innerHTML.toLowerCase().indexOf(str.toLowerCase()) != -1) {
                    obj.items[i].style.display = '';
                } else {
                    obj.items[i].style.display = 'none';
                }
            };
            var numVisibleItems = function (items) {
                var visible = 0;
                for (var j = 0; j < items.length; j++) {
                    if (items[j].style.display != 'none') {
                        visible++;
                    }
                }
                return visible;
            }
            // Hide groups
            for (var i = 0; i < obj.groups.length; i++) {
                if (numVisibleItems(obj.groups[i].querySelectorAll('.jdropdown-item'))) {
                    obj.groups[i].children[0].style.display = '';
                } else {
                    obj.groups[i].children[0].style.display = 'none';
                }
            }
        }
        obj.updateLabel = function () {
            // Update label
            header.value = obj.getText();
        }
        obj.open = function () {
            if (jSuites.dropdown.current != el) {
                if (jSuites.dropdown.current) {
                    jSuites.dropdown.current.dropdown.close();
                }
                jSuites.dropdown.current = el;
            }
            // Focus
            if (!el.classList.contains('jdropdown-focus')) {
                // Add focus
                el.classList.add('jdropdown-focus');
                // Animation
                if (jSuites.getWindowWidth() < 800) {
                    if (obj.options.type == null || obj.options.type == 'picker') {
                        container.classList.add('slide-bottom-in');
                    }
                }
                // Filter
                if (obj.options.autocomplete == true) {
                    // Redo search
                    obj.find();
                    // Clear search field
                    header.value = '';
                    header.focus();
                }
                // Selected
                var selected = el.querySelector('.jdropdown-selected');
                // Update cursor position
                if (selected) {
                    obj.updateCursor(selected.getAttribute('data-index'));
                }
                // Container Size
                if (!obj.options.type || obj.options.type == 'default') {
                    const rect = el.getBoundingClientRect();
                    const rectContainer = container.getBoundingClientRect();
                    container.style.minWidth = rect.width + 'px';
                    // container.style.maxWidth = '100%';
                    if (obj.options.position) {
                        container.style.position = 'fixed';
                        if (window.innerHeight < rect.bottom + rectContainer.height) {
                            container.style.top = (rect.top - rectContainer.height - 2) + 'px';
                        } else {
                            container.style.top = (rect.top + rect.height + 1) + 'px';
                        }
                        container.style.left = rect.left;
                    } else {
                        if (window.innerHeight < rect.bottom + rectContainer.height) {
                            container.style.bottom = (rect.height) + 'px';
                        } else {
                            container.style.top = '';
                            container.style.bottom = '';
                        }
                    }
                }
            }
            // Events
            if (typeof (obj.options.onopen) == 'function') {
                obj.options.onopen(el);
            }
        }
        obj.close = function (ignoreEvents) {
            if (jSuites.dropdown.current) {
                // Remove controller
                jSuites.dropdown.current = null
                // Remove cursor
                var cursor = el.querySelector('.jdropdown-cursor');
                if (cursor) {
                    cursor.classList.remove('jdropdown-cursor');
                }
                // Update labels
                obj.updateLabel();
                // Events
                if (!ignoreEvents && typeof (obj.options.onclose) == 'function') {
                    obj.options.onclose(el);
                }
                // Reset
                obj.currentIndex = null;
                // Blur
                if (header.blur) {
                    header.blur();
                }
                // Remove focus
                el.classList.remove('jdropdown-focus');
            }
            return obj.getValue();
        }
        obj.reset = function () {
            // Remove current cursor
            var cursor = el.querySelector('.jdropdown-cursor');
            if (cursor) {
                cursor.classList.remove('jdropdown-cursor');
            }
            // Unselected all
            obj.items.forEach(function (v) {
                v.classList.remove('jdropdown-selected');
            });
            // Update labels
            obj.updateLabel();
        }
        obj.firstVisible = function () {
            var newIndex = null;
            for (var i = 0; i < obj.options.data.length; i++) {
                if (obj.items[i].style.display != 'none') {
                    newIndex = i;
                    break;
                }
            }
            if (newIndex == null) {
                return false;
            }
            obj.updateCursor(newIndex);
        }
        obj.first = function () {
            var newIndex = null;
            for (var i = obj.currentIndex - 1; i >= 0; i--) {
                if (obj.items[i].style.display != 'none') {
                    newIndex = i;
                }
            }
            if (newIndex == null) {
                return false;
            }
            obj.updateCursor(newIndex);
        }
        obj.last = function () {
            var newIndex = null;
            for (var i = obj.currentIndex + 1; i < obj.options.data.length; i++) {
                if (obj.items[i].style.display != 'none') {
                    newIndex = i;
                }
            }
            if (newIndex == null) {
                return false;
            }
            obj.updateCursor(newIndex);
        }
        obj.next = function () {
            var newIndex = null;
            for (var i = obj.currentIndex + 1; i < obj.options.data.length; i++) {
                if (obj.items[i].style.display != 'none') {
                    newIndex = i;
                    break;
                }
            }
            if (newIndex == null) {
                return false;
            }
            obj.updateCursor(newIndex);
        }
        obj.prev = function () {
            var newIndex = null;
            for (var i = obj.currentIndex - 1; i >= 0; i--) {
                if (obj.items[i].style.display != 'none') {
                    newIndex = i;
                    break;
                }
            }
            if (newIndex == null) {
                return false;
            }
            obj.updateCursor(newIndex);
        }
        obj.updateCursor = function (index) {
            // Update cursor
            if (obj.items[obj.currentIndex]) {
                obj.items[obj.currentIndex].classList.remove('jdropdown-cursor');
            }
            if (obj.items && obj.items[index]) {
                obj.items[index].classList.add('jdropdown-cursor');
                // Update position
                obj.currentIndex = parseInt(index);
                // Update scroll
                var container = content.scrollTop;
                var element = obj.items[obj.currentIndex];
                content.scrollTop = element.offsetTop - element.scrollTop + element.clientTop - 95;
            }
        }
        if (!jSuites.dropdown.hasEvents) {
            if ('ontouchsend' in document.documentElement === true) {
                document.addEventListener('touchsend', jSuites.dropdown.mouseup);
            } else {
                document.addEventListener('mouseup', jSuites.dropdown.mouseup);
            }
            document.addEventListener('keydown', jSuites.dropdown.onkeydown);
            jSuites.dropdown.hasEvents = true;
        }
        // Start dropdown
        obj.init();
        // Keep object available from the node
        el.dropdown = obj;
        return obj;
    });
    jSuites.dropdown.mouseup = function (e) {
        var element = jSuites.getElement(e.target, 'jdropdown');
        if (element) {
            var dropdown = element.dropdown;
            if (e.target.classList.contains('jdropdown-header')) {
                if (element.classList.contains('jdropdown-focus') && element.classList.contains('jdropdown-default')) {
                    dropdown.close();
                } else {
                    dropdown.open();
                }
            } else if (e.target.classList.contains('jdropdown-group-name')) {
                var items = e.target.nextSibling.children;
                if (e.target.nextSibling.style.display != 'none') {
                    for (var i = 0; i < items.length; i++) {
                        if (items[i].style.display != 'none') {
                            dropdown.selectItem(items[i]);
                        }
                    }
                }
            } else if (e.target.classList.contains('jdropdown-group-arrow')) {
                if (e.target.classList.contains('jdropdown-group-arrow-down')) {
                    e.target.classList.remove('jdropdown-group-arrow-down');
                    e.target.classList.add('jdropdown-group-arrow-up');
                    e.target.parentNode.nextSibling.style.display = 'none';
                } else {
                    e.target.classList.remove('jdropdown-group-arrow-up');
                    e.target.classList.add('jdropdown-group-arrow-down');
                    e.target.parentNode.nextSibling.style.display = '';
                }
            } else if (e.target.classList.contains('jdropdown-item')) {
                dropdown.selectItem(e.target);
            } else if (e.target.classList.contains('jdropdown-image')) {
                dropdown.selectIndex(e.target.parentNode.getAttribute('data-index'));
            } else if (e.target.classList.contains('jdropdown-description')) {
                dropdown.selectIndex(e.target.parentNode.getAttribute('data-index'));
            } else if (e.target.classList.contains('jdropdown-title')) {
                dropdown.selectIndex(e.target.parentNode.parentNode.getAttribute('data-index'));
            } else if (e.target.classList.contains('jdropdown-close') || e.target.classList.contains('jdropdown-backdrop')) {
                // Close
                dropdown.close();
            }
            e.stopPropagation();
            e.preventDefault();
        } else {
            if (jSuites.dropdown.current) {
                jSuites.dropdown.current.dropdown.close();
            }
        }
    }
    // Keydown controls
    jSuites.dropdown.onkeydown = function (e) {
        if (jSuites.dropdown.current) {
            // Element
            var element = jSuites.dropdown.current.dropdown;
            // Index
            var index = element.currentIndex;
            if (e.shiftKey) {} else {
                if (e.which == 13 || e.which == 27 || e.which == 35 || e.which == 36 || e.which == 38 || e.which == 40) {
                    // Move cursor
                    if (e.which == 13) {
                        element.selectIndex(index)
                    } else if (e.which == 38) {
                        if (index == null) {
                            element.firstVisible();
                        } else if (index > 0) {
                            element.prev();
                        }
                    } else if (e.which == 40) {
                        if (index == null) {
                            element.firstVisible();
                        } else if (index + 1 < element.options.data.length) {
                            element.next();
                        }
                    } else if (e.which == 36) {
                        element.first();
                    } else if (e.which == 35) {
                        element.last();
                    } else if (e.which == 27) {
                        element.close();
                    }
                    e.stopPropagation();
                    e.preventDefault();
                }
            }
        }
    }
    /**
     * (c) jTools Text Editor
     * https://github.com/paulhodel/jtools
     *
     * @author: Paul Hodel <paul.hodel@gmail.com>
     * @description: Inline richtext editor
     */
    jSuites.editor = (function (el, options) {
        var obj = {};
        obj.options = {};
        // Default configuration
        var defaults = {
            // Initial HTML content
            value: null,
            // Initial snippet
            snippet: null,
            // Add toolbar
            toolbar: null,
            // Max height
            maxHeight: null,
            // Website parser is to read websites and images from cross domain
            remoteParser: null,
            // Key from youtube to read properties from URL
            youtubeKey: null,
            // User list
            userSearch: null,
            // Parse URL
            parseURL: false,
            // Accept drop files
            dropZone: true,
            dropAsAttachment: false,
            acceptImages: true,
            acceptFiles: false,
            maxFileSize: 5000000,
            // Border
            border: true,
            padding: true,
            focus: false,
            // Events
            onclick: null,
            onfocus: null,
            onblur: null,
            onload: null,
            onenter: null,
            onkeyup: null,
            onkeydown: null,
        };
        // Loop through our object
        for (var property in defaults) {
            if (options && options.hasOwnProperty(property)) {
                obj.options[property] = options[property];
            } else {
                obj.options[property] = defaults[property];
            }
        }
        // Private controllers
        var imageResize = 0;
        var editorTimer = null;
        var editorAction = null;
        // Make sure element is empty
        el.innerHTML = '';
        // Prepare container
        el.classList.add('jeditor-container');
        // Padding
        if (obj.options.padding == true) {
            el.classList.add('jeditor-padding');
        }
        // Border
        if (obj.options.border == false) {
            el.style.border = '0px';
        }
        // Snippet
        var snippet = document.createElement('div');
        snippet.className = 'snippet';
        snippet.setAttribute('contenteditable', false);
        // Toolbar
        var toolbar = document.createElement('div');
        toolbar.className = 'jeditor-toolbar';
        // Create editor
        var editor = document.createElement('div');
        editor.setAttribute('contenteditable', true);
        editor.setAttribute('spellcheck', false);
        editor.className = 'jeditor';
        // Max height
        if (obj.options.maxHeight) {
            editor.style.overflowY = 'auto';
            editor.style.maxHeight = obj.options.maxHeight;
        }
        // Set editor initial value
        if (obj.options.value) {
            var value = obj.options.value;
        } else {
            var value = el.innerHTML ? el.innerHTML : '';
        }
        if (!value) {
            var value = '<br>';
        }
        /**
         * Extract images from a HTML string
         */
        var extractImageFromHtml = function (html) {
            // Create temp element
            var div = document.createElement('div');
            div.innerHTML = html;
            // Extract images
            var img = div.querySelectorAll('img');
            if (img.length) {
                for (var i = 0; i < img.length; i++) {
                    obj.addImage(img[i].src);
                }
            }
        }
        /**
         * Insert node at caret
         */
        var insertNodeAtCaret = function (newNode) {
            var sel, range;
            if (window.getSelection) {
                sel = window.getSelection();
                if (sel.rangeCount) {
                    range = sel.getRangeAt(0);
                    var selectedText = range.toString();
                    range.deleteContents();
                    range.insertNode(newNode);
                    // move the cursor after element
                    range.setStartAfter(newNode);
                    range.setEndAfter(newNode);
                    sel.removeAllRanges();
                    sel.addRange(range);
                }
            }
        }
        /**
         * Append snippet or thumbs in the editor
         * @Param object data
         */
        var appendElement = function (data) {
            // Reset snippet
            snippet.innerHTML = '';
            if (data.image) {
                var div = document.createElement('div');
                div.className = 'snippet-image';
                div.setAttribute('data-k', 'image');
                snippet.appendChild(div);
                var image = document.createElement('img');
                image.src = data.image;
                div.appendChild(image);
            }
            var div = document.createElement('div');
            div.className = 'snippet-title';
            div.setAttribute('data-k', 'title');
            div.innerHTML = data.title;
            snippet.appendChild(div);
            var div = document.createElement('div');
            div.className = 'snippet-description';
            div.setAttribute('data-k', 'description');
            div.innerHTML = data.description;
            snippet.appendChild(div);
            var div = document.createElement('div');
            div.className = 'snippet-host';
            div.setAttribute('data-k', 'host');
            div.innerHTML = data.host;
            snippet.appendChild(div);
            var div = document.createElement('div');
            div.className = 'snippet-url';
            div.setAttribute('data-k', 'url');
            div.innerHTML = data.url;
            snippet.appendChild(div);
            editor.appendChild(snippet);
        }
        var verifyEditor = function () {
            clearTimeout(editorTimer);
            editorTimer = setTimeout(function () {
                var snippet = editor.querySelector('.snippet');
                var thumbsContainer = el.querySelector('.jeditor-thumbs-container');
                if (!snippet && !thumbsContainer) {
                    var html = editor.innerHTML.replace(/\n/g, ' ');
                    var container = document.createElement('div');
                    container.innerHTML = html;
                    var thumbsContainer = container.querySelector('.jeditor-thumbs-container');
                    if (thumbsContainer) {
                        thumbsContainer.remove();
                    }
                    var text = container.innerText;
                    var url = jSuites.editor.detectUrl(text);
                    if (url) {
                        if (url[0].substr(-3) == 'jpg' || url[0].substr(-3) == 'png' || url[0].substr(-3) == 'gif') {
                            if (jSuites.editor.getDomain(url[0]) == window.location.hostname) {
                                obj.importImage(url[0], '');
                            } else {
                                obj.importImage(obj.options.remoteParser + url[0], '');
                            }
                        } else {
                            var id = jSuites.editor.youtubeParser(url[0]);
                            if (id) {
                                obj.getYoutube(id);
                            } else {
                                obj.getWebsite(url[0]);
                            }
                        }
                    }
                }
            }, 1000);
        }
        /**
         * Get metadata from a youtube video
         */
        obj.getYoutube = function (id) {
            if (!obj.options.youtubeKey) {
                console.error('The youtubeKey is not defined');
            } else {
                jSuites.ajax({
                    url: 'https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&key=' + obj.options.youtubeKey + '&id=' + id,
                    method: 'GET',
                    dataType: 'json',
                    success: function (result) {
                        // Only valid elements to be appended
                        if (result.items && result.items[0]) {
                            var p = {
                                title: '',
                                description: '',
                                image: '',
                                host: 'www.youtube.com',
                                url: 'https://www.youtube.com?watch=' + id,
                            }
                            if (result.items[0].snippet.title) {
                                p.title = result.items[0].snippet.title;
                            }
                            if (result.items[0].snippet.description) {
                                p.description = result.items[0].snippet.description;
                                if (p.description.length > 150) {
                                    p.description = p.description.substr(0, 150) + '...';
                                }
                            }
                            if (result.items[0].snippet.thumbnails.medium.url) {
                                p.image = result.items[0].snippet.thumbnails.medium.url;
                            }
                            appendElement(p);
                        }
                    }
                });
            }
        }
        /**
         * Get meta information from a website
         */
        obj.getWebsite = function (url) {
            if (!obj.options.remoteParser) {
                console.log('The remoteParser is not defined');
            } else {
                jSuites.ajax({
                    url: obj.options.remoteParser + encodeURI(url.trim()),
                    method: 'GET',
                    dataType: 'json',
                    success: function (result) {
                        var p = {
                            title: '',
                            description: '',
                            image: '',
                            host: url,
                            url: url,
                        }
                        if (result.title) {
                            p.title = result.title;
                        }
                        if (result.description) {
                            p.description = result.description;
                        }
                        if (result.image) {
                            p.image = result.image;
                        } else if (result['og:image']) {
                            p.image = result['og:image'];
                        }
                        if (result.host) {
                            p.host = result.host;
                        }
                        if (result.url) {
                            p.url = result.url;
                        }
                        appendElement(p);
                    }
                });
            }
        }
        /**
         * Set editor value
         */
        obj.setData = function (html) {
            editor.innerHTML = html;
            cursor();
        }
        /**
         * Get editor data
         */
        obj.getData = function (json) {
            if (!json) {
                var data = editor.innerHTML;
            } else {
                var data = {
                    content: '',
                }
                // Get tag users
                var tagged = editor.querySelectorAll('.post-tag');
                if (tagged.length) {
                    data.users = [];
                    for (var i = 0; i < tagged.length; i++) {
                        var userId = tagged[i].getAttribute('data-user');
                        if (userId) {
                            data.users.push(userId);
                        }
                    }
                    data.users = data.users.join(',');
                }
                if (snippet.innerHTML) {
                    var index = 0;
                    data.snippet = {};
                    for (var i = 0; i < snippet.children.length; i++) {
                        // Get key from element
                        var key = snippet.children[i].getAttribute('data-k');
                        if (key) {
                            if (key == 'image') {
                                data.snippet.image = snippet.children[i].children[0].getAttribute('src');
                            } else {
                                data.snippet[key] = snippet.children[i].innerHTML;
                            }
                        }
                    }
                    snippet.innerHTML = '';
                    snippet.remove();
                }
                var text = editor.innerHTML;
                text = text.replace(/<br>/g, "\n");
                text = text.replace(/<\/div>/g, "<\/div>\n");
                text = text.replace(/<(?:.|\n)*?>/gm, "");
                data.content = text.trim();
                data = JSON.stringify(data);
            }
            return data;
        }
        // Reset
        obj.reset = function () {
            editor.innerHTML = '';
        }
        obj.addPdf = function (data) {
            if (data.result.substr(0, 4) != 'data') {
                console.error('Invalid source');
            } else {
                var canvas = document.createElement('canvas');
                canvas.width = 60;
                canvas.height = 60;
                var img = new Image();
                var ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                canvas.toBlob(function (blob) {
                    var newImage = document.createElement('img');
                    newImage.src = window.URL.createObjectURL(blob);
                    newImage.setAttribute('data-extension', 'pdf');
                    if (data.name) {
                        newImage.setAttribute('data-name', data.name);
                    }
                    if (data.size) {
                        newImage.setAttribute('data-size', data.size);
                    }
                    if (data.date) {
                        newImage.setAttribute('data-date', data.date);
                    }
                    newImage.className = 'jfile pdf';
                    insertNodeAtCaret(newImage);
                    jSuites.files[newImage.src] = data.result.substr(data.result.indexOf(',') + 1);
                });
            }
        }
        obj.addImage = function (src, name, size, date) {
            if (src.substr(0, 4) != 'data' && !obj.options.remoteParser) {
                console.error('remoteParser not defined in your initialization');
            } else {
                // This is to process cross domain images
                if (src.substr(0, 4) == 'data') {
                    var extension = src.split(';')
                    extension = extension[0].split('/');
                    extension = extension[1];
                } else {
                    var extension = src.substr(src.lastIndexOf('.') + 1);
                    // Work for cross browsers
                    src = obj.options.remoteParser + src;
                }
                var img = new Image();
                img.onload = function onload() {
                    var canvas = document.createElement('canvas');
                    canvas.width = img.width;
                    canvas.height = img.height;
                    var ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                    canvas.toBlob(function (blob) {
                        var newImage = document.createElement('img');
                        newImage.src = window.URL.createObjectURL(blob);
                        newImage.setAttribute('tabindex', '900');
                        newImage.setAttribute('data-extension', extension);
                        if (name) {
                            newImage.setAttribute('data-name', name);
                        }
                        if (size) {
                            newImage.setAttribute('data-size', size);
                        }
                        if (date) {
                            newImage.setAttribute('data-date', date);
                        }
                        newImage.className = 'jfile';
                        var content = canvas.toDataURL();
                        insertNodeAtCaret(newImage);
                        jSuites.files[newImage.src] = content.substr(content.indexOf(',') + 1);
                    });
                };
                img.src = src;
            }
        }
        obj.addFile = function (files) {
            var reader = [];
            for (var i = 0; i < files.length; i++) {
                if (files[i].size > obj.options.maxFileSize) {
                    alert('The file is too big');
                } else {
                    // Only PDF or Images
                    var type = files[i].type.split('/');
                    if (type[0] == 'image') {
                        type = 1;
                    } else if (type[1] == 'pdf') {
                        type = 2;
                    } else {
                        type = 0;
                    }
                    if (type) {
                        // Create file
                        reader[i] = new FileReader();
                        reader[i].index = i;
                        reader[i].type = type;
                        reader[i].name = files[i].name;
                        reader[i].date = files[i].lastModified;
                        reader[i].size = files[i].size;
                        reader[i].addEventListener("load", function (data) {
                            // Get result
                            if (data.target.type == 2) {
                                if (obj.options.acceptFiles == true) {
                                    obj.addPdf(data.target);
                                }
                            } else {
                                obj.addImage(data.target.result, data.target.name, data.total, data.target.lastModified);
                            }
                        }, false);
                        reader[i].readAsDataURL(files[i])
                    } else {
                        alert('The extension is not allowed');
                    }
                }
            }
        }
        // Destroy
        obj.destroy = function () {
            editor.removeEventListener('mouseup', editorMouseUp);
            editor.removeEventListener('mousedown', editorMouseDown);
            editor.removeEventListener('mousemove', editorMouseMove);
            editor.removeEventListener('keyup', editorKeyUp);
            editor.removeEventListener('keydown', editorKeyDown);
            editor.removeEventListener('dragstart', editorDragStart);
            editor.removeEventListener('dragenter', editorDragEnter);
            editor.removeEventListener('dragover', editorDragOver);
            editor.removeEventListener('drop', editorDrop);
            editor.removeEventListener('paste', editorPaste);
            if (typeof (obj.options.onblur) == 'function') {
                editor.removeEventListener('blur', editorBlur);
            }
            if (typeof (obj.options.onfocus) == 'function') {
                editor.removeEventListener('focus', editorFocus);
            }
            el.editor = null;
            el.classList.remove('jeditor-container');
            toolbar.remove();
            snippet.remove();
            editor.remove();
        }
        var isLetter = function (str) {
            var regex = /([\u0041-\u005A\u0061-\u007A\u00AA\u00B5\u00BA\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02C1\u02C6-\u02D1\u02E0-\u02E4\u02EC\u02EE\u0370-\u0374\u0376\u0377\u037A-\u037D\u0386\u0388-\u038A\u038C\u038E-\u03A1\u03A3-\u03F5\u03F7-\u0481\u048A-\u0527\u0531-\u0556\u0559\u0561-\u0587\u05D0-\u05EA\u05F0-\u05F2\u0620-\u064A\u066E\u066F\u0671-\u06D3\u06D5\u06E5\u06E6\u06EE\u06EF\u06FA-\u06FC\u06FF\u0710\u0712-\u072F\u074D-\u07A5\u07B1\u07CA-\u07EA\u07F4\u07F5\u07FA\u0800-\u0815\u081A\u0824\u0828\u0840-\u0858\u08A0\u08A2-\u08AC\u0904-\u0939\u093D\u0950\u0958-\u0961\u0971-\u0977\u0979-\u097F\u0985-\u098C\u098F\u0990\u0993-\u09A8\u09AA-\u09B0\u09B2\u09B6-\u09B9\u09BD\u09CE\u09DC\u09DD\u09DF-\u09E1\u09F0\u09F1\u0A05-\u0A0A\u0A0F\u0A10\u0A13-\u0A28\u0A2A-\u0A30\u0A32\u0A33\u0A35\u0A36\u0A38\u0A39\u0A59-\u0A5C\u0A5E\u0A72-\u0A74\u0A85-\u0A8D\u0A8F-\u0A91\u0A93-\u0AA8\u0AAA-\u0AB0\u0AB2\u0AB3\u0AB5-\u0AB9\u0ABD\u0AD0\u0AE0\u0AE1\u0B05-\u0B0C\u0B0F\u0B10\u0B13-\u0B28\u0B2A-\u0B30\u0B32\u0B33\u0B35-\u0B39\u0B3D\u0B5C\u0B5D\u0B5F-\u0B61\u0B71\u0B83\u0B85-\u0B8A\u0B8E-\u0B90\u0B92-\u0B95\u0B99\u0B9A\u0B9C\u0B9E\u0B9F\u0BA3\u0BA4\u0BA8-\u0BAA\u0BAE-\u0BB9\u0BD0\u0C05-\u0C0C\u0C0E-\u0C10\u0C12-\u0C28\u0C2A-\u0C33\u0C35-\u0C39\u0C3D\u0C58\u0C59\u0C60\u0C61\u0C85-\u0C8C\u0C8E-\u0C90\u0C92-\u0CA8\u0CAA-\u0CB3\u0CB5-\u0CB9\u0CBD\u0CDE\u0CE0\u0CE1\u0CF1\u0CF2\u0D05-\u0D0C\u0D0E-\u0D10\u0D12-\u0D3A\u0D3D\u0D4E\u0D60\u0D61\u0D7A-\u0D7F\u0D85-\u0D96\u0D9A-\u0DB1\u0DB3-\u0DBB\u0DBD\u0DC0-\u0DC6\u0E01-\u0E30\u0E32\u0E33\u0E40-\u0E46\u0E81\u0E82\u0E84\u0E87\u0E88\u0E8A\u0E8D\u0E94-\u0E97\u0E99-\u0E9F\u0EA1-\u0EA3\u0EA5\u0EA7\u0EAA\u0EAB\u0EAD-\u0EB0\u0EB2\u0EB3\u0EBD\u0EC0-\u0EC4\u0EC6\u0EDC-\u0EDF\u0F00\u0F40-\u0F47\u0F49-\u0F6C\u0F88-\u0F8C\u1000-\u102A\u103F\u1050-\u1055\u105A-\u105D\u1061\u1065\u1066\u106E-\u1070\u1075-\u1081\u108E\u10A0-\u10C5\u10C7\u10CD\u10D0-\u10FA\u10FC-\u1248\u124A-\u124D\u1250-\u1256\u1258\u125A-\u125D\u1260-\u1288\u128A-\u128D\u1290-\u12B0\u12B2-\u12B5\u12B8-\u12BE\u12C0\u12C2-\u12C5\u12C8-\u12D6\u12D8-\u1310\u1312-\u1315\u1318-\u135A\u1380-\u138F\u13A0-\u13F4\u1401-\u166C\u166F-\u167F\u1681-\u169A\u16A0-\u16EA\u1700-\u170C\u170E-\u1711\u1720-\u1731\u1740-\u1751\u1760-\u176C\u176E-\u1770\u1780-\u17B3\u17D7\u17DC\u1820-\u1877\u1880-\u18A8\u18AA\u18B0-\u18F5\u1900-\u191C\u1950-\u196D\u1970-\u1974\u1980-\u19AB\u19C1-\u19C7\u1A00-\u1A16\u1A20-\u1A54\u1AA7\u1B05-\u1B33\u1B45-\u1B4B\u1B83-\u1BA0\u1BAE\u1BAF\u1BBA-\u1BE5\u1C00-\u1C23\u1C4D-\u1C4F\u1C5A-\u1C7D\u1CE9-\u1CEC\u1CEE-\u1CF1\u1CF5\u1CF6\u1D00-\u1DBF\u1E00-\u1F15\u1F18-\u1F1D\u1F20-\u1F45\u1F48-\u1F4D\u1F50-\u1F57\u1F59\u1F5B\u1F5D\u1F5F-\u1F7D\u1F80-\u1FB4\u1FB6-\u1FBC\u1FBE\u1FC2-\u1FC4\u1FC6-\u1FCC\u1FD0-\u1FD3\u1FD6-\u1FDB\u1FE0-\u1FEC\u1FF2-\u1FF4\u1FF6-\u1FFC\u2071\u207F\u2090-\u209C\u2102\u2107\u210A-\u2113\u2115\u2119-\u211D\u2124\u2126\u2128\u212A-\u212D\u212F-\u2139\u213C-\u213F\u2145-\u2149\u214E\u2183\u2184\u2C00-\u2C2E\u2C30-\u2C5E\u2C60-\u2CE4\u2CEB-\u2CEE\u2CF2\u2CF3\u2D00-\u2D25\u2D27\u2D2D\u2D30-\u2D67\u2D6F\u2D80-\u2D96\u2DA0-\u2DA6\u2DA8-\u2DAE\u2DB0-\u2DB6\u2DB8-\u2DBE\u2DC0-\u2DC6\u2DC8-\u2DCE\u2DD0-\u2DD6\u2DD8-\u2DDE\u2E2F\u3005\u3006\u3031-\u3035\u303B\u303C\u3041-\u3096\u309D-\u309F\u30A1-\u30FA\u30FC-\u30FF\u3105-\u312D\u3131-\u318E\u31A0-\u31BA\u31F0-\u31FF\u3400-\u4DB5\u4E00-\u9FCC\uA000-\uA48C\uA4D0-\uA4FD\uA500-\uA60C\uA610-\uA61F\uA62A\uA62B\uA640-\uA66E\uA67F-\uA697\uA6A0-\uA6E5\uA717-\uA71F\uA722-\uA788\uA78B-\uA78E\uA790-\uA793\uA7A0-\uA7AA\uA7F8-\uA801\uA803-\uA805\uA807-\uA80A\uA80C-\uA822\uA840-\uA873\uA882-\uA8B3\uA8F2-\uA8F7\uA8FB\uA90A-\uA925\uA930-\uA946\uA960-\uA97C\uA984-\uA9B2\uA9CF\uAA00-\uAA28\uAA40-\uAA42\uAA44-\uAA4B\uAA60-\uAA76\uAA7A\uAA80-\uAAAF\uAAB1\uAAB5\uAAB6\uAAB9-\uAABD\uAAC0\uAAC2\uAADB-\uAADD\uAAE0-\uAAEA\uAAF2-\uAAF4\uAB01-\uAB06\uAB09-\uAB0E\uAB11-\uAB16\uAB20-\uAB26\uAB28-\uAB2E\uABC0-\uABE2\uAC00-\uD7A3\uD7B0-\uD7C6\uD7CB-\uD7FB\uF900-\uFA6D\uFA70-\uFAD9\uFB00-\uFB06\uFB13-\uFB17\uFB1D\uFB1F-\uFB28\uFB2A-\uFB36\uFB38-\uFB3C\uFB3E\uFB40\uFB41\uFB43\uFB44\uFB46-\uFBB1\uFBD3-\uFD3D\uFD50-\uFD8F\uFD92-\uFDC7\uFDF0-\uFDFB\uFE70-\uFE74\uFE76-\uFEFC\uFF21-\uFF3A\uFF41-\uFF5A\uFF66-\uFFBE\uFFC2-\uFFC7\uFFCA-\uFFCF\uFFD2-\uFFD7\uFFDA-\uFFDC]+)/g;
            return str.match(regex) ? 1 : 0;
        }
        // Event handlers
        var editorMouseUp = function (e) {
            editorAction = false;
        }
        var editorMouseDown = function (e) {
            var close = function (snippet) {
                var rect = snippet.getBoundingClientRect();
                if (rect.width - (e.clientX - rect.left) < 40 && e.clientY - rect.top < 40) {
                    snippet.innerHTML = '';
                    snippet.remove();
                }
            }
            if (e.target.tagName == 'IMG') {
                if (e.target.style.cursor) {
                    var rect = e.target.getBoundingClientRect();
                    editorAction = {
                        e: e.target,
                        x: e.clientX,
                        y: e.clientY,
                        w: rect.width,
                        h: rect.height,
                        d: e.target.style.cursor,
                    }
                    if (!e.target.style.width) {
                        e.target.style.width = rect.width + 'px';
                    }
                    if (!e.target.style.height) {
                        e.target.style.height = rect.height + 'px';
                    }
                    var s = window.getSelection();
                    if (s.rangeCount) {
                        for (var i = 0; i < s.rangeCount; i++) {
                            s.removeRange(s.getRangeAt(i));
                        }
                    }
                } else {
                    editorAction = true;
                }
            } else {
                if (e.target.classList.contains('snippet')) {
                    close(e.target);
                } else if (e.target.parentNode.classList.contains('snippet')) {
                    close(e.target.parentNode);
                }
                editorAction = true;
            }
        }
        var editorMouseMove = function (e) {
            if (e.target.tagName == 'IMG') {
                if (e.target.getAttribute('tabindex')) {
                    var rect = e.target.getBoundingClientRect();
                    if (e.clientY - rect.top < 5) {
                        if (rect.width - (e.clientX - rect.left) < 5) {
                            e.target.style.cursor = 'ne-resize';
                        } else if (e.clientX - rect.left < 5) {
                            e.target.style.cursor = 'nw-resize';
                        } else {
                            e.target.style.cursor = 'n-resize';
                        }
                    } else if (rect.height - (e.clientY - rect.top) < 5) {
                        if (rect.width - (e.clientX - rect.left) < 5) {
                            e.target.style.cursor = 'se-resize';
                        } else if (e.clientX - rect.left < 5) {
                            e.target.style.cursor = 'sw-resize';
                        } else {
                            e.target.style.cursor = 's-resize';
                        }
                    } else if (rect.width - (e.clientX - rect.left) < 5) {
                        e.target.style.cursor = 'e-resize';
                    } else if (e.clientX - rect.left < 5) {
                        e.target.style.cursor = 'w-resize';
                    } else {
                        e.target.style.cursor = '';
                    }
                }
            }
            // Move
            if (e.which == 1 && editorAction && editorAction.d) {
                if (editorAction.d == 'e-resize' || editorAction.d == 'ne-resize' || editorAction.d == 'se-resize') {
                    editorAction.e.style.width = (editorAction.w + (e.clientX - editorAction.x)) + 'px';
                    if (e.shiftKey) {
                        var newHeight = (e.clientX - editorAction.x) * (editorAction.h / editorAction.w);
                        editorAction.e.style.height = editorAction.h + newHeight + 'px';
                    } else {
                        var newHeight = null;
                    }
                }
                if (!newHeight) {
                    if (editorAction.d == 's-resize' || editorAction.d == 'se-resize' || editorAction.d == 'sw-resize') {
                        if (!e.shiftKey) {
                            editorAction.e.style.height = editorAction.h + (e.clientY - editorAction.y);
                        }
                    }
                }
            }
        }
        var editorKeyUp = function (e) {
            if (!editor.innerHTML) {
                editor.innerHTML = '<div><br></div>';
            }
            if (typeof (obj.options.onkeyup) == 'function') {
                obj.options.onkeyup(e, el);
            }
        }
        var editorKeyDown = function (e) {
            // Check for URL
            if (obj.options.parseURL == true) {
                verifyEditor();
            }
            // Closable
            if (typeof (obj.options.onenter) == 'function' && e.which == 13) {
                var data = obj.getData();
                obj.options.onenter(obj, el, data, e);
            }
            if (typeof (obj.options.onkeydown) == 'function') {
                obj.options.onkeydown(e, el);
            }
        }
        var editorPaste = function (e) {
            if (e.clipboardData || e.originalEvent.clipboardData) {
                var html = (e.originalEvent || e).clipboardData.getData('text/html');
                var text = (e.originalEvent || e).clipboardData.getData('text/plain');
                var file = (e.originalEvent || e).clipboardData.files
            } else if (window.clipboardData) {
                var html = window.clipboardData.getData('Html');
                var text = window.clipboardData.getData('Text');
                var file = window.clipboardData.files
            }
            if (file.length) {
                // Paste a image from the clipboard
                obj.addFile(file);
            } else {
                // Paste text
                text = text.split('\r\n');
                var str = '';
                if (e.target.nodeName == 'DIV' && !e.target.classList.contains('jeditor')) {
                    for (var i = 0; i < text.length; i++) {
                        if (text[i]) {
                            str += text[i] + "<br>\r\n";
                        }
                    }
                } else {
                    for (var i = 0; i < text.length; i++) {
                        if (text[i]) {
                            str += '<div>' + text[i] + '</div>';
                        } else {
                            str += '<div><br></div>';
                        }
                    }
                }
                // Insert text
                document.execCommand('insertHtml', false, str);
                // Extra images from the paste
                if (obj.options.acceptImages == true) {
                    extractImageFromHtml(html);
                }
            }
            e.preventDefault();
        }
        var editorDragStart = function (e) {
            if (editorAction && editorAction.e) {
                e.preventDefault();
            }
        }
        var editorDragEnter = function (e) {
            if (editorAction || obj.options.dropZone == false) {
                // Do nothing
            } else {
                el.style.border = '1px dashed #000';
            }
        }
        var editorDragOver = function (e) {
            if (editorAction || obj.options.dropZone == false) {
                // Do nothing
            } else {
                if (editorTimer) {
                    clearTimeout(editorTimer);
                }
                editorTimer = setTimeout(function () {
                    el.style.border = '';
                }, 100);
            }
        }
        var editorDrop = function (e) {
            if (editorAction || obj.options.dropZone == false) {
                // Do nothing
            } else {
                // Position caret on the drop
                var range = null;
                if (document.caretRangeFromPoint) {
                    range = document.caretRangeFromPoint(e.clientX, e.clientY);
                } else if (e.rangeParent) {
                    range = document.createRange();
                    range.setStart(e.rangeParent, e.rangeOffset);
                }
                var sel = window.getSelection();
                sel.removeAllRanges();
                sel.addRange(range);
                sel.anchorNode.parentNode.focus();
                var html = (e.originalEvent || e).dataTransfer.getData('text/html');
                var text = (e.originalEvent || e).dataTransfer.getData('text/plain');
                var file = (e.originalEvent || e).dataTransfer.files;
                if (file.length) {
                    obj.addFile(file);
                } else if (text) {
                    extractImageFromHtml(html);
                }
                el.style.border = '';
                e.preventDefault();
            }
        }
        var editorBlur = function () {
            obj.options.onblur(obj, el, obj.getData());
        }
        var editorFocus = function () {
            obj.options.onfocus(obj, el, obj.getData());
        }
        editor.addEventListener('mouseup', editorMouseUp);
        editor.addEventListener('mousedown', editorMouseDown);
        editor.addEventListener('mousemove', editorMouseMove);
        editor.addEventListener('keyup', editorKeyUp);
        editor.addEventListener('keydown', editorKeyDown);
        editor.addEventListener('dragstart', editorDragStart);
        editor.addEventListener('dragenter', editorDragEnter);
        editor.addEventListener('dragover', editorDragOver);
        editor.addEventListener('drop', editorDrop);
        editor.addEventListener('paste', editorPaste);
        // Blur
        if (typeof (obj.options.onblur) == 'function') {
            editor.addEventListener('blur', editorBlur);
        }
        // Focus
        if (typeof (obj.options.onfocus) == 'function') {
            editor.addEventListener('focus', editorFocus);
        }
        // Onload
        if (typeof (obj.options.onload) == 'function') {
            obj.options.onload(el, editor);
        }
        // Set value to the editor
        editor.innerHTML = value;
        // Append editor to the containre
        el.appendChild(editor);
        // Snippet
        if (obj.options.snippet) {
            appendElement(obj.options.snippet);
        }
        // Default toolbar
        if (obj.options.toolbar == null) {
            obj.options.toolbar = jSuites.editor.getDefaultToolbar();
        }
        // Add toolbar
        if (obj.options.toolbar) {
            for (var i = 0; i < obj.options.toolbar.length; i++) {
                if (obj.options.toolbar[i].icon) {
                    var item = document.createElement('div');
                    item.style.userSelect = 'none';
                    var itemIcon = document.createElement('i');
                    itemIcon.className = 'material-icons';
                    itemIcon.innerHTML = obj.options.toolbar[i].icon;
                    itemIcon.onclick = (function (a) {
                        let b = a;
                        return function () {
                            obj.options.toolbar[b].onclick(el, obj, this)
                        };
                    })(i);
                    item.appendChild(itemIcon);
                    toolbar.appendChild(item);
                } else {
                    if (obj.options.toolbar[i].type == 'divisor') {
                        var item = document.createElement('div');
                        item.className = 'jeditor-toolbar-divisor';
                        toolbar.appendChild(item);
                    } else if (obj.options.toolbar[i].type == 'button') {
                        var item = document.createElement('div');
                        item.classList.add('jeditor-toolbar-button');
                        item.innerHTML = obj.options.toolbar[i].value;
                        toolbar.appendChild(item);
                    }
                }
            }
            el.appendChild(toolbar);
        }
        // Focus to the editor
        if (obj.options.focus == true) {
            jSuites.editor.setCursor(editor);
        }
        el.editor = obj;
        return obj;
    });
    jSuites.editor.setCursor = function (element) {
        element.focus();
        document.execCommand('selectAll');
        var sel = window.getSelection();
        var range = sel.getRangeAt(0);
        var node = range.endContainer;
        var size = node.length;
        range.setStart(node, size);
        range.setEnd(node, size);
        sel.removeAllRanges();
        sel.addRange(range);
    }
    jSuites.editor.getDomain = function (url) {
        return url.replace('http://', '').replace('https://', '').replace('www.', '').split(/[/?#]/)[0].split(/:/g)[0];
    }
    jSuites.editor.detectUrl = function (text) {
        var expression = /(((https?:\/\/)|(www\.))[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|]+)/ig;
        var links = text.match(expression);
        if (links) {
            if (links[0].substr(0, 3) == 'www') {
                links[0] = 'http://' + links[0];
            }
        }
        return links;
    }
    jSuites.editor.youtubeParser = function (url) {
        var regExp = /^.*((youtu.be\/)|(v\/)|(\/u\/\w\/)|(embed\/)|(watch\?))\??v?=?([^#\&\?]*).*/;
        var match = url.match(regExp);
        return (match && match[7].length == 11) ? match[7] : false;
    }
    jSuites.editor.getDefaultToolbar = function () {
        return [{
                icon: 'undo',
                onclick: function () {
                    document.execCommand('undo');
                }
            },
            {
                icon: 'redo',
                onclick: function () {
                    document.execCommand('redo');
                }
            },
            {
                type: 'divisor'
            },
            {
                icon: 'format_bold',
                onclick: function (a, b, c) {
                    document.execCommand('bold');
                    if (document.queryCommandState("bold")) {
                        c.classList.add('selected');
                    } else {
                        c.classList.remove('selected');
                    }
                }
            },
            {
                icon: 'format_italic',
                onclick: function (a, b, c) {
                    document.execCommand('italic');
                    if (document.queryCommandState("italic")) {
                        c.classList.add('selected');
                    } else {
                        c.classList.remove('selected');
                    }
                }
            },
            {
                icon: 'format_underline',
                onclick: function (a, b, c) {
                    document.execCommand('underline');
                    if (document.queryCommandState("underline")) {
                        c.classList.add('selected');
                    } else {
                        c.classList.remove('selected');
                    }
                }
            },
            {
                type: 'divisor'
            },
            {
                icon: 'format_list_bulleted',
                onclick: function (a, b, c) {
                    document.execCommand('insertUnorderedList');
                    if (document.queryCommandState("insertUnorderedList")) {
                        c.classList.add('selected');
                    } else {
                        c.classList.remove('selected');
                    }
                }
            },
            {
                icon: 'format_list_numbered',
                onclick: function (a, b, c) {
                    document.execCommand('insertOrderedList');
                    if (document.queryCommandState("insertOrderedList")) {
                        c.classList.add('selected');
                    } else {
                        c.classList.remove('selected');
                    }
                }
            },
            {
                icon: 'format_indent_increase',
                onclick: function (a, b, c) {
                    document.execCommand('indent', true, null);
                    if (document.queryCommandState("indent")) {
                        c.classList.add('selected');
                    } else {
                        c.classList.remove('selected');
                    }
                }
            },
            {
                icon: 'format_indent_decrease',
                onclick: function (a, b, c) {
                    document.execCommand('outdent');
                    if (document.queryCommandState("outdent")) {
                        c.classList.add('selected');
                    } else {
                        c.classList.remove('selected');
                    }
                }
            }
            /*{
                type:'select',
                items: ['Verdana','Arial','Courier New'],
                onchange: function() {
                }
            },
            {
                type:'select',
                items: ['10px','12px','14px','16px','18px','20px','22px'],
                onchange: function() {
                }
            },
            {
                icon:'format_align_left',
                onclick: function() {
                    document.execCommand('JustifyLeft');
                    if (document.queryCommandState("JustifyLeft")) {
                        this.classList.add('selected');
                    } else {
                        this.classList.remove('selected');
                    }
                }
            },
            {
                icon:'format_align_center',
                onclick: function() {
                    document.execCommand('justifyCenter');
                    if (document.queryCommandState("justifyCenter")) {
                        this.classList.add('selected');
                    } else {
                        this.classList.remove('selected');
                    }
                }
            },
            {
                icon:'format_align_right',
                onclick: function() {
                    document.execCommand('justifyRight');
                    if (document.queryCommandState("justifyRight")) {
                        this.classList.add('selected');
                    } else {
                        this.classList.remove('selected');
                    }
                }
            },
            {
                icon:'format_align_justify',
                onclick: function() {
                    document.execCommand('justifyFull');
                    if (document.queryCommandState("justifyFull")) {
                        this.classList.add('selected');
                    } else {
                        this.classList.remove('selected');
                    }
                }
            },
            {
                icon:'format_list_bulleted',
                onclick: function() {
                    document.execCommand('insertUnorderedList');
                    if (document.queryCommandState("insertUnorderedList")) {
                        this.classList.add('selected');
                    } else {
                        this.classList.remove('selected');
                    }
                }
            }*/
        ];
    }
    jSuites.image = (function (el, options) {
        var obj = {};
        obj.options = {};
        // Default configuration
        var defaults = {
            minWidth: false,
            onchange: null,
            singleFile: true,
            remoteParser: null,
            text: {
                extensionNotAllowed: 'The extension is not allowed',
                imageTooSmall: 'The resolution is too low, try a image with a better resolution. width > 800px',
            }
        };
        // Loop through our object
        for (var property in defaults) {
            if (options && options.hasOwnProperty(property)) {
                obj.options[property] = options[property];
            } else {
                obj.options[property] = defaults[property];
            }
        }
        // Upload icon
        el.classList.add('jupload');
        // Add image
        obj.addImage = function (file) {
            if (!file.date) {
                file.date = '';
            }
            var img = document.createElement('img');
            img.setAttribute('data-date', file.lastmodified ? file.lastmodified : file.date);
            img.setAttribute('data-name', file.name);
            img.setAttribute('data-size', file.size);
            img.setAttribute('data-small', file.small ? file.small : '');
            img.setAttribute('data-cover', file.cover ? 1 : 0);
            img.setAttribute('data-extension', file.extension);
            img.setAttribute('src', file.file);
            img.className = 'jfile';
            img.style.width = '100%';
            return img;
        }
        // Add image
        obj.addImages = function (files) {
            if (obj.options.singleFile == true) {
                el.innerHTML = '';
            }
            for (var i = 0; i < files.length; i++) {
                el.appendChild(obj.addImage(files[i]));
            }
        }
        obj.addFromFile = function (file) {
            var type = file.type.split('/');
            if (type[0] == 'image') {
                if (obj.options.singleFile == true) {
                    el.innerHTML = '';
                }
                var imageFile = new FileReader();
                imageFile.addEventListener("load", function (v) {
                    var img = new Image();
                    img.onload = function onload() {
                        var canvas = document.createElement('canvas');
                        canvas.width = img.width;
                        canvas.height = img.height;
                        var ctx = canvas.getContext('2d');
                        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                        var data = {
                            file: canvas.toDataURL(),
                            extension: file.name.substr(file.name.lastIndexOf('.') + 1),
                            name: file.name,
                            size: file.size,
                            lastmodified: file.lastModified,
                        }
                        var newImage = obj.addImage(data);
                        el.appendChild(newImage);
                        // Onchange
                        if (typeof (obj.options.onchange) == 'function') {
                            obj.options.onchange(newImage);
                        }
                    };
                    img.src = v.srcElement.result;
                });
                imageFile.readAsDataURL(file);
            } else {
                alert(text.extentionNotAllowed);
            }
        }
        obj.addFromUrl = function (src) {
            if (src.substr(0, 4) != 'data' && !obj.options.remoteParser) {
                console.error('remoteParser not defined in your initialization');
            } else {
                // This is to process cross domain images
                if (src.substr(0, 4) == 'data') {
                    var extension = src.split(';')
                    extension = extension[0].split('/');
                    extension = extension[1];
                } else {
                    var extension = src.substr(src.lastIndexOf('.') + 1);
                    // Work for cross browsers
                    src = obj.options.remoteParser + src;
                }
                var img = new Image();
                img.onload = function onload() {
                    var canvas = document.createElement('canvas');
                    canvas.width = img.width;
                    canvas.height = img.height;
                    var ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                    canvas.toBlob(function (blob) {
                        var data = {
                            file: window.URL.createObjectURL(blob),
                            extension: extension
                        }
                        var newImage = obj.addImage(data);
                        el.appendChild(newImage);
                        // Keep base64 ready to go
                        var content = canvas.toDataURL();
                        jSuites.files[data.file] = content.substr(content.indexOf(',') + 1);
                        // Onchange
                        if (typeof (obj.options.onchange) == 'function') {
                            obj.options.onchange(newImage);
                        }
                    });
                };
                img.src = src;
            }
        }
        var attachmentInput = document.createElement('input');
        attachmentInput.type = 'file';
        attachmentInput.setAttribute('accept', 'image/*');
        attachmentInput.onchange = function () {
            for (var i = 0; i < this.files.length; i++) {
                obj.addFromFile(this.files[i]);
            }
        }
        el.addEventListener("dblclick", function (e) {
            jSuites.click(attachmentInput);
        });
        el.addEventListener('dragenter', function (e) {
            el.style.border = '1px dashed #000';
        });
        el.addEventListener('dragleave', function (e) {
            el.style.border = '1px solid #eee';
        });
        el.addEventListener('dragstop', function (e) {
            el.style.border = '1px solid #eee';
        });
        el.addEventListener('dragover', function (e) {
            e.preventDefault();
        });
        el.addEventListener('drop', function (e) {
            e.preventDefault();
            e.stopPropagation();
            var html = (e.originalEvent || e).dataTransfer.getData('text/html');
            var file = (e.originalEvent || e).dataTransfer.files;
            if (file.length) {
                for (var i = 0; i < e.dataTransfer.files.length; i++) {
                    obj.addFromFile(e.dataTransfer.files[i]);
                }
            } else if (html) {
                if (obj.options.singleFile == true) {
                    el.innerHTML = '';
                }
                // Create temp element
                var div = document.createElement('div');
                div.innerHTML = html;
                // Extract images
                var img = div.querySelectorAll('img');
                if (img.length) {
                    for (var i = 0; i < img.length; i++) {
                        obj.addFromUrl(img[i].src);
                    }
                }
            }
            el.style.border = '1px solid #eee';
            return false;
        });
        el.image = obj;
        return obj;
    });
    /**
     * (c) jLoading
     * https://github.com/paulhodel/jtools
     *
     * @author: Paul Hodel <paul.hodel@gmail.com>
     * @description: Page loading spin
     */
    jSuites.loading = (function () {
        var obj = {};
        var loading = document.createElement('div');
        loading.className = 'jloading';
        obj.show = function () {
            document.body.appendChild(loading);
        };
        obj.hide = function () {
            document.body.removeChild(loading);
        };
        return obj;
    })();
    /**
     * (c) jLogin
     * https://github.com/paulhodel/jtools
     *
     * @author: Paul Hodel <paul.hodel@gmail.com>
     * @description: Login helper
     */
    jSuites.login = (function (el, options) {
        var obj = {};
        obj.options = {};
        // Default configuration
        var defaults = {
            url: window.location.href,
            prepareRequest: null,
            accessToken: null,
            deviceToken: null,
            facebookUrl: null,
            maxHeight: null,
            onload: null,
            message: null,
            logo: null,
            newProfile: false,
            newProfileUrl: false,
            newProfileLogin: false,
            fullscreen: false,
        };
        // Loop through our object
        for (var property in defaults) {
            if (options && options.hasOwnProperty(property)) {
                obj.options[property] = options[property];
            } else {
                obj.options[property] = defaults[property];
            }
        }
        // Message console container
        if (!obj.options.message) {
            var messageElement = document.querySelector('.message');
            if (messageElement) {
                obj.options.message = messageElement;
            }
        }
        // Action
        var action = null;
        // Container
        var container = document.createElement('form');
        el.appendChild(container);
        // Logo
        var divLogo = document.createElement('div');
        divLogo.className = 'jlogin-logo'
        container.appendChild(divLogo);
        if (obj.options.logo) {
            var logo = document.createElement('img');
            logo.src = obj.options.logo;
            divLogo.appendChild(logo);
        }
        // Code
        var labelCode = document.createElement('label');
        labelCode.innerHTML = 'Please enter here the code received';
        var inputCode = document.createElement('input');
        inputCode.type = 'number';
        inputCode.id = 'code';
        inputCode.setAttribute('maxlength', 6);
        var divCode = document.createElement('div');
        divCode.appendChild(labelCode);
        divCode.appendChild(inputCode);
        // Hash
        var inputHash = document.createElement('input');
        inputHash.type = 'hidden';
        inputHash.name = 'h';
        var divHash = document.createElement('div');
        divHash.appendChild(inputHash);
        // Recovery
        var inputRecovery = document.createElement('input');
        inputRecovery.type = 'hidden';
        inputRecovery.name = 'recovery';
        inputRecovery.value = '1';
        var divRecovery = document.createElement('div');
        divRecovery.appendChild(inputRecovery);
        // Login
        var labelLogin = document.createElement('label');
        labelLogin.innerHTML = 'Login';
        var inputLogin = document.createElement('input');
        inputLogin.type = 'text';
        inputLogin.name = 'login';
        inputLogin.setAttribute('autocomplete', 'off');
        inputLogin.onkeyup = function () {
            this.value = this.value.toLowerCase().replace(/[^a-zA-Z0-9_+]+/gi, '');
        }
        var divLogin = document.createElement('div');
        divLogin.appendChild(labelLogin);
        divLogin.appendChild(inputLogin);
        // Name
        var labelName = document.createElement('label');
        labelName.innerHTML = 'Name';
        var inputName = document.createElement('input');
        inputName.type = 'text';
        inputName.name = 'name';
        var divName = document.createElement('div');
        divName.appendChild(labelName);
        divName.appendChild(inputName);
        // Email
        var labelUsername = document.createElement('label');
        labelUsername.innerHTML = 'E-mail';
        var inputUsername = document.createElement('input');
        inputUsername.type = 'text';
        inputUsername.name = 'username';
        inputUsername.setAttribute('autocomplete', 'new-username');
        var divUsername = document.createElement('div');
        divUsername.appendChild(labelUsername);
        divUsername.appendChild(inputUsername);
        // Password
        var labelPassword = document.createElement('label');
        labelPassword.innerHTML = 'Password';
        var inputPassword = document.createElement('input');
        inputPassword.type = 'password';
        inputPassword.name = 'password';
        inputPassword.setAttribute('autocomplete', 'new-password');
        var divPassword = document.createElement('div');
        divPassword.appendChild(labelPassword);
        divPassword.appendChild(inputPassword);
        divPassword.onkeydown = function (e) {
            if (e.keyCode == 13) {
                obj.execute();
            }
        }
        // Repeat password
        var labelRepeatPassword = document.createElement('label');
        labelRepeatPassword.innerHTML = 'Password';
        var inputRepeatPassword = document.createElement('input');
        inputRepeatPassword.type = 'password';
        inputRepeatPassword.name = 'password';
        var divRepeatPassword = document.createElement('div');
        divRepeatPassword.appendChild(labelRepeatPassword);
        divRepeatPassword.appendChild(inputRepeatPassword);
        // Remember checkbox
        var labelRemember = document.createElement('label');
        labelRemember.innerHTML = 'Remember me on this device';
        var inputRemember = document.createElement('input');
        inputRemember.type = 'checkbox';
        inputRemember.name = 'remember';
        inputRemember.value = '1';
        labelRemember.appendChild(inputRemember);
        var divRememberButton = document.createElement('div');
        divRememberButton.className = 'rememberButton';
        divRememberButton.appendChild(labelRemember);
        // Login button
        var actionButton = document.createElement('input');
        actionButton.type = 'button';
        actionButton.value = 'Log In';
        actionButton.onclick = function () {
            obj.execute();
        }
        var divActionButton = document.createElement('div');
        divActionButton.appendChild(actionButton);
        // Cancel button
        var cancelButton = document.createElement('div');
        cancelButton.innerHTML = 'Cancel';
        cancelButton.className = 'cancelButton';
        cancelButton.onclick = function () {
            obj.requestAccess();
        }
        var divCancelButton = document.createElement('div');
        divCancelButton.appendChild(cancelButton);
        // Captcha
        var labelCaptcha = document.createElement('label');
        labelCaptcha.innerHTML = 'Please type here the code below';
        var inputCaptcha = document.createElement('input');
        inputCaptcha.type = 'text';
        inputCaptcha.name = 'captcha';
        var imageCaptcha = document.createElement('img');
        var divCaptcha = document.createElement('div');
        divCaptcha.className = 'jlogin-captcha';
        divCaptcha.appendChild(labelCaptcha);
        divCaptcha.appendChild(inputCaptcha);
        divCaptcha.appendChild(imageCaptcha);
        // Facebook
        var facebookButton = document.createElement('div');
        facebookButton.innerHTML = 'Login with Facebook';
        facebookButton.className = 'facebookButton';
        var divFacebookButton = document.createElement('div');
        divFacebookButton.appendChild(facebookButton);
        divFacebookButton.onclick = function () {
            obj.requestLoginViaFacebook();
        }
        // Forgot password
        var inputRequest = document.createElement('span');
        inputRequest.innerHTML = 'Request a new password';
        var divRequestButton = document.createElement('div');
        divRequestButton.className = 'requestButton';
        divRequestButton.appendChild(inputRequest);
        divRequestButton.onclick = function () {
            obj.requestNewPassword();
        }
        // Create a new Profile
        var inputNewProfile = document.createElement('span');
        inputNewProfile.innerHTML = 'Create a new profile';
        var divNewProfileButton = document.createElement('div');
        divNewProfileButton.className = 'newProfileButton';
        divNewProfileButton.appendChild(inputNewProfile);
        divNewProfileButton.onclick = function () {
            obj.newProfile();
        }
        el.className = 'jlogin';
        if (obj.options.fullscreen == true) {
            el.classList.add('jlogin-fullscreen');
        }
        /** 
         * Show message
         */
        obj.showMessage = function (data) {
            var message = (typeof (data) == 'object') ? data.message : data;
            if (typeof (obj.options.showMessage) == 'function') {
                obj.options.showMessage(data);
            } else {
                jSuites.alert(data);
            }
        }
        /**
         * New profile
         */
        obj.newProfile = function () {
            container.innerHTML = '';
            container.appendChild(divLogo);
            if (obj.options.newProfileLogin) {
                container.appendChild(divLogin);
            }
            container.appendChild(divName);
            container.appendChild(divUsername);
            container.appendChild(divActionButton);
            container.appendChild(divFacebookButton);
            container.appendChild(divCancelButton);
            // Reset inputs
            inputLogin.value = '';
            inputUsername.value = '';
            inputPassword.value = '';
            // Button
            actionButton.value = 'Create new profile';
            // Action
            action = 'newProfile';
        }
        /**
         * Request the email with the recovery instructions
         */
        obj.requestNewPassword = function () {
            if (Array.prototype.indexOf.call(container.children, divCaptcha) >= 0) {
                var captcha = true;
            }
            container.innerHTML = '';
            container.appendChild(divLogo);
            container.appendChild(divRecovery);
            container.appendChild(divUsername);
            if (captcha) {
                container.appendChild(divCaptcha);
            }
            container.appendChild(divActionButton);
            container.appendChild(divCancelButton);
            actionButton.value = 'Request a new password';
            inputRecovery.value = 1;
            // Action
            action = 'requestNewPassword';
        }
        /**
         * Confirm recovery code
         */
        obj.codeConfirmation = function () {
            container.innerHTML = '';
            container.appendChild(divLogo);
            container.appendChild(divHash);
            container.appendChild(divCode);
            container.appendChild(divActionButton);
            container.appendChild(divCancelButton);
            actionButton.value = 'Confirm code';
            inputRecovery.value = 2;
            // Action
            action = 'codeConfirmation';
        }
        /**
         * Update my password
         */
        obj.changeMyPassword = function (hash) {
            container.innerHTML = '';
            container.appendChild(divLogo);
            container.appendChild(divHash);
            container.appendChild(divPassword);
            container.appendChild(divRepeatPassword);
            container.appendChild(divActionButton);
            container.appendChild(divCancelButton);
            actionButton.value = 'Change my password';
            inputHash.value = hash;
            // Action
            action = 'changeMyPassword';
        }
        /**
         * Request access default method
         */
        obj.requestAccess = function () {
            container.innerHTML = '';
            container.appendChild(divLogo);
            container.appendChild(divUsername);
            container.appendChild(divPassword);
            container.appendChild(divActionButton);
            container.appendChild(divFacebookButton);
            container.appendChild(divRequestButton);
            container.appendChild(divRememberButton);
            container.appendChild(divRequestButton);
            if (obj.options.newProfile == true) {
                container.appendChild(divNewProfileButton);
            }
            // Button
            actionButton.value = 'Login';
            // Password
            inputPassword.value = '';
            // Email persistence
            if (window.localStorage.getItem('username')) {
                inputUsername.value = window.localStorage.getItem('username');
                inputPassword.focus();
            } else {
                inputUsername.focus();
            }
            // Action
            action = 'requestAccess';
        }
        /**
         * Request login via facebook
         */
        obj.requestLoginViaFacebook = function () {
            if (typeof (deviceNotificationToken) == 'undefined') {
                FB.getLoginStatus(function (response) {
                    if (!response.status || response.status != 'connected') {
                        FB.login(function (response) {
                            if (response.authResponse) {
                                obj.execute({
                                    f: response.authResponse.accessToken
                                });
                            } else {
                                obj.showMessage('Not authorized by facebook');
                            }
                        }, {
                            scope: 'public_profile,email'
                        });
                    } else {
                        obj.execute({
                            f: response.authResponse.accessToken
                        });
                    }
                }, true);
            } else {
                jDestroy = function () {
                    fbLogin.removeEventListener('loadstart', jStart);
                    fbLogin.removeEventListener('loaderror', jError);
                    fbLogin.removeEventListener('exit', jExit);
                    fbLogin.close();
                    fbLogin = null;
                }
                jStart = function (event) {
                    var url = event.url;
                    if (url.indexOf("access_token") >= 0) {
                        setTimeout(function () {
                            var u = url.match(/=(.*?)&/);
                            if (u[1].length > 32) {
                                obj.execute({
                                    f: u[1]
                                });
                            }
                            jDestroy();
                        }, 500);
                    }
                    if (url.indexOf("error=access_denied") >= 0) {
                        setTimeout(jDestroy, 500);
                        // Not authorized by facebook
                        obj.showMessage('Not authorized by facebook');
                    }
                }
                jError = function (event) {
                    jDestroy();
                }
                jExit = function (event) {
                    jDestroy();
                }
                fbLogin = window.open(this.facebookUrl, "_blank", "location=no,closebuttoncaption=Exit,disallowoverscroll=yes,toolbar=no");
                fbLogin.addEventListener('loadstart', jStart);
                fbLogin.addEventListener('loaderror', jError);
                fbLogin.addEventListener('exit', jExit);
            }
            // Action
            action = 'requestLoginViaFacebook';
        }
        // Perform request
        obj.execute = function (data) {
            // New profile
            if (action == 'newProfile') {
                var pattern = new RegExp(/^([\w-\.]+@([\w-]+\.)+[\w-]{2,4})?$/);
                if (!inputUsername.value || !pattern.test(inputUsername.value)) {
                    var message = 'Invalid e-mail address';
                }
                var pattern = new RegExp(/^[a-zA-Z0-9\_\-\.\s+]+$/);
                if (!inputLogin.value || !pattern.test(inputLogin.value)) {
                    var message = 'Invalid username, please use only characters and numbers';
                }
                if (message) {
                    obj.showMessage(message);
                    return false;
                }
            }
            // Keep email
            if (inputUsername.value != '') {
                window.localStorage.setItem('username', inputUsername.value);
            }
            // Captcha
            if (Array.prototype.indexOf.call(container.children, divCaptcha) >= 0) {
                if (inputCaptcha.value == '') {
                    obj.showMessage('Please enter the captch code below');
                    return false;
                }
            }
            // Url
            var url = obj.options.url;
            // Device token
            if (obj.options.deviceToken) {
                url += '?token=' + obj.options.deviceToken;
            }
            // Callback
            var onsuccess = function (result) {
                if (result) {
                    // Successfully response
                    if (result.success == 1) {
                        // Recovery process
                        if (action == 'requestNewPassword') {
                            obj.codeConfirmation();
                        } else if (action == 'codeConfirmation') {
                            obj.requestAccess();
                        } else if (action == 'newProfile') {
                            obj.requestAccess();
                            // New profile
                            result.newProfile = true;
                        }
                        // Token
                        if (result.token) {
                            // Set token
                            obj.options.accessToken = result.token;
                            // Save token
                            window.localStorage.setItem('Access-Token', result.token);
                        }
                    }
                    // Show message
                    if (result.message) {
                        // Show message
                        obj.showMessage(result.message)
                    }
                    // Request captcha code
                    if (!result.data) {
                        if (Array.prototype.indexOf.call(container.children, divCaptcha) >= 0) {
                            divCaptcha.remove();
                        }
                    } else {
                        container.insertBefore(divCaptcha, divActionButton);
                        imageCaptcha.setAttribute('src', 'data:image/png;base64,' + result.data);
                    }
                    // Give time to user see the message
                    if (result.hash) {
                        // Change password
                        obj.changeMyPassword(result.hash);
                    } else if (result.url) {
                        // App initialization
                        if (result.success == 1) {
                            if (typeof (obj.options.onload) == 'function') {
                                obj.options.onload(result);
                            } else {
                                if (result.message) {
                                    setTimeout(function () {
                                        window.location.href = result.url;
                                    }, 2000);
                                } else {
                                    window.location.href = result.url;
                                }
                            }
                        } else {
                            if (typeof (obj.options.onerror) == 'function') {
                                obj.options.onerror(result);
                            }
                        }
                    }
                }
            }
            // Password
            if (!data) {
                var data = jSuites.getFormElements(el);
                // Encode passworfd
                if (data.password) {
                    data.password = jSuites.login.sha512(data.password);
                }
                // Recovery code
                if (Array.prototype.indexOf.call(container.children, divCode) >= 0 && inputCode.value) {
                    data.h = jSuites.login.sha512(inputCode.value);
                }
            }
            // Loading
            el.classList.add('jlogin-loading');
            // Url
            var url = (action == 'newProfile' && obj.options.newProfileUrl) ? obj.options.newProfileUrl : obj.options.url;
            // Remote call
            jSuites.ajax({
                url: url,
                method: 'POST',
                dataType: 'json',
                data: data,
                success: function (result) {
                    // Remove loading
                    el.classList.remove('jlogin-loading');
                    // Callback
                    onsuccess(result);
                },
                error: function () {
                    // Error
                    el.classList.remove('jlogin-loading');
                }
            });
        }
        obj.requestAccess();
        return obj;
    });
    jSuites.login.sha512 = (function (str) {
        function int64(msint_32, lsint_32) {
            this.highOrder = msint_32;
            this.lowOrder = lsint_32;
        }
        var H = [new int64(0x6a09e667, 0xf3bcc908), new int64(0xbb67ae85, 0x84caa73b),
            new int64(0x3c6ef372, 0xfe94f82b), new int64(0xa54ff53a, 0x5f1d36f1),
            new int64(0x510e527f, 0xade682d1), new int64(0x9b05688c, 0x2b3e6c1f),
            new int64(0x1f83d9ab, 0xfb41bd6b), new int64(0x5be0cd19, 0x137e2179)
        ];
        var K = [new int64(0x428a2f98, 0xd728ae22), new int64(0x71374491, 0x23ef65cd),
            new int64(0xb5c0fbcf, 0xec4d3b2f), new int64(0xe9b5dba5, 0x8189dbbc),
            new int64(0x3956c25b, 0xf348b538), new int64(0x59f111f1, 0xb605d019),
            new int64(0x923f82a4, 0xaf194f9b), new int64(0xab1c5ed5, 0xda6d8118),
            new int64(0xd807aa98, 0xa3030242), new int64(0x12835b01, 0x45706fbe),
            new int64(0x243185be, 0x4ee4b28c), new int64(0x550c7dc3, 0xd5ffb4e2),
            new int64(0x72be5d74, 0xf27b896f), new int64(0x80deb1fe, 0x3b1696b1),
            new int64(0x9bdc06a7, 0x25c71235), new int64(0xc19bf174, 0xcf692694),
            new int64(0xe49b69c1, 0x9ef14ad2), new int64(0xefbe4786, 0x384f25e3),
            new int64(0x0fc19dc6, 0x8b8cd5b5), new int64(0x240ca1cc, 0x77ac9c65),
            new int64(0x2de92c6f, 0x592b0275), new int64(0x4a7484aa, 0x6ea6e483),
            new int64(0x5cb0a9dc, 0xbd41fbd4), new int64(0x76f988da, 0x831153b5),
            new int64(0x983e5152, 0xee66dfab), new int64(0xa831c66d, 0x2db43210),
            new int64(0xb00327c8, 0x98fb213f), new int64(0xbf597fc7, 0xbeef0ee4),
            new int64(0xc6e00bf3, 0x3da88fc2), new int64(0xd5a79147, 0x930aa725),
            new int64(0x06ca6351, 0xe003826f), new int64(0x14292967, 0x0a0e6e70),
            new int64(0x27b70a85, 0x46d22ffc), new int64(0x2e1b2138, 0x5c26c926),
            new int64(0x4d2c6dfc, 0x5ac42aed), new int64(0x53380d13, 0x9d95b3df),
            new int64(0x650a7354, 0x8baf63de), new int64(0x766a0abb, 0x3c77b2a8),
            new int64(0x81c2c92e, 0x47edaee6), new int64(0x92722c85, 0x1482353b),
            new int64(0xa2bfe8a1, 0x4cf10364), new int64(0xa81a664b, 0xbc423001),
            new int64(0xc24b8b70, 0xd0f89791), new int64(0xc76c51a3, 0x0654be30),
            new int64(0xd192e819, 0xd6ef5218), new int64(0xd6990624, 0x5565a910),
            new int64(0xf40e3585, 0x5771202a), new int64(0x106aa070, 0x32bbd1b8),
            new int64(0x19a4c116, 0xb8d2d0c8), new int64(0x1e376c08, 0x5141ab53),
            new int64(0x2748774c, 0xdf8eeb99), new int64(0x34b0bcb5, 0xe19b48a8),
            new int64(0x391c0cb3, 0xc5c95a63), new int64(0x4ed8aa4a, 0xe3418acb),
            new int64(0x5b9cca4f, 0x7763e373), new int64(0x682e6ff3, 0xd6b2b8a3),
            new int64(0x748f82ee, 0x5defb2fc), new int64(0x78a5636f, 0x43172f60),
            new int64(0x84c87814, 0xa1f0ab72), new int64(0x8cc70208, 0x1a6439ec),
            new int64(0x90befffa, 0x23631e28), new int64(0xa4506ceb, 0xde82bde9),
            new int64(0xbef9a3f7, 0xb2c67915), new int64(0xc67178f2, 0xe372532b),
            new int64(0xca273ece, 0xea26619c), new int64(0xd186b8c7, 0x21c0c207),
            new int64(0xeada7dd6, 0xcde0eb1e), new int64(0xf57d4f7f, 0xee6ed178),
            new int64(0x06f067aa, 0x72176fba), new int64(0x0a637dc5, 0xa2c898a6),
            new int64(0x113f9804, 0xbef90dae), new int64(0x1b710b35, 0x131c471b),
            new int64(0x28db77f5, 0x23047d84), new int64(0x32caab7b, 0x40c72493),
            new int64(0x3c9ebe0a, 0x15c9bebc), new int64(0x431d67c4, 0x9c100d4c),
            new int64(0x4cc5d4be, 0xcb3e42b6), new int64(0x597f299c, 0xfc657e2a),
            new int64(0x5fcb6fab, 0x3ad6faec), new int64(0x6c44198c, 0x4a475817)
        ];
        var W = new Array(64);
        var a, b, c, d, e, f, g, h, i, j;
        var T1, T2;
        var charsize = 8;

        function utf8_encode(str) {
            return unescape(encodeURIComponent(str));
        }

        function str2binb(str) {
            var bin = [];
            var mask = (1 << charsize) - 1;
            var len = str.length * charsize;
            for (var i = 0; i < len; i += charsize) {
                bin[i >> 5] |= (str.charCodeAt(i / charsize) & mask) << (32 - charsize - (i % 32));
            }
            return bin;
        }

        function binb2hex(binarray) {
            var hex_tab = "0123456789abcdef";
            var str = "";
            var length = binarray.length * 4;
            var srcByte;
            for (var i = 0; i < length; i += 1) {
                srcByte = binarray[i >> 2] >> ((3 - (i % 4)) * 8);
                str += hex_tab.charAt((srcByte >> 4) & 0xF) + hex_tab.charAt(srcByte & 0xF);
            }
            return str;
        }

        function safe_add_2(x, y) {
            var lsw, msw, lowOrder, highOrder;
            lsw = (x.lowOrder & 0xFFFF) + (y.lowOrder & 0xFFFF);
            msw = (x.lowOrder >>> 16) + (y.lowOrder >>> 16) + (lsw >>> 16);
            lowOrder = ((msw & 0xFFFF) << 16) | (lsw & 0xFFFF);
            lsw = (x.highOrder & 0xFFFF) + (y.highOrder & 0xFFFF) + (msw >>> 16);
            msw = (x.highOrder >>> 16) + (y.highOrder >>> 16) + (lsw >>> 16);
            highOrder = ((msw & 0xFFFF) << 16) | (lsw & 0xFFFF);
            return new int64(highOrder, lowOrder);
        }

        function safe_add_4(a, b, c, d) {
            var lsw, msw, lowOrder, highOrder;
            lsw = (a.lowOrder & 0xFFFF) + (b.lowOrder & 0xFFFF) + (c.lowOrder & 0xFFFF) + (d.lowOrder & 0xFFFF);
            msw = (a.lowOrder >>> 16) + (b.lowOrder >>> 16) + (c.lowOrder >>> 16) + (d.lowOrder >>> 16) + (lsw >>> 16);
            lowOrder = ((msw & 0xFFFF) << 16) | (lsw & 0xFFFF);
            lsw = (a.highOrder & 0xFFFF) + (b.highOrder & 0xFFFF) + (c.highOrder & 0xFFFF) + (d.highOrder & 0xFFFF) + (msw >>> 16);
            msw = (a.highOrder >>> 16) + (b.highOrder >>> 16) + (c.highOrder >>> 16) + (d.highOrder >>> 16) + (lsw >>> 16);
            highOrder = ((msw & 0xFFFF) << 16) | (lsw & 0xFFFF);
            return new int64(highOrder, lowOrder);
        }

        function safe_add_5(a, b, c, d, e) {
            var lsw, msw, lowOrder, highOrder;
            lsw = (a.lowOrder & 0xFFFF) + (b.lowOrder & 0xFFFF) + (c.lowOrder & 0xFFFF) + (d.lowOrder & 0xFFFF) + (e.lowOrder & 0xFFFF);
            msw = (a.lowOrder >>> 16) + (b.lowOrder >>> 16) + (c.lowOrder >>> 16) + (d.lowOrder >>> 16) + (e.lowOrder >>> 16) + (lsw >>> 16);
            lowOrder = ((msw & 0xFFFF) << 16) | (lsw & 0xFFFF);
            lsw = (a.highOrder & 0xFFFF) + (b.highOrder & 0xFFFF) + (c.highOrder & 0xFFFF) + (d.highOrder & 0xFFFF) + (e.highOrder & 0xFFFF) + (msw >>> 16);
            msw = (a.highOrder >>> 16) + (b.highOrder >>> 16) + (c.highOrder >>> 16) + (d.highOrder >>> 16) + (e.highOrder >>> 16) + (lsw >>> 16);
            highOrder = ((msw & 0xFFFF) << 16) | (lsw & 0xFFFF);
            return new int64(highOrder, lowOrder);
        }

        function maj(x, y, z) {
            return new int64(
                (x.highOrder & y.highOrder) ^ (x.highOrder & z.highOrder) ^ (y.highOrder & z.highOrder),
                (x.lowOrder & y.lowOrder) ^ (x.lowOrder & z.lowOrder) ^ (y.lowOrder & z.lowOrder)
            );
        }

        function ch(x, y, z) {
            return new int64(
                (x.highOrder & y.highOrder) ^ (~x.highOrder & z.highOrder),
                (x.lowOrder & y.lowOrder) ^ (~x.lowOrder & z.lowOrder)
            );
        }

        function rotr(x, n) {
            if (n <= 32) {
                return new int64(
                    (x.highOrder >>> n) | (x.lowOrder << (32 - n)),
                    (x.lowOrder >>> n) | (x.highOrder << (32 - n))
                );
            } else {
                return new int64(
                    (x.lowOrder >>> n) | (x.highOrder << (32 - n)),
                    (x.highOrder >>> n) | (x.lowOrder << (32 - n))
                );
            }
        }

        function sigma0(x) {
            var rotr28 = rotr(x, 28);
            var rotr34 = rotr(x, 34);
            var rotr39 = rotr(x, 39);
            return new int64(
                rotr28.highOrder ^ rotr34.highOrder ^ rotr39.highOrder,
                rotr28.lowOrder ^ rotr34.lowOrder ^ rotr39.lowOrder
            );
        }

        function sigma1(x) {
            var rotr14 = rotr(x, 14);
            var rotr18 = rotr(x, 18);
            var rotr41 = rotr(x, 41);
            return new int64(
                rotr14.highOrder ^ rotr18.highOrder ^ rotr41.highOrder,
                rotr14.lowOrder ^ rotr18.lowOrder ^ rotr41.lowOrder
            );
        }

        function gamma0(x) {
            var rotr1 = rotr(x, 1),
                rotr8 = rotr(x, 8),
                shr7 = shr(x, 7);
            return new int64(
                rotr1.highOrder ^ rotr8.highOrder ^ shr7.highOrder,
                rotr1.lowOrder ^ rotr8.lowOrder ^ shr7.lowOrder
            );
        }

        function gamma1(x) {
            var rotr19 = rotr(x, 19);
            var rotr61 = rotr(x, 61);
            var shr6 = shr(x, 6);
            return new int64(
                rotr19.highOrder ^ rotr61.highOrder ^ shr6.highOrder,
                rotr19.lowOrder ^ rotr61.lowOrder ^ shr6.lowOrder
            );
        }

        function shr(x, n) {
            if (n <= 32) {
                return new int64(
                    x.highOrder >>> n,
                    x.lowOrder >>> n | (x.highOrder << (32 - n))
                );
            } else {
                return new int64(
                    0,
                    x.highOrder << (32 - n)
                );
            }
        }
        var str = utf8_encode(str);
        var strlen = str.length * charsize;
        str = str2binb(str);
        str[strlen >> 5] |= 0x80 << (24 - strlen % 32);
        str[(((strlen + 128) >> 10) << 5) + 31] = strlen;
        for (var i = 0; i < str.length; i += 32) {
            a = H[0];
            b = H[1];
            c = H[2];
            d = H[3];
            e = H[4];
            f = H[5];
            g = H[6];
            h = H[7];
            for (var j = 0; j < 80; j++) {
                if (j < 16) {
                    W[j] = new int64(str[j * 2 + i], str[j * 2 + i + 1]);
                } else {
                    W[j] = safe_add_4(gamma1(W[j - 2]), W[j - 7], gamma0(W[j - 15]), W[j - 16]);
                }
                T1 = safe_add_5(h, sigma1(e), ch(e, f, g), K[j], W[j]);
                T2 = safe_add_2(sigma0(a), maj(a, b, c));
                h = g;
                g = f;
                f = e;
                e = safe_add_2(d, T1);
                d = c;
                c = b;
                b = a;
                a = safe_add_2(T1, T2);
            }
            H[0] = safe_add_2(a, H[0]);
            H[1] = safe_add_2(b, H[1]);
            H[2] = safe_add_2(c, H[2]);
            H[3] = safe_add_2(d, H[3]);
            H[4] = safe_add_2(e, H[4]);
            H[5] = safe_add_2(f, H[5]);
            H[6] = safe_add_2(g, H[6]);
            H[7] = safe_add_2(h, H[7]);
        }
        var binarray = [];
        for (var i = 0; i < H.length; i++) {
            binarray.push(H[i].highOrder);
            binarray.push(H[i].lowOrder);
        }
        return binb2hex(binarray);
    });
    /**
     * (c) jTools Input Mask
     * https://github.com/paulhodel/jtools
     *
     * @author: Paul Hodel <paul.hodel@gmail.com>
     * @description: Input mask
     */
    jSuites.mask = (function () {
        var obj = {};
        var index = 0;
        var values = []
        var pieces = [];
        obj.run = function (value, mask, decimal) {
            if (value && mask) {
                if (!decimal) {
                    decimal = '.';
                }
                if (value == Number(value)) {
                    var number = ('' + value).split('.');
                    var value = number[0];
                    var valueDecimal = number[1];
                } else {
                    value = '' + value;
                }
                index = 0;
                values = [];
                // Create mask token
                obj.prepare(mask);
                // Current value
                var currentValue = value;
                if (currentValue) {
                    // Checking current value
                    for (var i = 0; i < currentValue.length; i++) {
                        if (currentValue[i] != null) {
                            obj.process(currentValue[i]);
                        }
                    }
                }
                if (valueDecimal) {
                    obj.process(decimal);
                    var currentValue = valueDecimal;
                    if (currentValue) {
                        // Checking current value
                        for (var i = 0; i < currentValue.length; i++) {
                            if (currentValue[i] != null) {
                                obj.process(currentValue[i]);
                            }
                        }
                    }
                }
                // Formatted value
                return values.join('');
            } else {
                return '';
            }
        }
        obj.apply = function (e) {
            var mask = e.target.getAttribute('data-mask');
            if (mask && e.keyCode > 46) {
                index = 0;
                values = [];
                // Create mask token
                obj.prepare(mask);
                // Current value
                if (e.target.selectionStart < e.target.selectionEnd) {
                    var currentValue = e.target.value.substring(0, e.target.selectionStart);
                } else {
                    var currentValue = e.target.value;
                }
                if (currentValue) {
                    // Checking current value
                    for (var i = 0; i < currentValue.length; i++) {
                        if (currentValue[i] != null) {
                            obj.process(currentValue[i]);
                        }
                    }
                }
                // New input
                obj.process(obj.fromKeyCode(e));
                // Update value to the element
                e.target.value = values.join('');
                if (pieces.length == values.length && pieces[pieces.length - 1].length == values[values.length - 1].length) {
                    e.target.setAttribute('data-completed', 'true');
                } else {
                    e.target.setAttribute('data-completed', 'false');
                }
                // Prevent default
                e.preventDefault();
            }
        }
        /**
         * Process inputs and save to values
         */
        obj.process = function (input) {
            do {
                if (pieces[index] == 'mm') {
                    if (values[index] == null || values[index] == '') {
                        if (parseInt(input) > 1 && parseInt(input) < 10) {
                            values[index] = '0' + input;
                            index++;
                            return true;
                        } else if (parseInt(input) < 10) {
                            values[index] = input;
                            return true;
                        } else {
                            return false;
                        }
                    } else {
                        if (values[index] == 1 && values[index] < 2 && parseInt(input) < 3) {
                            values[index] += input;
                            index++;
                            return true;
                        } else if (values[index] == 0 && values[index] < 10) {
                            values[index] += input;
                            index++;
                            return true;
                        } else {
                            return false
                        }
                    }
                } else if (pieces[index] == 'dd') {
                    if (values[index] == null || values[index] == '') {
                        if (parseInt(input) > 3 && parseInt(input) < 10) {
                            values[index] = '0' + input;
                            index++;
                            return true;
                        } else if (parseInt(input) < 10) {
                            values[index] = input;
                            return true;
                        } else {
                            return false;
                        }
                    } else {
                        if (values[index] == 3 && parseInt(input) < 2) {
                            values[index] += input;
                            index++;
                            return true;
                        } else if (values[index] < 3 && parseInt(input) < 10) {
                            values[index] += input;
                            index++;
                            return true;
                        } else {
                            return false
                        }
                    }
                } else if (pieces[index] == 'hh24') {
                    if (values[index] == null || values[index] == '') {
                        if (parseInt(input) > 2 && parseInt(input) < 10) {
                            values[index] = '0' + input;
                            index++;
                            return true;
                        } else if (parseInt(input) < 10) {
                            values[index] = input;
                            return true;
                        } else {
                            return false;
                        }
                    } else {
                        if (values[index] == 2 && parseInt(input) < 4) {
                            values[index] += input;
                            index++;
                            return true;
                        } else if (values[index] < 2 && parseInt(input) < 10) {
                            values[index] += input;
                            index++;
                            return true;
                        } else {
                            return false
                        }
                    }
                } else if (pieces[index] == 'hh') {
                    if (values[index] == null || values[index] == '') {
                        if (parseInt(input) > 1 && parseInt(input) < 10) {
                            values[index] = '0' + input;
                            index++;
                            return true;
                        } else if (parseInt(input) < 10) {
                            values[index] = input;
                            return true;
                        } else {
                            return false;
                        }
                    } else {
                        if (values[index] == 1 && parseInt(input) < 3) {
                            values[index] += input;
                            index++;
                            return true;
                        } else if (values[index] < 1 && parseInt(input) < 10) {
                            values[index] += input;
                            index++;
                            return true;
                        } else {
                            return false
                        }
                    }
                } else if (pieces[index] == 'mi' || pieces[index] == 'ss') {
                    if (values[index] == null || values[index] == '') {
                        if (parseInt(input) > 5 && parseInt(input) < 10) {
                            values[index] = '0' + input;
                            index++;
                            return true;
                        } else if (parseInt(input) < 10) {
                            values[index] = input;
                            return true;
                        } else {
                            return false;
                        }
                    } else {
                        if (parseInt(input) < 10) {
                            values[index] += input;
                            index++;
                            return true;
                        } else {
                            return false
                        }
                    }
                } else if (pieces[index] == 'yy' || pieces[index] == 'yyyy') {
                    if (parseInt(input) < 10) {
                        if (values[index] == null || values[index] == '') {
                            values[index] = input;
                        } else {
                            values[index] += input;
                        }
                        if (values[index].length == pieces[index].length) {
                            index++;
                        }
                        return true;
                    } else {
                        return false;
                    }
                } else if (pieces[index] == '#' || pieces[index] == '#.##' || pieces[index] == '#,##') {
                    if (input.match(/[0-9]/g)) {
                        if (pieces[index] == '#.##') {
                            var separator = '.';
                        } else if (pieces[index] == '#,##') {
                            var separator = ',';
                        } else {
                            var separator = '';
                        }
                        if (values[index] == null || values[index] == '') {
                            values[index] = input;
                        } else {
                            values[index] += input;
                            if (separator) {
                                values[index] = values[index].match(/[0-9]/g).join('');
                                var t = [];
                                var s = 0;
                                for (var j = values[index].length - 1; j >= 0; j--) {
                                    t.push(values[index][j]);
                                    s++;
                                    if (!(s % 3)) {
                                        t.push(separator);
                                    }
                                }
                                t = t.reverse();
                                values[index] = t.join('');
                                if (values[index].substr(0, 1) == separator) {
                                    values[index] = values[index].substr(1);
                                }
                            }
                        }
                        return true;
                    } else {
                        if (pieces[index] == '#.##' && input == '.') {
                            // Do nothing
                        } else if (pieces[index] == '#,##' && input == ',') {
                            // Do nothing
                        } else {
                            if (values[index]) {
                                index++;
                                if (pieces[index]) {
                                    if (pieces[index] == input) {
                                        values[index] = input;
                                        return true;
                                    } else {
                                        if (pieces[index] == '0' && pieces[index + 1] == input) {
                                            index++;
                                            values[index] = input;
                                            return true;
                                        }
                                    }
                                }
                            }
                        }
                        return false;
                    }
                } else if (pieces[index] == '[-]') {
                    if (input == '-' || input == '+') {
                        values[index] = input;
                    } else {
                        values[index] = ' ';
                    }
                    index++;
                    return true;
                } else if (pieces[index] == '0') {
                    if (input.match(/[0-9]/g)) {
                        values[index] = input;
                        index++;
                        return true;
                    } else {
                        return false;
                    }
                } else if (pieces[index] == 'a') {
                    if (input.match(/[a-zA-Z]/g)) {
                        values[index] = input;
                        index++;
                        return true;
                    } else {
                        return false;
                    }
                } else {
                    if (pieces[index] != null) {
                        if (pieces[index] == '\\a') {
                            var v = 'a';
                        } else if (pieces[index] == '\\0') {
                            var v = '0';
                        } else {
                            var v = pieces[index];
                        }
                        values[index] = v;
                        if (input == v) {
                            index++;
                            return true;
                        }
                    }
                }
                index++;
            } while (pieces[index]);
        }
        /**
         * Create tokens for the mask
         */
        obj.prepare = function (mask) {
            pieces = [];
            for (var i = 0; i < mask.length; i++) {
                if (mask[i].match(/[0-9]|[a-z]|\\/g)) {
                    if (mask[i] == 'y' && mask[i + 1] == 'y' && mask[i + 2] == 'y' && mask[i + 3] == 'y') {
                        pieces.push('yyyy');
                        i += 3;
                    } else if (mask[i] == 'y' && mask[i + 1] == 'y') {
                        pieces.push('yy');
                        i++;
                    } else if (mask[i] == 'm' && mask[i + 1] == 'm' && mask[i + 2] == 'm' && mask[i + 3] == 'm') {
                        pieces.push('mmmm');
                        i += 3;
                    } else if (mask[i] == 'm' && mask[i + 1] == 'm' && mask[i + 2] == 'm') {
                        pieces.push('mmm');
                        i += 2;
                    } else if (mask[i] == 'm' && mask[i + 1] == 'm') {
                        pieces.push('mm');
                        i++;
                    } else if (mask[i] == 'd' && mask[i + 1] == 'd') {
                        pieces.push('dd');
                        i++;
                    } else if (mask[i] == 'h' && mask[i + 1] == 'h' && mask[i + 2] == '2' && mask[i + 3] == '4') {
                        pieces.push('hh24');
                        i += 3;
                    } else if (mask[i] == 'h' && mask[i + 1] == 'h') {
                        pieces.push('hh');
                        i++;
                    } else if (mask[i] == 'm' && mask[i + 1] == 'i') {
                        pieces.push('mi');
                        i++;
                    } else if (mask[i] == 's' && mask[i + 1] == 's') {
                        pieces.push('ss');
                        i++;
                    } else if (mask[i] == 'a' && mask[i + 1] == 'm') {
                        pieces.push('am');
                        i++;
                    } else if (mask[i] == 'p' && mask[i + 1] == 'm') {
                        pieces.push('pm');
                        i++;
                    } else if (mask[i] == '\\' && mask[i + 1] == '0') {
                        pieces.push('\\0');
                        i++;
                    } else if (mask[i] == '\\' && mask[i + 1] == 'a') {
                        pieces.push('\\a');
                        i++;
                    } else {
                        pieces.push(mask[i]);
                    }
                } else {
                    if (mask[i] == '#' && mask[i + 1] == '.' && mask[i + 2] == '#' && mask[i + 3] == '#') {
                        pieces.push('#.##');
                        i += 3;
                    } else if (mask[i] == '#' && mask[i + 1] == ',' && mask[i + 2] == '#' && mask[i + 3] == '#') {
                        pieces.push('#,##');
                        i += 3;
                    } else if (mask[i] == '[' && mask[i + 1] == '-' && mask[i + 2] == ']') {
                        pieces.push('[-]');
                        i += 2;
                    } else {
                        pieces.push(mask[i]);
                    }
                }
            }
        }
        /** 
         * Thanks for the collaboration
         */
        obj.fromKeyCode = function (e) {
            var _to_ascii = {
                '188': '44',
                '109': '45',
                '190': '46',
                '191': '47',
                '192': '96',
                '220': '92',
                '222': '39',
                '221': '93',
                '219': '91',
                '173': '45',
                '187': '61', //IE Key codes
                '186': '59', //IE Key codes
                '189': '45' //IE Key codes
            }
            var shiftUps = {
                "96": "~",
                "49": "!",
                "50": "@",
                "51": "#",
                "52": "$",
                "53": "%",
                "54": "^",
                "55": "&",
                "56": "*",
                "57": "(",
                "48": ")",
                "45": "_",
                "61": "+",
                "91": "{",
                "93": "}",
                "92": "|",
                "59": ":",
                "39": "\"",
                "44": "<",
                "46": ">",
                "47": "?"
            };
            var c = e.which;
            if (_to_ascii.hasOwnProperty(c)) {
                c = _to_ascii[c];
            }
            if (!e.shiftKey && (c >= 65 && c <= 90)) {
                c = String.fromCharCode(c + 32);
            } else if (e.shiftKey && shiftUps.hasOwnProperty(c)) {
                c = shiftUps[c];
            } else if (96 <= c && c <= 105) {
                c = String.fromCharCode(c - 48);
            } else {
                c = String.fromCharCode(c);
            }
            return c;
        }
        return obj;
    })();
    jSuites.mobile = (function (el, options) {
        var obj = {};
        obj.options = {};
        if (jSuites.el) {
            jSuites.el.addEventListener('mousedown', function (e) {
                if (e.target.classList.contains('option-title')) {
                    if (e.target.classList.contains('selected')) {
                        e.target.classList.remove('selected');
                    } else {
                        e.target.classList.add('selected');
                    }
                }
            });
        }
        return obj;
    })();
    jSuites.pages = (function () {
        var container = null;
        var current = null;
        // Create a page
        var createPage = function (options, callback) {
            // Create page
            var page = document.createElement('div');
            page.classList.add('page');
            // Always hidden
            page.style.display = 'none';
            // Keep options
            page.options = options ? options : {};
            if (!current) {
                container.appendChild(page);
            } else {
                container.insertBefore(page, current.nextSibling);
            }
            jSuites.ajax({
                url: page.options.url,
                method: 'GET',
                success: function (result) {
                    // Push to refresh controls
                    jSuites.refresh(page, page.options.onpush);
                    // Open page
                    page.innerHTML = result;
                    // Get javascript
                    var script = page.getElementsByTagName('script');
                    // Run possible inline scripts
                    for (var i = 0; i < script.length; i++) {
                        // Get type
                        var type = script[i].getAttribute('type');
                        if (!type || type == 'text/javascript') {
                            eval(script[i].innerHTML);
                        }
                    }
                    // Set title
                    page.setTitle = function (text) {
                        this.children[0].children[0].children[1].innerHTML = text;
                    }
                    // Show page
                    if (!page.options.closed) {
                        showPage(page);
                    }
                    // Onload callback
                    if (typeof (page.options.onload) == 'function') {
                        page.options.onload(page);
                    }
                    // Force callback
                    if (typeof (callback) == 'function') {
                        callback(page);
                    }
                }
            });
            return page;
        }
        var showPage = function (page, ignoreHistory, callback) {
            if (current) {
                if (current == page) {
                    current = page;
                } else {
                    // Keep scroll in the top
                    window.scrollTo({
                        top: 0
                    });
                    // Show page
                    page.style.display = '';
                    var a = Array.prototype.indexOf.call(container.children, current);
                    var b = Array.prototype.indexOf.call(container.children, page);
                    // Leave
                    if (typeof (current.options.onleave) == 'function') {
                        current.options.onleave(current, page, ignoreHistory);
                    }
                    jSuites.slideLeft(container, (a < b ? 0 : 1), function () {
                        current.style.display = 'none';
                        current = page;
                    });
                    // Enter
                    if (typeof (page.options.onenter) == 'function') {
                        page.options.onenter(page, current, ignoreHistory);
                    }
                }
            } else {
                // Show
                page.style.display = '';
                // Keep current
                current = page;
                // Enter
                if (typeof (page.options.onenter) == 'function') {
                    page.options.onenter(page);
                }
            }
            // Add history
            if (!ignoreHistory) {
                // Add history
                window.history.pushState({
                    route: page.options.route
                }, page.options.title, page.options.route);
            }
            // Callback
            if (typeof (callback) == 'function') {
                callback(page);
            }
        }
        // Init method
        var obj = function (route, mixed) {
            // Create page container
            if (!container) {
                container = document.querySelector('.pages');
                if (!container) {
                    container = document.createElement('div');
                    container.className = 'pages';
                }
                // Append container to the application
                if (jSuites.el) {
                    jSuites.el.appendChild(container);
                } else {
                    document.body.appendChild(container);
                }
            }
            if (!obj.pages[route]) {
                if (!route) {
                    alert('Error, no route provided');
                } else {
                    if (typeof (mixed) == 'function') {
                        var options = {};
                        var callback = mixed;
                    } else {
                        // Page options
                        var options = mixed ? mixed : {};
                    }
                    // Closed
                    options.closed = mixed && mixed.closed ? 1 : 0;
                    // Keep Route
                    options.route = route;
                    // New page url
                    if (!options.url) {
                        var routePath = route.split('#');
                        options.url = jSuites.pages.path + routePath[0] + '.html';
                    }
                    // Title
                    if (!options.title) {
                        options.title = 'Untitled';
                    }
                    // Create new page
                    obj.pages[route] = createPage(options, callback ? callback : null);
                }
            } else {
                // Update config
                if (mixed) {
                    // History
                    var ignoreHistory = 0;
                    if (typeof (mixed) == 'function') {
                        var callback = mixed;
                    } else {
                        if (typeof (mixed.onenter) == 'function') {
                            obj.pages[route].options.onenter = mixed.onenter;
                        }
                        if (typeof (mixed.onleave) == 'function') {
                            obj.pages[route].options.onleave = mixed.onleave;
                        }
                        // Ignore history
                        ignoreHistory = mixed.ignoreHistory ? 1 : 0;
                    }
                }
                showPage(obj.pages[route], ignoreHistory, callback ? callback : null);
            }
        }
        obj.pages = {};
        // Get page
        obj.get = function (route) {
            if (obj.pages[route]) {
                return obj.pages[route];
            }
        }
        obj.getContainer = function () {
            return container;
        }
        obj.destroy = function () {
            // Current is null
            current = null;
            // Destroy containers
            obj.pages = {};
            // Reset container
            container.innerHTML = '';
        }
        return obj;
    })();
    // Path
    jSuites.pages.path = 'pages';
    // Panel
    jSuites.panel = (function () {
        // No initial panel declared
        var panel = null;
        var obj = function (route) {
            if (!panel) {
                obj.create(jSuites.pages.path + route + '.html');
            }
            // Show panel
            panel.style.display = '';
            // Add animation
            if (panel.classList.contains('panel-left')) {
                jSuites.slideLeft(panel, 1);
            } else {
                jSuites.slideRight(panel, 1);
            }
        }
        obj.create = function (route) {
            if (!panel) {
                // Create element
                panel = document.createElement('div');
                panel.classList.add('panel');
                panel.classList.add('panel-left');
                panel.style.display = 'none';
                // Bind to the app
                if (jSuites.el) {
                    jSuites.el.appendChild(panel);
                } else {
                    document.body.appendChild(panel);
                }
            }
            // Remote content
            if (route) {
                var url = jSuites.pages.path + route + '.html';
                jSuites.ajax({
                    url: url,
                    method: 'GET',
                    success: function (result) {
                        // Set content
                        panel.innerHTML = result;
                        // Get javascript
                        var script = panel.getElementsByTagName('script');
                        // Run possible inline scripts
                        for (var i = 0; i < script.length; i++) {
                            // Get type
                            var type = script[i].getAttribute('type');
                            if (!type || type == 'text/javascript') {
                                eval(script[i].innerHTML);
                            }
                        }
                    }
                });
            }
        }
        obj.close = function () {
            if (panel) {
                // Animation
                if (panel.classList.contains('panel-left')) {
                    jSuites.slideLeft(panel, 0, function () {
                        panel.style.display = 'none';
                    });
                } else {
                    jSuites.slideRight(panel, 0, function () {
                        panel.style.display = 'none';
                    });
                }
            }
        }
        obj.get = function () {
            return panel;
        }
        obj.destroy = function () {
            panel.remove();
            panel = null;
        }
        return obj;
    })();
    jSuites.toolbar = (function (el, options) {
        var obj = {};
        obj.options = options;
        obj.selectItem = function (element) {
            var elements = toolbarContent.children;
            for (var i = 0; i < elements.length; i++) {
                elements[i].classList.remove('selected');
            }
            element.classList.add('selected');
        }
        obj.hide = function () {
            jSuites.slideBottom(toolbar, 0, function () {
                toolbar.style.display = 'none';
            });
        }
        obj.show = function () {
            toolbar.style.display = '';
            jSuites.slideBottom(toolbar, 1);
        }
        obj.get = function () {
            return toolbar;
        }
        obj.setBadge = function (index, value) {
            toolbarContent.children[index].children[1].firstChild.innerHTML = value;
        }
        obj.destroy = function () {
            toolbar.remove();
            toolbar = null;
        }
        var toolbar = document.createElement('div');
        toolbar.classList.add('jtoolbar');
        toolbar.onclick = function (e) {
            var element = jSuites.getElement(e.target, 'jtoolbar-item');
            if (element) {
                obj.selectItem(element);
            }
        }
        var toolbarContent = document.createElement('div');
        toolbar.appendChild(toolbarContent);
        for (var i = 0; i < options.items.length; i++) {
            let toolbarItem = document.createElement('div');
            toolbarItem.classList.add('jtoolbar-item');
            if (options.items[i].route) {
                toolbarItem.setAttribute('data-href', options.items[i].route);
                jSuites.pages(options.items[i].route, {
                    closed: true,
                    onenter: function () {
                        obj.selectItem(toolbarItem);
                    }
                });
            }
            if (options.items[i].icon) {
                var toolbarIcon = document.createElement('i');
                toolbarIcon.classList.add('material-icons');
                toolbarIcon.innerHTML = options.items[i].icon;
                toolbarItem.appendChild(toolbarIcon);
            }
            var toolbarBadge = document.createElement('div');
            toolbarBadge.classList.add('jbadge');
            var toolbarBadgeContent = document.createElement('div');
            toolbarBadgeContent.innerHTML = options.items[i].badge ? options.items[i].badge : '';
            toolbarBadge.appendChild(toolbarBadgeContent);
            toolbarItem.appendChild(toolbarBadge);
            if (options.items[i].title) {
                var toolbarTitle = document.createElement('span');
                toolbarTitle.innerHTML = options.items[i].title;
                toolbarItem.appendChild(toolbarTitle);
            }
            toolbarContent.appendChild(toolbarItem);
        }
        el.toolbar = obj;
        el.appendChild(toolbar);
        return obj;
    });
    jSuites.actionsheet = (function () {
        var actionsheet = document.createElement('div');
        actionsheet.className = 'jactionsheet';
        actionsheet.style.display = 'none';
        var actionContent = document.createElement('div');
        actionContent.className = 'jactionsheet-content';
        actionsheet.appendChild(actionContent);
        var obj = function (options) {
            if (options) {
                obj.options = options;
            }
            // Reset container
            actionContent.innerHTML = '';
            // Create new elements
            for (var i = 0; i < obj.options.length; i++) {
                var actionGroup = document.createElement('div');
                actionGroup.className = 'jactionsheet-group';
                for (var j = 0; j < obj.options[i].length; j++) {
                    var v = obj.options[i][j];
                    var actionItem = document.createElement('div');
                    var actionInput = document.createElement('input');
                    actionInput.type = 'button';
                    actionInput.value = v.title;
                    if (v.className) {
                        actionInput.className = v.className;
                    }
                    if (v.onclick) {
                        actionInput.onclick = v.onclick;
                    }
                    if (v.action == 'cancel') {
                        actionInput.style.color = 'red';
                    }
                    actionItem.appendChild(actionInput);
                    actionGroup.appendChild(actionItem);
                }
                actionContent.appendChild(actionGroup);
            }
            // Show
            actionsheet.style.display = '';
            // Append
            jSuites.el.appendChild(actionsheet);
            // Animation
            jSuites.slideBottom(actionContent, true);
        }
        obj.close = function () {
            if (actionsheet.style.display != 'none') {
                // Remove any existing actionsheet
                jSuites.slideBottom(actionContent, false, function () {
                    actionsheet.remove();
                    actionsheet.style.display = 'none';
                });
            }
        }
        var mouseUp = function (e) {
            obj.close();
        }
        actionsheet.addEventListener('mouseup', mouseUp);
        obj.options = {};
        return obj;
    })();
    /**
     * (c) jSuites modal
     * https://github.com/paulhodel/jsuites
     *
     * @author: Paul Hodel <paul.hodel@gmail.com>
     * @description: Modal
     */
    jSuites.modal = (function (el, options) {
        var obj = {};
        obj.options = {};
        // Default configuration
        var defaults = {
            url: null,
            onopen: null,
            onclose: null,
            closed: false,
            width: null,
            height: null,
            title: null,
        };
        // Loop through our object
        for (var property in defaults) {
            if (options && options.hasOwnProperty(property)) {
                obj.options[property] = options[property];
            } else {
                obj.options[property] = defaults[property];
            }
        }
        el.classList.add('jmodal');
        if (obj.options.title) {
            el.setAttribute('title', obj.options.title);
        }
        if (obj.options.width) {
            el.style.width = obj.options.width;
        }
        if (obj.options.height) {
            el.style.height = obj.options.height;
        }
        var container = document.createElement('div');
        for (var i = 0; i < el.children.length; i++) {
            container.appendChild(el.children[i]);
        }
        el.appendChild(container);
        // Title
        if (!el.getAttribute('title')) {
            el.classList.add('no-title');
        }
        obj.open = function () {
            el.style.display = 'block';
            if (typeof (obj.options.onopen) == 'function') {
                obj.options.onopen(el);
            }
            // Backdrop
            document.body.appendChild(jSuites.backdrop);
            // Current
            jSuites.modal.current = el;
        }
        obj.isOpen = function () {
            return el.style.display != 'none' ? true : false;
        }
        obj.close = function () {
            el.style.display = 'none';
            if (typeof (obj.options.onclose) == 'function') {
                obj.options.onclose(el);
            }
            // Backdrop
            jSuites.backdrop.remove();
            // Current
            jSuites.modal.current = null;
        }
        if (!jSuites.modal.hasEvents) {
            jSuites.modal.current = el;
            document.addEventListener('mousedown', jSuites.modal.mouseDownControls);
            document.addEventListener('mousemove', jSuites.modal.mouseMoveControls);
            document.addEventListener('mouseup', jSuites.modal.mouseUpControls);
            jSuites.modal.hasEvents = true;
        }
        if (obj.options.url) {
            jSuites.ajax({
                url: obj.options.url,
                method: 'GET',
                success: function (data) {
                    container.innerHTML = data;
                    if (!obj.options.closed) {
                        obj.open();
                    }
                }
            });
        } else {
            if (!obj.options.closed) {
                obj.open();
            }
        }
        // Keep object available from the node
        el.modal = obj;
        return obj;
    });
    jSuites.modal.current = null;
    jSuites.modal.position = null;
    jSuites.modal.mouseUpControls = function (e) {
        if (jSuites.modal.current) {
            jSuites.modal.current.style.cursor = 'auto';
        }
        jSuites.modal.position = null;
    }
    jSuites.modal.mouseMoveControls = function (e) {
        if (jSuites.modal.current && jSuites.modal.position) {
            if (e.which == 1 || e.which == 3) {
                var position = jSuites.modal.position;
                jSuites.modal.current.style.top = (position[1] + (e.clientY - position[3]) + (position[5] / 2)) + 'px';
                jSuites.modal.current.style.left = (position[0] + (e.clientX - position[2]) + (position[4] / 2)) + 'px';
                jSuites.modal.current.style.cursor = 'move';
            } else {
                jSuites.modal.current.style.cursor = 'auto';
            }
        }
    }
    jSuites.modal.mouseDownControls = function (e) {
        jSuites.modal.position = [];
        if (e.target.classList.contains('jmodal')) {
            setTimeout(function () {
                var rect = e.target.getBoundingClientRect();
                if (rect.width - (e.clientX - rect.left) < 50 && e.clientY - rect.top < 50) {
                    e.target.modal.close();
                } else {
                    if (e.target.getAttribute('title') && e.clientY - rect.top < 50) {
                        if (document.selection) {
                            document.selection.empty();
                        } else if (window.getSelection) {
                            window.getSelection().removeAllRanges();
                        }
                        jSuites.modal.position = [
                            rect.left,
                            rect.top,
                            e.clientX,
                            e.clientY,
                            rect.width,
                            rect.height,
                        ];
                    }
                }
            }, 100);
        }
    }
    jSuites.notification = (function (options) {
        var obj = {};
        obj.options = {};
        // Default configuration
        var defaults = {
            icon: null,
            name: null,
            date: null,
            title: null,
            message: null,
            timeout: 4000,
            autoHide: true,
            closeable: true,
        };
        // Loop through our object
        for (var property in defaults) {
            if (options && options.hasOwnProperty(property)) {
                obj.options[property] = options[property];
            } else {
                obj.options[property] = defaults[property];
            }
        }
        var notification = document.createElement('div');
        notification.className = 'jnotification';
        var notificationContainer = document.createElement('div');
        notificationContainer.className = 'jnotification-container';
        notification.appendChild(notificationContainer);
        var notificationHeader = document.createElement('div');
        notificationHeader.className = 'jnotification-header';
        notificationContainer.appendChild(notificationHeader);
        var notificationImage = document.createElement('div');
        notificationImage.className = 'jnotification-image';
        notificationHeader.appendChild(notificationImage);
        if (obj.options.icon) {
            var notificationIcon = document.createElement('img');
            notificationIcon.src = obj.options.icon;
            notificationImage.appendChild(notificationIcon);
        }
        var notificationName = document.createElement('div');
        notificationName.className = 'jnotification-name';
        notificationHeader.appendChild(notificationName);
        if (obj.options.name) {
            notificationName.innerHTML = obj.options.name;
        } else {
            notificationName.innerHTML = 'Notification';
        }
        if (obj.options.closeable == true) {
            var notificationClose = document.createElement('div');
            notificationClose.className = 'jnotification-close';
            notificationClose.onclick = function () {
                obj.hide();
            }
            notificationHeader.appendChild(notificationClose);
        }
        var notificationDate = document.createElement('div');
        notificationDate.className = 'jnotification-date';
        notificationHeader.appendChild(notificationDate);
        var notificationContent = document.createElement('div');
        notificationContent.className = 'jnotification-content';
        notificationContainer.appendChild(notificationContent);
        if (obj.options.title) {
            var notificationTitle = document.createElement('div');
            notificationTitle.className = 'jnotification-title';
            notificationTitle.innerHTML = obj.options.title;
            notificationContent.appendChild(notificationTitle);
        }
        var notificationMessage = document.createElement('div');
        notificationMessage.className = 'jnotification-message';
        notificationMessage.innerHTML = obj.options.message;
        notificationContent.appendChild(notificationMessage);
        obj.show = function () {
            document.body.appendChild(notification);
            if (jSuites.getWindowWidth() > 800) {
                jSuites.fadeIn(notification);
            } else {
                jSuites.slideTop(notification, 1);
            }
        }
        obj.hide = function () {
            if (jSuites.getWindowWidth() > 800) {
                jSuites.fadeOut(notification, function () {
                    notification.parentNode.removeChild(notification);
                });
            } else {
                jSuites.slideTop(notification, 0, function () {
                    notification.parentNode.removeChild(notification);
                });
            }
        };
        obj.show();
        if (obj.options.autoHide == true) {
            setTimeout(function () {
                obj.hide();
            }, obj.options.timeout);
        }
        if (jSuites.getWindowWidth() < 800) {
            notification.addEventListener("swipeup", function (e) {
                obj.hide();
                e.preventDefault();
                e.stopPropagation();
            });
        }
        return obj;
    });
    jSuites.rating = (function (el, options) {
        var obj = {};
        obj.options = {};
        // Default configuration
        var defaults = {
            number: 5,
            value: 0,
            tooltip: ['Very bad', 'Bad', 'Average', 'Good', 'Very good'],
            onchange: null,
        };
        // Loop through the initial configuration
        for (var property in defaults) {
            if (options && options.hasOwnProperty(property)) {
                obj.options[property] = options[property];
            } else {
                obj.options[property] = defaults[property];
            }
        }
        // Class
        el.classList.add('jrating');
        // Add elements
        for (var i = 0; i < obj.options.number; i++) {
            var div = document.createElement('div');
            div.setAttribute('data-index', (i + 1))
            div.setAttribute('title', obj.options.tooltip[i])
            el.appendChild(div);
        }
        // Set value
        obj.setValue = function (index) {
            for (var i = 0; i < obj.options.number; i++) {
                if (i < index) {
                    el.children[i].classList.add('jrating-selected');
                } else {
                    el.children[i].classList.remove('jrating-selected');
                }
            }
            obj.options.value = index;
            if (typeof (obj.options.onchange) == 'function') {
                obj.options.onchange(el, index);
            }
        }
        obj.getValue = function () {
            return obj.options.value;
        }
        if (obj.options.value) {
            for (var i = 0; i < obj.options.number; i++) {
                if (i < obj.options.value) {
                    el.children[i].classList.add('jrating-selected');
                }
            }
        }
        // Events
        el.addEventListener("click", function (e) {
            var index = e.target.getAttribute('data-index');
            if (index == obj.options.value) {
                obj.setValue(0);
            } else {
                obj.setValue(index);
            }
        });
        el.addEventListener("mouseover", function (e) {
            var index = e.target.getAttribute('data-index');
            for (var i = 0; i < obj.options.number; i++) {
                if (i < index) {
                    el.children[i].classList.add('jrating-over');
                } else {
                    el.children[i].classList.remove('jrating-over');
                }
            }
        });
        el.addEventListener("mouseout", function (e) {
            for (var i = 0; i < obj.options.number; i++) {
                el.children[i].classList.remove('jrating-over');
            }
        });
        el.rating = obj;
        return obj;
    });
    /**
     * (c) Image slider
     * https://github.com/paulhodel/jtools
     *
     * @author: Paul Hodel <paul.hodel@gmail.com>
     * @description: Image Slider
     */
    jSuites.slider = (function (el, options) {
        var obj = {};
        obj.options = {};
        obj.currentImage = null;
        if (options) {
            obj.options = options;
        }
        // Items
        obj.options.items = [];
        if (!el.classList.contains('jslider')) {
            el.classList.add('jslider');
            // Create container
            var container = document.createElement('div');
            container.className = 'jslider-container';
            // Move children inside
            if (el.children.length > 0) {
                // Keep children items
                for (var i = 0; i < el.children.length; i++) {
                    obj.options.items.push(el.children[i]);
                }
            }
            if (obj.options.items.length > 0) {
                for (var i = 0; i < obj.options.items.length; i++) {
                    obj.options.items[i].classList.add('jfile');
                    var index = obj.options.items[i].src.lastIndexOf('/');
                    if (index < 0) {
                        obj.options.items[i].setAttribute('data-name', obj.options.items[i].src);
                    } else {
                        obj.options.items[i].setAttribute('data-name', obj.options.items[i].src.substr(index + 1));
                    }
                    var index = obj.options.items[i].src.lastIndexOf('/');
                    container.appendChild(obj.options.items[i]);
                }
            }
            el.appendChild(container);
            // Add close buttom
            var close = document.createElement('div');
            close.className = 'jslider-close';
            close.innerHTML = '';
            close.onclick = function () {
                obj.close();
            }
            el.appendChild(close);
        } else {
            var container = el.querySelector('slider-container');
        }
        obj.show = function (target) {
            if (!target) {
                var target = container.children[0];
            }
            if (!container.classList.contains('jslider-preview')) {
                container.classList.add('jslider-preview');
                close.style.display = 'block';
            }
            // Hide all images
            for (var i = 0; i < container.children.length; i++) {
                container.children[i].style.display = 'none';
            }
            // Show clicked only
            target.style.display = 'block';
            // Is there any previous
            if (target.previousSibling) {
                container.classList.add('jslider-left');
            } else {
                container.classList.remove('jslider-left');
            }
            // Is there any next
            if (target.nextSibling) {
                container.classList.add('jslider-right');
            } else {
                container.classList.remove('jslider-right');
            }
            obj.currentImage = target;
        }
        obj.open = function () {
            obj.show();
            // Event
            if (typeof (obj.options.onopen) == 'function') {
                obj.options.onopen(el);
            }
        }
        obj.close = function () {
            container.classList.remove('jslider-preview');
            container.classList.remove('jslider-left');
            container.classList.remove('jslider-right');
            for (var i = 0; i < container.children.length; i++) {
                container.children[i].style.display = '';
            }
            close.style.display = '';
            obj.currentImage = null;
            // Event
            if (typeof (obj.options.onclose) == 'function') {
                obj.options.onclose(el);
            }
        }
        obj.reset = function () {
            container.innerHTML = '';
        }
        obj.addFile = function (v, ignoreEvents) {
            var img = document.createElement('img');
            img.setAttribute('data-lastmodified', v.lastmodified);
            img.setAttribute('data-name', v.name);
            img.setAttribute('data-size', v.size);
            img.setAttribute('data-extension', v.extension);
            img.setAttribute('data-cover', v.cover);
            img.setAttribute('src', v.file);
            img.className = 'jfile';
            container.appendChild(img);
            obj.options.items.push(img);
            // Onchange
            if (!ignoreEvents) {
                if (typeof (obj.options.onchange) == 'function') {
                    obj.options.onchange(el, v);
                }
            }
        }
        obj.addFiles = function (files) {
            for (var i = 0; i < files.length; i++) {
                obj.addFile(files[i]);
            }
        }
        obj.next = function () {
            if (obj.currentImage.nextSibling) {
                obj.show(obj.currentImage.nextSibling);
            }
        }
        obj.prev = function () {
            if (obj.currentImage.previousSibling) {
                obj.show(obj.currentImage.previousSibling);
            }
        }
        obj.getData = function () {
            return jSuites.getFiles(container);
        }
        // Append data
        if (obj.options.data && obj.options.data.length) {
            for (var i = 0; i < obj.options.data.length; i++) {
                if (obj.options.data[i]) {
                    obj.addFile(obj.options.data[i]);
                }
            }
        }
        // Allow insert
        if (obj.options.allowAttachment) {
            var attachmentInput = document.createElement('input');
            attachmentInput.type = 'file';
            attachmentInput.className = 'slider-attachment';
            attachmentInput.setAttribute('accept', 'image/*');
            attachmentInput.style.display = 'none';
            attachmentInput.onchange = function () {
                var reader = [];
                for (var i = 0; i < this.files.length; i++) {
                    var type = this.files[i].type.split('/');
                    if (type[0] == 'image') {
                        var extension = this.files[i].name;
                        extension = extension.split('.');
                        extension = extension[extension.length - 1];
                        var file = {
                            size: this.files[i].size,
                            name: this.files[i].name,
                            extension: extension,
                            cover: 0,
                            lastmodified: this.files[i].lastModified,
                        }
                        reader[i] = new FileReader();
                        reader[i].addEventListener("load", function (e) {
                            file.file = e.target.result;
                            obj.addFile(file);
                        }, false);
                        reader[i].readAsDataURL(this.files[i]);
                    } else {
                        alert('The extension is not allowed');
                    }
                };
            }
            var attachmentIcon = document.createElement('i');
            attachmentIcon.innerHTML = 'attachment';
            attachmentIcon.className = 'jslider-attach material-icons';
            attachmentIcon.onclick = function () {
                jSuites.click(attachmentInput);
            }
            el.appendChild(attachmentInput);
            el.appendChild(attachmentIcon);
        }
        // Push to refresh
        var longTouchTimer = null;
        var mouseDown = function (e) {
            if (e.target.tagName == 'IMG') {
                // Remove
                var targetImage = e.target;
                longTouchTimer = setTimeout(function () {
                    if (e.target.src.substr(0, 4) == 'data') {
                        e.target.remove();
                    } else {
                        if (e.target.classList.contains('jremove')) {
                            e.target.classList.remove('jremove');
                        } else {
                            e.target.classList.add('jremove');
                        }
                    }
                    // Onchange
                    if (typeof (obj.options.onchange) == 'function') {
                        obj.options.onchange(el, e.target);
                    }
                }, 1000);
            }
        }
        var mouseUp = function (e) {
            if (longTouchTimer) {
                clearTimeout(longTouchTimer);
            }
            // Open slider
            if (e.target.tagName == 'IMG') {
                if (!e.target.classList.contains('jremove')) {
                    obj.show(e.target);
                }
            } else {
                // Arrow controls
                if (e.target.clientWidth - e.offsetX < 40) {
                    // Show next image
                    obj.next();
                } else if (e.offsetX < 40) {
                    // Show previous image
                    obj.prev();
                }
            }
        }
        container.addEventListener('mousedown', mouseDown);
        container.addEventListener('touchstart', mouseDown);
        container.addEventListener('mouseup', mouseUp);
        container.addEventListener('touchend', mouseUp);
        // Add global events
        el.addEventListener("swipeleft", function (e) {
            obj.next();
            e.preventDefault();
            e.stopPropagation();
        });
        el.addEventListener("swiperight", function (e) {
            obj.prev();
            e.preventDefault();
            e.stopPropagation();
        });
        el.slider = obj;
        return obj;
    });
    /**
     * (c) jTools v1.0.1 - Element sorting
     * https://github.com/paulhodel/jtools
     *
     * @author: Paul Hodel <paul.hodel@gmail.com>
     * @description: Element drag and drop sorting
     */
    jSuites.sorting = (function (el, options) {
        el.classList.add('jsorting');
        el.addEventListener('dragstart', function (e) {
            e.target.classList.add('dragging');
        });
        el.addEventListener('dragover', function (e) {
            e.preventDefault();
            if (e.target.clientHeight / 2 > e.offsetY) {
                e.path[0].style.borderTop = '1px dotted #ccc';
                e.path[0].style.borderBottom = '';
            } else {
                e.path[0].style.borderTop = '';
                e.path[0].style.borderBottom = '1px dotted #ccc';
            }
        });
        el.addEventListener('dragleave', function (e) {
            e.path[0].style.borderTop = '';
            e.path[0].style.borderBottom = '';
        });
        el.addEventListener('dragend', function (e) {
            e.path[1].querySelector('.dragging').classList.remove('dragging');
        });
        el.addEventListener('drop', function (e) {
            var element = e.path[1].querySelector('.dragging');
            if (e.target.clientHeight / 2 > e.offsetY) {
                e.path[1].insertBefore(element, e.path[0]);
            } else {
                e.path[1].insertBefore(element, e.path[0].nextSibling);
            }
            e.path[0].style.borderTop = '';
            e.path[0].style.borderBottom = '';
        });
        for (var i = 0; i < el.children.length; i++) {
            el.children[i].setAttribute('draggable', 'true');
        };
        return el;
    });
    jSuites.tabs = (function (el, options) {
        var obj = {};
        obj.options = {};
        // Default configuration
        var defaults = {
            onchange: null,
        };
        // Loop through the initial configuration
        for (var property in defaults) {
            if (options && options.hasOwnProperty(property)) {
                obj.options[property] = options[property];
            } else {
                obj.options[property] = defaults[property];
            }
        }
        // Class
        el.classList.add('jtabs');
        // Elements
        var headers = el.children[0];
        var content = el.children[1];
        headers.classList.add('jtabs-headers');
        content.classList.add('jtabs-content');
        // Set value
        obj.open = function (index) {
            for (var i = 0; i < headers.children.length; i++) {
                headers.children[i].classList.remove('jtabs-selected');
                if (content.children[i]) {
                    content.children[i].classList.remove('jtabs-selected');
                }
            }
            headers.children[index].classList.add('jtabs-selected');
            if (content.children[index]) {
                content.children[index].classList.add('jtabs-selected');
            }
        }
        // Events
        headers.addEventListener("click", function (e) {
            var index = Array.prototype.indexOf.call(headers.children, e.target);
            if (index >= 0) {
                obj.open(index);
            }
        });
        obj.open(0);
        el.tabs = obj;
        return obj;
    });
    jSuites.tracker = (function (el, options) {
        var obj = {};
        obj.options = {};
        // Default configuration
        var defaults = {
            url: null,
            message: 'Are you sure? There are unsaved information in your form',
            ignore: false,
            currentHash: null,
            submitButton: null,
            onload: null,
            onbeforesave: null,
            onsave: null,
        };
        // Loop through our object
        for (var property in defaults) {
            if (options && options.hasOwnProperty(property)) {
                obj.options[property] = options[property];
            } else {
                obj.options[property] = defaults[property];
            }
        }
        obj.setUrl = function (url) {
            obj.options.url = url;
        }
        obj.load = function () {
            jSuites.ajax({
                url: obj.options.url,
                method: 'GET',
                dataType: 'json',
                success: function (data) {
                    var elements = el.querySelectorAll("input, select, textarea");
                    for (var i = 0; i < elements.length; i++) {
                        var name = elements[i].getAttribute('name');
                        if (data[name]) {
                            elements[i].value = data[name];
                        }
                    }
                    if (typeof (obj.options.onload) == 'function') {
                        obj.options.onload(el, data);
                    }
                }
            });
        }
        obj.save = function () {
            var test = obj.validate();
            if (test) {
                jSuites.alert(test);
            } else {
                var data = obj.getElements(true);
                if (typeof (obj.options.onbeforesave) == 'function') {
                    var data = obj.options.onbeforesave(el, data);
                    if (data === false) {
                        console.log('Onbeforesave returned false');
                        return;
                    }
                }
                jSuites.ajax({
                    url: obj.options.url,
                    method: 'POST',
                    dataType: 'json',
                    data: data,
                    success: function (result) {
                        jSuites.alert(result.message);
                        if (typeof (obj.options.onsave) == 'function') {
                            var data = obj.options.onsave(el, result);
                        }
                        obj.reset();
                    }
                });
            }
        }
        obj.validateElement = function (element) {
            var emailChecker = function (data) {
                var pattern = new RegExp(/^([\w-\.]+@([\w-]+\.)+[\w-]{2,4})?$/);
                return pattern.test(data) ? true : false;
            }
            var passwordChecker = function (data) {
                return (data.length > 5) ? true : false;
            }
            var addError = function (element) {
                // Add error in the element
                element.classList.add('error');
                // Submit button
                if (obj.options.submitButton) {
                    obj.options.submitButton.setAttribute('disabled', true);
                }
                // Return error message
                return element.getAttribute('data-error') || 'There is an error in the form';
            }
            var delError = function (element) {
                var error = false;
                // Remove class from this element
                element.classList.remove('error');
                // Get elements in the form
                var elements = el.querySelectorAll("input, select, textarea");
                // Run all elements 
                for (var i = 0; i < elements.length; i++) {
                    if (elements[i].getAttribute('data-validation')) {
                        if (elements[i].classList.contains('error')) {
                            error = true;
                        }
                    }
                }
                if (obj.options.submitButton) {
                    if (error) {
                        obj.options.submitButton.setAttribute('disabled', true);
                    } else {
                        obj.options.submitButton.removeAttribute('disabled');
                    }
                }
            }
            // Blank
            var test = '';
            if (!element.value) {
                test = addError(element);
            } else if (element.getAttribute('data-email') && !emailChecker(element.value)) {
                test = addError(element);
            } else if (element.getAttribute('data-password') && !emailChecker(element.value)) {
                test = addError(element);
            } else {
                if (element.classList.contains('error')) {
                    delError(element);
                }
            }
            return test;
        }
        // Run form validation
        obj.validate = function () {
            var test = '';
            // Get elements in the form
            var elements = el.querySelectorAll("input, select, textarea");
            // Run all elements 
            for (var i = 0; i < elements.length; i++) {
                if (elements[i].getAttribute('data-validation')) {
                    if (test) {
                        test += "<br>\r\n";
                    }
                    test += obj.validateElement(elements[i]);
                }
            }
            return test;
        }
        // Check the form
        obj.getError = function () {
            // Validation
            return obj.validation() ? true : false;
        }
        // Return the form hash
        obj.setHash = function () {
            return obj.getHash(obj.getElements());
        }
        // Get the form hash
        obj.getHash = function (str) {
            var hash = 0,
                i, chr;
            if (str.length === 0) {
                return hash;
            } else {
                for (i = 0; i < str.length; i++) {
                    chr = str.charCodeAt(i);
                    hash = ((hash << 5) - hash) + chr;
                    hash |= 0;
                }
            }
            return hash;
        }
        // Is there any change in the form since start tracking?
        obj.isChanged = function () {
            var hash = obj.setHash();
            return (obj.options.currentHash != hash);
        }
        // Restart tracking
        obj.resetTracker = function () {
            obj.options.currentHash = obj.setHash();
            obj.options.ignore = false;
        }
        obj.reset = function () {
            obj.options.currentHash = obj.setHash();
            obj.options.ignore = false;
        }
        // Ignore flag
        obj.setIgnore = function (ignoreFlag) {
            obj.options.ignore = ignoreFlag ? true : false;
        }
        // Get form elements
        obj.getElements = function (asArray) {
            var data = {};
            var elements = el.querySelectorAll("input, select, textarea");
            for (var i = 0; i < elements.length; i++) {
                var element = elements[i];
                var name = element.name;
                var value = element.value;
                if (name) {
                    data[name] = value;
                }
            }
            return asArray == true ? data : JSON.stringify(data);
        }
        // Start tracking in one second
        setTimeout(function () {
            obj.options.currentHash = obj.setHash();
        }, 1000);
        // Alert
        window.addEventListener("beforeunload", function (e) {
            if (obj.isChanged() && obj.options.ignore == false) {
                var confirmationMessage = obj.options.message ? obj.options.message : "\o/";
                if (confirmationMessage) {
                    if (typeof e == 'undefined') {
                        e = window.event;
                    }
                    if (e) {
                        e.returnValue = confirmationMessage;
                    }
                    return confirmationMessage;
                } else {
                    return void(0);
                }
            }
        });
        // Validations
        el.addEventListener("keyup", function (e) {
            if (e.target.getAttribute('data-validation')) {
                obj.validateElement(e.target);
            }
        });
        el.tracker = obj;
        return obj;
    });
    return jSuites;
    // })));
});