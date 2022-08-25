/*!
FullCalendar Moment Timezone Plugin v4.4.0
Docs & License: https://fullcalendar.io/
(c) 2019 Adam Shaw
*/

(function (global, factory) {
    typeof exports === 'object' && typeof module !== 'undefined' ? factory(exports, require('moment'), require('moment-timezone/builds/moment-timezone-with-data'), require('@fullcalendar/core')) :
    typeof define === 'function' && define.amd ? define(['exports', 'moment', 'moment-timezone/builds/moment-timezone-with-data', '@fullcalendar/core'], factory) :
    (global = global || self, factory(global.FullCalendarMomentTimezone = {}, global.moment, global.moment, global.FullCalendar));
}(this, function (exports, momentNs, momentTimezoneWithData, core) { 'use strict';

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

    var moment = momentNs; // the directly callable function
    var MomentNamedTimeZone = /** @class */ (function (_super) {
        __extends(MomentNamedTimeZone, _super);
        function MomentNamedTimeZone() {
            return _super !== null && _super.apply(this, arguments) || this;
        }
        MomentNamedTimeZone.prototype.offsetForArray = function (a) {
            return moment.tz(a, this.timeZoneName).utcOffset();
        };
        MomentNamedTimeZone.prototype.timestampToArray = function (ms) {
            return moment.tz(ms, this.timeZoneName).toArray();
        };
        return MomentNamedTimeZone;
    }(core.NamedTimeZoneImpl));
    var main = core.createPlugin({
        namedTimeZonedImpl: MomentNamedTimeZone
    });

    exports.default = main;

    Object.defineProperty(exports, '__esModule', { value: true });

}));
