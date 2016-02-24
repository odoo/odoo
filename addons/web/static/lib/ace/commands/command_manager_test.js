/* ***** BEGIN LICENSE BLOCK *****
 * Distributed under the BSD license:
 *
 * Copyright (c) 2010, Ajax.org B.V.
 * All rights reserved.
 * 
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *     * Redistributions of source code must retain the above copyright
 *       notice, this list of conditions and the following disclaimer.
 *     * Redistributions in binary form must reproduce the above copyright
 *       notice, this list of conditions and the following disclaimer in the
 *       documentation and/or other materials provided with the distribution.
 *     * Neither the name of Ajax.org B.V. nor the
 *       names of its contributors may be used to endorse or promote products
 *       derived from this software without specific prior written permission.
 * 
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
 * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL AJAX.ORG B.V. BE LIABLE FOR ANY
 * DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 * ***** END LICENSE BLOCK ***** */

if (typeof process !== "undefined") {
    require("amd-loader");
}

define(function(require, exports, module) {
"use strict";

var CommandManager = require("./command_manager").CommandManager;
var keys = require("../lib/keys");
var assert = require("../test/assertions");

module.exports = {

    setUp: function() {
        this.command = {
            name: "gotoline",
            bindKey: {
                mac: "Command-L",
                win: "Ctrl-L"
            },
            called: false,
            exec: function(editor) { this.called = true; }
        };

        this.cm = new CommandManager("mac", [this.command]);
    },

    "test: register command": function() {
        this.cm.exec("gotoline");
        assert.ok(this.command.called);
    },

    "test: mac hotkeys": function() {
        var command = this.cm.findKeyCommand(keys.KEY_MODS.command, "l");
        assert.equal(command, this.command);

        var command = this.cm.findKeyCommand(keys.KEY_MODS.ctrl, "l");
        assert.equal(command, undefined);
    },

    "test: win hotkeys": function() {
        var cm = new CommandManager("win", [this.command]);

        var command = cm.findKeyCommand(keys.KEY_MODS.command, "l");
        assert.equal(command, undefined);

        var command = cm.findKeyCommand(keys.KEY_MODS.ctrl, "l");
        assert.equal(command, this.command);
    },

    "test: remove command by object": function() {
        this.cm.removeCommand(this.command);

        this.cm.exec("gotoline");
        assert.ok(!this.command.called);

        var command = this.cm.findKeyCommand(keys.KEY_MODS.command, "l");
        assert.equal(command, null);
    },

    "test: remove command by name": function() {
        this.cm.removeCommand("gotoline");

        this.cm.exec("gotoline");
        assert.ok(!this.command.called);

        var command = this.cm.findKeyCommand(keys.KEY_MODS.command, "l");
        assert.equal(command, null);
    },

    "test: adding a new command with the same name as an existing one should remove the old one first": function() {
        var command = {
            name: "gotoline",
            bindKey: {
                mac: "Command-L",
                win: "Ctrl-L"
            },
            called: false,
            exec: function(editor) { this.called = true; }
        };
        this.cm.addCommand(command);

        this.cm.exec("gotoline");
        assert.ok(command.called);
        assert.ok(!this.command.called);

        assert.equal(this.cm.findKeyCommand(keys.KEY_MODS.command, "l"), command);
    },

    "test: adding commands and recording a macro": function() {
        var called = "";
        this.cm.addCommands({
            togglerecording: function(editor) {
                editor.cm.toggleRecording(editor);
            },
            replay: function(editor) {
                editor.cm.replay();
            },
            cm1: function(editor, arg) {
                called += "1" + (arg || "");
            },
            cm2: function(editor) {
                called += "2";
            }
        });
        
        
        var statusUpdateEmitted = false;
        this._emit = function() {statusUpdateEmitted = true};

        this.cm.exec("togglerecording", this);
        assert.ok(this.cm.recording);
        assert.ok(statusUpdateEmitted);

        this.cm.exec("cm1", this, "-");
        this.cm.exec("cm2");
        this.cm.exec("replay", this);
        assert.ok(!this.cm.recording);
        assert.equal(called, "1-2");

        called = "";
        this.cm.exec("replay", this);
        assert.equal(called, "1-2");
    },

    "test: bindkeys": function() {
        this.cm.bindKeys({
            "Ctrl-L|Command-C": "cm1",
            "Ctrl-R": "cm2"
        });

        var command = this.cm.findKeyCommand(keys.KEY_MODS.command, "c");
        assert.equal(command, "cm1");

        var command = this.cm.findKeyCommand(keys.KEY_MODS.ctrl, "r");
        assert.equal(command, "cm2");

        this.cm.bindKeys({
            "Ctrl-R": null
        });

        var command = this.cm.findKeyCommand(keys.KEY_MODS.ctrl, "r");
        assert.equal(command, null);
    },

    "test: binding keys without modifiers": function() {
        this.cm.bindKeys({
            "R": "cm1",
            "Shift-r": "cm2",
            "Return": "cm4",
            "Enter": "cm3"
        });

        var command = this.cm.findKeyCommand(-1, "r");
        assert.equal(command, "cm1");

        var command = this.cm.findKeyCommand(-1, "R");
        assert.equal(command, "cm2");

        var command = this.cm.findKeyCommand(0, "return");
        assert.equal(command + "", ["cm4", "cm3"] + "");
    }
};

});

if (typeof module !== "undefined" && module === require.main) {
    require("asyncjs").test.testcase(module.exports).exec();
}
