/*!
FullCalendar Google Calendar Plugin v4.4.0
Docs & License: https://fullcalendar.io/
(c) 2019 Adam Shaw
*/

(function (global, factory) {
    typeof exports === 'object' && typeof module !== 'undefined' ? factory(exports, require('@fullcalendar/core')) :
    typeof define === 'function' && define.amd ? define(['exports', '@fullcalendar/core'], factory) :
    (global = global || self, factory(global.FullCalendarGoogleCalendar = {}, global.FullCalendar));
}(this, function (exports, core) { 'use strict';

    /*! *****************************************************************************
    Copyright (c) Microsoft Corporation. All rights reserved.
    Licensed under the Apache License, Version 2.0 (the "License"); you may not use
    this file except in compliance with the License. You may obtain a copy of the
    License at http://www.apache.org/licenses/LICENSE-2.0

    THIS CODE IS PROVIDED ON AN *AS IS* BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
    KIND, EITHER EXPRESS OR IMPLIED, INCLUDING WITHOUT LIMITATION ANY IMPLIED
    WARRANTIES OR CONDITIONS OF TITLE, FITNESS FOR A PARTICULAR PURPOSE,
    MERCHANTABLITY OR NON-INFRINGEMENT.

    See the Apache Version 2.0 License for specific language governing permissions
    and limitations under the License.
    ***************************************************************************** */

    var __assign = function() {
        __assign = Object.assign || function __assign(t) {
            for (var s, i = 1, n = arguments.length; i < n; i++) {
                s = arguments[i];
                for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p)) t[p] = s[p];
            }
            return t;
        };
        return __assign.apply(this, arguments);
    };

    // TODO: expose somehow
    var API_BASE = 'https://www.googleapis.com/calendar/v3/calendars';
    var STANDARD_PROPS = {
        url: String,
        googleCalendarApiKey: String,
        googleCalendarId: String,
        googleCalendarApiBase: String,
        data: null
    };
    var eventSourceDef = {
        parseMeta: function (raw) {
            if (typeof raw === 'string') {
                raw = { url: raw };
            }
            if (typeof raw === 'object') {
                var standardProps = core.refineProps(raw, STANDARD_PROPS);
                if (!standardProps.googleCalendarId && standardProps.url) {
                    standardProps.googleCalendarId = parseGoogleCalendarId(standardProps.url);
                }
                delete standardProps.url;
                if (standardProps.googleCalendarId) {
                    return standardProps;
                }
            }
            return null;
        },
        fetch: function (arg, onSuccess, onFailure) {
            var calendar = arg.calendar;
            var meta = arg.eventSource.meta;
            var apiKey = meta.googleCalendarApiKey || calendar.opt('googleCalendarApiKey');
            if (!apiKey) {
                onFailure({
                    message: 'Specify a googleCalendarApiKey. See http://fullcalendar.io/docs/google_calendar/'
                });
            }
            else {
                var url = buildUrl(meta);
                var requestParams_1 = buildRequestParams(arg.range, apiKey, meta.data, calendar.dateEnv);
                core.requestJson('GET', url, requestParams_1, function (body, xhr) {
                    if (body.error) {
                        onFailure({
                            message: 'Google Calendar API: ' + body.error.message,
                            errors: body.error.errors,
                            xhr: xhr
                        });
                    }
                    else {
                        onSuccess({
                            rawEvents: gcalItemsToRawEventDefs(body.items, requestParams_1.timeZone),
                            xhr: xhr
                        });
                    }
                }, function (message, xhr) {
                    onFailure({ message: message, xhr: xhr });
                });
            }
        }
    };
    function parseGoogleCalendarId(url) {
        var match;
        // detect if the ID was specified as a single string.
        // will match calendars like "asdf1234@calendar.google.com" in addition to person email calendars.
        if (/^[^\/]+@([^\/\.]+\.)*(google|googlemail|gmail)\.com$/.test(url)) {
            return url;
        }
        else if ((match = /^https:\/\/www.googleapis.com\/calendar\/v3\/calendars\/([^\/]*)/.exec(url)) ||
            (match = /^https?:\/\/www.google.com\/calendar\/feeds\/([^\/]*)/.exec(url))) {
            return decodeURIComponent(match[1]);
        }
    }
    function buildUrl(meta) {
        var apiBase = meta.googleCalendarApiBase;
        if (!apiBase) {
            apiBase = API_BASE;
        }
        return apiBase + '/' + encodeURIComponent(meta.googleCalendarId) + '/events';
    }
    function buildRequestParams(range, apiKey, extraParams, dateEnv) {
        var params;
        var startStr;
        var endStr;
        if (dateEnv.canComputeOffset) {
            // strings will naturally have offsets, which GCal needs
            startStr = dateEnv.formatIso(range.start);
            endStr = dateEnv.formatIso(range.end);
        }
        else {
            // when timezone isn't known, we don't know what the UTC offset should be, so ask for +/- 1 day
            // from the UTC day-start to guarantee we're getting all the events
            // (start/end will be UTC-coerced dates, so toISOString is okay)
            startStr = core.addDays(range.start, -1).toISOString();
            endStr = core.addDays(range.end, 1).toISOString();
        }
        params = __assign({}, (extraParams || {}), { key: apiKey, timeMin: startStr, timeMax: endStr, singleEvents: true, maxResults: 9999 });
        if (dateEnv.timeZone !== 'local') {
            params.timeZone = dateEnv.timeZone;
        }
        return params;
    }
    function gcalItemsToRawEventDefs(items, gcalTimezone) {
        return items.map(function (item) {
            return gcalItemToRawEventDef(item, gcalTimezone);
        });
    }
    function gcalItemToRawEventDef(item, gcalTimezone) {
        var url = item.htmlLink || null;
        // make the URLs for each event show times in the correct timezone
        if (url && gcalTimezone) {
            url = injectQsComponent(url, 'ctz=' + gcalTimezone);
        }
        return {
            id: item.id,
            title: item.summary,
            start: item.start.dateTime || item.start.date,
            end: item.end.dateTime || item.end.date,
            url: url,
            location: item.location,
            description: item.description
        };
    }
    // Injects a string like "arg=value" into the querystring of a URL
    // TODO: move to a general util file?
    function injectQsComponent(url, component) {
        // inject it after the querystring but before the fragment
        return url.replace(/(\?.*?)?(#|$)/, function (whole, qs, hash) {
            return (qs ? qs + '&' : '?') + component + hash;
        });
    }
    var main = core.createPlugin({
        eventSourceDefs: [eventSourceDef]
    });

    exports.default = main;

    Object.defineProperty(exports, '__esModule', { value: true });

}));
