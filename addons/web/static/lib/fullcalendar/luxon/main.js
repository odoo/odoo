/*!
FullCalendar Luxon Plugin v4.4.0
Docs & License: https://fullcalendar.io/
(c) 2019 Adam Shaw
*/

(function (global, factory) {
    typeof exports === 'object' && typeof module !== 'undefined' ? factory(exports, require('luxon'), require('@fullcalendar/core')) :
    typeof define === 'function' && define.amd ? define(['exports', 'luxon', '@fullcalendar/core'], factory) :
    (global = global || self, factory(global.FullCalendarLuxon = {}, global.luxon, global.FullCalendar));
}(this, function (exports, luxon, core) { 'use strict';

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
    /* global Reflect, Promise */

    var extendStatics = function(d, b) {
        extendStatics = Object.setPrototypeOf ||
            ({ __proto__: [] } instanceof Array && function (d, b) { d.__proto__ = b; }) ||
            function (d, b) { for (var p in b) if (b.hasOwnProperty(p)) d[p] = b[p]; };
        return extendStatics(d, b);
    };

    function __extends(d, b) {
        extendStatics(d, b);
        function __() { this.constructor = d; }
        d.prototype = b === null ? Object.create(b) : (__.prototype = b.prototype, new __());
    }

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

    function toDateTime(date, calendar) {
        if (!(calendar instanceof core.Calendar)) {
            throw new Error('must supply a Calendar instance');
        }
        return luxon.DateTime.fromJSDate(date, {
            zone: calendar.dateEnv.timeZone,
            locale: calendar.dateEnv.locale.codes[0]
        });
    }
    function toDuration(duration, calendar) {
        if (!(calendar instanceof core.Calendar)) {
            throw new Error('must supply a Calendar instance');
        }
        return luxon.Duration.fromObject(__assign({}, duration), { locale: calendar.dateEnv.locale.codes[0] });
    }
    var LuxonNamedTimeZone = /** @class */ (function (_super) {
        __extends(LuxonNamedTimeZone, _super);
        function LuxonNamedTimeZone() {
            return _super !== null && _super.apply(this, arguments) || this;
        }
        LuxonNamedTimeZone.prototype.offsetForArray = function (a) {
            return arrayToLuxon(a, this.timeZoneName).offset;
        };
        LuxonNamedTimeZone.prototype.timestampToArray = function (ms) {
            return luxonToArray(luxon.DateTime.fromMillis(ms, {
                zone: this.timeZoneName
            }));
        };
        return LuxonNamedTimeZone;
    }(core.NamedTimeZoneImpl));
    function formatWithCmdStr(cmdStr, arg) {
        var cmd = parseCmdStr(cmdStr);
        if (arg.end) {
            var start = arrayToLuxon(arg.start.array, arg.timeZone, arg.localeCodes[0]);
            var end = arrayToLuxon(arg.end.array, arg.timeZone, arg.localeCodes[0]);
            return formatRange(cmd, start.toFormat.bind(start), end.toFormat.bind(end), arg.separator);
        }
        return arrayToLuxon(arg.date.array, arg.timeZone, arg.localeCodes[0]).toFormat(cmd.whole);
    }
    var main = core.createPlugin({
        cmdFormatter: formatWithCmdStr,
        namedTimeZonedImpl: LuxonNamedTimeZone
    });
    function luxonToArray(datetime) {
        return [
            datetime.year,
            datetime.month - 1,
            datetime.day,
            datetime.hour,
            datetime.minute,
            datetime.second,
            datetime.millisecond
        ];
    }
    function arrayToLuxon(arr, timeZone, locale) {
        return luxon.DateTime.fromObject({
            year: arr[0],
            month: arr[1] + 1,
            day: arr[2],
            hour: arr[3],
            minute: arr[4],
            second: arr[5],
            millisecond: arr[6]
        }, {
            zone: timeZone,
            locale: locale,
        });
    }
    function parseCmdStr(cmdStr) {
        var parts = cmdStr.match(/^(.*?)\{(.*)\}(.*)$/); // TODO: lookbehinds for escape characters
        if (parts) {
            var middle = parseCmdStr(parts[2]);
            return {
                head: parts[1],
                middle: middle,
                tail: parts[3],
                whole: parts[1] + middle.whole + parts[3]
            };
        }
        else {
            return {
                head: null,
                middle: null,
                tail: null,
                whole: cmdStr
            };
        }
    }
    function formatRange(cmd, formatStart, formatEnd, separator) {
        if (cmd.middle) {
            var startHead = formatStart(cmd.head);
            var startMiddle = formatRange(cmd.middle, formatStart, formatEnd, separator);
            var startTail = formatStart(cmd.tail);
            var endHead = formatEnd(cmd.head);
            var endMiddle = formatRange(cmd.middle, formatStart, formatEnd, separator);
            var endTail = formatEnd(cmd.tail);
            if (startHead === endHead && startTail === endTail) {
                return startHead +
                    (startMiddle === endMiddle ? startMiddle : startMiddle + separator + endMiddle) +
                    startTail;
            }
        }
        var startWhole = formatStart(cmd.whole);
        var endWhole = formatEnd(cmd.whole);
        if (startWhole === endWhole) {
            return startWhole;
        }
        else {
            return startWhole + separator + endWhole;
        }
    }

    exports.default = main;
    exports.toDateTime = toDateTime;
    exports.toDuration = toDuration;

    Object.defineProperty(exports, '__esModule', { value: true });

}));
