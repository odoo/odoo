/*!
FullCalendar Bootstrap Plugin v4.4.0
Docs & License: https://fullcalendar.io/
(c) 2019 Adam Shaw
*/

(function (global, factory) {
    typeof exports === 'object' && typeof module !== 'undefined' ? factory(exports, require('@fullcalendar/core')) :
    typeof define === 'function' && define.amd ? define(['exports', '@fullcalendar/core'], factory) :
    (global = global || self, factory(global.FullCalendarBootstrap = {}, global.FullCalendar));
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

    var BootstrapTheme = /** @class */ (function (_super) {
        __extends(BootstrapTheme, _super);
        function BootstrapTheme() {
            return _super !== null && _super.apply(this, arguments) || this;
        }
        return BootstrapTheme;
    }(core.Theme));
    BootstrapTheme.prototype.classes = {
        widget: 'fc-bootstrap',
        tableGrid: 'table-bordered',
        tableList: 'table',
        tableListHeading: 'table-active',
        buttonGroup: 'btn-group',
        button: 'btn btn-primary',
        buttonActive: 'active',
        today: 'alert alert-info',
        popover: 'card card-primary',
        popoverHeader: 'card-header',
        popoverContent: 'card-body',
        // day grid
        // for left/right border color when border is inset from edges (all-day in timeGrid view)
        // avoid `table` class b/c don't want margins/padding/structure. only border color.
        headerRow: 'table-bordered',
        dayRow: 'table-bordered',
        // list view
        listView: 'card card-primary'
    };
    BootstrapTheme.prototype.baseIconClass = 'fa';
    BootstrapTheme.prototype.iconClasses = {
        close: 'fa-times',
        prev: 'fa-chevron-left',
        next: 'fa-chevron-right',
        prevYear: 'fa-angle-double-left',
        nextYear: 'fa-angle-double-right'
    };
    BootstrapTheme.prototype.iconOverrideOption = 'bootstrapFontAwesome';
    BootstrapTheme.prototype.iconOverrideCustomButtonOption = 'bootstrapFontAwesome';
    BootstrapTheme.prototype.iconOverridePrefix = 'fa-';
    var main = core.createPlugin({
        themeClasses: {
            bootstrap: BootstrapTheme
        }
    });

    exports.BootstrapTheme = BootstrapTheme;
    exports.default = main;

    Object.defineProperty(exports, '__esModule', { value: true });

}));
